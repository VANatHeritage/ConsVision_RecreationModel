-- CREATE DATABASE rec_model_source;
COMMENT on database rec_model_source is 'Source datasets for ConservationVision Recreation Model analysis.';
-- set up database
CREATE EXTENSION postgis;

-- create schemas
CREATE schema lookup;
COMMENT ON SCHEMA lookup is 'lookup tables for foreign-key fields in database tables.';

CREATE TABLE lookup.facil_type (
	facil_code CHARACTER VARYING(4) PRIMARY KEY, 
	facil_desc CHARACTER VARYING);

delete from lookup.facil_type;
INSERT INTO lookup.facil_type VALUES ('aqua', 'aquatic features'), ('terr', 'terrestrial features');

drop table lookup.src_table;
CREATE TABLE lookup.src_table (
	table_name CHARACTER VARYING PRIMARY KEY, 
	table_desc CHARACTER VARYING,
	table_orig_source CHARACTER VARYING,
	facil_code CHARACTER VARYING(4) references lookup.facil_type (facil_code),
	table_code character varying(4)); 
	
CREATE schema roads;
COMMENT ON SCHEMA roads IS 'source roads datasets from Tiger roads datasets.';
-- tables loaded using ogr2ogr

CREATE SCHEMA rec_source;
COMMENT ON SCHEMA rec_source IS 'source datasets representing recreational facilities.';
-- tables loaded using ogr2ogr
-- each table should be documented in lookup.scr_table

CREATE SCHEMA rec_access;
COMMENT ON SCHEMA rec_access IS 'features representing recreational access points/areas to be used as inputs for service area analysis.';

-- terrestrial
drop table rec_access.access_t;
CREATE TABLE rec_access.access_t (
	acs_t_id SERIAL PRIMARY KEY, 
	facil_code CHARACTER VARYING REFERENCES lookup.facil_type (facil_code),
	facil_rid integer,
	src_table CHARACTER VARYING REFERENCES lookup.src_table (table_name),
	src_id integer,
	src_cid CHARACTER VARYING, -- lookup.src_table.table_code + src_id
	-- src_name CHARACTER VARYING,  -- not implemented; should create a field with this name in original rec_source datasets (e.g. in ArcGIS)
	join_table character varying REFERENCES lookup.src_table (table_name),
	join_fid integer,
	join_score double precision,
	join_name CHARACTER VARYING,
	use integer,
	use_why character varying,
	road_dist double precision,
	geom GEOMETRY('POINT', 5070)); -- CONUS projection from pub_lands_dissolve
ALTER TABLE rec_access.access_t ADD UNIQUE (facil_code, src_table, src_id, geom);
comment on table rec_access.access_t is 'Recreational access points for terrestrial recreation features.';

-- aquatic
drop table rec_access.access_a;
CREATE TABLE rec_access.access_a (
	acs_a_id SERIAL PRIMARY KEY, 
	facil_code CHARACTER VARYING REFERENCES lookup.facil_type (facil_code),
	facil_rid integer,
	src_table CHARACTER VARYING REFERENCES lookup.src_table (table_name),
	src_id integer,
	src_cid CHARACTER VARYING, -- lookup.src_table.table_code + src_id
	-- src_name CHARACTER VARYING, -- not implemented; should create a field with this name in original rec_source datasets (e.g. in ArcGIS)
	join_table character varying REFERENCES lookup.src_table (table_name),
	join_fid integer,
	join_score double precision,
	join_name CHARACTER VARYING,  -- not implemented for aquatic; leaving for now
	use integer,
	use_why character varying,
	road_dist double precision,
	geom GEOMETRY('POINT', 5070)); -- CONUS projection from pub_lands_dissolve
ALTER TABLE rec_access.access_a ADD UNIQUE (facil_code, src_table, src_id, geom);
comment on table rec_access.access_a is 'Recreational access points for aquatic recreation features.';

-- loaded all datasets via osgeo4w shell (see upload_ogr.txt)
-- run VACUUM ON FULL DB now

-- add all source tables to lookup table
INSERT INTO lookup.src_table (table_name) 
SELECT table_name from information_schema.tables where table_schema = 'rec_source' AND table_name NOT IN (select table_name from lookup.src_table);

SELECT * from lookup.src_table;

-- set types
-- UPDATE lookup.src_table set facil_code = 'aqua' WHERE table_name in ('water_access','stocked_trout_reaches','pub_fish_lake','boat_access');
-- UPDATE lookup.src_table set facil_code = 'terr' WHERE table_name in ('wma_bound','trailheads','pub_lands','managed_trails','public_beaches','bwt_sites','state_trails');

-- still need aquatic polygons.

