-- 1. Trail cleaning
-- Starts from original trails dataset with all attributes from ArcGIS [vatrails_orig in database]
 
-- remove all exact dups
-- retains multis
drop table trails_clean_multi;
create table trails_clean_multi as 
with groupids as (
select a.objectid, min(b.objectid) min_group, count(b.objectid) from 
rec_source.vatrails_orig a,
rec_source.vatrails_orig b
where st_equals(a.geom, b.geom)
group by a.objectid
order by count(b.objectid) desc)
select * from rec_source.vatrails_orig where objectid in (select min_group from groupids where objectid = min_group);
--
create index trails_clean_multi_idx on trails_clean_multi using gist (geom);
update trails_clean_multi set shape_length = st_length(geom);

-- dump to all single linestrings
drop table trails_clean;
create table trails_clean as
select row_number() over ()::int as rid, b.* FROM 
(select a.*, st_makevalid(st_force2d((st_dump(a.geom)).geom)::geometry('LINESTRING',5070)) as geom_single from trails_clean_multi a) b;
alter table trails_clean drop column geom;
alter table trails_clean rename column geom_single to geom;
create index trails_clean_idx on trails_clean using gist (geom);
update trails_clean set shape_length = st_length(geom);
analyze trails_clean;

select distinct st_isvalid(geom) from trails_clean;

-- test if there are still overlaps (should return nothing)
select a.rid, b.rid from
trails_clean a, trails_clean b where 
st_intersects (a.geom, b.geom) and 
st_overlaps(a.geom, b.geom) and 
a.rid != b.rid
limit 1;

-- length is equal - no overlaps
select sum(st_length(geom)) from trails_clean where watertrail is null and QC is null and on_road = 0;
select st_length(st_union(geom)) from trails_clean where watertrail is null and QC is null and on_road = 0;

-- add exclude column
select distinct QC from trails_clean;
-- add exclude field
-- W = excluded b/c in water
-- R = excluded b/c in road
-- P = excluded b/c in "by permission" land
-- N = excluded b/c believed non-existent (i.e., proposed)
-- D = excluded as manaully identified as duplicate
-- C = excluded because marked as closed in original dataset
-- I = include (default normal trails with no reason to exclude).
alter table trails_clean add column exclude character(1);
update trails_clean set exclude = NULL;
update trails_clean set exclude = 'W' where watertrail = 1;
update trails_clean set exclude = 'R' where on_road = 1;
update trails_clean set exclude = 'P' where qc = 'Restricted';
update trails_clean set exclude = 'N' where qc in ('Proposed', 'NotExist?');
update trails_clean set exclude = 'C' where qc = 'Closed';
update trails_clean set exclude = 'D' where qc = 'Duplicate';
update trails_clean set exclude = 'I' where exclude is null;

select QC, exclude, count(*) from trails_clean group by QC, exclude;
alter table trails_clean add primary key (rid);

-- create table trails_clean_simple as
-- select rid, fid_prep_vatrails_2017_20190201 as orig_fid, trailname, exclude, geom from trails_clean;

-- final table with only included trails. This unions everything to (hopefully) remove any remaining overlap
-- 2.5 mins
drop table trails_include;
create table trails_include as 
select row_number() over() as rid, geom FROM
(select ((st_dump(a.geom)).geom) geom
from (select st_union(geom) geom from trails_clean where exclude = 'I') a) b;
-- clean up
delete from trails_include where st_geometrytype(geom) = 'ST_Point';
delete from trails_include where st_length(geom) < 0.01;
ALTER TABLE trails_include ALTER COLUMN geom type geometry('Linestring', 5070);
create index trails_include_idx on trails_include using gist (geom);


-- these two could/should be different (if union worked)
select sum(st_length(geom)) from trails_clean where exclude = 'I';
select sum(st_length(geom)) from trails_include;

select distinct rid from trails_include limit 5;

####################

/*
-- automated non-exact duplicate removal
vacuum analyze trails_clean;

-- gets polygons where overlap exists (non-existent polygon areas are good-no overlap at defined distance)
drop table trails_clean_2;
create table trails_clean_2 as 
select row_number() over()::int as rid, st_buffer((st_dump(geom)).geom,-1.001) from 
	(select st_union(st_buffer(geom,1, 'join=bevel')) geom from trails_clean
	where landunit = 'James River Park'
	or trailname = 'Richmond Canal Walk'
	--and exclude = 'I'
	) b;

create table trails_clean_2 as
with groupids as (
select a.rid, min(b.rid) min_group, min(st_length(a.geom)), count(b.rid) 
from trails_clean a, trails_clean b
-- and a.rid != b.rid
and st_length(a.geom) > 6
and st_dwithin(st_startpoint(a.geom), st_startpoint(b.geom), 3) and st_dwithin(st_endpoint(a.geom), st_endpoint(b.geom), 3) -- within 5 meters start and end points
and round(st_length(a.geom)::numeric,-1) = round(st_length(b.geom)::numeric, -1) -- similar distances
group by a.rid
order by count(b.rid) desc)
select * from trails_clean where rid in (select min_group from groupids where rid = min_group);

create index trails_clean_multi_idx on trails_clean_multi using gist (geom);
update trails_clean_multi set shape_length = st_length(geom);


create temp table dups as
select least(a.rid, b.rid) rid_1, greatest(a.rid, b.rid) rid_2, st_length(a.geom), a.geom 
from trails_clean a, trails_clean b
where a.rid != b.rid and
st_dwithin(st_startpoint(a.geom), st_startpoint(b.geom), 10) and st_dwithin(st_endpoint(a.geom), st_endpoint(b.geom), 10)
and round(st_length(a.geom)::numeric,-1) = round(st_length(b.geom)::numeric, 1)
limit 10;
--and st_length(a.geom) > 50
*/

###############


-- 2. Trail networks (grouping by sep. distance)

drop table trails_clean_network;
create table trails_clean_network as 
	select row_number() over ()::int as rid, round(st_length(a.geom)::numeric/1609.344,8) as leng_miles, a.geom as geom from 
	(select st_setsrid(st_collectionextract(unnest(ST_ClusterWithin(geom, 402.25)),2),5070) as geom from trails_include 
	where st_length(geom) > 0) a -- HOW LONG SHOULD A SEGMENT BE TO BE IN A CLUSTSER?
	where st_length(a.geom)/1609.344 >= 1; -- HOW LONG SHOULD A CLUSTER BE TO BE INCLUDED?
CREATE INDEX trails_clean_network_idx ON trails_clean_network USING gist (geom);
-- insert into lookup.src_table (table_name) values ('trails_clean_network');


-- update trails_clean with clusterid (update after choosing cluster distances)
vacuum analyze trails_clean;
alter table trails_clean drop column clus_rid;
alter table trails_clean add column clus_rid int;
update trails_clean set clus_rid = NULL;
update trails_clean set clus_rid = 
sub.clus_rid from
(select a.rid, b.rid clus_rid from 
trails_clean a,
trails_clean_network b 
where a.exclude = 'I'
and st_intersects(a.geom, b.geom)) sub
where trails_clean.rid = sub.rid;


select a.clus_rid, min(b.leng_miles), sum(st_length(a.geom))::numeric*0.000621371 from trails_clean a join trails_clean_network b on (a.clus_rid = b.rid)
where clus_rid is not null
group by clus_rid;


-- summaries - 50m
select count(*), round(leng_miles, 1) from trails_clean_network
group by round(leng_miles, 1)
order by round(leng_miles, 1) desc;
-- total miles
select sum(st_length(geom))::numeric*0.000621371 from trails_clean_network;
-- 805m
select count(*), round(leng_miles, 1) from trails_clean_network_halfmile
group by round(leng_miles, 1)
order by round(leng_miles, 1) desc;
-- total miles
select sum(st_length(geom))::numeric*0.000621371 from trails_clean_network_halfmile;
-- 5420.35 miles
