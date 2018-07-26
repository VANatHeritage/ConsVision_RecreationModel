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
Last update: 2018-07-26
*/

-- Terrestrial rec access

-- reset table if needed
DELETE FROM rec_access.access_t;
ALTER SEQUENCE rec_access.access_t_access_t_id_seq RESTART WITH 1;

-- check if all polygons valid
SELECT distinct st_isvalid(st_makevalid(geom)) from rec_source.pub_lands_dissolve;

-- set up public table with only 'open', non-water, public access polygons
drop table pub_lands_terr_open CASCADE;
CREATE TABLE pub_lands_terr_open AS
SELECT * FROM rec_source.pub_lands_dissolve WHERE acs_simple in ('open','water') and water = 0;
CREATE INDEX plto_geomidx ON pub_lands_terr_open USING gist (geom);


-- EXTRA ATTRIBUTES FOR POLYGONS
-- summarize trails (lines) in polygons - vatrails
drop table pub_lands_trls;
CREATE TABLE pub_lands_trls AS
	SELECT a.objectid, b.objectid oid_t, st_intersection(b.geom, a.geom) geom -- could use st_buffer(50m) around polygons to account for trails along polygon buffers
	FROM pub_lands_terr_open a,
	rec_source.vatrails b
	WHERE st_intersects(a.geom, b.geom); -- could use st_buffer around polygons to account for trails along polygon buffers
COMMENT ON TABLE pub_lands_trls is 'Trails intersecting pub_lands_terr_open polygon from the trails table ''rec_source.vatrails''';
-- summarize trails (lines) in polygons - state_trails
drop table pub_lands_strl;
CREATE TABLE pub_lands_strl AS
	SELECT a.objectid, b.ogc_fid oid_t, st_intersection(st_transform(b.geom, 3968), a.geom) geom
	FROM pub_lands_terr_open a,
	rec_source.state_trails b
	WHERE b.type = 'Trail' AND st_intersects(a.geom, st_transform(b.geom, 3968)); -- only (foot) trails, not the on-road trails included in this table
COMMENT ON TABLE pub_lands_trls is 'Trails intersecting pub_lands_terr_open polygon from the trails table ''rec_source.state_trails''';

-- drop view pub_lands_alltrls;
CREATE or replace VIEW pub_lands_alltrls AS
SELECT t.*, round(st_area(p.geom)::numeric/10000,8) as plt_area FROM
	((SELECT distinct on (objectid) objectid as plt_fid, count(oid_t) as trls_sgmts, sum(st_length(geom))/1000 as trls_length_km 
	FROM pub_lands_trls group by plt_fid) a
	FULL OUTER JOIN
	(SELECT distinct on (objectid) objectid as plt_fid, count(oid_t) as strl_sgmts, sum(st_length(geom))/1000 as strl_length_km 
	FROM pub_lands_strl group by plt_fid) b
	using (plt_fid)) t
	JOIN
	pub_lands_terr_open p on (p.objectid = t.plt_fid);
COMMENT ON VIEW pub_lands_alltrls is 'Summary of total length of trails within pub_lands_terr_open polygon from the trail lines tables.';
-- area and length summary
select plt_fid, plt_area, trls_length_km, strl_length_km from pub_lands_alltrls order by trls_length_km desc;
-- END TRAIL ATTRIBUTES FOR PUBLIC LANDS

-- TRAIL CLUSTERS outside public lands -- just do trail clusters overall, not in/out public lands
/*
drop table bla;
create temp table bla as select oid_t, st_union(geom) geom from pub_lands_trls group by oid_t;
drop table vatrails_cluster50;
create table vatrails_cluster50 as 
	select row_number() over () as fid, round(st_length(a.geom)::numeric/1000,8) as length_km, a.geom as geom from 
	(select st_setsrid(st_collectionextract(unnest(ST_ClusterWithin(geom, 50)),2),3968) as geom from 
		(select distinct a.objectid, st_difference(a.geom, st_buffer(b.geom, 10)) geom from rec_source.vatrails a,
		 bla b where a.objectid = b.oid_t) bla
	where st_length(a.geom) > 0 
	) a;
CREATE INDEX trl50_geomidx ON vatrails_cluster50 USING gist (geom);
drop table bla;
*/
-- group by 50m
drop table vatrails_cluster;
create table vatrails_cluster as 
	select row_number() over () as fid, round(st_length(a.geom)::numeric/1000,8) as length_km, a.geom as geom from 
	(select st_setsrid(st_collectionextract(unnest(ST_ClusterWithin(geom, 50)),2),3968) as geom from rec_source.vatrails) a
	where st_length(a.geom) > 0;
CREATE INDEX trl_geomidx ON vatrails_cluster USING gist (geom);
-- summary
select count(*), round((st_length(geom)/1000)::numeric, 1) from vatrails_cluster
group by round((st_length(geom)/1000)::numeric, 1)
order by round((st_length(geom)/1000)::numeric, 1);

-- no grouping by distance
/*
drop table vatrails_cluster;
create table vatrails_cluster as 
	select row_number() over () as fid, round(st_length(a.geom)::numeric/1000,8) as length_km, a.geom as geom from 
	(select st_setsrid(st_collectionextract(unnest(ST_ClusterIntersecting(geom)),2),3968) as geom from rec_source.vatrails) a
	where st_length(a.geom) > 0;
CREATE INDEX trl_geomidx ON vatrails_cluster USING gist (geom);
select count(*), round((st_length(geom)/1000)::numeric, 1) from vatrails_cluster 
group by round((st_length(geom)/1000)::numeric, 1)
order by round((st_length(geom)/1000)::numeric, 1);
*/
--- END


-- Trailheads
-- intersecting pub_lands 
-- (trailheads could be duplicated when intersecting multiple (overlapping) public lands, except if using pub_lands_terr_open)
INSERT INTO rec_access.access_t (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom) 
	SELECT 'tlnd', 'vatrailheads', a.objectid, 'pub_lands_terr_open', b.objectid, round(st_area(b.geom)::numeric/10000,8), 1, 'intersects pub_lands_terr_open', st_transform(st_force2d(a.geom), 3968) 
	FROM rec_source.vatrailheads a, pub_lands_terr_open b
	WHERE st_intersects(st_transform(a.geom, 3968), b.geom)
	and st_area(b.geom) > 1000;
-- within a distance of pub_lands (50m) -> associate with closest
INSERT INTO rec_access.access_t (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom) 
	SELECT distinct on (a.objectid) 'tlnd', 'vatrailheads', a.objectid, 'pub_lands_terr_open', b.objectid, round(st_area(b.geom)::numeric/10000,8), 1, 'within 50m pub_lands_terr_open',
	 st_transform(st_force2d(a.geom), 3968) 
	FROM rec_source.vatrailheads a, pub_lands_terr_open b
	WHERE st_dwithin(st_transform(a.geom, 3968), b.geom, 50)
	and st_area(b.geom) > 1000
	AND a.objectid NOT IN (SELECT distinct src_id FROM rec_access.access_t WHERE facil_code = 'tlnd' and src_table = 'vatrailheads')
	order by a.objectid, st_distance(st_transform(a.geom, 3968), b.geom) asc;
-- within a distance of pub_lands (500m) -> associate with closest
INSERT INTO rec_access.access_t (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom) 
	SELECT distinct on (a.objectid) 'tlnd', 'vatrailheads', a.objectid, 'pub_lands_terr_open', b.objectid, round(st_area(b.geom)::numeric/10000,8), 1, 'within 50-500m pub_lands_terr_open',
	 st_transform(st_force2d(a.geom), 3968) 
	FROM rec_source.vatrailheads a, pub_lands_terr_open b
	WHERE st_dwithin(st_transform(a.geom, 3968), b.geom, 500)
	and st_area(b.geom) > 1000
	AND a.objectid NOT IN (SELECT distinct src_id FROM rec_access.access_t WHERE facil_code = 'tlnd' and src_table = 'vatrailheads')
	order by a.objectid, st_distance(st_transform(a.geom, 3968), b.geom) asc;

select objectid from rec_source.vatrailheads where objectid not in (select distinct src_id from rec_access.access_t where src_table = 'vatrailheads');
-- 199 not associated with lands
-- insert these with use = 0.
INSERT INTO rec_access.access_t (facil_code, src_table, src_id, use, use_why, geom) 
	SELECT 'tlnd', 'vatrailheads', a.objectid, 0, 'not within 500m of any public land', st_transform(st_force2d(a.geom), 3968) 
	FROM rec_source.vatrailheads a 
	where objectid not in (select distinct src_id from rec_access.access_t where facil_code = 'tlnd' and src_table = 'vatrailheads');
-- done.

-- BWT Sites
-- intersecting pub_lands 
-- (points could be duplicated when intersecting multiple (overlapping) public lands, except if using pub_lands_terr_open
INSERT INTO rec_access.access_t (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom) 
	SELECT 'tlnd', 'bwt_sites', a.ogc_fid,'pub_lands_terr_open', b.objectid, round(st_area(b.geom)::numeric/10000,8), 1, 'intersects pub_lands_terr_open', st_transform(st_force2d(a.geom), 3968) 
	FROM rec_source.bwt_sites a, pub_lands_terr_open b
	WHERE st_intersects(st_transform(a.geom, 3968), b.geom)
	and st_area(b.geom) > 1000;

-- within a distance of pub_lands (50m) -> associate with closest
INSERT INTO rec_access.access_t (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom) 
	SELECT distinct on (a.ogc_fid) 'tlnd', 'bwt_sites', a.ogc_fid,'pub_lands_terr_open', b.objectid, round(st_area(b.geom)::numeric/10000,8), 1, 'within 50m pub_lands_terr_open',
	 st_transform(st_force2d(a.geom), 3968) 
	FROM rec_source.bwt_sites a, pub_lands_terr_open b
	WHERE st_dwithin(st_transform(a.geom, 3968), b.geom, 50)
	and st_area(b.geom) > 1000
	AND a.ogc_fid NOT IN (SELECT distinct src_id FROM rec_access.access_t where facil_code = 'tlnd' and src_table = 'bwt_sites')
	order by a.ogc_fid, st_distance(st_transform(a.geom, 3968), b.geom) asc;

-- within a distance of pub_lands (500m) -> associate with closest
INSERT INTO rec_access.access_t (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom) 
	SELECT distinct on (a.ogc_fid) 'tlnd', 'bwt_sites', a.ogc_fid,'pub_lands_terr_open', b.objectid, round(st_area(b.geom)::numeric/10000,8), 1, 'within 50-500m pub_lands_terr_open',
	 st_transform(st_force2d(a.geom), 3968) 
	FROM rec_source.bwt_sites a, pub_lands_terr_open b
	WHERE st_dwithin(st_transform(a.geom, 3968), b.geom, 500)
	and st_area(b.geom) > 1000
	AND a.ogc_fid NOT IN (SELECT distinct src_id FROM rec_access.access_t where facil_code = 'tlnd' and src_table = 'bwt_sites')
	order by a.ogc_fid, st_distance(st_transform(a.geom, 3968), b.geom) asc;

select a.ogc_fid from rec_source.bwt_sites a where a.ogc_fid not in (SELECT distinct src_id FROM rec_access.access_t where facil_code = 'tlnd' and src_table = 'bwt_sites');
-- 229 not associated with lands
-- insert these with use = 0.
INSERT INTO rec_access.access_t (facil_code, src_table, src_id, use, use_why, geom) 
	SELECT 'tlnd', 'bwt_sites', a.ogc_fid, 0, 'not within 500m of any public land', st_transform(st_force2d(a.geom), 3968) 
	FROM rec_source.bwt_sites a 
	where a.ogc_fid not in (select distinct src_id from rec_access.access_t where facil_code = 'tlnd' and src_table = 'bwt_sites');

select a.ogc_fid from rec_source.bwt_sites a where a.ogc_fid not in (select distinct src_id from rec_access.access_t where facil_code = 'tlnd' and src_table = 'bwt_sites');
select use, count(use) from rec_access.access_t where src_table = 'bwt_sites' group by use;
-- done.


-- Public access sites. Explore attributes to find terrestrial points of access:
select * from rec_source.va_public_access limit 5; -- only terrestrial relevant attribute seems to be 'trail'
select trail, count(*) from rec_source.va_public_access group by trail; -- use 'Yes', 'yes'

INSERT INTO rec_access.access_t (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom) 
	SELECT 'tlnd', 'va_public_access', a.ogc_fid,'pub_lands_terr_open', b.objectid, round(st_area(b.geom)::numeric/10000,8), 1, 'intersects pub_lands_terr_open', st_transform(st_force2d(a.geom), 3968) 
	FROM rec_source.va_public_access a, pub_lands_terr_open b
	WHERE st_intersects(st_transform(a.geom, 3968), b.geom)
	and st_area(b.geom) > 1000
	--AND a.trail in ('Yes', 'yes')
	;

-- within a distance of pub_lands (50m) -> associate with closest
INSERT INTO rec_access.access_t (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom) 
	SELECT distinct on (a.ogc_fid) 'tlnd', 'va_public_access', a.ogc_fid,'pub_lands_terr_open', b.objectid, round(st_area(b.geom)::numeric/10000,8), 1, 'within 50m pub_lands_terr_open',
	 st_transform(st_force2d(a.geom), 3968) 
	FROM rec_source.va_public_access a, pub_lands_terr_open b
	WHERE st_dwithin(st_transform(a.geom, 3968), b.geom, 50)
	and st_area(b.geom) > 1000
	AND a.ogc_fid NOT IN (SELECT distinct src_id FROM rec_access.access_t where facil_code = 'tlnd' and src_table = 'va_public_access')
	--AND a.trail in ('Yes', 'yes')
	order by a.ogc_fid, st_distance(st_transform(a.geom, 3968), b.geom) asc;

-- within a distance of pub_lands (500m) -> associate with closest
INSERT INTO rec_access.access_t (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom) 
	SELECT distinct on (a.ogc_fid) 'tlnd', 'va_public_access', a.ogc_fid,'pub_lands_terr_open', b.objectid, round(st_area(b.geom)::numeric/10000,8), 1, 'within 50-500m pub_lands_terr_open',
	 st_transform(st_force2d(a.geom), 3968) 
	FROM rec_source.va_public_access a, pub_lands_terr_open b
	WHERE st_dwithin(st_transform(a.geom, 3968), b.geom, 500)
	and st_area(b.geom) > 1000
	AND a.ogc_fid NOT IN (SELECT distinct src_id FROM rec_access.access_t where facil_code = 'tlnd' and src_table = 'va_public_access')
	--AND a.trail in ('Yes', 'yes')
	order by a.ogc_fid, st_distance(st_transform(a.geom, 3968), b.geom) asc;

-- insert these with use = 0.
INSERT INTO rec_access.access_t (facil_code, src_table, src_id, use, use_why, geom) 
	SELECT 'tlnd', 'va_public_access', a.ogc_fid, 0, 'not within 500m of any public land', st_transform(st_force2d(a.geom), 3968) 
	FROM rec_source.va_public_access a 
	where a.ogc_fid not in (select distinct src_id from rec_access.access_t where facil_code = 'tlnd' and src_table = 'va_public_access')
	--AND a.trail in ('Yes', 'yes')
	;

-- VDGIF gate/kiosks
-- need these


-- Public lands polygons - generating one point per non-associated polygon
-- these are associated
create or replace view plnd_assoc as 
select distinct join_fid from rec_access.access_t where facil_code = 'tlnd' and join_table = 'pub_lands_terr_open' and join_fid is not null and use != 0
union all
select distinct src_id from rec_access.access_t where facil_code = 'tlnd' and src_table = 'pub_lands_terr_open' and use != 0;

-- delete from rec_access.access_t where src_table = 'pub_lands_terr_open' and join_table = 'pub_lands_terr_open';
-- These are polygons intersecting roads
-- take closest point on intersecting roads to the polygon's centroid points
INSERT INTO rec_access.access_t (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom) 
SELECT DISTINCT ON (a.objectid) 'tlnd', 'pub_lands_terr_open', a.objectid, 'pub_lands_terr_open', a.objectid, round(st_area(a.geom)::numeric/10000,8),
			2, 'closest point on intersecting roads to polygon centroid', st_closestpoint((st_dump(st_intersection(b.geom, a.geom))).geom, st_centroid(a.geom)) FROM
		pub_lands_terr_open a,
		roads.va_centerline b
		where st_intersects(a.geom, b.geom)
		and st_area(a.geom) > 1000	 -- more than 0.1 hectares
		and a.objectid NOT IN (select join_fid from plnd_assoc)
		and b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500', -- excluded from analysis; already not included in va_centerline but here for reference
		'S1100','S1100HOV','S1640'); -- these are limited access higways
-- non-road intersecting polygons
INSERT INTO rec_access.access_t (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom)
SELECT DISTINCT ON (a.objectid) 'tlnd', 'pub_lands_terr_open', a.objectid, 'pub_lands_terr_open', a.objectid, round(st_area(a.geom)::numeric/10000,8),
			2, 'closest point on polygon boundary to road', st_closestpoint(a.geom, b.geom) geom FROM
		pub_lands_terr_open a,
		roads.va_centerline b 
		where st_dwithin(a.geom, b.geom, 10000) -- manually adjust here with increasingly higher values to speed up/provide cutoff for polys > a distance to closest road
		and st_area(a.geom) > 1000	 -- more than 0.1 hectares
		and a.objectid NOT IN (select join_fid from plnd_assoc)
		AND b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500', -- excluded from analysis
		'S1100','S1100HOV','S1640')
		ORDER BY a.objectid, ST_Distance(a.geom,b.geom) asc;
-- check	
select join_fid from plnd_assoc order by join_fid;
drop view plnd_assoc;
-- all polygons have a point now


-- Trailheads/trail clusters
-- These are a different "facil_code", and use length in km as join_score.
-- Use trailheads, bwt_sites, and va_public_access with trails.
-- for unassociated, generate a single point per trail cluster.

-- within a distance of vatrails_cluster (50m) -> associate trailheads, bwt with closest
delete from rec_access.access_t where facil_code = 'ttrl';
-- trhd
INSERT INTO rec_access.access_t (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom) 
	SELECT distinct on (a.objectid) 'ttrl', 'vatrailheads', a.objectid, 'vatrails_cluster', b.fid, b.length_km, 1, 'within 50m vatrails_cluster',
	 st_transform(st_force2d(a.geom), 3968) 
	FROM rec_source.vatrailheads a, vatrails_cluster b
	WHERE st_dwithin(st_transform(a.geom, 3968), b.geom, 50)
	and b.length_km > 0.5
	AND a.objectid NOT IN (SELECT distinct src_id FROM rec_access.access_t WHERE facil_code = 'ttrl' and src_table = 'vatrailheads')
	order by a.objectid, st_distance(st_transform(a.geom, 3968), b.geom) asc;
INSERT INTO rec_access.access_t (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom) 
	SELECT distinct on (a.objectid) 'ttrl', 'vatrailheads', a.objectid, 'vatrails_cluster', b.fid, b.length_km, 1, 'within 50-500m vatrails_cluster',
	 st_transform(st_force2d(a.geom), 3968) 
	FROM rec_source.vatrailheads a, vatrails_cluster b
	WHERE st_dwithin(st_transform(a.geom, 3968), b.geom, 500)
	and b.length_km > 0.5
	AND a.objectid NOT IN (SELECT distinct src_id FROM rec_access.access_t WHERE facil_code = 'ttrl' and src_table = 'vatrailheads')
	order by a.objectid, st_distance(st_transform(a.geom, 3968), b.geom) asc;
-- bwt
INSERT INTO rec_access.access_t (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom) 
	SELECT distinct on (a.objectid) 'ttrl', 'bwt_sites', a.objectid, 'vatrails_cluster', b.fid, b.length_km, 1, 'within 50m vatrails_cluster',
	 st_transform(st_force2d(a.geom), 3968) 
	FROM rec_source.bwt_sites a, vatrails_cluster b
	WHERE st_dwithin(st_transform(a.geom, 3968), b.geom, 50)
	and b.length_km > 0.5
	AND a.objectid NOT IN (SELECT distinct src_id FROM rec_access.access_t WHERE facil_code = 'ttrl' and src_table = 'bwt_sites')
	order by a.objectid, st_distance(st_transform(a.geom, 3968), b.geom) asc;
INSERT INTO rec_access.access_t (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom) 
	SELECT distinct on (a.objectid) 'ttrl', 'bwt_sites', a.objectid, 'vatrails_cluster', b.fid, b.length_km, 1, 'within 50-500m vatrails_cluster',
	 st_transform(st_force2d(a.geom), 3968) 
	FROM rec_source.bwt_sites a, vatrails_cluster b
	WHERE st_dwithin(st_transform(a.geom, 3968), b.geom, 500)
	and b.length_km > 0.5
	AND a.objectid NOT IN (SELECT distinct src_id FROM rec_access.access_t WHERE facil_code = 'ttrl' and src_table = 'bwt_sites')
	order by a.objectid, st_distance(st_transform(a.geom, 3968), b.geom) asc;
-- va_public_access
INSERT INTO rec_access.access_t (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom) 
	SELECT distinct on (a.objectid) 'ttrl', 'va_public_access', a.objectid, 'vatrails_cluster', b.fid, b.length_km, 1, 'within 50m vatrails_cluster',
	 st_transform(st_force2d(a.geom), 3968) 
	FROM rec_source.va_public_access a, vatrails_cluster b
	WHERE st_dwithin(st_transform(a.geom, 3968), b.geom, 50)
	and b.length_km > 0.5
	--AND a.trail in ('Yes', 'yes')
	AND a.objectid NOT IN (SELECT distinct src_id FROM rec_access.access_t WHERE facil_code = 'ttrl' and src_table = 'va_public_access')
	order by a.objectid, st_distance(st_transform(a.geom, 3968), b.geom) asc;
INSERT INTO rec_access.access_t (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom) 
	SELECT distinct on (a.objectid) 'ttrl', 'va_public_access', a.objectid, 'vatrails_cluster', b.fid, b.length_km, 1, 'within 50-500m vatrails_cluster',
	 st_transform(st_force2d(a.geom), 3968) 
	FROM rec_source.va_public_access a, vatrails_cluster b
	WHERE st_dwithin(st_transform(a.geom, 3968), b.geom, 500)
	and b.length_km > 0.5
	--AND a.trail in ('Yes', 'yes')
	AND a.objectid NOT IN (SELECT distinct src_id FROM rec_access.access_t WHERE facil_code = 'ttrl' and src_table = 'va_public_access')
	order by a.objectid, st_distance(st_transform(a.geom, 3968), b.geom) asc;

-- all remaining trail clusters (1 point per)
select distinct join_fid from rec_access.access_t where facil_code = 'ttrl' and join_table = 'vatrails_cluster';
---
-- These are trails intersecting roads
-- take closest point on intersecting roads to the trail clusters's centroid points
INSERT INTO rec_access.access_t (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom) 
SELECT DISTINCT ON (a.fid) 'ttrl', 'vatrails_cluster', a.fid,'vatrails_cluster', a.fid, a.length_km,
			2, 'closest point on intersecting roads to trail centroid', st_closestpoint((st_dump(st_intersection(b.geom, a.geom))).geom, st_centroid(a.geom)) FROM
		vatrails_cluster a,
		roads.va_centerline b
		where st_intersects(a.geom, b.geom)
		and a.length_km > 0.5
		and a.fid NOT IN (select distinct join_fid from rec_access.access_t where facil_code = 'ttrl' and join_table = 'vatrails_cluster')
		and b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500', -- excluded from analysis; already not included in va_centerline but here for reference
		'S1100','S1100HOV','S1640'); -- these are limited access higways
-- non-road intersecting trail clusters
INSERT INTO rec_access.access_t (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom)
SELECT DISTINCT ON (a.fid) 'ttrl', 'vatrails_cluster', a.fid,'vatrails_cluster', a.fid, a.length_km,
			2, 'closest point on trail boundary to road', st_closestpoint(a.geom, b.geom) geom FROM
		vatrails_cluster a,
		roads.va_centerline b 
		where st_dwithin(a.geom, b.geom, 10000) -- manually adjust here with increasingly higher values to speed up/provide cutoff for polys > a distance to closest road
		and a.fid NOT IN (select distinct join_fid from rec_access.access_t where facil_code = 'ttrl' and join_table = 'vatrails_cluster')
		and a.length_km > 0.5
		AND b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500', -- excluded from analysis
		'S1100','S1100HOV','S1640')
		ORDER BY a.fid, ST_Distance(a.geom,b.geom) asc;

-- summary
select facil_code, src_table, count(*) from rec_access.access_t
group by facil_code, src_table
order by facil_code, src_table;


-- area per access points - "least accessible" polygons (< 1 point per 1000 ha)
-- should we do something with these or leave as is?
select *, area_ha/ct_acc as ha_per_acc from
(select join_fid, count(join_fid) ct_acc  from 
rec_access.access_t
group by join_fid) a
join
(select objectid, st_area(geom)/10000 area_ha from pub_lands_terr_open) b 
on (a.join_fid = b.objectid)
where  area_ha/ct_acc > 1000
order by ha_per_acc desc;

-- should we set a size limit on using generated points? (e.g. must be >1ha to generate a point?)
select count(*) from rec_access.access_t where join_score < 1 and use != 0 and src_table = 'pub_lands_terr_open';
-- would drop 543 points.

/*post-processing terrestrial facilities
1. add src_cid
2. add road_dist
3. identify (near) duplicates
*/
UPDATE rec_access.access_t a SET src_cid =
	(SELECT b.table_code || '_' || lpad(a.src_id::text, 6, '0') FROM
	lookup.src_table b
	WHERE a.src_table = b.table_name)
	where src_cid is null; -- if just updating new points, leave this

select * from rec_access.access_t where src_cid is null;
-- update distance to closest road
UPDATE rec_access.access_t a SET road_dist = 
	(SELECT dist from
	(SELECT distinct on (access_t_id) access_t_id, st_distance(a.geom, b.geom)::numeric(6,2) dist FROM
	rec_access.access_t a,
	roads.va_centerline b
	where st_dwithin(a.geom, b.geom, 100) -- run progressively at 100, 1000, 10000
	and b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500')
	order by access_t_id, st_distance(a.geom, b.geom) asc) b
where a.access_t_id = b.access_t_id)
where a.road_dist is null;
UPDATE rec_access.access_t a SET road_dist = 
	(SELECT dist from
	(SELECT distinct on (access_t_id) access_t_id, st_distance(a.geom, b.geom)::numeric(6,2) dist FROM
	rec_access.access_t a,
	roads.va_centerline b
	where st_dwithin(a.geom, b.geom, 1000) -- run progressively at 100, 1000, 10000
	and b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500')
	order by access_t_id, st_distance(a.geom, b.geom) asc) b
where a.access_t_id = b.access_t_id)
where a.road_dist is null;
UPDATE rec_access.access_t a SET road_dist = 
	(SELECT dist from
	(SELECT distinct on (access_t_id) access_t_id, st_distance(a.geom, b.geom)::numeric(6,2) dist FROM
	rec_access.access_t a,
	roads.va_centerline b
	where st_dwithin(a.geom, b.geom, 10000) -- run progressively at 100, 1000, 10000
	and b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500')
	order by access_t_id, st_distance(a.geom, b.geom) asc) b
where a.access_t_id = b.access_t_id)
where a.road_dist is null;

-- exact duplicates to use = 0
update rec_access.access_t set use = 0, use_why = 'exact duplicate with access point with same facil_code' WHERE access_t_id IN
(select a2 FROM
(select distinct on (greatest(a.access_t_id, b.access_t_id) || '-' || least(a.access_t_id, b.access_t_id))
 a.access_t_id a1, b.access_t_id a2 from rec_access.access_t a, rec_access.access_t b where a.use = 1 and b.use = 1 and 
 a.access_t_id != b.access_t_id and a.facil_code = b.facil_code and st_intersects(a.geom, b.geom)) sub);
-- end rec_access.access_t


/*
Aquatic access

This will use an NHDArea + NHDWaterbody composite table (nhd_area_wtrb). 
Points will generated on polygon surface if not already intersecting, and if close enough to the water feature.

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
ALTER SEQUENCE rec_access.access_a_access_a_id_seq RESTART WITH 1;
select * from rec_access.access_a;

-- Public access sites. All are meant to represent some type of water access. Different codes for different access type.
select * from rec_source.va_public_access limit 5; 
select count(*) from rec_source.va_public_access;
select distinct boat_ramp from rec_source.va_public_access; -- facil code = awtc
select distinct fishing from rec_source.va_public_access; -- facil code = afsh
select distinct swimming from rec_source.va_public_access; -- facil code = agen
-- join table for type of access
drop view afacil;
create or replace view afacil as 
select ogc_fid as src_id, 'awct' as facil_code from rec_source.va_public_access where boat_ramp in ('Yes','yes','es','hand carry') UNION ALL
select ogc_fid as src_id, 'afsh' as facil_code from rec_source.va_public_access where fishing in ('Yes','yes') UNION ALL
select ogc_fid as src_id, 'aswm' as facil_code from rec_source.va_public_access where swimming in ('Yes','yes') UNION ALL
select ogc_fid as src_id, 'agen' as facil_code from rec_source.va_public_access;
select * from afacil;

-- within 500m
drop table aqua_temp;
CREATE TEMP TABLE aqua_temp as
SELECT distinct on (a.ogc_fid) 'va_public_access' as src_table, a.ogc_fid as src_id, 
		'nhd_area_wtrb' as join_table, b.objectid as join_fid, round(st_area(b.geom)::numeric/10000,8) as join_score, 
		st_distance(st_transform(a.geom, 3968), b.geom) as pla_dist, st_closestpoint(b.geom,st_transform(a.geom, 3968)) as geom_cp, st_transform(a.geom, 3968) as geom, -- generating points on polygon boundary
		st_intersects(st_transform(a.geom, 3968), b.geom) as int 
	from rec_source.va_public_access a,
	rec_source.nhd_area_wtrb b
	where st_dwithin(st_transform(a.geom, 3968), b.geom, 500)
	order by a.ogc_fid, st_distance(st_transform(a.geom, 3968), b.geom);
-- insert line closest where not already intersecting nhd_area_wtrb
INSERT INTO aqua_temp
SELECT distinct on (a.ogc_fid) 'va_public_access' as src_table, a.ogc_fid as src_id, 
		'nhd_flowline' as join_table, b.objectid as join_fid, round(st_area(b.geom)::numeric/10000,8) as join_score, 
		st_distance(st_transform(a.geom, 3968), b.geom) as pla_dist, st_closestpoint(b.geom,st_transform(a.geom, 3968)) as geom_cp, st_transform(a.geom, 3968) as geom, -- generating points on polygon boundary
		st_intersects(st_transform(a.geom, 3968), b.geom) as int 
	from rec_source.va_public_access a,
	rec_source.nhd_flowline b
	where st_dwithin(st_transform(a.geom, 3968), b.geom, 500)
	and a.ogc_fid not in (select distinct src_id from aqua_temp where int) 
	order by a.ogc_fid, st_distance(st_transform(a.geom, 3968), b.geom);
-- aqua_temp has duplicates; this query will be the closest to an aquatic feature (from either polys or lines) by src_id 
select * from 
(select src_id, pla_dist pla_dist_l from aqua_temp
where pla_area = 0 and pla_dist > 50) a join (
select src_id, pla_dist pla_dist_p, geom from aqua_temp
where pla_area > 0 and pla_dist > 50) b using (src_id)
where (pla_dist_l > 300 and pla_dist_p > 300)
order by pla_dist_p desc;
select * from aqua_temp;

-- insert intersecting
INSERT INTO rec_access.access_a (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom)
	select facil_code, src_table, src_id, join_table, join_fid, join_score, 1, 'intersecting aquatic features', geom 
	from (select distinct on (src_id, facil_code) * from aqua_temp natural join afacil order by src_id, facil_code, pla_dist) a
	where int;
-- 50m
INSERT INTO rec_access.access_a (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom)
	select facil_code, src_table, src_id, join_table, join_fid, join_score, 1, 'within 50m of aquatic features - point on feature', geom_cp 
	from (select distinct on (src_id, facil_code) * from aqua_temp natural join afacil order by src_id, facil_code, pla_dist) a
	where pla_dist < 50 and src_id not in (select src_id from rec_access.access_a where src_table = 'va_public_access');
-- 300m
INSERT INTO rec_access.access_a (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom)
	select facil_code, src_table, src_id, join_table, join_fid, join_score, 1, 'within 50-300m of aquatic features - point on feature', geom_cp 
	from (select distinct on (src_id, facil_code) * from aqua_temp natural join afacil order by src_id, facil_code, pla_dist) a
	where pla_dist < 300 and src_id not in (select src_id from rec_access.access_a where src_table = 'va_public_access');
-- insert not within 300m with use = 0.
INSERT INTO rec_access.access_a (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom) 
	SELECT facil_code, src_table, src_id, join_table, join_fid, join_score, 0, 'within 300-500m of aquatic features - point on feature', geom_cp
	FROM (select distinct on (src_id, facil_code) * from aqua_temp natural join afacil order by src_id, facil_code, pla_dist) a
	where a.src_id not in (select distinct src_id from rec_access.access_a where src_table = 'va_public_access');


-- boat access
select distinct type, count(*) from rec_source.boat_access group by type order by type
-- all watercraft access (awct)
-- within 500m
drop table aqua_temp;
CREATE TEMP TABLE aqua_temp as
SELECT distinct on (a.ogc_fid) 'boat_access' as src_table, 'awct' as facil_code, a.ogc_fid as src_id, 
		'nhd_area_wtrb' as join_table, b.objectid as join_fid, round(st_area(b.geom)::numeric/10000,8) as join_score, 
		st_distance(st_transform(a.geom, 3968), b.geom) as pla_dist, st_closestpoint(b.geom,st_transform(a.geom, 3968)) as geom_cp, st_transform(a.geom, 3968) as geom, -- generating points on polygon boundary
		st_intersects(st_transform(a.geom, 3968), b.geom) as int 
	from rec_source.boat_access a,
	rec_source.nhd_area_wtrb b
	where st_dwithin(st_transform(a.geom, 3968), b.geom, 500)
	order by a.ogc_fid, st_distance(st_transform(a.geom, 3968), b.geom);
-- insert line closest where not already intersecting nhd_area_wtrb
INSERT INTO aqua_temp
SELECT distinct on (a.ogc_fid) 'boat_access' as src_table, 'awct' as facil_code, a.ogc_fid as src_id, 
		'nhd_area_wtrb' as join_table, b.objectid as join_fid, round(st_area(b.geom)::numeric/10000,8) as join_score, 
		st_distance(st_transform(a.geom, 3968), b.geom) as pla_dist, st_closestpoint(b.geom,st_transform(a.geom, 3968)) as geom_cp, st_transform(a.geom, 3968) as geom, -- generating points on polygon boundary
		st_intersects(st_transform(a.geom, 3968), b.geom) as int 
	from rec_source.boat_access a,
	rec_source.nhd_flowline b
	where st_dwithin(st_transform(a.geom, 3968), b.geom, 500)
	and a.ogc_fid not in (select distinct src_id from aqua_temp where int)
	order by a.ogc_fid, st_distance(st_transform(a.geom, 3968), b.geom);
-- within 300m check
select * from aqua_temp;

-- insert intersecting
INSERT INTO rec_access.access_a (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom)
	select facil_code, src_table, src_id, join_table, join_fid, join_score, 1, 'intersecting aquatic features', geom 
	from (select distinct on (src_id) * from aqua_temp order by src_id, pla_dist) a
	where int;
-- 50m
INSERT INTO rec_access.access_a (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom)
	select facil_code, src_table, src_id, join_table, join_fid, join_score, 1, 'within 50m of aquatic features - point on feature', geom_cp 
	from (select distinct on (src_id) * from aqua_temp order by src_id, pla_dist) a
	where pla_dist < 50 and src_id not in (select src_id from rec_access.access_a where src_table = 'boat_access');
-- 300m
INSERT INTO rec_access.access_a (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom)
	select facil_code, src_table, src_id, join_table, join_fid, join_score, 1, 'within 50-300m of aquatic features - point on feature', geom_cp 
	from (select distinct on (src_id) * from aqua_temp order by src_id, pla_dist) a
	where pla_dist < 300 and src_id not in (select src_id from rec_access.access_a where src_table = 'boat_access');
-- insert not within 300m with use = 0.
INSERT INTO rec_access.access_a (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom) 
	SELECT facil_code, src_table, src_id, join_table, join_fid, join_score, 1, 'within 300-500m of aquatic features - point on feature', geom_cp 
	FROM (select distinct on (src_id) * from aqua_temp order by src_id, pla_dist) a 
	where a.src_id not in (select distinct src_id from rec_access.access_a where src_table = 'boat_access');

--
-- bwt_sites
-- all general water access (agen)
-- within 50m only
drop table aqua_temp;
CREATE TEMP TABLE aqua_temp as
SELECT distinct on (a.ogc_fid) 'bwt_sites' as src_table, 'agen' as facil_code, a.ogc_fid as src_id, 
		'nhd_area_wtrb' as join_table, b.objectid as join_fid, round(st_area(b.geom)::numeric/10000,8) as join_score, 
		st_distance(st_transform(a.geom, 3968), b.geom) as pla_dist, st_closestpoint(b.geom,st_transform(a.geom, 3968)) as geom_cp, st_transform(a.geom, 3968) as geom, -- generating points on polygon boundary
		st_intersects(st_transform(a.geom, 3968), b.geom) as int 
	from rec_source.bwt_sites a,
	rec_source.nhd_area_wtrb b
	where st_dwithin(st_transform(a.geom, 3968), b.geom, 50)
	order by a.ogc_fid, st_distance(st_transform(a.geom, 3968), b.geom);
-- insert line closest where not already intersecting nhd_area_wtrb
INSERT INTO aqua_temp
SELECT distinct on (a.ogc_fid) 'bwt_sites' as src_table, 'agen' as facil_code, a.ogc_fid as src_id, 
		'nhd_area_wtrb' as join_table, b.objectid as join_fid, round(st_area(b.geom)::numeric/10000,8) as join_score, 
		st_distance(st_transform(a.geom, 3968), b.geom) as pla_dist, st_closestpoint(b.geom,st_transform(a.geom, 3968)) as geom_cp, st_transform(a.geom, 3968) as geom, -- generating points on polygon boundary
		st_intersects(st_transform(a.geom, 3968), b.geom) as int 
	from rec_source.bwt_sites a,
	rec_source.nhd_flowline b
	where st_dwithin(st_transform(a.geom, 3968), b.geom, 50)
	and a.ogc_fid not in (select distinct src_id from aqua_temp where int)
	order by a.ogc_fid, st_distance(st_transform(a.geom, 3968), b.geom);
select count(*) from aqua_temp;

-- insert intersecting
--delete from rec_access.access_a where facil_code = 'agen' and src_table = 'bwt_sites';
INSERT INTO rec_access.access_a (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom)
	select facil_code, src_table, src_id, join_table, join_fid, join_score, 1, 'intersecting aquatic features', geom 
	from (select distinct on (src_id) * from aqua_temp order by src_id, pla_dist) a
	where int;
-- 50m
INSERT INTO rec_access.access_a (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom)
	select facil_code, src_table, src_id, join_table, join_fid, join_score, 1, 'within 50m of aquatic features - point on feature', geom_cp 
	from (select distinct on (src_id) * from aqua_temp order by src_id, pla_dist) a
	where pla_dist < 50 and src_id not in (select src_id from rec_access.access_a where src_table = 'bwt_sites');
-- no 500m or unassociated for bwt_sites

--
-- trailheads
-- all general aquatic access (agen)
-- within 50m only
drop table aqua_temp;
CREATE TEMP TABLE aqua_temp as
SELECT distinct on (a.objectid) 'vatrailheads' as src_table, 'agen' as facil_code, a.objectid as src_id, 
		'nhd_area_wtrb' as join_table, b.objectid as join_fid, round(st_area(b.geom)::numeric/10000,8) as join_score, 
		st_distance(a.geom, b.geom) as pla_dist, st_closestpoint(b.geom,a.geom) as geom_cp, a.geom as geom, -- generating points on polygon boundary
		st_intersects(a.geom, b.geom) as int 
	from rec_source.vatrailheads a,
	rec_source.nhd_area_wtrb b
	where st_dwithin(a.geom, b.geom, 50)
	order by a.objectid, st_distance(a.geom, b.geom);
-- insert point closest to line where not already intersecting nhd_area_wtrb
INSERT INTO aqua_temp
SELECT distinct on (a.objectid) 'vatrailheads' as src_table, 'agen' as facil_code, a.objectid as src_id, 
		'nhd_area_wtrb' as join_table, b.objectid as join_fid, round(st_area(b.geom)::numeric/10000,8) as join_score, 
		st_distance(a.geom, b.geom) as pla_dist, st_closestpoint(b.geom,a.geom) as geom_cp, a.geom as geom, -- generating points on polygon boundary
		st_intersects(a.geom, b.geom) as int 
	from rec_source.vatrailheads a,
	rec_source.nhd_flowline b
	where st_dwithin(a.geom, b.geom, 50)
	and a.objectid not in (select distinct src_id from aqua_temp where int)
	order by a.objectid, st_distance(a.geom, b.geom);
-- this will be closest by src_id from either polys or lines
select count(*) from aqua_temp;

-- insert intersecting
INSERT INTO rec_access.access_a (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom)
	select facil_code, src_table, src_id, join_table, join_fid, join_score, 1, 'intersecting aquatic features', geom 
	from (select distinct on (src_id) * from aqua_temp order by src_id, pla_dist) a
	where int;
-- 50m
INSERT INTO rec_access.access_a (facil_code, src_table, src_id, join_table, join_fid, join_score, use, use_why, geom)
	select facil_code, src_table, src_id, join_table, join_fid, join_score, 1, 'within 50m of aquatic features - point on feature', geom_cp 
	from (select distinct on (src_id) * from aqua_temp order by src_id, pla_dist) a
	where pla_dist < 50 and src_id not in (select src_id from rec_access.access_a where src_table = 'vatrailheads');
-- no 500m or unassociated for vatrailheads

--

--- GENERATING "FAKE" ACCESS POINTS

-- unassociated lakes, trout reaches, scenic rivers, beaches
-- for these, generate one point per feature
-- on feature's boundary, relative to intersecting/nearby roads
-- these will have use = 2 (indicating generated but should be used), or use = 0 if not intended to be used
 
-- pub_fish_lake
-- all [facil_code = afsh] access 
-- first dump and transform lakes
drop table rec_source.pub_fish_lake_dump;
create table rec_source.pub_fish_lake_dump as
	select row_number() over() as fid, a.*
	from (select ogc_fid as pub_fish_lake_ogc_fid, st_transform((st_dump(geom)).geom, 3968)::geometry('POLYGON',3968) geom from rec_source.pub_fish_lake) a;
comment on table rec_source.pub_fish_lake_dump is 'Exploded polygons from pub_fish_lake.';
-- those already with access points
-- drop table excl;
create temp table excl as
select distinct fid from rec_source.pub_fish_lake_dump a,
rec_access.access_a b where 
st_dwithin(a.geom, b.geom, 50);

-- intersecting lakes
-- QUESTION; maybe generate one point for every lake, regardless if it has access point already? Just one point added per (distinct polygon) lake anyways
	-- for now only generating points for lakes not already with access pt
-- delete from rec_access.access_a where src_table = 'pub_fish_lake_dump';
INSERT INTO rec_access.access_a (facil_code, src_table, src_id, use, use_why, geom)
SELECT DISTINCT ON (a.fid) 'afsh', 'pub_fish_lake_dump', a.fid, 2, 'closest point to polygon centroid from road intersections', 
			st_closestpoint((st_dump(st_intersection(b.geom, a.geom))).geom, st_centroid(a.geom)) FROM 	
		rec_source.pub_fish_lake_dump a,
		roads.va_centerline b
		where st_intersects(st_boundary(a.geom), b.geom)
		and a.fid NOT IN (select fid from excl) -- excludes lakes/aqua already within 50m of an access point
		and b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500', -- excluded from analysis
		'S1100','S1100HOV','S1640');
INSERT INTO rec_access.access_a (facil_code, src_table, src_id, use, use_why, geom)
SELECT DISTINCT ON (a.fid) 'afsh', 'pub_fish_lake_dump', a.fid, 2, 'closest point on boundary to road', st_closestpoint(a.geom, b.geom) geom FROM
		rec_source.pub_fish_lake_dump a,
		roads.va_centerline b 
		where st_dwithin(a.geom, b.geom, 5000) -- manually adjust here with increasingly higher values to speed up/provide cutoff for polys > a distance to closest road
		and a.fid not in (select distinct src_id from rec_access.access_a where src_table = 'pub_fish_lake_dump')
		and a.fid NOT IN (select fid from excl)
		AND b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500', -- excluded from analysis
		'S1100','S1100HOV','S1640')
		ORDER BY a.fid, ST_Distance(a.geom,b.geom) asc;
-- update features with nhd feature ids, using nhd area within 50m
update rec_access.access_a SET join_table = 'nhd_area_wtrb', join_fid = sub.objectid, join_score = sub.area FROM
(select distinct on (a.access_a_id) a.access_a_id, b.objectid, round(st_area(b.geom)::numeric/10000,8) as area, st_distance(a.geom, b.geom) from
rec_access.access_a a,
rec_source.nhd_area_wtrb b
where a.src_table = 'pub_fish_lake_dump'
and st_dwithin(a.geom, b.geom, 50)
order by a.access_a_id, st_distance(a.geom, b.geom) asc) sub
where access_a.access_a_id = sub.access_a_id;
-- update features with nhd flowline ids, using nhd area within 50m
update rec_access.access_a SET  join_table = 'nhd_flowline', join_fid = sub.objectid, join_score = sub.area FROM
(select distinct on (a.access_a_id) a.access_a_id, b.objectid, round(st_area(b.geom)::numeric/10000,8) as area, st_distance(a.geom, b.geom) from
rec_access.access_a a,
rec_source.nhd_flowline b
where a.src_table = 'pub_fish_lake_dump' and a.join_fid is null
and st_dwithin(a.geom, b.geom, 50)
order by a.access_a_id, st_distance(a.geom, b.geom) asc) sub
where access_a.access_a_id = sub.access_a_id;
-- not necessary - Burning lakes into aqua raster if they are not associated this way. Will get areas from generated polys anyways.
-- update rec_access.access_a SET use = 0, use_why = 'no associated NHD feature' where pla_fid is null and src_table = 'pub_fish_lake_dump';
-- 5 points not within 50m of NHD features

-- will need to also burn pub_fish_lakes into a raster layer if using cost distance to derive land polygons
select * from rec_access.access_a where join_fid is null and src_table = 'pub_fish_lake_dump';


-- trout reaches
-- all [facil_code = afsh] access
drop table rec_source.stocked_trout_reaches_diss;
create table rec_source.stocked_trout_reaches_diss as select row_number() over() as fid, round(st_length(a.geom)::numeric/1000,8) as length_km, geom FROM
(select st_transform(st_setsrid(st_collectionextract(unnest(st_clusterintersecting(geom)), 2), 26917),3968) geom from rec_source.stocked_trout_reaches) a;
select * from rec_source.stocked_trout_reaches_diss order by length_km desc;
-- those already with access points
drop table excl;
create temp table excl as
select distinct fid, st_length(a.geom) from rec_source.stocked_trout_reaches_diss a,
rec_access.access_a b where 
src_table != 'stocked_trout_reaches' AND
st_dwithin(a.geom, b.geom, 50);
--37/229 already associated; 192 points to create

-- intersecting trout reaches
-- take all intersecting points
-- delete from rec_access.access_a where src_table = 'stocked_trout_reaches_diss';
INSERT INTO rec_access.access_a (facil_code, src_table, src_id, use, use_why, geom)
SELECT 'afsh', 'stocked_trout_reaches_diss', a.fid, 2, 'stocked trout reach road intersection',
-- SELECT DISTINCT ON (a.fid) 'aqua', 'stocked_trout_reaches_diss', a.fid, 2, 'closest point to feature centroid from road intersections', 
			--st_closestpoint((st_dump(st_intersection(b.geom, a.geom))).geom, st_centroid(a.geom)) FROM 	-- old method for just one point
			(st_dump(st_intersection(b.geom, a.geom))).geom FROM 	
		rec_source.stocked_trout_reaches_diss a, -- transformed table
		roads.va_centerline b
		where st_intersects(a.geom, b.geom)
		-- and a.fid NOT IN (select fid from excl) -- would exclude str already within 50m of an access point
		and b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500', -- excluded from analysis
		'S1100','S1100HOV','S1640');
INSERT INTO rec_access.access_a (facil_code, src_table, src_id, use, use_why, geom)
SELECT DISTINCT ON (a.fid) 'afsh', 'stocked_trout_reaches_diss', a.fid, 0, 'closest point on boundary to road', st_closestpoint(a.geom, b.geom) geom FROM
		rec_source.stocked_trout_reaches_diss a,
		roads.va_centerline b 
		where st_dwithin(a.geom, b.geom, 10000) -- manually adjust here with increasingly higher values to speed up/provide cutoff for polys > a distance to closest road
		and a.fid not in (select distinct src_id from rec_access.access_a where src_table = 'stocked_trout_reaches_diss')
		AND b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500', -- excluded from analysis
		'S1100','S1100HOV','S1640')
		ORDER BY a.fid, ST_Distance(a.geom,b.geom) asc;
-- update features with nhd feature ids, using nhd area within 50m
update rec_access.access_a SET join_table = 'nhd_area_wtrb', join_fid = sub.objectid, join_score = sub.area FROM
(select distinct on (a.access_a_id) a.access_a_id, b.objectid, round(st_area(b.geom)::numeric/10000,8) as area, st_distance(a.geom, b.geom) from
rec_access.access_a a,
rec_source.nhd_area_wtrb b
where a.src_table = 'stocked_trout_reaches_diss' and a.join_fid is null
and st_dwithin(a.geom, b.geom, 50)
order by a.access_a_id, st_distance(a.geom, b.geom) asc) sub
where access_a.access_a_id = sub.access_a_id;
-- update remaining features with nhd feature ids, using nhd flowline within 50m
update rec_access.access_a SET join_table = 'nhd_flowline', join_fid = sub.objectid, join_score = sub.area FROM
(select distinct on (a.access_a_id) a.access_a_id, b.objectid, round(st_area(b.geom)::numeric/10000,8) as area, st_distance(a.geom, b.geom) from
rec_access.access_a a,
rec_source.nhd_flowline b
where a.src_table = 'stocked_trout_reaches_diss' and a.join_fid is null
and st_dwithin(a.geom, b.geom, 50)
order by a.access_a_id, st_distance(a.geom, b.geom) asc) sub
where access_a.access_a_id = sub.access_a_id;
update rec_access.access_a SET use = 0, use_why = 'no associated NHD feature' where join_fid is null and src_table = 'stocked_trout_reaches_diss';
-- 1 unassociated point not within 50m

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
		roads.va_centerline b
		where st_intersects(a.geom, b.geom)
		and a.ogc_fid NOT IN (select ogc_fid from excl) -- excludes lakes/aqua already within 50m of an access point
		and b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500', -- excluded from analysis
		'S1100','S1100HOV','S1640');
-- add closest for non intersecting
INSERT INTO rec_access.access_a (facil_code, src_table, src_id, use, use_why, geom)
SELECT DISTINCT ON (a.ogc_fid) 'aqua', 'scenic_rivers', a.ogc_fid, 0, 'closest point on boundary to road', st_closestpoint(a.geom, b.geom) geom FROM
		sriv a,
		roads.va_centerline b 
		where st_dwithin(a.geom, b.geom, 10000) -- manually adjust here with increasingly higher values to speed up/provide cutoff for polys > a distance to closest road
		and a.ogc_fid not in (select distinct src_id from rec_access.access_a where src_table = 'scenic_rivers')
		and a.ogc_fid NOT IN (select ogc_fid from excl)
		AND b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500', -- excluded from analysis
		'S1100','S1100HOV','S1640')
		ORDER BY a.ogc_fid, ST_Distance(a.geom,b.geom) asc;
-- update features with nhd feature ids, using nhd area within 50m
update rec_access.access_a SET pla_fid = sub.objectid, pla_area = sub.area FROM
(select distinct on (a.access_a_id) a.access_a_id, b.objectid, round(st_area(b.geom)::numeric/10000,8) as area, st_distance(a.geom, b.geom) from
rec_access.access_a a,
rec_source.nhd_area_wtrb b
where a.src_table = 'scenic_rivers' and a.pla_fid is null
and st_dwithin(a.geom, b.geom, 50)
order by a.access_a_id, st_distance(a.geom, b.geom) asc) sub
where access_a.access_a_id = sub.access_a_id;
-- update remaining features with nhd feature ids, using nhd flowline within 50m
update rec_access.access_a SET pla_fid = sub.objectid, pla_area = sub.area FROM
(select distinct on (a.access_a_id) a.access_a_id, b.objectid, round(st_area(b.geom)::numeric/10000,8) as area, st_distance(a.geom, b.geom) from
rec_access.access_a a,
rec_source.nhd_flowline b
where a.src_table = 'scenic_rivers' and a.pla_fid is null
and st_dwithin(a.geom, b.geom, 50)
order by a.access_a_id, st_distance(a.geom, b.geom) asc) sub
where access_a.access_a_id = sub.access_a_id;
update rec_access.access_a SET use = 0, use_why = 'no associated NHD feature' where pla_fid is null and src_table = 'scenic_rivers';
-- 0 unassociated points
-- end scenic rivers
*/


----
-- beaches 
-- these are [facil_code = aswm] access
-- beach access include all intersections with roads (within 50m)
select * from rec_source.public_beaches_polys;
-- those already with access points - this is only used in second case where polygon is not within 50m of (any) roads
drop table excl;
create temp table excl as
select distinct fid_line from rec_source.public_beaches_polys a,
rec_access.access_a b where
src_table != 'public_beaches_polys' and
st_dwithin(a.geom, b.geom, 50);

-- add points on roads within 50m
-- delete from rec_access.access_a where src_table = 'public_beaches_polys';
INSERT INTO rec_access.access_a (facil_code, src_table, src_id, use, use_why, geom)
SELECT DISTINCT 'aswm', 'public_beaches_polys', a.fid_line, 2, 'points on beaches within 50m of roads', 
			st_closestpoint(a.geom, b.geom) FROM 	
		rec_source.public_beaches_polys a,
		roads.va_centerline b
		where st_dwithin(a.geom, b.geom, 50)
		and b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500', -- excluded from analysis
		'S1100','S1100HOV','S1640');
-- add closest for non intersecting
INSERT INTO rec_access.access_a (facil_code, src_table, src_id, use, use_why, geom)
SELECT DISTINCT on (a.fid_line) 'aswm', 'public_beaches_polys', a.fid_line, 2, 'closest point on boundary to road', st_closestpoint(a.geom, b.geom) geom FROM
		rec_source.public_beaches_polys a,
		roads.va_centerline b 
		where st_dwithin(a.geom, b.geom, 10000) -- manually adjust here with increasingly higher values to speed up/provide cutoff for polys > a distance to closest road
		and a.fid_line not in (select distinct src_id from rec_access.access_a where src_table = 'public_beaches_polys')
		and a.fid_line not in (select * from excl) -- those already with access points
		AND b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500', -- excluded from analysis
		'S1100','S1100HOV','S1640')
		ORDER BY a.fid_line, ST_Distance(a.geom ,b.geom) asc;
-- update features with nhd feature ids, using nhd area within 500m
update rec_access.access_a SET join_table = 'nhd_area_wtrb', join_fid = sub.objectid, join_score = sub.area FROM
(select distinct on (a.access_a_id) a.access_a_id, b.objectid, round(st_area(b.geom)::numeric/10000,8) as area, st_distance(a.geom, b.geom) from
rec_access.access_a a,
rec_source.nhd_area_wtrb b
where a.src_table = 'public_beaches_polys' --and a.pla_fid is null
and st_dwithin(a.geom, b.geom, 500)
order by a.access_a_id, st_distance(a.geom, b.geom) asc) sub
where access_a.access_a_id = sub.access_a_id;
select * from rec_access.access_a where src_table = 'public_beaches_polys' and join_fid is null;
-- don't use nhd flowlines for beaches
-- end public beaches


/*post-processing aquatic facilities
1. add src_cid
2. add road_dist
3. identify (near) duplicates
*/
UPDATE rec_access.access_a a SET src_cid =
	(SELECT b.table_code || '_' || lpad(a.src_id::text, 6, '0') FROM
	lookup.src_table b
	WHERE a.src_table = b.table_name)
	where src_cid is null; -- if just updating new points, leave this

-- update distance to closest road
UPDATE rec_access.access_a a SET road_dist = 
	(SELECT dist from
	(SELECT distinct on (access_a_id) access_a_id, st_distance(a.geom, b.geom)::numeric(6,2) dist FROM
	rec_access.access_a a,
	roads.va_centerline b
	where st_dwithin(a.geom, b.geom, 100) -- run progressively at 100, 1000, 10000
	and b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500')
	order by access_a_id, st_distance(a.geom, b.geom) asc) b
where a.access_a_id = b.access_a_id)
where a.road_dist is null;
UPDATE rec_access.access_a a SET road_dist = 
	(SELECT dist from
	(SELECT distinct on (access_a_id) access_a_id, st_distance(a.geom, b.geom)::numeric(6,2) dist FROM
	rec_access.access_a a,
	roads.va_centerline b
	where st_dwithin(a.geom, b.geom, 1000) -- run progressively at 100, 1000, 10000
	and b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500')
	order by access_a_id, st_distance(a.geom, b.geom) asc) b
where a.access_a_id = b.access_a_id)
where a.road_dist is null;
UPDATE rec_access.access_a a SET road_dist = 
	(SELECT dist from
	(SELECT distinct on (access_a_id) access_a_id, st_distance(a.geom, b.geom)::numeric(6,2) dist FROM
	rec_access.access_a a,
	roads.va_centerline b
	where st_dwithin(a.geom, b.geom, 10000) -- run progressively at 100, 1000, 10000
	and b.mtfcc NOT IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500')
	order by access_a_id, st_distance(a.geom, b.geom) asc) b
where a.access_a_id = b.access_a_id)
where a.road_dist is null;

-- exact duplicates to use = 0
update rec_access.access_a set use = 0, use_why = 'exact duplicate with access point with same facil_code' WHERE access_a_id IN
(select a2 FROM
(select distinct on (greatest(a.access_a_id, b.access_a_id) || '-' || least(a.access_a_id, b.access_a_id))
 a.access_a_id a1, b.access_a_id a2 from rec_access.access_a a, rec_access.access_a b where a.use = 1 and b.use = 1 and 
 a.access_a_id != b.access_a_id and a.facil_code = b.facil_code and st_intersects(a.geom, b.geom)) sub);

-- end rec_access.access_a

vacuum analyze rec_access.access_a;
vacuum analyze rec_access.access_t;

/*
-- SUMMARIES

select src_table, facil_code, use, count(*) from rec_access.access_a
where use != 0
group by src_table, facil_code, use
order by facil_code, use;
-- 1486 total use points (non-0)

-- 
select facil_code, count(distinct join_fid) from rec_access.access_a
group by facil_code;
"afsh";579
"agen";477
"aswm";28
"awct";131
-- these will need distinct service areas (n = 1134). But generating aquatic areas, so this isn't what will be used.
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
	(select access_t_id attrl, src_table, src_id from rec_access.access_t where use <> 0 and 
	join_fid IN
	(select join_fid from rec_access.access_t where use <> 0 and facil_code = 'ttrl'
	group by join_fid
	having count(*) = 1)) a
	JOIN
	(select access_t_id atlnd, src_table, src_id from rec_access.access_t where use <> 0 and 
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
select * from rec_access.access_t where join_score < 1 and facil_code = 'ttrl';
-- small polygons included
select * from rec_access.access_t where join_score < 0.5 and facil_code = 'tlnd'; 
*/

