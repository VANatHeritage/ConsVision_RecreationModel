--- TODO
---

/*
Recreation access tables for recreation model.

Populates 'access_t' and 'access_a' tables
with point features associated with
recreational facilities from original source tables.
Tables are used as input for service area analyses
in ArcGIS.

Note: ogc_fid = original FID from an imported shapefile.
objectid = usually from an imported geodatabase feature class.

Author: David Bucklin

Created: 2018-06-15
Last update: 2018-08-20
*/

-- Terrestrial rec access
update rec_source.va_public_access set objectid = objectid_1; -- objectid is null for a couple records, this sets it to match primary key

-- reset table if needed
DELETE FROM rec_access.access_t;
ALTER SEQUENCE rec_access.access_t_acs_t_id_seq RESTART WITH 1;

-- Public lands
-- pub_lands_dissolve was set up with unique known public access polygons
-- processinng moved to park_points.sql
-- table is pub_lands_final

-- roads query view
create or replace view roads.roads_sub as 
select * from roads.tiger_2018 where
	mtfcc NOT IN ('S1710','S1720','S1740','S1750', -- excluded from analysis
	'S1100','S1630'); -- these are limited access highways


-- EXTRA ATTRIBUTES FOR POLYGONS
-- summarize trails (lines) in polygons - vatrails
/*
drop table pub_lands_trls;
CREATE TABLE pub_lands_trls AS
	SELECT a.objectid, b.objectid oid_t, st_intersection(b.geom, a.geom) geom -- could use st_buffer(50m) around polygons to account for trails along polygon buffers
	FROM pub_lands_final a,
	rec_source.vatrails b
	WHERE st_intersects(a.geom, b.geom); -- could use st_buffer around polygons to account for trails along polygon buffers
COMMENT ON TABLE pub_lands_trls is 'Trails intersecting pub_lands_final polygon from the trails table ''rec_source.vatrails''';
-- summarize trails (lines) in polygons - state_trails
drop table pub_lands_strl;
CREATE TABLE pub_lands_strl AS
	SELECT a.objectid, b.ogc_fid oid_t, st_intersection(st_transform(b.geom, 3968), a.geom) geom
	FROM pub_lands_final a,
	rec_source.state_trails b
	WHERE b.type = 'Trail' AND st_intersects(a.geom, st_transform(b.geom, 3968)); -- only (foot) trails, not the on-road trails included in this table
COMMENT ON TABLE pub_lands_trls is 'Trails intersecting pub_lands_final polygon from the trails table ''rec_source.state_trails''';


-- drop view pub_lands_alltrls;
CREATE or replace VIEW pub_lands_alltrls AS
SELECT t.*, round(st_area(p.geom)::numeric/4046.856,8) as plt_area FROM
	((SELECT distinct on (objectid) objectid as plt_fid, count(oid_t) as trls_sgmts, sum(st_length(geom))/1609.344 as trls_leng_miles 
	FROM pub_lands_trls group by plt_fid) a
	FULL OUTER JOIN
	(SELECT distinct on (objectid) objectid as plt_fid, count(oid_t) as strl_sgmts, sum(st_length(geom))/1609.344 as strl_leng_miles 
	FROM pub_lands_strl group by plt_fid) b
	using (plt_fid)) t
	JOIN
	pub_lands_final p on (p.objectid = t.plt_fid);
COMMENT ON VIEW pub_lands_alltrls is 'Summary of total length of trails within pub_lands_final polygon from the trail lines tables.';
-- area and length summary
select plt_fid, plt_area, trls_leng_miles, strl_leng_miles from pub_lands_alltrls order by trls_leng_miles desc;
-- END TRAIL ATTRIBUTES FOR PUBLIC LANDS
*/

-- create temp table by subtype
drop table t_tlnd;
create table t_tlnd as 
select row_number() over () as rid, * from (
select objectid, t_tlnd, 'bwt_sites' as src_table, geom from rec_source.bwt_sites where t_tlnd = 1 UNION ALL
select objectid, t_tlnd, 'dgif_boataccess', geom from rec_source.dgif_boataccess where t_tlnd = 1 UNION ALL
select objectid, t_tlnd, 'local_parks', geom from rec_source.local_parks where t_tlnd = 1 and use = 1 UNION ALL
select objectid, t_tlnd, 'va_public_access', geom from rec_source.va_public_access where t_tlnd = 1 UNION ALL
select objectid, t_tlnd, 'va_trailheads', geom from rec_source.va_trailheads where t_tlnd = 1 UNION ALL
select objectid, t_tlnd, 'vop_boataccess', geom from rec_source.vop_boataccess where t_tlnd = 1 UNION ALL
select objectid, t_tlnd, 'wma_points', geom from rec_source.wma_points where t_tlnd = 1
) a;

-- grouping dissolved buffer
-- select row_number() over () as rid, a.dump geom from (
-- select st_dump(st_union(st_buffer(geom, 500))) dump from t_tlnd) a;

-- t_tlnd (all access points)
INSERT INTO rec_access.access_t (facil_code, facil_rid, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom) 
	SELECT 'tlnd', a.rid, a.src_table, a.objectid, 'pub_lands_final', b.objectid, 
		round(st_area(b.geom)::numeric/4046.856,8), 1, 'intersects pub_lands_final', a.geom
	FROM t_tlnd a, pub_lands_final b
	WHERE st_intersects(a.geom, b.geom)
	and st_area(b.geom) > 20234.3; -- 5 acres
-- within a distance of pub_lands (50m) -> associate with closest
INSERT INTO rec_access.access_t (facil_code, facil_rid, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom) 
	SELECT distinct on (a.rid) 'tlnd', a.rid, a.src_table, a.objectid, 'pub_lands_final', b.objectid, round(st_area(b.geom)::numeric/4046.856,8), 1, 'within 50m pub_lands_final', a.geom
	FROM t_tlnd a, pub_lands_final b
	WHERE st_dwithin(a.geom, b.geom, 50)
	and st_area(b.geom) > 20234.3
	AND a.rid NOT IN (SELECT distinct facil_rid FROM rec_access.access_t where facil_code = 'tlnd')
	order by a.rid, st_distance(a.geom, b.geom) asc;
-- within a distance of pub_lands (402.25) -> associate with closest
INSERT INTO rec_access.access_t (facil_code, facil_rid, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom) 
	SELECT distinct on (a.rid) 'tlnd', a.rid, a.src_table, a.objectid, 'pub_lands_final', b.objectid, round(st_area(b.geom)::numeric/4046.856,8), 1, 'within 50m-quarter mile of pub_lands_final', a.geom
	FROM t_tlnd a, pub_lands_final b
	WHERE st_dwithin(a.geom, b.geom, 402.25)
	and st_area(b.geom) > 20234.3
	AND a.rid NOT IN (SELECT distinct facil_rid FROM rec_access.access_t where facil_code = 'tlnd')
	order by a.rid, st_distance(a.geom, b.geom) asc;
-- Select distinct rid from t_tlnd where rid not in (select facil_rid from rec_access.access_t where facil_code = 'tlnd') 


-- Public lands polygons - generating one point per non-associated polygon
-- these are associated
create or replace view plnd_assoc as 
select distinct join_fid from rec_access.access_t where facil_code = 'tlnd' and join_table = 'pub_lands_final' and join_fid is not null and use != 0
union all
select distinct src_id from rec_access.access_t where facil_code = 'tlnd' and src_table = 'pub_lands_final' and use != 0;

delete from rec_access.access_t where src_table = 'pub_lands_final' and join_table = 'pub_lands_final';
-- These are polygons intersecting roads
-- take closest point on intersecting roads to the polygon's centroid points
INSERT INTO rec_access.access_t (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom) 
SELECT DISTINCT ON (a.objectid) 'tlnd', 'pub_lands_final', a.objectid, 'pub_lands_final', a.objectid, round(st_area(a.geom)::numeric/4046.856,8),
			2, 'closest point on intersecting roads to polygon centroid', st_closestpoint((st_dump(st_intersection(b.geom, a.geom))).geom, st_centroid(a.geom)) FROM
		pub_lands_final a,
		roads.roads_sub b
		where st_intersects(a.geom, b.geom)
		and st_area(a.geom) > 20234.3 -- 5 acres
		and a.objectid NOT IN (select join_fid from plnd_assoc);
		
-- non-road intersecting polygons (RUN THIS WITH ADJUSTED DWITHIN DISTANCES UNTIL NOTHING NEW ADDED)
INSERT INTO rec_access.access_t (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom)
SELECT DISTINCT ON (a.objectid) 'tlnd', 'pub_lands_final', a.objectid, 'pub_lands_final', a.objectid, round(st_area(a.geom)::numeric/4046.856,8),
			2, 'closest point on polygon boundary to road', st_closestpoint(a.geom, b.geom) geom FROM
		pub_lands_final a,
		roads.roads_sub b
		where st_dwithin(a.geom, b.geom, 15000) -- manually adjust here with increasingly higher values to speed up/provide cutoff for polys > a distance to closest road
		and st_area(a.geom) > 20234.3 -- 5 acres
		and a.objectid NOT IN (select join_fid from plnd_assoc)
		ORDER BY a.objectid, ST_Distance(a.geom,b.geom) asc;
-- check	
select objectid, st_area(geom) from pub_lands_final where objectid not in (select * from plnd_assoc order by join_fid) order by st_area(geom) desc;
-- should be just small polys (<5 acres area) excluded
drop view plnd_assoc;
-- all polygons have a point now
select join_fid, count(*) from rec_access.access_t where join_score < 5 group by join_fid order by count(*) desc;


-- Terrestrial Trails

-- create temp table by subtype
drop table t_trl;
create table t_trl as 
select row_number() over () as rid, * from (
select objectid, t_trl, 'bwt_sites' as src_table, geom from rec_source.bwt_sites where t_trl = 1 UNION ALL
select objectid, t_trl, 'dgif_boataccess', geom from rec_source.dgif_boataccess where t_trl = 1 UNION ALL
select objectid, t_trl, 'local_parks', geom from rec_source.local_parks where t_trl = 1 and use = 1 UNION ALL
select objectid, t_trl, 'va_public_access', geom from rec_source.va_public_access where t_trl = 1 UNION ALL
select objectid, t_trl, 'va_trailheads', geom from rec_source.va_trailheads where t_trl = 1 UNION ALL
select objectid, t_trl, 'vop_boataccess', geom from rec_source.vop_boataccess where t_trl = 1 UNION ALL
select objectid, t_trl, 'wma_points', geom from rec_source.wma_points where t_trl = 1
) a;

-- total # of trail networks
select count(*) from trails_clean_network;

-- grouping dissolved buffer
-- select row_number() over () as rid, a.dump geom from (
-- select st_dump(st_union(st_buffer(geom, 500))) dump from t_trl) a;

-- t_trl (all access points)
-- within a distance of trail clusters (50m) -> associate with closest
delete from rec_access.access_t where facil_code = 'ttrl';
INSERT INTO rec_access.access_t (facil_code, facil_rid, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom) 
	SELECT distinct on (a.rid) 'ttrl', a.rid, a.src_table, a.objectid, 'trails_clean_network', b.rid, b.leng_miles, 1, 'within 50m trails_clean_network', a.geom
	FROM t_trl a, trails_clean_network b
	WHERE st_dwithin(a.geom, b.geom, 50)
	and b.leng_miles > 1
	AND a.rid NOT IN (SELECT distinct facil_rid FROM rec_access.access_t where facil_code = 'ttrl')
	order by a.rid, st_distance(a.geom, b.geom) asc;
-- within a distance of trail_clusters (500m) -> associate with closest
INSERT INTO rec_access.access_t (facil_code, facil_rid, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom) 
	SELECT distinct on (a.rid) 'ttrl', a.rid, a.src_table, a.objectid, 'trails_clean_network', b.rid, b.leng_miles, 1, 'within 50m-quarter mile of trails_clean_network', a.geom
	FROM t_trl a, trails_clean_network b
	WHERE st_dwithin(a.geom, b.geom, 402.25)
	and b.leng_miles > 1
	AND a.rid NOT IN (SELECT distinct facil_rid FROM rec_access.access_t where facil_code = 'ttrl')
	order by a.rid, st_distance(a.geom, b.geom) asc;
--Select distinct rid from t_trl where rid not in (select facil_rid from rec_access.access_t where facil_code = 'ttrl') 


-- all remaining trail clusters (1 point per)
select distinct join_fid from rec_access.access_t where facil_code = 'ttrl' and join_table = 'trails_clean_network';
---
-- These are trails intersecting roads
-- take closest point on intersecting roads to the trail clusters's centroid points
INSERT INTO rec_access.access_t (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom) 
SELECT DISTINCT ON (a.rid) 'ttrl', 'trails_clean_network', a.rid,'trails_clean_network', a.rid, a.leng_miles,
			2, 'closest point on intersecting roads to trail centroid', st_closestpoint((st_dump(st_intersection(b.geom, a.geom))).geom, st_centroid(a.geom)) FROM
		trails_clean_network a,
		roads.roads_sub b
		where st_intersects(a.geom, b.geom)
		and a.leng_miles > 1
		and a.rid NOT IN (select distinct join_fid from rec_access.access_t where facil_code = 'ttrl' and join_table = 'trails_clean_network');
-- non-road intersecting trail clusters
INSERT INTO rec_access.access_t (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom)
SELECT DISTINCT ON (a.rid) 'ttrl', 'trails_clean_network', a.rid,'trails_clean_network', a.rid, a.leng_miles,
			2, 'closest point on trail boundary to road', st_closestpoint(a.geom, b.geom) geom FROM
		trails_clean_network a,
		roads.roads_sub b
		where st_dwithin(a.geom, b.geom, 10000) -- manually adjust here with increasingly higher values to speed up/provide cutoff for trails > a distance to closest road
		and a.rid NOT IN (select distinct join_fid from rec_access.access_t where facil_code = 'ttrl' and join_table = 'trails_clean_network')
		and a.leng_miles > 1
		ORDER BY a.rid, ST_Distance(a.geom,b.geom) asc;
		
-- check		
select rid, leng_miles from trails_clean_network where 
rid not in (select distinct join_fid from rec_access.access_t where facil_code = 'ttrl' and join_table = 'trails_clean_network')
order by leng_miles desc; 

-- summary
select facil_code, src_table, count(*) from rec_access.access_t
group by facil_code, src_table
order by facil_code, src_table;


-- area per access points - "least accessible" polygons (< 1 point per 1000 ha)
-- should we do something with these or leave as is?
select *, area_acres/ct_acc as acres_per_acc from
(select join_fid, count(join_fid) ct_acc  from 
rec_access.access_t
group by join_fid) a
join
(select objectid, st_area(geom)/4046.856 area_acres from pub_lands_final) b 
on (a.join_fid = b.objectid)
order by acres_per_acc desc;

-- should we set a size limit on using generated points? (e.g. must be >1ha to generate a point?)
select count(*) from rec_access.access_t where join_score < 1 and use != 0 and src_table = 'pub_lands_final';
-- would drop 543 points.

/*post-processing terrestrial facilities
1. add src_cid
2. add road_dist
3. identify (near) duplicates
*/
UPDATE rec_access.access_t a SET src_cid =
	(SELECT b.table_name || '_' || lpad(a.src_id::text, 6, '0') FROM
	lookup.src_table b
	WHERE a.src_table = b.table_name)
	where src_cid is null; -- if just updating new points, leave this
select * from rec_access.access_t where src_cid is null;

-- update distance to closest road
UPDATE rec_access.access_t a SET road_dist = 
	(SELECT dist from
	(SELECT distinct on (acs_t_id) acs_t_id, st_distance(a.geom, b.geom)::numeric(7,2) dist FROM
	rec_access.access_t a,
	roads.tiger_2018 b
	where st_dwithin(a.geom, b.geom, 20000) -- run progressively at 100, 1000, 10000, 20000
	and b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500')
	order by acs_t_id, st_distance(a.geom, b.geom) asc) b
where a.acs_t_id = b.acs_t_id)
where a.road_dist is null;

-- exact duplicates to use = 0
update rec_access.access_t set use = 0, use_why = 'exact duplicate with same facil_code' WHERE acs_t_id IN
(select distinct a1 FROM
(
select distinct on (greatest(a.acs_t_id, b.acs_t_id) || '-' || least(a.acs_t_id, b.acs_t_id))
 greatest(a.acs_t_id, b.acs_t_id) a1, least(a.acs_t_id, b.acs_t_id) a2
 from rec_access.access_t a, rec_access.access_t b 
 where a.use != 0 and b.use != 0 and 
 a.acs_t_id != b.acs_t_id and 
 a.facil_code = b.facil_code and 
 st_intersects(a.geom, b.geom)
 ) sub);
-- end rec_access.access_t

-- counts, total and by- join_fid
select facil_code, count(*) from rec_access.access_t where use != 0 group by facil_code;
select facil_code, count(distinct join_fid) from rec_access.access_t where use != 0 group by facil_code;

select rid from trails_clean_network where rid not in (select join_fid from rec_access.access_t where facil_code = 'ttrl' and use != 0);


/*
Aquatic access

This will use an NHDArea + NHDWaterbody composite table (nhd_area_wtrb). 
Points will generated on polygon surface if not already intersecting, and if close enough to the water feature.

Aquatic points:
	- group if within 1/4 mile
	- are kept if within 1/4 mile of aquatic features (NHD)
	-


Populating the accesss_a table.
- access point tables:
va_public_access
boat_access
bwt_sites
vatrailheads

For each point table (each step will exclude a given point from successive steps, if it becomes associated)
1. find those intersecting waters, insert
2. find those within 50m of waters, insert closest point on waters
3. find those within 300m of waters insert closest point on waters
4. insert remaining points with use = 0
===
Can do these steps efficiently for each access point table by:
- generating temp table [aqua_temp] with closest point on nhd_area_wtrb (within 500m)
- adding points to temp table [aqua_temp] that are closest point on nhd_flowline (within 500m)
- select the one point from [aqua_temp] with the closer distance [between nhd_area_wtrb and nhd_flowline]

*/

-- reset table if needed
-- create table rec_access_access_a_a20180711 as select * from rec_access.access_a;
DELETE FROM rec_access.access_a;
ALTER SEQUENCE rec_access.access_a_acs_a_id_seq RESTART WITH 1;
select * from rec_access.access_a;


-- ONE SECTION OF THIS PER FACIL_CODE
drop table a_wct;
create table a_wct as 
select row_number() over () as rid, * from (
select objectid, a_wct, 'bwt_sites' as src_table, geom from rec_source.bwt_sites where a_wct = 1 UNION ALL
select objectid, a_wct, 'dgif_boataccess', geom from rec_source.dgif_boataccess where a_wct = 1 UNION ALL
select objectid, a_wct, 'local_parks', geom from rec_source.local_parks where a_wct = 1 and use = 1 UNION ALL
select objectid, a_wct, 'va_public_access', geom from rec_source.va_public_access where a_wct = 1 UNION ALL
select objectid, a_wct, 'va_trailheads', geom from rec_source.va_trailheads where a_wct = 1 UNION ALL
select objectid, a_wct, 'vop_boataccess', geom from rec_source.vop_boataccess where a_wct = 1 UNION ALL
select objectid, a_wct, 'wma_points', geom from rec_source.wma_points where a_wct = 1
) a;
-- delete (exact) duplicates
delete from a_wct where rid not in (select min(a.rid) from a_wct a group by a.geom);

INSERT INTO rec_access.access_a (facil_code, facil_rid, src_table, src_id, join_score, use, use_why, geom)
	select 'awct', rid, src_table, objectid, 1, 1, 'access point from source dataset', geom 
	from a_wct;


drop table a_fsh;
create table a_fsh as 
select row_number() over () as rid, * from (
select objectid, a_fsh, 'bwt_sites' as src_table, geom from rec_source.bwt_sites where a_fsh = 1 UNION ALL
select objectid, a_fsh, 'dgif_boataccess', geom from rec_source.dgif_boataccess where a_fsh = 1 UNION ALL
select objectid, a_fsh, 'local_parks', geom from rec_source.local_parks where a_fsh = 1 and use = 1 UNION ALL
select objectid, a_fsh, 'va_public_access', geom from rec_source.va_public_access where a_fsh = 1 UNION ALL
select objectid, a_fsh, 'va_trailheads', geom from rec_source.va_trailheads where a_fsh = 1 UNION ALL
select objectid, a_fsh, 'vop_boataccess', geom from rec_source.vop_boataccess where a_fsh = 1 UNION ALL
select objectid, a_fsh, 'wma_points', geom from rec_source.wma_points where a_fsh = 1
) a;
-- delete (exact) duplicates
delete from a_fsh where rid not in (select min(a.rid) from a_fsh a group by a.geom);

INSERT INTO rec_access.access_a (facil_code, facil_rid, src_table, src_id, join_score, use, use_why, geom)
	select 'afsh', rid, src_table, objectid, 1, 1, 'access point from source dataset', geom 
	from a_fsh;

drop table a_swm;
create table a_swm as 
select row_number() over () as rid, * from (
select objectid, a_swm, 'bwt_sites' as src_table, geom from rec_source.bwt_sites where a_swm = 1 UNION ALL
select objectid, a_swm, 'dgif_boataccess', geom from rec_source.dgif_boataccess where a_swm = 1 UNION ALL
select objectid, a_swm, 'local_parks', geom from rec_source.local_parks where a_swm = 1 and use = 1 UNION ALL
select objectid, a_swm, 'va_public_access', geom from rec_source.va_public_access where a_swm = 1 UNION ALL
select objectid, a_swm, 'va_trailheads', geom from rec_source.va_trailheads where a_swm = 1 UNION ALL
select objectid, a_swm, 'vop_boataccess', geom from rec_source.vop_boataccess where a_swm = 1 UNION ALL
select objectid, a_swm, 'wma_points', geom from rec_source.wma_points where a_swm = 1
) a;
-- delete (exact) duplicates
delete from a_swm where rid not in (select min(a.rid) from a_swm a group by a.geom);

INSERT INTO rec_access.access_a (facil_code, facil_rid, src_table, src_id, join_score, use, use_why, geom)
	select 'aswm', rid, src_table, objectid, 1, 1, 'access point from source dataset', geom 
	from a_swm;


--- GENERATING NEW ACCESS POINTS

drop table fish_access;
create table fish_access as 
select row_number() over () as rid, * from (
select objectid, 'bwt_sites' as src_table, geom from rec_source.bwt_sites where (a_wct = 1 or a_fsh = 1 or a_swm = 1 or a_gen = 1 or t_trl = 1 or t_tlnd = 1) UNION ALL
select objectid, 'dgif_boataccess', geom from rec_source.dgif_boataccess where (a_wct = 1 or a_fsh = 1 or a_swm = 1 or a_gen = 1 or t_trl = 1 or t_tlnd = 1) UNION ALL
select objectid, 'local_parks', geom from rec_source.local_parks where (a_wct = 1 or a_fsh = 1 or a_swm = 1 or a_gen = 1 or t_trl = 1 or t_tlnd = 1) and use = 1 UNION ALL
select objectid, 'va_public_access', geom from rec_source.va_public_access where (a_wct = 1 or a_fsh = 1 or a_swm = 1 or a_gen = 1 or t_trl = 1 or t_tlnd = 1) UNION ALL
select objectid, 'va_trailheads', geom from rec_source.va_trailheads where (a_wct = 1 or a_fsh = 1 or a_swm = 1 or a_gen = 1 or t_trl = 1 or t_tlnd = 1) UNION ALL
select objectid, 'vop_boataccess', geom from rec_source.vop_boataccess where (a_wct = 1 or a_fsh = 1 or a_swm = 1 or a_gen = 1 or t_trl = 1 or t_tlnd = 1) UNION ALL
select objectid, 'wma_points', geom from rec_source.wma_points where (a_wct = 1 or a_fsh = 1 or a_swm = 1 or a_gen = 1 or t_trl = 1 or t_tlnd = 1)
) a;
-- delete (exact) duplicates
delete from fish_access where rid not in (select min(a.rid) from fish_access a group by a.geom);

-- for unassociated lakes, trout reaches
-- point generation technique varies by feature type
-- points generated on feature's boundary, relative to intersecting/nearby roads
-- these points will have use = 2 (indicating generated but should be used), or use = 0 if not intended to be used

--
-- pub_fish_lake
-- all [facil_code = afsh] access 
-- first dump and transform lakes
drop table rec_source.pub_fish_lake_dump;
create table rec_source.pub_fish_lake_dump as
	select row_number() over() as fid, a.geom
	from 
	(select st_setsrid(st_collectionextract(unnest(st_clusterwithin(b.geom,402.25)),3),5070) geom -- cluster within quarter mile to not over-represent lakes
		from
		(select objectid as pub_fish_lake_objectid, 
		(st_dump(geom)).geom::geometry('POLYGON',5070) geom
		from rec_source.pub_fish_lake) b) a;
comment on table rec_source.pub_fish_lake_dump is 'Exploded polygons from pub_fish_lake.';
insert into lookup.src_table (table_name) values ('pub_fish_lake_dump');

-- any facil code allowed to associate with lakes; update those points already in access_a with lakes ids
INSERT INTO rec_access.access_a (facil_code, facil_rid, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom)
	select distinct on (a.rid) 'afsh', a.rid, a.src_table, a.objectid, 'pub_fish_lake_dump', b.fid as fid, 
	1, 1, 'access point from source dataset near fishing lake', a.geom 
	from fish_access a,
	rec_source.pub_fish_lake_dump b
	where st_dwithin(a.geom, b.geom, 404.25)
	order by a.rid, st_distance(a.geom, b.geom)
	on conflict on CONSTRAINT access_a_facil_code_src_table_src_id_geom_key do update 
	set join_table = 'pub_fish_lake_dump', join_fid = excluded.join_fid, use_why = 'access point from source dataset near fishing lake';

-- 85/215 not associated 
delete from rec_access.access_a where join_table = 'pub_fish_lake_dump' and use = 2;
select distinct a.fid from rec_source.pub_fish_lake_dump a
where a.fid not in (select distinct join_fid from rec_access.access_a where join_table = 'pub_fish_lake_dump');

-- one point per unasssociated lake
INSERT INTO rec_access.access_a (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom)
SELECT DISTINCT ON (a.fid) 'afsh', 'pub_fish_lake_dump', a.fid,  'pub_fish_lake_dump', a.fid, 1, 2, 
			'closest point to polygon centroid from intersection of lake boundary with roads', 
			st_closestpoint((st_dump(st_intersection(b.geom, st_boundary(a.geom)))).geom, st_centroid(a.geom))
		FROM
		rec_source.pub_fish_lake_dump a,
		roads.roads_sub b 
		where st_intersects(a.geom, b.geom) -- manually adjust here with increasingly higher values to speed up/provide cutoff for polys > a distance to closest road
		and a.fid not in (select distinct join_fid from rec_access.access_a where join_table = 'pub_fish_lake_dump');
		
INSERT INTO rec_access.access_a (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom)
SELECT DISTINCT ON (a.fid) 'afsh', 'pub_fish_lake_dump', a.fid,  'pub_fish_lake_dump', a.fid, 1, 2, 
			'closest point on boundary to road', st_closestpoint(st_boundary(a.geom), b.geom) geom FROM
		rec_source.pub_fish_lake_dump a,
		roads.roads_sub b 
		where st_dwithin(a.geom, b.geom, 10000) -- manually adjust here with increasingly higher values to speed up/provide cutoff for polys > a distance to closest road
		and a.fid not in (select distinct join_fid from rec_access.access_a where join_table = 'pub_fish_lake_dump')
		ORDER BY a.fid, ST_Distance(a.geom,b.geom) asc;

-- should return nothing
select distinct a.fid from rec_source.pub_fish_lake_dump a
where a.fid not in (select distinct join_fid from rec_access.access_a where join_table = 'pub_fish_lake_dump');

select join_fid, count(*) from rec_access.access_a where join_table = 'pub_fish_lake_dump' and use = 2 group by join_fid;



/*
-- intersecting lakes : GET ALL UNIQUE (SECONDARY) ROAD INTERSECTIONS WITH BOUNDARY
delete from rec_access.access_a where src_table = 'pub_fish_lake_dump';
INSERT INTO rec_access.access_a (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom)
SELECT DISTINCT 'afsh', 'pub_fish_lake_dump', a.fid,'pub_fish_lake_dump', a.fid, 1, 2, 'intersection of lake boundary and secondary road', 
			(st_dump(st_intersection(b.geom, st_boundary(a.geom)))).geom 
		FROM 	
		rec_source.pub_fish_lake_dump a,
		roads.roads_sub b
		where st_intersects(st_boundary(a.geom), b.geom)
		and b.mtfcc = 'S1200';
INSERT INTO rec_access.access_a (facil_code, src_table, src_id, join_score, use, use_why, geom)
SELECT DISTINCT ON (a.fid) 'afsh', 'pub_fish_lake_dump', a.fid, 1, 2, 'closest point on boundary to road', st_closestpoint(a.geom, b.geom) geom FROM
		rec_source.pub_fish_lake_dump a,
		roads.roads_sub b 
		where st_dwithin(a.geom, b.geom, 100) -- manually adjust here with increasingly higher values to speed up/provide cutoff for polys > a distance to closest road
		and a.fid not in (select distinct src_id from rec_access.access_a where src_table = 'pub_fish_lake_dump')
		ORDER BY a.fid, ST_Distance(a.geom,b.geom) asc;

*/

-- trout reaches
delete from rec_access.access_a where src_table = 'stocked_trout_reaches_diss';
-- all [facil_code = afsh] access
drop table rec_source.stocked_trout_reaches_diss;
create table rec_source.stocked_trout_reaches_diss as select row_number() over() as fid, round(st_length(a.geom)::numeric/1609.344,8) as leng_miles, geom FROM
(select st_setsrid(st_collectionextract(unnest(st_clusterwithin(geom, 402.25)), 2), 5070) geom from rec_source.stocked_trout_reaches) a;
select * from rec_source.stocked_trout_reaches_diss order by leng_miles desc;
insert into lookup.src_table (table_name) values ('stocked_trout_reaches_diss');

-- any facil code allowed to associate with reaches; update those points already in access_a with reaches ids
INSERT INTO rec_access.access_a (facil_code, facil_rid, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom)
	select distinct on (a.rid) 'afsh', a.rid, a.src_table, a.objectid, 'stocked_trout_reaches_diss', b.fid as fid, 
	1, 1, 'access point from source dataset near stocked trout reach', a.geom 
	from fish_access a,
	rec_source.stocked_trout_reaches_diss b
	where st_dwithin(a.geom, b.geom, 404.25)
	order by a.rid, st_distance(a.geom, b.geom)
	on conflict on CONSTRAINT access_a_facil_code_src_table_src_id_geom_key do update 
	set join_table = 'stocked_trout_reaches_diss', join_fid = excluded.join_fid, use_why = 'access point from source dataset near trout reach';

-- 120/216 not associated 
delete from rec_access.access_a where join_table = 'stocked_trout_reaches_diss' and use = 2;
select distinct a.fid from rec_source.stocked_trout_reaches_diss a
where a.fid not in (select distinct join_fid from rec_access.access_a where join_table = 'stocked_trout_reaches_diss');

-- one point per unasssociated lake
INSERT INTO rec_access.access_a (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom)
SELECT DISTINCT ON (a.fid) 'afsh', 'stocked_trout_reaches_diss', a.fid,  'stocked_trout_reaches_diss', a.fid, 1, 2, 
			'closest point to reach centroid from intersection of reach with roads', 
			st_closestpoint((st_dump(st_intersection(b.geom, a.geom))).geom, st_centroid(a.geom))
		FROM
		rec_source.stocked_trout_reaches_diss a,
		roads.roads_sub b 
		where st_intersects(a.geom, b.geom) -- manually adjust here with increasingly higher values to speed up/provide cutoff for polys > a distance to closest road
		and a.fid not in (select distinct join_fid from rec_access.access_a where join_table = 'stocked_trout_reaches_diss');

-- one point per unassociated (dissolved) reach
INSERT INTO rec_access.access_a (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom)
SELECT DISTINCT ON (a.fid) 'afsh', 'stocked_trout_reaches_diss', a.fid,  'stocked_trout_reaches_diss', a.fid, 1, 2, 
			'closest point on reach to road', st_closestpoint(a.geom, b.geom) geom FROM
		rec_source.stocked_trout_reaches_diss a,
		roads.roads_sub b 
		where st_dwithin(a.geom, b.geom, 1000) -- manually adjust here with increasingly higher values to speed up/provide cutoff for polys > a distance to closest road
		and a.fid not in (select distinct join_fid from rec_access.access_a where join_table = 'stocked_trout_reaches_diss')
		ORDER BY a.fid, ST_Distance(a.geom,b.geom) asc;

-- should be empty
select distinct a.fid from rec_source.stocked_trout_reaches_diss a
where a.fid not in (select distinct join_fid from rec_access.access_a where join_table = 'stocked_trout_reaches_diss');

select join_fid, count(*) from rec_access.access_a where join_table = 'stocked_trout_reaches_diss' and use = 2 group by join_fid;


/*
-- intersecting trout reaches
-- take all intersecting points
INSERT INTO rec_access.access_a (facil_code, src_table, src_id, join_table, join_fid,join_score, use, use_why, geom)
SELECT DISTINCT 'afsh', 'stocked_trout_reaches_diss', a.fid, 'stocked_trout_reaches_diss', a.fid, 1, 2, 'intersection of trout reach and secondary road',
-- SELECT DISTINCT ON (a.fid) 'aqua', 'stocked_trout_reaches_diss', a.fid, 2, 'closest point to feature centroid from road intersections', 
			--st_closestpoint((st_dump(st_intersection(b.geom, a.geom))).geom, st_centroid(a.geom)) FROM 	-- old method for just one point
			(st_dump(st_intersection(b.geom, a.geom))).geom FROM 	
		rec_source.stocked_trout_reaches_diss a,
		roads.roads_sub b
		where st_intersects(a.geom, b.geom)
		and b.mtfcc = 'S1200';
INSERT INTO rec_access.access_a (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom)
SELECT DISTINCT ON (a.fid) 'afsh', 'stocked_trout_reaches_diss', a.fid, 'stocked_trout_reaches_diss', a.fid, 1,
			2, 'closest point on boundary to road', st_closestpoint(a.geom, b.geom) geom FROM
		rec_source.stocked_trout_reaches_diss a,
		roads.roads_sub b 
		where st_dwithin(a.geom, b.geom, 10000) -- manually adjust here with increasingly higher values to speed up/provide cutoff for polys > a distance to closest road
		and a.fid not in (select distinct src_id from rec_access.access_a where src_table = 'stocked_trout_reaches_diss')
		ORDER BY a.fid, ST_Distance(a.geom,b.geom) asc;
-- should be empty
select fid from rec_source.stocked_trout_reaches_diss where fid not in 
(select src_id from rec_access.access_a where src_table = 'stocked_trout_reaches_diss');
*/


/*
-- scenic rivers (DON'T INCLUDE)
--drop table sriv;
create temp table sriv as select ogc_fid, st_transform(geom, 3968) geom from rec_source.scenic_rivers where status = 'Designated';
select distinct ogc_fid from sriv;
-- those already with access points
drop table excl;
create temp table excl as
select distinct ogc_fid from sriv a,
rec_access.access_a b where 
src_table != 'scenic_rivers' AND
st_dwithin(a.geom, b.geom, 50);
--23/34 already associated; 11 new points to create

-- add intersecting points
-- delete from rec_access.access_a where src_table = 'scenic_rivers';
INSERT INTO rec_access.access_a (facil_code, src_table, src_id, use, use_why, geom)
SELECT DISTINCT ON (a.ogc_fid) 'aqua', 'scenic_rivers', a.ogc_fid, 0, 'closest point to feature centroid from road intersections', 
			st_closestpoint((st_dump(st_intersection(b.geom, a.geom))).geom, st_centroid(a.geom)) FROM 	
		sriv a, -- temp tranformed table
		roads.roads_sub b
		where st_intersects(a.geom, b.geom)
		and a.ogc_fid NOT IN (select ogc_fid from excl); -- excludes lakes/aqua already within 50m of an access point
-- add closest for non intersecting
INSERT INTO rec_access.access_a (facil_code, src_table, src_id, use, use_why, geom)
SELECT DISTINCT ON (a.ogc_fid) 'aqua', 'scenic_rivers', a.ogc_fid, 0, 'closest point on boundary to road', st_closestpoint(a.geom, b.geom) geom FROM
		sriv a,
		roads.roads_sub b 
		where st_dwithin(a.geom, b.geom, 10000) -- manually adjust here with increasingly higher values to speed up/provide cutoff for polys > a distance to closest road
		and a.ogc_fid not in (select distinct src_id from rec_access.access_a where src_table = 'scenic_rivers')
		and a.ogc_fid NOT IN (select ogc_fid from excl)
		ORDER BY a.ogc_fid, ST_Distance(a.geom,b.geom) asc;
-- update features with nhd feature ids, using nhd area within 50m
update rec_access.access_a SET pla_fid = sub.objectid, pla_area = sub.area FROM
(select distinct on (a.acs_a_id) a.acs_a_id, b.objectid, round(st_area(b.geom)::numeric/4046.856,8) as area, st_distance(a.geom, b.geom) from
rec_access.access_a a,
rec_source.nhd_area_wtrb b
where a.src_table = 'scenic_rivers' and a.pla_fid is null
and st_dwithin(a.geom, b.geom, 50)
order by a.acs_a_id, st_distance(a.geom, b.geom) asc) sub
where access_a.acs_a_id = sub.acs_a_id;
-- update remaining features with nhd feature ids, using nhd flowline within 50m
update rec_access.access_a SET pla_fid = sub.objectid, pla_area = sub.area FROM
(select distinct on (a.acs_a_id) a.acs_a_id, b.objectid, round(st_area(b.geom)::numeric/4046.856,8) as area, st_distance(a.geom, b.geom) from
rec_access.access_a a,
rec_source.nhd_flowline b
where a.src_table = 'scenic_rivers' and a.pla_fid is null
and st_dwithin(a.geom, b.geom, 50)
order by a.acs_a_id, st_distance(a.geom, b.geom) asc) sub
where access_a.acs_a_id = sub.acs_a_id;
update rec_access.access_a SET use = 0, use_why = 'no associated NHD feature' where pla_fid is null and src_table = 'scenic_rivers';
-- 0 unassociated points
-- end scenic rivers
*/


----
-- beaches 
-- these are [facil_code = aswm] access

-- generate points along line for beach lines > half a mile
drop table beach_points;
create table beach_points as 
select a.objectid, st_closestpoint(a.geom, b.geom) geom from 
rec_source.public_beaches a,
(select objectid, (st_dumppoints(st_segmentize(st_simplify(geom, 804.5), 804.5))).geom from rec_source.public_beaches
where st_length(geom) > 804.5) b
where a.objectid = b.objectid;
insert into beach_points 
select objectid, st_startpoint(st_linemerge(geom)) from rec_source.public_beaches where st_length(geom) <= 804.5;
insert into beach_points 
select objectid, st_endpoint(st_linemerge(geom)) from rec_source.public_beaches where st_length(geom) <= 804.5;

insert into lookup.src_table (table_name) values ('beach_points');
-- add to access_a
delete from rec_access.access_a where src_table = 'beach_points';
INSERT INTO rec_access.access_a (facil_code, src_table, src_id, join_score, use, use_why, geom)
SELECT DISTINCT 'aswm', 'beach_points', a.objectid, 1, 2, 'points along beaches every half mile', a.geom	
		FROM beach_points a;

/*post-processing aquatic facilities
1. update use by distance from NHD, fish lakes
2. add src_cid
3. add road_dist
4. identify duplicates
*/

-- update 'use = 0'; those points not within a quarter mile of an aquatic feature
update rec_access.access_a set use = use + 10
where acs_a_id in
(select acs_a_id 
from rec_access.access_a a,
rec_source.nhd_flowline b
where
use in (1,2)
and st_dwithin(a.geom, b.geom, 402.25));
update rec_access.access_a set use = use + 10
where acs_a_id in
(select acs_a_id 
from rec_access.access_a a,
rec_source.nhd_area_wtrb b
where
use in (1,2)
and st_dwithin(a.geom, b.geom, 402.25));
update rec_access.access_a set use = use + 10
where acs_a_id in
(select acs_a_id 
from rec_access.access_a a,
rec_source.pub_fish_lake_dump b
where
use in (1,2)
and st_dwithin(a.geom, b.geom, 402.25));
--
update rec_access.access_a set use = 0, use_why = 'not within a quarter-mile of an aquatic feature.' where use = 1;
update rec_access.access_a set use = use-10 where use in (11,12);

-- done updating use
select use, count(*) from rec_access.access_a group by use;

-- grouping (by facil_code, distance)
drop table groups;
create temp table groups as
select row_number() over() as rid, row_number() over(partition by facil_code) as group_id, facil_code, geom FROM
(select facil_code, (st_dump(st_union(st_buffer(geom, 402.25/2)))).geom from rec_access.access_a -- buffer by half grouping distance
where use != 0
group by facil_code) dump;

update rec_access.access_a set group_id = null where use = 0;
-- add to join_fid
-- alter table rec_access.access_a add column group_id int;
update rec_access.access_a set group_id =
groups.group_id 
from groups
where access_a.facil_code = groups.facil_code
and access_a.facil_code = 'afsh' -- for just resetting a specific facil_code
and st_intersects(access_a.geom, groups.geom);
-- after table finalized and manual use checks/edits, can update by facil_code as needed

-- number of groups
select facil_code, count(distinct group_id) from rec_access.access_a 
where use != 0
group by facil_code;

-- should be null
select * from rec_access.access_a where group_id is null;

-- finalize table
UPDATE rec_access.access_a a SET src_cid =
	(SELECT b.table_name || '_' || lpad(a.src_id::text, 6, '0') FROM
	lookup.src_table b
	WHERE a.src_table = b.table_name)
	where src_cid is null; -- if just updating new points, leave this
-- update distance to closest road
UPDATE rec_access.access_a a SET road_dist = 
	(SELECT dist from
	(SELECT distinct on (acs_a_id) acs_a_id, st_distance(a.geom, b.geom)::numeric(7,2) dist FROM
	rec_access.access_a a,
	roads.tiger_2018 b
	where st_dwithin(a.geom, b.geom, 1000) -- run progressively at 100, 1000, 10000
	and b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500')
	order by acs_a_id, st_distance(a.geom, b.geom) asc) b
where a.acs_a_id = b.acs_a_id)
where a.road_dist is null;

-- exact duplicates to use = 0
update rec_access.access_a set use = 0, use_why = 'exact duplicate with same facil_code' WHERE acs_a_id IN
(select distinct a1 FROM
(
select distinct on (greatest(a.acs_a_id, b.acs_a_id) || '-' || least(a.acs_a_id, b.acs_a_id))
 greatest(a.acs_a_id, b.acs_a_id) a1, least(a.acs_a_id, b.acs_a_id) a2
 from rec_access.access_a a, rec_access.access_a b 
 where a.use != 0 and b.use != 0 and 
 a.acs_a_id != b.acs_a_id and 
 a.facil_code = b.facil_code and 
 st_intersects(a.geom, b.geom)
 ) sub);
--


/*
"boat_access";1;232
"bwt_sites";1;219
"pub_fish_lake_dump";2;170
"public_beaches_polys";2;131
"scenic_rivers";2;11
"stocked_trout_reaches";2;191
"va_public_access";1;219
"vatrailheads";1;340
*/

-- end rec_access.access_a

vacuum analyze rec_access.access_a;
vacuum analyze rec_access.access_t;

-- no mixing of use = 1/2 in fish or watercraft within groups
select facil_code, group_id, count(*) from
(select distinct facil_code, group_id, use from rec_access.access_a --where facil_code = 'afsh'
) a
group by facil_code, group_id having count(*) > 1;


-- SUMMARIES

select src_table, facil_code, use, count(*) from rec_access.access_a
where use != 0
group by src_table, facil_code, use
order by facil_code, use;
-- 1486 total use points (non-0)

-- total groups (for service areas)
select facil_code, count(distinct join_fid) from rec_access.access_a
group by facil_code;
"afsh";740
"agen";-
"aswm";130
"awct";719
-- these will need distinct service areas (n = 1134). But we're generating aquatic areas, so this isn't what will be used.
select facil_code, join_table, join_fid, count(*) from rec_access.access_a where use <> 0
group by facil_code, join_table, join_fid
order by count(*) desc;

--terrestrial number of groups
select facil_code, count(distinct join_fid) from rec_access.access_t
group by facil_code;
"tlnd";2784
"ttrl";946
-- these will need distinct service areas (n = 3729)
select facil_code, join_table, join_fid, count(*) from rec_access.access_t where use <> 0
group by facil_code, join_table, join_fid
order by count(*) desc;
-- some are exact same (1) point of access - service area could be re-used. might be worth doing if SA generation takes too long.
select * from 
	(select acs_t_id attrl, src_table, src_id from rec_access.access_t where use <> 0 and 
	join_fid IN
	(select join_fid from rec_access.access_t where use <> 0 and facil_code = 'ttrl'
	group by join_fid
	having count(*) = 1)) a
	JOIN
	(select acs_t_id atlnd, src_table, src_id from rec_access.access_t where use <> 0 and 
	join_fid IN
	(select join_fid from rec_access.access_t where use <> 0 and facil_code = 'tlnd'
	group by join_fid
	having count(*) = 1)) b
using (src_table, src_id);
-- 674 with same 1 point of access. Same SA but different score.

 -- SUMMARY
select src_table, facil_code, use_why, count(*) from rec_access.access_t
where use != 0
group by src_table, facil_code, use_why
order by src_table, facil_code, use_why;

-- short trails included
select * from rec_access.access_t where join_score < 1 and facil_code = 'ttrl' order by join_score asc;
-- small polygons included
select * from rec_access.access_t where join_score < 0.5 and facil_code = 'tlnd' order by join_score asc; 
*/

