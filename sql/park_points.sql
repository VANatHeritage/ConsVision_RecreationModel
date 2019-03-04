-- Associating local parks points and public lands

/*
TODO: rename pub_lands_final_2 to pub_lands_final. Original "new" polygons did not
retain multi-polygons that were maintatined across water. This resulted in a small
number of "new" polygons that are now combined back into original pub_lands_dissolve
polygons.

Script uses:
-- rec_source.local_parks
-- rec_source.pub_lands (for determining if points are associated with polygons already)
-- rec_source.pub_lands_dissolve (for combining with buffered, unassociated points into pub_lands_final)
*/

-- park_name, total_acres
select * from rec_source.local_parks limit 5; -- any subset of this????
select park_name from rec_source.local_parks where lower(park_name) like '%golf%';

-- QC check. Must be in county assigned and not have empty fips (geom missing)
-- also removes golf courses
alter table rec_source.local_parks add column use int default 1;
update rec_source.local_parks set use = 0 
where fips != fips_orig or fips is null
or lower(park_name) like '%golf%';

-- closest polygon within 5000m
create or replace view pt_poly_matches as
select distinct on (pt_id) * FROM
(
select a.objectid pt_id, a.park_name pt_name, a.total_acres pt_acre, 
b.objectid poly_id, b.maname poly_name, b.gisacre poly_acre,
b.gisacre - a.total_acres diff_acres, st_distance(a.geom, b.geom) dist_m, st_distance(a.geom, st_centroid(b.geom)) dist_m_cent, a.geom
from rec_source.local_parks a, rec_source.pub_lands b
where a.use = 1
and (st_dwithin(a.geom, b.geom, 5000) or st_dwithin(a.geom, st_centroid(b.geom), 5000))
and b.access != 'BY PERMISSION'
-- and regexp_split_to_array(REGEXP_REPLACE(lower(a.park_name),' park| and| center| &',''), ' ') && (regexp_split_to_array(REGEXP_REPLACE(lower(b.maname),' park| and| center',''), ' '))
-- and (b.gisacre - 100 < a.total_acres and b.gisacre + 100 > a.total_acres) -- within 100 acres
order by dist_m desc
) a
order by pt_id, dist_m asc; 

-- set up match table
-- within 100m, or a partial name match (n = 1260)...
drop table local_parks_areas cascade;
create table local_parks_areas as
select * from pt_poly_matches  
where (dist_m < 100 or dist_m_cent < 100) -- within 100m
or (dist_m < 2000 and regexp_split_to_array(REGEXP_REPLACE(lower(pt_name),' park| and| center| &',''), ' ') && (regexp_split_to_array(REGEXP_REPLACE(lower(poly_name),' park| and| center| &',''), ' '))
	and (poly_acre - 10 < pt_acre and poly_acre + 10 > pt_acre)) -- within 2000m , matching name, acres within 10 of one antoher
order by pt_id;

-- these are associated points; not pulling polygon into table for these
select * from local_parks_areas where dist_m is not null order by dist_m desc;

-- buffered points for unassoc; added to local_park_areas
alter table local_parks_areas add column geom_poly geometry('POLYGON', 5070);
insert into local_parks_areas (pt_id, pt_name, pt_acre, geom, geom_poly) 
select pt_id, pt_name, pt_acre, geom, st_buffer(a.geom, radius, 20) geom_poly
 from (
select a.objectid pt_id, a.park_name pt_name, a.total_acres pt_acre,
case when a.total_acres is NULL or a.total_acres = 0 then sqrt((0.25 * 4046.8564)/pi())::numeric else sqrt((a.total_acres * 4046.8564)/pi())::numeric end as radius, geom --.25 acre default when missing
from rec_source.local_parks a
where use = 1
and a.objectid not in (select pt_id from local_parks_areas)
) a;

-- remove self-intersections from local_parks_areas (drop smaller polygon)
drop table ints;
create table ints as
select distinct on (int_polys.rid) a.*, int_polys.geom int_geom from 
local_parks_areas a,
(select row_number() over() as rid, geom from
(select (st_dump(st_union(a.geom_poly))).geom from
local_parks_areas a,
local_parks_areas b
where a.geom_poly is not null
and st_intersects(a.geom_poly,b.geom_poly)
and a.pt_id != b.pt_id) b) int_polys
where st_intersects(a.geom_poly, int_polys.geom)
order by int_polys.rid, st_area(a.geom_poly) desc;

-- update local_parks areas;
delete from local_parks_areas a where a.pt_id in (select a.pt_id from local_parks_areas a, ints b where st_intersects(a.geom_poly, b.int_geom));
insert into local_parks_areas (pt_id, pt_name, pt_acre, geom, geom_poly) select pt_id, pt_name, pt_acre, geom, int_geom from ints;


-- create final table of public lands
-- pub_lands_final ints
drop table ints;
create table ints as
select a.pt_id, b.objectid, st_union(a.geom_poly, b.geom) geom from
local_parks_areas a,
rec_source.pub_lands_dissolve b
where a.geom_poly is not null
and b.water = 0
and st_intersects(a.geom_poly, b.geom);

drop table pub_lands_final_2;
create table pub_lands_final_2 (
objectid serial primary key,
pub_lands_dissolve_objectid int,
local_parks_areas_pt_id int,
geom geometry('MultiPolygon', 5070));

-- pub lands dissolve
insert into pub_lands_final_2 (pub_lands_dissolve_objectid, geom) 
select objectid, st_force2d(geom) from rec_source.pub_lands_dissolve where water = 0
and objectid not in (select objectid from ints);

-- buffered local park points
insert into pub_lands_final_2 (local_parks_areas_pt_id, geom) 
select pt_id, st_multi(geom_poly) from local_parks_areas where geom_poly is not null
and pt_id not in (select pt_id from ints);

-- new polygons (from two tables intersects)
insert into pub_lands_final_2(geom) 
select st_multi((st_dump(st_union(geom))).geom) from
(select st_union(geom_poly) geom from local_parks_areas where pt_id in (select pt_id from ints)
union all
select st_union(geom) from rec_source.pub_lands_dissolve where objectid in (select objectid from ints)) a;

-- update new (combined) polygons with an objectid from pub_lands_dissolve 
update pub_lands_final_2 b set pub_lands_dissolve_objectid = 
aoid from
(select distinct on (b.objectid) a.objectid aoid, b.objectid boid from
rec_source.pub_lands_dissolve a, pub_lands_final_2 b
where st_intersects(b.geom, a.geom)
and a.water = 0
and b.pub_lands_dissolve_objectid is null and b.local_parks_areas_pt_id is null
order by b.objectid, st_area(a.geom) desc) sub
where objectid = boid;
-- re-combine those geoms
update pub_lands_final_2 set geom = a.geom
from
(select pub_lands_dissolve_objectid, st_union(geom) geom from pub_lands_final_2 
where pub_lands_dissolve_objectid is not null
group by pub_lands_dissolve_objectid having count(*) > 1) a
where pub_lands_final_2.pub_lands_dissolve_objectid = a.pub_lands_dissolve_objectid;
-- delete dups by geom
delete from pub_lands_final_2 where objectid not in
(select distinct on (geom) min(objectid)
from pub_lands_final_2
group by geom);


select sum(st_area(geom))/100000 from rec_source.pub_lands_dissolve where water = 0;

vacuum analyze pub_lands_final_2;
-- finalize
create index pub_lands_final_2_geomidx on pub_lands_final_2 USING gist (geom); 
-- insert into lookup.src_table (table_name) values ('pub_lands_final_2');

-- check self-intersects
select a.*, b.* from pub_lands_final_2 a,
 pub_lands_final_2 b
 where st_intersects(a.geom, b.geom) and st_overlaps(a.geom, b.geom) and a.objectid != b.objectid;
-- should return nothing