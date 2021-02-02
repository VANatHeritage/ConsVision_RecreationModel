## Virginia Recreation Access Model, access points workflow

*DCR-DNH*

*Author: David Bucklin*

*Date: 2018-07-26*

*Model Version 2.*

---

[TOC]

---

This document describes the workflow used to create access point datasets to recreational facilities (in [rec_access.sql](../sql/rec_access.sql)), for use in the Virginia ConservationVision Recreation Access Model.



### Input data 

#### Recreation Input datasets

From DCR (PRR and DNH), and datasets for Virginia Outdoors Plan (VOP) Mapper:

- VA_PUBLIC_ACCESS_LANDS (Polygon)
  - Represents all public lands in Virginia, with a 'ACCESS' column specifying level of access generally; 'PUBACCESS' has a bit more specifics
- 2018 Public Access (Point)
  - public-access recreation sites and amenities. Includes attributes which indicate specific types of activities available.
- VATrails_2017 (Line)
- VATrailheads_2017 (Point)
- Local_Park_Inventory_2018
  - This point dataset has attributes on facilities at local (municipalities) parks. Not always spatially precise on location of the facilities, but it has a lot of useful attributes
- Watertrails2017 
  - sent by Robbie Rhur (DCR PRR) 2/2019, and was updated for that date
- boataccess_WGS
  - boat access points from VOP mapper

From Virginia Dept. of Game and Inland Fisheries (VDGIF):

- Public\_fishing\_lakes (Polygon)
- Stocked\_Trout\_Reaches (Line)
- Birding\_&\_Wildlife\_Trail\_Sites (Point)
- VDGIF\_Maintained\_Boating\_Access\_Locations (Point)
- WMA_Points (Point)
  - points of access for DGIF's wildlife management areas

From Virginia Institute of Marine Science (VIMS):

- PublicBeaches (Line)

#### Road centerline data

From U.S. Census Tiger/Line:

- Tiger_2018.gdb (Line)

> Note: the following road types were excluded from all regional analyses:
>
> mtfcc IN ('S1710','S1720','S1740','S1750')
>
> This excludes pedestrian-only, private, and U.S. Census Internal types.

#### Aquatic features 

From the National Hydrography Dataset (NHD):

- derived the feature class *nhd_area_wtrb* from:
  - NHD Area
    - definition query: `FTYPE IN (445, 460, 312 , 364, 336)`: BayInlet, Foreshore, SeaOcean, StreamRiver; CanalDitch
  - NHD Waterbody
    - definition query: `FTYPE IN (390, 436, 493)`: LakePond, Resevoir, Estuary
- derived feature class *nhd_flowline* from :
  - NHD Flowline
    - definition query: `FTYPE IN (460, 558 ,336)`: ArtificialPath, StreamRiver, CanalDitch
- All features were combined into a raster `aqua_rast` to represent surface waters
  - From NHD Flowline, Dam/Weir features (`FTYPE = 343`) which were erased from `aqua_rast`



### Data pre-processing

#### Point datasets: attributing access types

Point features are considered **Recreational Access Points**. Each point dataset was attributed with six binary (0/1) fields indicating if they could be used for access for a given sub-type. 

The subtypes are:

- **a_awct** : watercraft (motorboat, kayak, canoe, etc.) access
- **a_afsh**: fishing access 
- **a_aswm**: swimming access (*pools not included*)
- **a_agen***: general aquatic access
- **t_ttrl***: terrestrial trails access
- **t_tlnd***: public lands access

> Subtypes marked with (*) are *potential* access points that would need to be associated with a recreation feature (e.g., fishing lake, public land, trail) in order to be used in the final model.

Point datasets:

1. WMA_Points
   - a_awct: `TYPE = Boat Ramp`
   - a_afsh: ` TYPE = Fishing Pier`
   - t_ttrl and t_tlnd: `TYPE IN ('Gate', 'Seasonal Gate', 'Parking')`
2. 2018_Public_Access
   - a_awct: `BOAT_RAMP = 'Y' or Launch > 0`
   - a_afsh: `FISHING = 'Y'`
   - a_aswm: `SWIMMING = 'Y'`
   - a_agen: all points that were not associated with another aquatic sub-type
   - t_ttrl: all points
   - t_tlnd: all points
3. VDGIF_Maintained_Boating_Access_Locations
   - a_awct: all points
4. boataccess_WGS
   - a_awct: all points
5. Local_Park_Inventory_2018
   - a_awct: `WATER_ACCESS in ('CANOE SLIDE','BOAT RAMP', 'ALL')`
   - a_afsh: `WATER_ACCESS in ('PIER', 'ALL')`
   - a_aswm: `SWIMMING_AREA = 'BEACH'`
     - note: there is also a POOL category
   - t_ttrl: `TRAIL_TYPE IN ('BIKE', 'FITNESS', 'HIKING', 'HORSE', 'MULTI-USE')`
   - tlnd: *Special Workflow*:
     - These points were divided into **associated** or **unassociated** with public lands polygons
     - associated points met one or more of the criteria:
       - within 100m of a public land polygon
       - [within 2000m AND name partial-matches polygon name AND sizes are within 10 acres of one another]
     - unassociated points were assigned an area using `park_acres`
       - empty or 0-areas were assigned a default 0.25-acre value
       - generated circle (buffer) polygons around these points, according to area assigned to the point
       - new table is `local_parks_areas`; see `pub_lands_dissolve` workflow below
6. VATrailheads_2017
   - a_agen: all points
   - t_ttrl: all points
   - t_tlnd: all points
7. Birding_and_Wildlife_Trail_Sites
   - a_agen: all points
   - t_ttrl: all points
   - t_tlnd: all points



#### Polygon/line datasets: cleaning

Polygon and line feature were considered **Recreational Features**. Several recreational feature datasets were modified before use in the model workflow:

- *pub\_lands\_dissolve*
  -  In ArcMap:
    -  used the query `ACCESS <> 'BY PERMISSION'` 
    -  dissolved into single-part polygons (no multi-part polygons)
    -  ArcMap Identity tool used to identify aquatic areas (using *nhd_area_wtrb*) within public lands, and attributed in a new `water` binary field (0 / 1). Dissolved again by original single-part ID and water, allowing mutli-part polygons only when waters within the a public access land boundary separate them
  -  `pub_lands_dissolve` merged with `local_parks_areas` (buffered local park points) in new table `pub_lands_final`
     -  excluded water areas using `water = 0`.
  -  `pub_lands_final` used as the final layer for the public lands components
     -  all polygons >= 5 acres used in regional analyses
     -  all polygons used in local analyses

- ~~*public_beaches_polys*~~
  - ~~These were digitized based on the line features in *public_beaches*, roughly encompassing the area from low tide to the edge of the sand upslope~~
  - ~~UPDATE: Not using these in the model. Using original lines instead.~~

- *stocked_trout_reaches*
  - In Postgres:
    - merged into new multi-part lines based on separation distance of quarter mile
    - resulting table is *stocked_trout_reaches_diss*
  - Association with access points: Any access point (for any facil_code) can be associated with a reach.

- *vatrails*
  - In ArcMap:
    - ArcMap Identity was used to attribute areas `on_road`.
      - this query selects those road surfaces that *can* cut out trails:
        - `(mtfcc in ('S1100', 'S1200', 'S1630')) or (mtfcc not in ('S1500', 'S1710', 'S1720', 'S1820', 'S1830') AND LOCAL_SPEED_MPH > 15)`
        - Note: Road surfaces used a Virginia RCL dataset (2017Q3), instead of Tiger for this procedure, since more detailed attributes were available for Virginia RCL.
      - Note: manually reset some Great Dismal Swamp NWR trails to on_road = 0 after consulting [FWS map](https://www.fws.gov/uploadedFiles/GreatDismalSwampTrails%204-16.pdf)
    - ArcMap Identity was used to attribute areas `on_nhdwater`.  In review, trails that were identified as potential water trails were marked `waterTrail = 1`.
    - ArcMap Identity was used to attribute areas `on_openpubland`.  
      - This will not be used to exclude trails
    - Other trails that were suspect were marked accordingly in the `QC` column.
      - Trails on 'BY_PERMISSION' public lands were reviewed and marked 'Restricted'
      - Trails suspected to not exist marked 'NotExist?' and confirmed 'Proposed'
      - Non-exact duplicates marked 'Duplicate', when found
      - TrailStatus = 'Closed' marked as 'Closed'
    - Used Integrate tool with a tolerance of 1-meter to clean up trails.
      - This doesn't remove duplicates, but puts them directly on top of one another. Allows to retain attributes of individual lines.
  - In Postgres:
    - removed exact spatial duplicates and dumped to single-part linestrings in **trails_clean**
    - added field `exclude` with values:
      - W = excluded b/c in water
      - R = excluded b/c in road
      - P = excluded b/c in "by permission" land
      - N = excluded b/c believed non-existent (e.g., proposed)
      - D = excluded b/c visually identified as duplicate
      - C = excluded b/c trail marked as closed in original dataset
      - I = include (default normal trails with no reason to exclude)
    - Only used `exclude = 'I'` in further analysis
      - These trails were dissolved to remove any further duplication. This is table: **trails_include**
        - This dataset used for local trails analyses
      - merged **trails_include** into new trail multi-part line features ("networks") based on distance (within quarter-mile of one another). This is table **trails_clean_network**.
        - To be included in table, a trail network had to be >= 1 mile in length.
        - This table used for regional trails analyses

- *pub_fish_lake* 
  - In Postgres:
    - dumped into single polygons, since some distinct lakes were joined as multi-part polygons in original dataset
    - Then into multi-polygons based on separation distance of quarter mile
    - resulting table is *pub_fish_lake_dump*
    - Association with access points: Any access point (for any facil_code) can be associated with a lake.




### Combining access points from recreation datasets

Recreational access points, and points derived from recreational features, were combined into final tables `access_t` (terrestrial) and `access_a` (aquatic). The following describes methods and rules used for populating these tables. 

>  Note: The **same exact point can get used multiple times, if it is associated with different types of access** (different *facil_code* values); e.g., one access point may lead to facilities for trails, boat access, swimming, and fishing in the same general location.

> Note: All methods where facilities were associated with a road (intersecting, or closest point on a facility to a road) excluded walkways, private roads, and internal US Census types [`mtfcc IN ('S1710','S1720','S1740','S1750')`] and limited access roads and ramps [`mftcc IN ('S1100','S1630')`].

#### Access point tables

All access points were input into tables ***access_t/access_a*** (for terrestrial and aquatic, respectively) which have the following fields:

* [acs_t_id]/[acs_a_id]: unique table ID
* facil\_code: type of recreation associated with access point, includes following types:
* facil_rid: unique ID  in a temporary combined table for access points for a particular `facil_code`
* src\_table: table of source feature from which the facility point was generated
* src\_id: ID/primary key of source feature in `src_table` (generally `objectid`)
* src\_cid: combination of source table code name and source table ID
* join_table: the joined public land or trails table with which the point is associated
* join_fid: the ID of the feature from the joined table with which the point is associated
* join_score: the 'score' of the feature from the joined table with which the point is associated
  * This was area in acres (public lands) or length in miles (trail clusters), or 1 (aquatic facility types)
* use: integer regarding further use in model
  * **0**: don't use
  * **1**: use
  * **2**: use (this is an identifier for usable points that were 'generated', rather than original points of access from a source table)
* use\_why: Reason/method for including/excluding the point in analysis
  * populated during insert into the table
* road\_dist: distance from point to nearest (motor vehicle) road
* geom: the point geometry (Albers CONUS; EPSG=5070)



##### Point generation methods for inclusion in access_t:

> Note: Public land parcels < 5 acres, and trail networks < 1 mile were not considered in this part of the analysis

1. Points from recreation access point datasets were added with their assigned `facil_code`, if they were within a quarter mile of a recreation feature for that `facil_code` (a public land or trail network).
2. Public lands parcels (pub_lands_final):
   - for polygons not already associated with an access point, generated ***one point each***:
     - for polygons intersecting roads - the closest point on road intersections to the polygon centroid
     - for polygons not intersecting roads - the closest point on the polygon boundary to a road
3.  Trail networks
   - for trail clusters not already associated with an access point, generated ***one point each***:
     - for trail networks intersecting roads - the closest point on trail/road intersections to the trail network centroid
     - for trail networks not intersecting roads - the closest point on the trails to a road

The field `join_score` is the **area in acres** (public lands) or **length in miles** (trail networks) of the associated recreation feature (with the ID stored in `join_fid`).



##### Point generation methods for inclusion in access_a:

1. Points from recreation access point datasets were added with their assigned `facil_code`.

2. Public fishing lakes

   - were grouped using a quarter-mile grouping distance

   - for lakes not already associated with an access point, generated ***one point each***:
     - for lakes intersecting roads - the closest point on road intersections to the lake centroid
     - for lakes not intersecting roads - the closest point on the lake to a road

3. Stocked trout reaches

   - were grouped using a quarter-mile grouping distance

   - for streams not already associated with an access point, generated ***one point each***:
     - for streams intersecting roads - the closest point on road intersections to the stream centroid
     - for streams not intersecting roads - the closest point on the stream to a road

4.  Public beaches

   - points were generated every half-mile along public beach lines

The field `join_score` is assigned to a **value of 1** for all aquatic access points.



### Post-processing

This section describes any steps used to prepare the access points for service area analysis. 

- Each table had their `source_cid` and `road_dist` columns populated. Points that were exact duplicates of another point with the same `facil_code` were assigned `use = 0`.

#### Table-specific processes

- **access_t**:
  - nothing
- **access_a**:
  - assigned `use = 0` for points if they were not within a quarter mile of an NHD aquatic feature (area, waterbody, or river/stream)
    - note: following review of these points, several points with obvious digitizing errors were manually corrected and assigned use = 1.
  - a new column **`group_id`** was added to the table. Point were divided into unique groups (by `facil_code`) using a quarter-mile separation distance. This column was used as the group for a unique service area.

#### Export to ArcGIS geodatabase

Points were to feature classes (one for each `facil_code`) for service area analysis in ArcGIS, where `use <> 0`. Files are time-stamped with the date of export.

 

------

*Last updated: 2019-02-2*8