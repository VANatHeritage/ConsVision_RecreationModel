/*
Facilities tables for recreation model.

Creates new 'all_facil' and 'all_facil_aqua' tables,
and populates them with point features associated with
recreational facilities from original source tables.
Tables are used as input for network analyst runs
in ArcGIS.

Author: David Bucklin

Last update: 2017-11-17
*/

-- Create facilities.all_facil
drop table facilities.all_facil;
CREATE TABLE facilities.all_facil
(
  all_facil_id serial NOT NULL,
  facil_code character varying references lookup.facil_type (facil_code),
  src_table character varying references lookup.src_table (table_name),
  src_id integer,
  src_cid character(11),
  plxu_fid integer,
  plxu_area double precision,
  road_dist double precision,
  use_why character varying,
  geom geometry(Point,900914),
  CONSTRAINT all_facil_pkey PRIMARY KEY (all_facil_id),
  CONSTRAINT all_facil_src_table_src_id_geom_key UNIQUE (src_table, src_id, plxu_fid, geom)
);


/* Public lands preprocessing
Starting from pub_lands_dissolve
1. group all within 50m into multipolygons
2. table is pub_lands_expl_union
*/

SELECT distinct st_isvalid(st_makevalid(geom)) from rec_source.pub_lands_dissolve;

-- cluster within 50m, transform to roads srid = 900914
DROP TABLE rec_source.pub_lands_expl_union;
CREATE TABLE rec_source.pub_lands_expl_union AS
SELECT row_number() over() as fid, 'pub_lands_dissolve'::text as src_table, a.geom geom FROM 
	(SELECT st_setsrid(st_collectionextract(unnest(ST_ClusterWithin(st_transform(geom, 900914), 50)),3),900914) geom from rec_source.pub_lands_dissolve) a;
ALTER TABLE rec_source.pub_lands_expl_union ALTER COLUMN geom TYPE geometry('MultiPolygon',900914);
ALTER TABLE rec_source.pub_lands_expl_union ADD PRIMARY KEY (fid);
CREATE INDEX pub_lands_expl_union_geomidx ON rec_source.pub_lands_expl_union USING gist (geom);

-- Trail pre-processing
-- group all trails intersecting for managed_trails (names are not all attributed like in state_trails)
-- used clusterwithin here to group trail segments within 30m of one another
drop table rec_source.managed_trails_union;
CREATE TABLE rec_source.managed_trails_union AS 
select row_number() over () as fid, st_force2d(geom) as geom FROM
	(SELECT st_setsrid(st_collectionextract(unnest(ST_ClusterWithin(ST_Transform(geom, 900914), 30)),2),900914) geom FROM rec_source.managed_trails) a;
ALTER TABLE rec_source.managed_trails_union ALTER COLUMN geom TYPE geometry('MultiLinestring',900914);
ALTER TABLE rec_source.managed_trails_union ADD PRIMARY KEY (fid);
CREATE INDEX managed_trails_union_geomidx ON rec_source.managed_trails_union USING gist (geom);

-- add new source tables to lookup table
INSERT INTO lookup.src_table (table_name, facil_code) VALUES ('pub_lands_expl', 'terr');
INSERT INTO lookup.src_table (table_name, facil_code) VALUES ('pub_lands_expl_union', 'terr');
INSERT INTO lookup.src_table (table_name, facil_code) VALUES ('managed_trails_union', 'terr');
INSERT INTO lookup.src_table (table_name, facil_code) VALUES ('pub_lands_aqua_union', 'aqua');
INSERT INTO lookup.src_table (table_name, facil_code) VALUES ('scenic_rivers', 'aqua');

-- verify
SELECT table_name from information_schema.tables where table_schema = 'rec_source' AND table_name NOT IN (select table_name from lookup.src_table);

/* Trailheads
1. insert those within 500m of public lands or trails (managed_trails, state_trails)
2. insertion is hierarchical (trailheads can only get included via one method)
2. don't include isolated trailheads
*/
-- this temp table could be used to exclude public lands exploded polygons from consideration by themselves (they are within 500m of a facility (add new as they come);
CREATE TEMP TABLE pub_land_ints AS 
	SELECT 'trailheads' as src_table, a.ogc_fid trl_ogr_fid, b.ogc_fid pub_ogr_fid, b.fid pub_fid, st_area(b.geom) as pub_expl_area, st_intersects(st_transform(a.geom, 900914), b.geom) as inter
	FROM rec_source.trailheads a, rec_source.pub_lands_expl b
	where st_dwithin(st_transform(a.geom, 900914), b.geom, 500)
	union all
	SELECT 'bwt_sites' as src_table, a.ogc_fid trl_ogr_fid, b.ogc_fid pub_ogr_fid, b.fid pub_fid, st_area(b.geom) as pub_expl_area, st_intersects(st_transform(a.geom, 900914), b.geom) as inter
	FROM rec_source.bwt_sites a, rec_source.pub_lands_expl b
	where st_dwithin(st_transform(a.geom, 900914), b.geom, 500);

select distinct pub_ogr_fid from pub_land_ints where inter;

select distinct plxu_fid from facilities.all_facil where src_table != 'pub_lands_expl_union';
select * from pub_land_ints where inter limit 100;
select min(plxu_fid) from facilities.all_facil;

/* associating points with pub_lands_expl
1. if intersecting 
	- if multiple intersecting, choose smallest by area
2. if not intersecting but within 500m
	- if multiple, choose closest
3. if not within 500m 
	- remove trailhead
	- add solo bwt site
	
-- pub_lands_expl
with remaining exploded un-associated pub_lands_expl:
1. add intersections with roads
2. if no road intersections, choose closest point on boundary to a road
*/

-- intersecting pub_lands 
-- (trailheads would be duplicated when intersecting multiple (overlapping) public lands, except if using pub_lands_expl_union)
INSERT INTO facilities.all_facil (facil_code, src_table, src_id, plxu_fid, plxu_area, use_why, geom) 
	SELECT 'terr', 'trailheads', a.ogc_fid, b.fid, round(st_area(b.geom)::numeric/10000,8), 'intersects pub_lands_expl_union', st_transform(st_force2d(a.geom), 900914) 
	FROM rec_source.trailheads a, rec_source.pub_lands_expl_union b
	WHERE st_intersects(st_transform(a.geom, 900914), b.geom);
select * from facilities.all_facil where src_table = 'trailheads';

-- within a distance of pub_lands (500m) -> associate with closest
INSERT INTO facilities.all_facil (facil_code, src_table, src_id, plxu_fid, plxu_area, use_why, geom) 
	SELECT distinct on (a.ogc_fid) 'terr', 'trailheads', a.ogc_fid, b.fid, round(st_area(b.geom)::numeric/10000,8), 'within 500m pub_lands_expl_union', st_transform(st_force2d(a.geom), 900914) 
	FROM rec_source.trailheads a, rec_source.pub_lands_expl_union b
	WHERE st_dwithin(st_transform(a.geom, 900914), b.geom, 500)
	AND a.ogc_fid NOT IN (SELECT distinct src_id FROM facilities.all_facil WHERE src_table = 'trailheads')
	order by a.ogc_fid, st_distance(st_transform(a.geom, 900914), b.geom) asc;

-- within a distance of state_trails (500m) - associate with closest
INSERT INTO facilities.all_facil (facil_code, src_table, src_id, use_why, geom) 
	SELECT distinct on (a.ogc_fid) 'terr', 'trailheads', a.ogc_fid, 'within 500m state_trails', st_transform(st_force2d(a.geom), 900914) 
	FROM rec_source.trailheads a, rec_source.state_trails b
	WHERE st_dwithin(st_transform(a.geom, 3857), b.geom, 500)
	AND a.ogc_fid NOT IN (SELECT distinct src_id FROM facilities.all_facil WHERE src_table = 'trailheads')
	order by a.ogc_fid, st_distance(st_transform(a.geom, 3857), b.geom) asc; -- not really necessary since not taking ids of trails

-- within a distance of managed_trails_union (500m) - associate with closest
INSERT INTO facilities.all_facil (facil_code, src_table, src_id, use_why, geom) 
	SELECT distinct on (a.ogc_fid) 'terr', 'trailheads', a.ogc_fid, 'within 500m managed_trails_union', st_transform(st_force2d(a.geom), 900914) 
	FROM rec_source.trailheads a, rec_source.managed_trails_union b
	WHERE st_dwithin(st_transform(a.geom, 900914), b.geom, 500)
	AND a.ogc_fid NOT IN (SELECT distinct src_id FROM facilities.all_facil WHERE src_table = 'trailheads')
	order by a.ogc_fid, st_distance(st_transform(a.geom, 900914), b.geom) asc; -- not really necessary since not taking ids of trails

-- checks
select ogc_fid from rec_source.trailheads where ogc_fid not in (select distinct src_id from facilities.all_facil where src_table = 'trailheads');
-- 77 trailheads not meeting criteria
select count(distinct src_id) from facilities.all_facil where src_table = 'trailheads';
select src_id, count(src_id) from facilities.all_facil where src_table = 'trailheads' group by src_id order by count(src_id) desc;
-- 1519 distinct trailheads

/* BWT sites
1. include those intersecting pub_lands
2. include the rest on their own
*/

-- intersecting pub_lands 
-- (bwt sites can be duplicated when intersecting multiple (overlapping) public lands)
INSERT INTO facilities.all_facil (facil_code, src_table, src_id, plxu_fid, plxu_area, use_why, geom) 
	SELECT 'terr', 'bwt_sites', a.ogc_fid, b.fid, round(st_area(b.geom)::numeric/10000,8), 'intersects pub_lands_expl', st_transform(st_force2d(a.geom), 900914) 
	FROM rec_source.bwt_sites a, rec_source.pub_lands_expl_union b
	WHERE st_intersects(st_transform(a.geom, 900914), b.geom);

-- within a distance of pub_lands (500m) - only associate with closest polygon
INSERT INTO facilities.all_facil (facil_code, src_table, src_id, plxu_fid, plxu_area, use_why, geom) 
	SELECT distinct on (a.ogc_fid) 'terr', 'bwt_sites', a.ogc_fid, b.fid, round(st_area(b.geom)::numeric/10000,8), 'within 500m pub_lands_expl', st_transform(st_force2d(a.geom), 900914) 
	FROM rec_source.bwt_sites a, rec_source.pub_lands_expl_union b
	WHERE st_dwithin(st_transform(a.geom, 900914), b.geom, 500)
	and a.ogc_fid not in (SELECT distinct src_id from facilities.all_facil where src_table = 'bwt_sites')
	order by a.ogc_fid, st_distance(st_transform(a.geom, 900914), b.geom) asc;

-- solo bwt sites (not intersecting public lands)
INSERT INTO facilities.all_facil (facil_code, src_table, src_id, use_why, geom)
	SELECT 'terr', 'bwt_sites', a.ogc_fid, 'solo bwt site', st_transform(st_force2d(a.geom), 900914)
	FROM rec_source.bwt_sites a
	where a.ogc_fid not in (SELECT distinct src_id from facilities.all_facil where src_table = 'bwt_sites');

-- checks
select src_id, count(src_id) from facilities.all_facil where src_table = 'bwt_sites' group by src_id order by count(src_id) desc;
-- 635 bwt sites


/* Public lands (pub_lands_expl)
1. include only those not already represented in other ways (by plxu_fid)
2. first intersect with roads (excluding a couple road types in query)
3. include closest point to roads for those not represented any other way
*/ 

-- pub_lands_expl intersecting roads
-- pub_lands
INSERT INTO facilities.all_facil (facil_code, src_table, plxu_fid, plxu_area, use_why, geom) 
SELECT DISTINCT 'terr', 'pub_lands_expl_union', a.fid, round(st_area(a.geom)::numeric/10000,8), 'boundary intersects road', (st_dump(st_intersection(st_boundary(a.geom), b.geom))).geom FROM 	
		rec_source.pub_lands_expl_union a,
		roads.va_centerline b
		where st_intersects(st_boundary(a.geom), b.geom)
		and a.fid NOT IN (SELECT DISTINCT plxu_fid FROM facilities.all_facil where plxu_fid is not null)
		and b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500', -- excluded from analysis
		'S1100','S1100HOV','S1640'); -- these are limited access higways

--SELECT * FROM facilities.all_facil where plxu_fid is not null;

-- closest points for non-intersecting pub_lands_expl
select fid from rec_source.pub_lands_expl_union where fid not in (SELECT DISTINCT plxu_fid FROM facilities.all_facil where plxu_fid is not null);
-- 1080
INSERT INTO facilities.all_facil (facil_code, src_table, plxu_fid, plxu_area, use_why, geom)
SELECT DISTINCT ON (a.fid) 'terr', 'pub_lands_expl_union', a.fid, round(st_area(a.geom)::numeric/10000,8),'closest point on boundary to road', st_closestpoint(a.geom, b.geom) geom FROM
		rec_source.pub_lands_expl_union a,
		roads.va_centerline b 
		where st_dwithin(a.geom, b.geom, 100) -- manually adjust here with increasingly higher values to speed up/provide cutoff for polys > a distance to closest road
		and a.fid NOT IN (SELECT DISTINCT plxu_fid FROM facilities.all_facil where plxu_fid is not null)
		AND b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500', -- excluded from analysis
		'S1100','S1100HOV','S1640')
		ORDER BY a.fid, ST_Distance(a.geom,b.geom) asc;
INSERT INTO facilities.all_facil (facil_code, src_table, plxu_fid, plxu_area, use_why, geom)
SELECT DISTINCT ON (a.fid) 'terr', 'pub_lands_expl_union', a.fid, round(st_area(a.geom)::numeric/10000,8),'closest point on boundary to road', st_closestpoint(a.geom, b.geom) geom FROM
		rec_source.pub_lands_expl_union a,
		roads.va_centerline b 
		where st_dwithin(a.geom, b.geom, 1000) -- manually adjust here with increasingly higher values to speed up/provide cutoff for polys > a distance to closest road
		and a.fid NOT IN (SELECT DISTINCT plxu_fid FROM facilities.all_facil where plxu_fid is not null)
		AND b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500', -- excluded from analysis
		'S1100','S1100HOV','S1640')
		ORDER BY a.fid, ST_Distance(a.geom,b.geom) asc;
INSERT INTO facilities.all_facil (facil_code, src_table, plxu_fid, plxu_area, use_why, geom)
SELECT DISTINCT ON (a.fid) 'terr', 'pub_lands_expl_union', a.fid, round(st_area(a.geom)::numeric/10000,8),'closest point on boundary to road', st_closestpoint(a.geom, b.geom) geom FROM
		rec_source.pub_lands_expl_union a,
		roads.va_centerline b 
		where st_dwithin(a.geom, b.geom, 10000) -- manually adjust here with increasingly higher values to speed up/provide cutoff for polys > a distance to closest road
		and a.fid NOT IN (SELECT DISTINCT plxu_fid FROM facilities.all_facil where plxu_fid is not null)
		AND b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500', -- excluded from analysis
		'S1100','S1100HOV','S1640')
		ORDER BY a.fid, ST_Distance(a.geom,b.geom) asc;

select count(distinct plxu_fid) from facilities.all_facil;
select count(*) from rec_source.pub_lands_expl_union;


/*post-processing terrestrial facilities
1. add src_cid
2. add road_dist
3. identify (near) duplicates
*/

ALTER TABLE lookup.src_table ADD COLUMN table_code CHARACTER(4) UNIQUE;
-- add codes manually
-- update src_cid (combo table + ogc_fid ID)

-- first update NULL src_cid (pub_land_expl_union)
UPDATE facilities.all_facil SET src_id = plxu_fid
where src_id is null and src_table = 'pub_lands_expl_union';

UPDATE facilities.all_facil a SET src_cid =
	(SELECT b.table_code || '_' || lpad(a.src_id::text, 6, '0') FROM
	lookup.src_table b
	WHERE a.src_table = b.table_name)
	where src_cid is null; -- if just updating new points, leave this

select * from facilities.all_facil where src_cid is null;
-- update distance to closest road
UPDATE facilities.all_facil a SET road_dist = 
	(SELECT dist from
	(SELECT distinct on (all_facil_id) all_facil_id, st_distance(a.geom, b.geom)::numeric(6,2) dist FROM
	facilities.all_facil a,
	roads.va_centerline b
	where st_dwithin(a.geom, b.geom, 100) -- run progressively at 100, 1000, 10000
	and b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500')
	order by all_facil_id, st_distance(a.geom, b.geom) asc) b
where a.all_facil_id = b.all_facil_id)
where a.road_dist is null;
UPDATE facilities.all_facil a SET road_dist = 
	(SELECT dist from
	(SELECT distinct on (all_facil_id) all_facil_id, st_distance(a.geom, b.geom)::numeric(6,2) dist FROM
	facilities.all_facil a,
	roads.va_centerline b
	where st_dwithin(a.geom, b.geom, 1000) -- run progressively at 100, 1000, 10000
	and b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500')
	order by all_facil_id, st_distance(a.geom, b.geom) asc) b
where a.all_facil_id = b.all_facil_id)
where a.road_dist is null;
UPDATE facilities.all_facil a SET road_dist = 
	(SELECT dist from
	(SELECT distinct on (all_facil_id) all_facil_id, st_distance(a.geom, b.geom)::numeric(6,2) dist FROM
	facilities.all_facil a,
	roads.va_centerline b
	where st_dwithin(a.geom, b.geom, 10000) -- run progressively at 100, 1000, 10000
	and b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500')
	order by all_facil_id, st_distance(a.geom, b.geom) asc) b
where a.all_facil_id = b.all_facil_id)
where a.road_dist is null;

select * from facilities.all_facil where road_dist is null;

begin;
delete from facilities.all_facil where all_facil_id IN (
select a2 FROM
(select distinct on (greatest(a.all_facil_id, b.all_facil_id) || '-' || least(a.all_facil_id, b.all_facil_id))
 a.all_facil_id a1, b.all_facil_id a2 from facilities.all_facil a, facilities.all_facil b where a.all_facil_id != b.all_facil_id and st_intersects(a.geom, b.geom)) sub
 );
-- there are 40 duplicates in trailheads/bwt_sites
commit;

-- points within 1m of one another, that also fall on a road (remove one of each pair from table)
begin;
delete from facilities.all_facil where all_facil_id IN (
select a2 from
(select distinct on (greatest(a.all_facil_id, b.all_facil_id) || '-' || least(a.all_facil_id, b.all_facil_id))
a.all_facil_id a1, a.src_table, b.all_facil_id a2, b.src_table, st_distance(a.geom, b.geom) from
(select a.all_facil_id, a.src_table, a.geom, c.ogc_fid
from facilities.all_facil a,
roads.va_centerline c
where st_intersects(st_buffer(a.geom,0.00001), c.geom)) a,
(select a.all_facil_id, a.src_table, a.geom, c.ogc_fid
from facilities.all_facil a,
roads.va_centerline c
where st_intersects(st_buffer(a.geom,0.00001), c.geom)) b
where a.all_facil_id != b.all_facil_id
and not st_intersects(a.geom,b.geom)
and st_dwithin(a.geom, b.geom, 1)
and a.ogc_fid = b.ogc_fid
order by 
(greatest(a.all_facil_id, b.all_facil_id) || '-' || least(a.all_facil_id, b.all_facil_id)),
a.all_facil_id) sub
);
-- 18 cases of this
commit;


/* Aquatic facilities
Includes water_access, boat_access, pub_fish_lake, stocked_trout_reaches and beach_access

1. first associate point access features with lakes
2. include others solo
3. for non-included lakes, add intersections with roads
4. add closest point on lake edge to roads for remained of lakes
*/

drop table facilities.all_facil_aqua;
CREATE TABLE facilities.all_facil_aqua
(
  all_facil_id serial NOT NULL PRIMARY KEY,
  facil_code character varying references lookup.facil_type (facil_code),
  src_table character varying references lookup.src_table (table_name),
  src_id integer,
  src_cid character(11),
  plau_fid integer,
  plau_area double precision,
  road_dist double precision,
  use_why character varying,
  geom geometry(Point,900914),
  CONSTRAINT afa_uniq_key UNIQUE (src_table, src_id, plau_fid, geom)
);

-- public lands aqua (canoe only and public fishing lakes)
DROP TABLE rec_source.pub_lands_aqua_union;
CREATE TABLE rec_source.pub_lands_aqua_union AS
SELECT row_number() over() as fid, src_table, a.geom geom FROM 
	(SELECT 'pub_lands_dissolve_aqua'::text as src_table,
	 st_setsrid(st_collectionextract(unnest(ST_ClusterWithin(st_transform(geom, 900914), 50)),3),900914) geom from (select (st_dump(geom)).geom from rec_source.pub_lands_dissolve_aqua) dump 
	 UNION ALL 
	 SELECT 'pub_fish_lake'::text as src_table,
	 st_setsrid(st_collectionextract(unnest(ST_ClusterWithin(st_transform(geom, 900914), 50)),3),900914) geom from (select (st_dump(geom)).geom from rec_source.pub_fish_lake) dump) a;	 
ALTER TABLE rec_source.pub_lands_aqua_union ALTER COLUMN geom TYPE geometry('MultiPolygon',900914);
ALTER TABLE rec_source.pub_lands_aqua_union ADD PRIMARY KEY (fid);
CREATE INDEX plau_geomidx ON rec_source.pub_lands_aqua_union USING gist (geom);

-- investigating lake/poly relationships
select a.ogc_fid from rec_source.pub_lands_dissolve_aqua a, rec_source.pub_fish_lake b where st_intersects(st_transform(a.geom,900914), st_transform(b.geom,900914));
-- not a problem -no overlap between these polygons
-- 193
select count(*) from rec_source.boat_access;
-- 236
select count(*) from rec_source.water_access;
-- 335

select distinct b.fid from rec_source.boat_access a, 
	rec_source.pub_lands_aqua_union b
	where st_dwithin(st_transform(a.geom,900914), b.geom, 500);

select distinct b.fid from rec_source.water_access a, 
	rec_source.pub_lands_aqua_union b
	where st_dwithin(st_transform(a.geom,900914), b.geom, 500);

drop table pub_lands_aqua_union_ints;
CREATE TEMP TABLE pub_lands_aqua_union_ints AS 
	SELECT 'boat_access', a.ogc_fid acc_ogr_fid, b.fid pub_lands_aqua_union_fid
	FROM rec_source.boat_access a, rec_source.pub_lands_aqua_union b
	where st_dwithin(st_transform(a.geom, 900914), b.geom, 500)
	union all
	SELECT 'water_access', a.ogc_fid acc_ogr_fid, b.fid pub_lands_aqua_union_fid
	FROM rec_source.water_access a, rec_source.pub_lands_aqua_union b
	where st_dwithin(st_transform(a.geom, 900914), b.geom, 500);
select distinct pub_lands_aqua_union_fid from pub_lands_aqua_union_ints;
-- 66

/* boat access 
1. find those inside fishing lake polygons
2. find those within 500m of fishing lake polygons
3. add remaining sites
*/

delete from facilities.all_facil_aqua where src_table = 'boat_access';
INSERT INTO facilities.all_facil_aqua (facil_code, src_table, src_id, plau_fid, plau_area, use_why, geom) 
	SELECT 'aqua', 'boat_access', a.ogc_fid, b.fid, round(st_area(b.geom)::numeric/10000,8), 'intersects pub_lands_aqua_union', st_transform(a.geom, 900914) 
	FROM rec_source.boat_access a, rec_source.pub_lands_aqua_union b
	WHERE st_intersects(st_transform(a.geom, 900914), b.geom);

-- within a distance of pub_lands (500m) -> only associate trailhead with closest (unused) polygon
INSERT INTO facilities.all_facil_aqua (facil_code, src_table, src_id, plau_fid, plau_area, use_why, geom) 
	SELECT distinct on (a.ogc_fid) 'aqua', 'boat_access', a.ogc_fid, b.fid, round(st_area(b.geom)::numeric/10000,8), 'within 500m pub_lands_aqua_union', st_transform(a.geom, 900914) 
	FROM rec_source.boat_access a, rec_source.pub_lands_aqua_union b
	WHERE st_dwithin(st_transform(a.geom, 900914), b.geom, 500)
	AND a.ogc_fid NOT IN (SELECT distinct src_id FROM facilities.all_facil_aqua WHERE src_table = 'boat_access')
	order by a.ogc_fid, st_distance(st_transform(a.geom, 900914), b.geom) asc;

-- solo sites
INSERT INTO facilities.all_facil_aqua (facil_code, src_table, src_id, use_why, geom)
	SELECT 'aqua', 'boat_access', a.ogc_fid, 'solo boat_access site', st_transform(a.geom, 900914)
	FROM rec_source.boat_access a
	where a.ogc_fid not in (SELECT distinct src_id from facilities.all_facil_aqua where src_table = 'boat_access');


/* water_access
-- exclude all within 30m of boat_access point (likely duplicates)
1. find those inside fishing lake polygons
2. find those within 500m of fishing lake polygons
3. add remaining sites
*/
delete from facilities.all_facil_aqua where src_table = 'water_access';
INSERT INTO facilities.all_facil_aqua (facil_code, src_table, src_id,  plau_fid, plau_area, use_why, geom) 
	SELECT 'aqua', 'water_access', a.ogc_fid, b.fid, round(st_area(b.geom)::numeric/10000,8), 'intersects pub_lands_aqua_union', st_transform(a.geom, 900914) 
	FROM (select * from rec_source.water_access where ogc_fid not in 
		(select distinct a.ogc_fid from rec_source.water_access a, rec_source.boat_access b where st_dwithin(st_transform(a.geom, 900914), st_transform(b.geom, 900914), 30))) a,
	rec_source.pub_lands_aqua_union b
	WHERE st_intersects(st_transform(a.geom, 900914), b.geom);

-- within a distance of pub_lands (500m) -> only associate trailhead with closest (unused) polygon
INSERT INTO facilities.all_facil_aqua (facil_code, src_table, src_id, plau_fid, plau_area, use_why, geom) 
	SELECT distinct on (a.ogc_fid) 'aqua', 'water_access', a.ogc_fid, b.fid, round(st_area(b.geom)::numeric/10000,8), 'within 500m pub_lands_aqua_union', st_transform(a.geom, 900914) 
	FROM (select * from rec_source.water_access where ogc_fid not in 
		(select distinct a.ogc_fid from rec_source.water_access a, rec_source.boat_access b where st_dwithin(st_transform(a.geom, 900914), st_transform(b.geom, 900914), 30))) a,
	rec_source.pub_lands_aqua_union b
	WHERE st_dwithin(st_transform(a.geom, 900914), b.geom, 500)
	AND a.ogc_fid NOT IN (SELECT distinct src_id FROM facilities.all_facil_aqua WHERE src_table = 'water_access')
	order by a.ogc_fid, st_distance(st_transform(a.geom, 900914), b.geom) asc;
	
-- solo sites
INSERT INTO facilities.all_facil_aqua (facil_code, src_table, src_id, use_why, geom)
	SELECT 'aqua', 'water_access', a.ogc_fid, 'solo water_access site', st_transform(a.geom, 900914)
	FROM (select * from rec_source.water_access where ogc_fid not in 
		(select distinct a.ogc_fid from rec_source.water_access a, rec_source.boat_access b where st_dwithin(st_transform(a.geom, 900914), st_transform(b.geom, 900914), 30))) a
	where a.ogc_fid not in (SELECT distinct src_id from facilities.all_facil_aqua where src_table = 'water_access');


/* bwt sites
Only include those within 500m of aqua lands
*/

INSERT INTO facilities.all_facil_aqua (facil_code, src_table, src_id,  plau_fid, plau_area, use_why, geom) 
	SELECT 'aqua', 'bwt_sites', a.ogc_fid, b.fid, round(st_area(b.geom)::numeric/10000,8), 'intersects pub_lands_aqua_union', st_transform(a.geom, 900914) 
	FROM rec_source.bwt_sites a, rec_source.pub_lands_aqua_union b
	WHERE st_intersects(st_transform(a.geom, 900914), b.geom);

-- within a distance of pub_lands (500m)
INSERT INTO facilities.all_facil_aqua (facil_code, src_table, src_id, plau_fid, plau_area, use_why, geom) 
	SELECT distinct on (a.ogc_fid) 'aqua', 'bwt_sites', a.ogc_fid, b.fid, round(st_area(b.geom)::numeric/10000,8), 'within 500m pub_lands_aqua_union', st_transform(a.geom, 900914) 
	FROM rec_source.bwt_sites a, rec_source.pub_lands_aqua_union b
	WHERE st_dwithin(st_transform(a.geom, 900914), b.geom, 500)
	AND a.ogc_fid NOT IN (SELECT distinct src_id FROM facilities.all_facil_aqua WHERE src_table = 'bwt_sites')
	order by a.ogc_fid, st_distance(st_transform(a.geom, 900914), b.geom) asc;

/* pub_lands_aqua_union
1. Exclude those already covered by <500m from boat_access or water_access
2. Include all intersections for road-intersecting lakes
3. include closest point on lake to road for remainder
*/
INSERT INTO facilities.all_facil_aqua (facil_code, src_table, src_id, plau_fid, plau_area, use_why, geom) 
SELECT DISTINCT 'aqua', 'pub_lands_aqua_union', a.fid, a.fid, round(st_area(a.geom)::numeric/10000,8), 'boundary intersects road', (st_dump(st_intersection(st_boundary(st_transform(a.geom,900914)), b.geom))).geom FROM 	
		rec_source.pub_lands_aqua_union a,
		roads.va_centerline b
		where st_intersects(st_boundary(st_transform(a.geom,900914)), b.geom)
		and a.fid NOT IN (select distinct plau_fid from facilities.all_facil_aqua where plau_fid is not null) -- excludes lakes/aqua lands which are within 500m of access points
		and b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500', -- excluded from analysis
		'S1100','S1100HOV','S1640');
select count(*) from facilities."all_facil_aqua_OLD11_17" where src_table = 'pub_lands_aqua_union' and use_why = 'boundary intersects road';
select count(*) from facilities."all_facil_aqua" where src_table = 'pub_lands_aqua_union' and use_why = 'boundary intersects road';

-- closest points for non-intersecting
select distinct fid from rec_source.pub_lands_aqua_union where fid not in (select plau_fid from facilities.all_facil_aqua);
-- 103
delete from facilities.all_facil_aqua where src_table = 'pub_lands_aqua_union' and use_why = 'closest point on boundary to road';
INSERT INTO facilities.all_facil_aqua (facil_code, src_table, src_id, plau_fid, plau_area, use_why, geom)
SELECT DISTINCT ON (a.fid) 'aqua', 'pub_lands_aqua_union', a.fid, a.fid, round(st_area(a.geom)::numeric/10000,8),'closest point on boundary to road', st_closestpoint(st_transform(a.geom,900914), b.geom) geom FROM
		rec_source.pub_lands_aqua_union a,
		roads.va_centerline b 
		where st_dwithin(st_transform(a.geom,900914), b.geom, 100) -- manually adjust here with increasingly higher values to speed up/provide cutoff for polys > a distance to closest road
		and a.fid not in (select distinct plau_fid from facilities.all_facil_aqua where plau_fid is not null)
		AND b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500', -- excluded from analysis
		'S1100','S1100HOV','S1640')
		ORDER BY a.fid, ST_Distance(st_transform(a.geom,900914),b.geom) asc;
INSERT INTO facilities.all_facil_aqua (facil_code, src_table, src_id, plau_fid, plau_area, use_why, geom)
SELECT DISTINCT ON (a.fid) 'aqua', 'pub_lands_aqua_union', a.fid, a.fid, round(st_area(a.geom)::numeric/10000,8),'closest point on boundary to road', st_closestpoint(st_transform(a.geom,900914), b.geom) geom FROM
		rec_source.pub_lands_aqua_union a,
		roads.va_centerline b 
		where st_dwithin(st_transform(a.geom,900914), b.geom, 1000) -- manually adjust here with increasingly higher values to speed up/provide cutoff for polys > a distance to closest road
		and a.fid not in (select distinct plau_fid from facilities.all_facil_aqua where plau_fid is not null)
		AND b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500', -- excluded from analysis
		'S1100','S1100HOV','S1640')
		ORDER BY a.fid, ST_Distance(st_transform(a.geom,900914),b.geom) asc;
INSERT INTO facilities.all_facil_aqua (facil_code, src_table, src_id, plau_fid, plau_area, use_why, geom)
SELECT DISTINCT ON (a.fid) 'aqua', 'pub_lands_aqua_union', a.fid, a.fid, round(st_area(a.geom)::numeric/10000,8),'closest point on boundary to road', st_closestpoint(st_transform(a.geom,900914), b.geom) geom FROM
		rec_source.pub_lands_aqua_union a,
		roads.va_centerline b 
		where st_dwithin(st_transform(a.geom,900914), b.geom, 10000) -- manually adjust here with increasingly higher values to speed up/provide cutoff for polys > a distance to closest road
		and a.fid not in (select distinct plau_fid from facilities.all_facil_aqua where plau_fid is not null)
		AND b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500', -- excluded from analysis
		'S1100','S1100HOV','S1640')
		ORDER BY a.fid, ST_Distance(st_transform(a.geom,900914),b.geom) asc;
select distinct fid from rec_source.pub_lands_aqua_union where fid not in (select plau_fid from facilities.all_facil_aqua);
-- should be empty


/* stocked_trout_reaches
1. Include intersections with roads
2. for non-intersecting, include closest point
3. exclude those not inside or within 500m of pub_lands_expl_union/pub_lands_aqua_union
*/
-- using two seperate tables takes forever, merge into one temp table
create temp table publand_union as
select geom from rec_source.pub_lands_expl_union
union all
select geom from rec_source.pub_lands_aqua_union;

delete from facilities.all_facil_aqua where src_table = 'stocked_trout_reaches';
INSERT INTO facilities.all_facil_aqua (facil_code, src_table, src_id, use_why, geom) 
SELECT DISTINCT a.facil_code, a.src_table, a.src_id, a.use_why, a.geom FROM
(SELECT DISTINCT 'aqua' as facil_code, 'stocked_trout_reaches' as src_table, a.ogc_fid as src_id, 'line intersects road' as use_why, (st_dump(st_intersection(st_transform(a.geom,900914), b.geom))).geom FROM 	
		rec_source.stocked_trout_reaches a,
		roads.va_centerline b
		where st_intersects(st_transform(a.geom,900914), b.geom)
		and b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500', -- excluded from analysis
		'S1100','S1100HOV','S1640')) a,
	-- include only those falling within 500m of public lands/lakes
	publand_union c
	where (st_intersects(a.geom, c.geom) or st_dwithin(a.geom, c.geom, 500));
-- within distance incrementing	
INSERT INTO facilities.all_facil_aqua (facil_code, src_table, src_id, use_why, geom) 
SELECT DISTINCT a.facil_code, a.src_table, a.src_id, a.use_why, a.geom FROM
(SELECT DISTINCT ON (a.ogc_fid) 'aqua'::text as facil_code, 'stocked_trout_reaches'::text as src_table, a.ogc_fid as src_id, 'closest point on line to road'::text as use_why, st_closestpoint(st_transform(a.geom,900914), b.geom) geom FROM 	
		rec_source.stocked_trout_reaches a,
		roads.va_centerline b
		where st_dwithin(st_transform(a.geom,900914), b.geom, 100)
		and a.ogc_fid not in (SELECT distinct src_id from facilities.all_facil_aqua where src_table = 'stocked_trout_reaches')
		and b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500', -- excluded from analysis
		'S1100','S1100HOV','S1640')
		ORDER BY a.ogc_fid, ST_Distance(st_transform(a.geom,900914),b.geom) asc) a,
		-- include only those falling within 500m of public lands/lakes
	publand_union c
	where (st_intersects(a.geom, c.geom) or st_dwithin(a.geom, c.geom, 500));
INSERT INTO facilities.all_facil_aqua (facil_code, src_table, src_id, use_why, geom) 
SELECT DISTINCT a.facil_code, a.src_table, a.src_id, a.use_why, a.geom FROM
(SELECT DISTINCT ON (a.ogc_fid) 'aqua'::text as facil_code, 'stocked_trout_reaches'::text as src_table, a.ogc_fid as src_id, 'closest point on line to road'::text as use_why, st_closestpoint(st_transform(a.geom,900914), b.geom) geom FROM 	
		rec_source.stocked_trout_reaches a,
		roads.va_centerline b
		where st_dwithin(st_transform(a.geom,900914), b.geom, 1000)
		and a.ogc_fid not in (SELECT distinct src_id from facilities.all_facil_aqua where src_table = 'stocked_trout_reaches')
		and b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500', -- excluded from analysis
		'S1100','S1100HOV','S1640')
		ORDER BY a.ogc_fid, ST_Distance(st_transform(a.geom,900914),b.geom) asc) a,
		-- include only those falling within 500m of public lands/lakes
	publand_union c
	where (st_intersects(a.geom, c.geom) or st_dwithin(a.geom, c.geom, 500));
INSERT INTO facilities.all_facil_aqua (facil_code, src_table, src_id, use_why, geom) 
SELECT DISTINCT a.facil_code, a.src_table, a.src_id, a.use_why, a.geom FROM
(SELECT DISTINCT ON (a.ogc_fid) 'aqua'::text as facil_code, 'stocked_trout_reaches'::text as src_table, a.ogc_fid as src_id, 'closest point on line to road'::text as use_why, st_closestpoint(st_transform(a.geom,900914), b.geom) geom FROM 	
		rec_source.stocked_trout_reaches a,
		roads.va_centerline b
		where st_dwithin(st_transform(a.geom,900914), b.geom, 10000)
		and a.ogc_fid not in (SELECT distinct src_id from facilities.all_facil_aqua where src_table = 'stocked_trout_reaches')
		and b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500', -- excluded from analysis
		'S1100','S1100HOV','S1640')
		ORDER BY a.ogc_fid, ST_Distance(st_transform(a.geom,900914),b.geom) asc) a,
		-- include only those falling within 500m of public lands/lakes
	publand_union c
	where (st_intersects(a.geom, c.geom) or st_dwithin(a.geom, c.geom, 500));
select distinct ogc_fid from rec_source.stocked_trout_reaches where ogc_fid not in (select src_id from facilities.all_facil_aqua where src_table = 'stocked_trout_reaches');
-- 110 reaches excluded

/* wild and scenic rivers
1. Include intersections with roads
2. for non-intersecting, include closest point
3. exclude those not inside/within 500m of pub_lands_expl_union/pub_lands_aqua_union
*/
delete from facilities.all_facil_aqua where src_table = 'scenic_rivers';
INSERT INTO facilities.all_facil_aqua (facil_code, src_table, src_id, use_why, geom) 
SELECT DISTINCT a.facil_code, a.src_table, a.src_id, a.use_why, a.geom FROM
(SELECT DISTINCT 'aqua' as facil_code, 'scenic_rivers' as src_table, a.ogc_fid as src_id, 'line intersects road' as use_why, (st_dump(st_intersection(st_transform(st_force2d(a.geom),900914), b.geom))).geom FROM 	
		rec_source.scenic_rivers a,
		roads.va_centerline b
		where a.status = 'Designated' --only include designated rivers
		and st_intersects(st_transform(st_force2d(a.geom),900914), b.geom)
		and b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500', -- excluded from analysis
		'S1100','S1100HOV','S1640')) a, -- takes 2:25 
	-- include only those falling within 500m of public lands/lakes
		publand_union c
	where (st_intersects(a.geom, c.geom) or st_dwithin(a.geom, c.geom, 500));
-- within distance incrementing		
INSERT INTO facilities.all_facil_aqua (facil_code, src_table, src_id, use_why, geom) 
SELECT DISTINCT a.facil_code, a.src_table, a.src_id, a.use_why, a.geom FROM
(SELECT DISTINCT ON (a.ogc_fid) 'aqua'::text as facil_code, 'scenic_rivers'::text as src_table, a.ogc_fid as src_id, 'closest point on line to road'::text as use_why, st_closestpoint(st_transform(st_force2d(a.geom),900914), b.geom) geom FROM 	
		rec_source.scenic_rivers a,
		roads.va_centerline b
		where a.status = 'Designated' --only include designated rivers
		and a.ogc_fid not in (SELECT distinct src_id from facilities.all_facil_aqua where src_table = 'scenic_rivers')
		and st_dwithin(st_transform(st_force2d(a.geom),900914), b.geom, 100)
		and b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500', -- excluded from analysis
		'S1100','S1100HOV','S1640')
		ORDER BY a.ogc_fid, ST_Distance(st_transform(st_force2d(a.geom),900914),b.geom) asc) a,
		-- include only those falling within 500m of public lands/lakes
		publand_union c
	where (st_intersects(a.geom, c.geom) or st_dwithin(a.geom, c.geom, 500));
INSERT INTO facilities.all_facil_aqua (facil_code, src_table, src_id, use_why, geom) 
SELECT DISTINCT a.facil_code, a.src_table, a.src_id, a.use_why, a.geom FROM
(SELECT DISTINCT ON (a.ogc_fid) 'aqua'::text as facil_code, 'scenic_rivers'::text as src_table, a.ogc_fid as src_id, 'closest point on line to road'::text as use_why, st_closestpoint(st_transform(st_force2d(a.geom),900914), b.geom) geom FROM 	
		rec_source.scenic_rivers a,
		roads.va_centerline b
		where a.status = 'Designated' --only include designated rivers
		and a.ogc_fid not in (SELECT distinct src_id from facilities.all_facil_aqua where src_table = 'scenic_rivers')
		and st_dwithin(st_transform(st_force2d(a.geom),900914), b.geom, 1000)
		and b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500', -- excluded from analysis
		'S1100','S1100HOV','S1640')
		ORDER BY a.ogc_fid, ST_Distance(st_transform(st_force2d(a.geom),900914),b.geom) asc) a,
		-- include only those falling within 500m of public lands/lakes
		publand_union c
	where (st_intersects(a.geom, c.geom) or st_dwithin(a.geom, c.geom, 500));
INSERT INTO facilities.all_facil_aqua (facil_code, src_table, src_id, use_why, geom) 
SELECT DISTINCT a.facil_code, a.src_table, a.src_id, a.use_why, a.geom FROM
(SELECT DISTINCT ON (a.ogc_fid) 'aqua'::text as facil_code, 'scenic_rivers'::text as src_table, a.ogc_fid as src_id, 'closest point on line to road'::text as use_why, st_closestpoint(st_transform(st_force2d(a.geom),900914), b.geom) geom FROM 	
		rec_source.scenic_rivers a,
		roads.va_centerline b
		where a.status = 'Designated' --only include designated rivers
		and a.ogc_fid not in (SELECT distinct src_id from facilities.all_facil_aqua where src_table = 'scenic_rivers')
		and st_dwithin(st_transform(st_force2d(a.geom),900914), b.geom, 10000)
		and b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500', -- excluded from analysis
		'S1100','S1100HOV','S1640')
		ORDER BY a.ogc_fid, ST_Distance(st_transform(st_force2d(a.geom),900914),b.geom) asc) a,
		-- include only those falling within 500m of public lands/lakes
		publand_union c
	where (st_intersects(a.geom, c.geom) or st_dwithin(a.geom, c.geom, 500));
select distinct ogc_fid from rec_source.scenic_rivers where ogc_fid not in (select src_id from facilities.all_facil_aqua where src_table = 'scenic_rivers');
-- 133 exlcuded features


/* beaches
1. Include intersections with roads
2. for non-intersecting, include closest point
*/
INSERT INTO facilities.all_facil_aqua (facil_code, src_table, src_id, use_why, geom) 
SELECT DISTINCT 'aqua', 'public_beaches', a.ogc_fid, 'line intersects road', (st_dump(st_intersection(st_transform(a.geom,900914), b.geom))).geom FROM 	
		rec_source.public_beaches a,
		roads.va_centerline b
		where st_intersects(st_transform(a.geom,900914), b.geom)
		and b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500', -- excluded from analysis
		'S1100','S1100HOV','S1640');

INSERT INTO facilities.all_facil_aqua (facil_code, src_table, src_id, use_why, geom) 
SELECT DISTINCT ON (a.ogc_fid) 'aqua', 'public_beaches', a.ogc_fid, 'closest point on line to road', st_closestpoint(st_transform(a.geom,900914), b.geom) FROM 	
		rec_source.public_beaches a,
		roads.va_centerline b
		where st_dwithin(st_transform(a.geom,900914), b.geom, 1000)
		and a.ogc_fid not in (SELECT distinct src_id from facilities.all_facil_aqua where src_table = 'public_beaches')
		and b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500', -- excluded from analysis
		'S1100','S1100HOV','S1640')
		ORDER BY a.ogc_fid, ST_Distance(st_transform(a.geom,900914),b.geom) asc;

-- count distinct src_ids by table
select src_table, count(*) as total_for_table, count(distinct src_id) total_unique_for_table from facilities.all_facil_aqua group by src_table;

---------
-- post-processing aquatic facilities
ALTER TABLE lookup.src_table ADD COLUMN table_code CHARACTER(4) UNIQUE;
-- add codes manually
-- update src_cid (combo table + ogc_fid ID)

UPDATE facilities.all_facil_aqua a SET src_cid =
	(SELECT b.table_code || '_' || lpad(a.src_id::text, 6, '0') FROM
	lookup.src_table b
	WHERE a.src_table = b.table_name)
	where src_cid is null; -- if just updating new points, leave this

select count(*) from facilities.all_facil_aqua;

select * from facilities.all_facil_aqua where src_cid is null;
-- update distance to closest road
UPDATE facilities.all_facil_aqua a SET road_dist = 
	(SELECT dist from
	(SELECT distinct on (all_facil_id) all_facil_id, st_distance(a.geom, b.geom)::numeric(6,2) dist FROM
	facilities.all_facil_aqua a,
	roads.va_centerline b
	where st_dwithin(a.geom, b.geom, 100) -- run progressively at 100, 1000, 10000
	and b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500')
	order by all_facil_id, st_distance(a.geom, b.geom) asc) b
where a.all_facil_id = b.all_facil_id)
where a.road_dist is null;
UPDATE facilities.all_facil_aqua a SET road_dist = 
	(SELECT dist from
	(SELECT distinct on (all_facil_id) all_facil_id, st_distance(a.geom, b.geom)::numeric(6,2) dist FROM
	facilities.all_facil_aqua a,
	roads.va_centerline b
	where st_dwithin(a.geom, b.geom, 1000) -- run progressively at 100, 1000, 10000
	and b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500')
	order by all_facil_id, st_distance(a.geom, b.geom) asc) b
where a.all_facil_id = b.all_facil_id)
where a.road_dist is null;
UPDATE facilities.all_facil_aqua a SET road_dist = 
	(SELECT dist from
	(SELECT distinct on (all_facil_id) all_facil_id, st_distance(a.geom, b.geom)::numeric(6,2) dist FROM
	facilities.all_facil_aqua a,
	roads.va_centerline b
	where st_dwithin(a.geom, b.geom, 10000) -- run progressively at 100, 1000, 10000
	and b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500')
	order by all_facil_id, st_distance(a.geom, b.geom) asc) b
where a.all_facil_id = b.all_facil_id)
where a.road_dist is null;

select * from facilities.all_facil_aqua where road_dist is null;
select a.all_facil_id from facilities.all_facil_aqua a, facilities.all_facil_aqua b where a.all_facil_id != b.all_facil_id and st_intersects(a.geom, b.geom);
-- no duplicates

-- points within 1m of one another, that also fall on a road (remove one of each pair from table)
begin;
delete from facilities.all_facil_aqua where all_facil_id IN (select a2 from
(select distinct on (greatest(a.all_facil_id, b.all_facil_id) || '-' || least(a.all_facil_id, b.all_facil_id))
a.all_facil_id a1, a.src_table, b.all_facil_id a2, b.src_table, st_distance(a.geom, b.geom) from
(select a.all_facil_id, a.src_table, a.geom, c.ogc_fid
from facilities.all_facil_aqua a,
roads.va_centerline c
where st_intersects(st_buffer(a.geom,0.00001), c.geom)) a,
(select a.all_facil_id, a.src_table, a.geom, c.ogc_fid
from facilities.all_facil_aqua a,
roads.va_centerline c
where st_intersects(st_buffer(a.geom,0.00001), c.geom)) b
where a.all_facil_id != b.all_facil_id
and not st_intersects(a.geom,b.geom)
and st_dwithin(a.geom, b.geom, 1)
and a.ogc_fid = b.ogc_fid
order by 
(greatest(a.all_facil_id, b.all_facil_id) || '-' || least(a.all_facil_id, b.all_facil_id)),
a.all_facil_id) sub);
commit;

-----------------
-- NHDPlusv2 scores for un-associated points
alter table facilities.all_facil_aqua add column nhd_farea integer;
alter table facilities.all_facil_aqua add column nhd_why character varying;

-- only include those not associated with plau 
select count(*) from facilities.all_facil_aqua where plau_fid is null;
-- 1025
select distinct src_table from facilities.all_facil_aqua;
update facilities.all_facil_aqua set nhd_farea = NULL;
update facilities.all_facil_aqua set nhd_why = NULL;

-- Uploaded NHD tables using rpostgis in R
-- within 500m of sea or ocean, score = 10000
UPDATE facilities.all_facil_aqua a SET nhd_farea = 10000, nhd_why = 'within 500m of nhdArea SeaOcean type'
WHERE a.all_facil_id in 
	(SELECT distinct all_facil_id FROM
	facilities.all_facil_aqua a,
	nhdplusv2.nhdarea b
	where b.ftype in ('SeaOcean','BayInlet','ForeShore')
	and a.all_facil_id in (select all_facil_id from facilities.all_facil_aqua where plau_fid is null)
	and (st_intersects(a.geom, st_transform(b.geom, 900914)) or st_dwithin(a.geom, st_transform(b.geom, 900914), 500))
	);

-- within 500m of large rivers, score = 100
UPDATE facilities.all_facil_aqua a SET nhd_farea = 100, nhd_why = 'within 500m of nhdArea StreamRiver type'
WHERE a.all_facil_id in 
	(SELECT distinct a.all_facil_id FROM
	facilities.all_facil_aqua a,
	nhdplusv2.nhdarea b
	where b.ftype = 'StreamRiver'
	and a.all_facil_id in (select all_facil_id from facilities.all_facil_aqua where plau_fid is null and nhd_farea is null)
	and (st_intersects(a.geom, st_transform(b.geom, 900914)) or st_dwithin(a.geom, st_transform(b.geom, 900914), 500)));
-- within 500m of swamp/marsh waterbody (mainly coastal, near large rivers) score = 100
UPDATE facilities.all_facil_aqua a SET nhd_farea = 100, nhd_why = 'within 500m of nhdWaterbody SwampMarsh type'
WHERE a.all_facil_id in 
	(SELECT distinct all_facil_id FROM
	facilities.all_facil_aqua a,
	nhdplusv2.waterbody b
	where b.ftype = 'SwampMarsh'
	and all_facil_id in (select all_facil_id from facilities.all_facil_aqua where plau_fid is null and nhd_farea is null)
	and (st_intersects(a.geom, st_transform(b.geom, 900914)) or st_dwithin(a.geom, st_transform(b.geom, 900914), 500))
	);

-- others, attach streamorder (values range 1-7), multiplied by 2
UPDATE facilities.all_facil_aqua a SET nhd_farea = sub.streamorde * 2, nhd_why = sub.why
FROM 
	(SELECT distinct on (a.all_facil_id) all_facil_id, b.streamorde, 'streamorder of closest nhd reach' as why
	FROM
	facilities.all_facil_aqua a,
	nhdplusv2.nhd_flowline b
	where all_facil_id in (select all_facil_id from facilities.all_facil_aqua where plau_fid is null and nhd_farea is null)
	and st_dwithin(a.geom, st_transform(b.geom, 900914), 100)
	order by all_facil_id, st_distance(a.geom, st_transform(b.geom, 900914)) asc) sub
where a.all_facil_id = sub.all_facil_id
and a.all_facil_id in (select all_facil_id from facilities.all_facil_aqua where plau_fid is null and nhd_farea is null);
UPDATE facilities.all_facil_aqua a SET nhd_farea = sub.streamorde * 2, nhd_why = sub.why
FROM 
	(SELECT distinct on (a.all_facil_id) all_facil_id, b.streamorde, 'streamorder of closest nhd reach' as why
	FROM
	facilities.all_facil_aqua a,
	nhdplusv2.nhd_flowline b
	where all_facil_id in (select all_facil_id from facilities.all_facil_aqua where plau_fid is null and nhd_farea is null)
	and st_dwithin(a.geom, st_transform(b.geom, 900914), 500)
	order by all_facil_id, st_distance(a.geom, st_transform(b.geom, 900914)) asc) sub
where a.all_facil_id = sub.all_facil_id
and a.all_facil_id in (select all_facil_id from facilities.all_facil_aqua where plau_fid is null and nhd_farea is null);

-- give remaining value of 0
update facilities.all_facil_aqua a SET nhd_farea = 0, nhd_why = 'unassociated facility'
WHERE a.all_facil_id in (select all_facil_id from facilities.all_facil_aqua where plau_fid is null and nhd_farea is null);

alter table facilities.all_facil_aqua add column comb_area double precision;

update facilities.all_facil_aqua set comb_area = plau_area where plau_area is not null;
update facilities.all_facil_aqua set comb_area = nhd_farea where nhd_farea is not null;

select nhd_why, count(nhd_why) from facilities.all_facil_aqua group by nhd_why;

