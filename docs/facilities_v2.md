## Virginia Recreation Access Model, access points to recreational facilities workflow

DCR-DNH

Author: David Bucklin

Date: 2018-07-26

Model Version 2.

[TOC]

This document describes the workflow used to create access point datasets to recreational facilities (in [rec_access.sql](../sql/rec_access.sql)), for use in the Virginia ConservationVision recreational model.

### Input data 

*Recreation Input datasets*

From Virginia Outdoors Plan (VOP) Mapper:

- publiclands\_wgs (Polygon)
- scenicrivers (Line)
- VA\_public\_access (Point)

From Virginia Dept. of Conservation &amp; Recreation, Division of Planning & Recreation Resources (DCR-PRR):

- vatrails (Line)
- vatrailheads (Point)

From Virginia Dept. of Game and Inland Fisheries (VDGIF):

- Public\_fishing\_lakes (Polygon)
- Stocked\_Trout\_Reaches (Line)
- Birding\_&\_Wildlife\_Trail\_Sites (Point)
- VDGIF\_Maintained\_Boating\_Access\_Locations (Point)
- WMA_Points (Point)

From Virginia Institute of Marine Science (VIMS):

- PublicBeaches (Line)

*Road centerline data*

From Virginia Geographic Information Network (VGIN):

- Virginia\_RCL\_Dataset\_2017Q3.gdb (Line)

> Note: the following road types were excluded from all analyses:
>
> mtfcc IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500')
>
> This excludes driveways, walkways/ped. trails, stairways, service vehicle private drives, bike paths/trails, bridle paths, 4wd vehicular trails.



*Aquatic features - National Hydrography Dataset (NHD)*

- derived feature class *nhd_area_wtrb* from:
  - NHD Area
    - definition query: `FTYPE IN ( 445, 460, 312 , 364, 336)`: BayInlet, Foreshore, SeaOcean, StreamRiver; CanalDitch
  - NHD Waterbody
    - definition query: `FTYPE IN ( 390, 436, 493)`: LakePond, Resevoir, Estuary

- derived feature class *nhd_flowline* from :
  - NHD Flowline
    - definition query: `FTYPE IN ( 460, 558 ,336)`: ArtificialPath, StreamRiver, CanalDitch

### Data pre-processing

Several recreational datasets were modified before use in the model workflow:

- *pub\_lands\_dissolve*
  - Public lands (from *publiclands_wgs*) were given an attribute `acs_simple` based on the `pubaccess` field in the original dataset, with 3 options: `open`, `limited`, or `water`
  - They were then dissolved based on `acs_simple`, into single-part polygons (no multi-part polygons)
  - ArcMap Identity tool used to identify aquatic areas (using *nhd_area_wtrb*) within public lands, and attributed in a new `water` binary field (0 / 1)
  - Layer used in analysis is *pub_lands_terr_open* which is defined by the query: `acs_simple in ('open','water') and water = 0`.
- *public_beaches_polys*
  - These were digitized based on the line features in *public_beaches*, roughly encompassing the area from low tide to the edge of the sand
- *stocked_trout_reaches*
  - merged into new multi-part lines based on contiguity (intersecting)
  - resulting table is *stocked_trout_reaches_diss*
- *vatrails*
  - merged into new trail multi-part line features ("clusters") based on distance (within 50m of one another)
  - resulting table is *va_trails_cluster*
- *pub_fish_lake* 
  - dumped into single polygons, since some distinct lakes were joined as multi-part polygons in original dataset
  - resulting table is *pub_fish_lake_dump*

### Generating recreational access points from recreation datasets

From recreation source features, points of access were determined.

We divided recreational facilities into two groups: terrestrial and aquatic. The following describes methods and rules used to generate access points for each input dataset.

Note that the **same exact point can get used multiple times, if it is associated with different types of access** (different *facil_code* values); e.g., one access point may lead to facilities for boat access, swimming, and fishing in the same general location.

> Note: All methods where facilities were associated with a road (intersecting, or closest point on a facility to a road) excluded limited access roads [mftcc IN ('S1100','S1100HOV','S1640')].

#### Terrestrial facilities

All terrestrial access points were input into table ***access_t***, which has the following fields:

* access_t_id: unique table ID
* facil\_code: type of recreation associated with access point, includes following types:
  * *tlnd*: access points to public lands
  * *ttrl*: access points to trails
* src\_table: table of source feature from which the facility point was generated
* src\_id: ID/primary key of source feature in src\_table
* src\_cid: combination of source table code name and source table ID
* join_table: the joined public land or trails table with which the point is associated
* join_fid: the ID of the feature from the joined table with which the point is associated
* join_score: the 'score' of the feature from the joined table with which the point is associated
  * This was area in HA (dissolved public lands) or length in KM (trail clusters)
* use: numeric identifying attributes regarding further use in model
  * **0**: don't use
    * This was used for points which were not within 500m of public lands or trails
  * **1**: use
  * **2**: use (this is an identifier for useable points that were 'generated', rather than known points of access from a source table)
* use\_why: Reason/method for including the point in analysis
  * populated during point creation, with reasoning for associated *use* value
* road\_dist: distance from point to nearest road
* geom: the point geometry

##### Point generation methods for inclusion in access_t:

> Notes: excluded from analysis public lands polygons with area < 0.1 hectares.
>
> Excluded all trail clusters with a length less than 500m.

1. Trailheads

    * **tlnd** facil_code: Included points that were associated with *pub_lands_dissolve*, or the nearest one up to a distance of 500m
    * **ttrl** facil_code: Included points that were associated with *vatrails_cluster*, or the nearest one up to a distance of 500m

2. BWT sites

    * **tlnd** facil_code: Included points that were associated with *pub_lands_dissolve*, or the nearest one up to a distance of 500m
    * **ttrl** facil_code: Included points that were associated with *vatrails_cluster*, or the nearest one up to a distance of 500m

3. va_public_access

    - **tlnd** facil_code: Included points that were associated with *pub_lands_dissolve*, or the nearest one up to a distance of 500m
    - **ttrl** facil_code: Included points that were associated with *vatrails_cluster*, or the nearest one up to a distance of 500m

4. wma_points

    - **tlnd** facil_code: Included points that were associated with *pub_lands_dissolve*, or the nearest one up to a distance of 500m
    - **ttrl** facil_code: Included points that were associated with *vatrails_cluster*, or the nearest one up to a distance of 500m

5. Public lands (pub\_lands\_expl\_union)

    * **tlnd** facil_code:
      * for polygons not already associated with an access point, generated ***one point each***:
        * for polygons intersecting roads - the closest point on road intersections to the polygon centroid
        * for polygons not intersecting roads - the closest point on the polygon boundary to a road

6. Trail clusters

    - **ttrl** facil_code:
      - for trail clusters not already associated with an access point, generated ***one point each***:
        - for trails intersecting roads - the closest point on road intersections to the trail cluster centroid
        - for trails not intersecting roads - the closest point on the trails to a road

    

#### Aquatic facilities

All aquatic facilities were input into table ***access_a***, which has the following fields:

- access_a_id: unique table ID
- facil\_code: type of recreation associated with access point, includes following types:
  - *afsh*: access points to known fishing areas
  - *aswm*: access points with known swimming areas
  - *awct*: access points with known watercraft access (boat ramps, landings, etc.)
  - *agen*: other general known access points, but unknown which facilities are available
- src\_table: table of source feature from which the facility point was generated
- src\_id: ID/primary key of source feature in src\_table
- src\_cid: combination of source table code name and source table ID
- join_table: the joined aquatic features table with which the point is associated
- join_fid: the ID of the feature from the joined table with which the point is associated
- join_score: the 'score' of the feature from the joined table with which the point is associated
  - This was area in HA (aquatic areas)
- use: numeric identifying attributes regarding further use in model
  - **0**: don't use
  - **1**: use
  - **2**: use (this is an identifier for useable points that were 'generated', rather than known points of access from a source table)
- use\_why: Reason/method for including the point in analysis
  - populated during point creation, with reasoning for associated *use* value
- road\_dist: distance from point to nearest road
- geom: the point geometry



##### Point generation methods for inclusion in access_a:

> Notes: Points in access_a were joined with either nhd_area_wtrb or nhd_flowline, depending on which they were closer to. In addition, a distance cutoff from the water feature (varies by table) was used to determine if the point should be used in the model

1. va_public access:

   - this layer had the attributes [boat_ramp, fishing, swimming], which were used to determine facil_code. All points not included in any of those classes were assigned the general facil_code *agen*.
   - included points within 300m of an aquatic feature - point snapped to aquatic feature boundary
2. boat_access

   - facil_code = *awct*
   - included points within 300m of an aquatic feature - point snapped to aquatic feature boundary
3. BWT sites

   - facil_code = *agen*
   - included points within 50m of an aquatic feature - point snapped to aquatic feature boundary
4. Trailheads

   - facil_code = *agen*
   - included points within 50m of an aquatic feature - point snapped to aquatic feature boundary
5. wma_points
    - For `type = 'Boat Ramp`: facil_code = *awct*
    - For `type = 'Fishing Pier`: facil_code = *afsh*
    - included points within 50m of an aquatic feature - point snapped to aquatic feature boundary
6. pub_fish_lake_dump

   - facil_code = *afsh*

   - for lakes that did not already have an access point within 50m, generate ***one point only***:
     - for polygons intersecting roads - the closest point on road intersections to the polygon centroid
     - for polygons not intersecting roads - the closest point on the polygon boundary to a road
7. stocked_trout_reaches_diss

    - facil_type = *afsh*

    - for stocked trout reaches that did not already have an access point within 50m:
      - Included points at all intersections with roads
      - For stocked\_trout\_reaches_diss not intersecting roads, generated one point on the line that was closest to a road
8. public_beaches_polys

    - facil_type = *aswm*
    - For each road segment within 50m of a beach boundary, generated one point on the boundary
    - For polygons not within 50m of roads, included one point on the beach polygon closest to a road

### Post-processing

This section describes steps used to prepare the access points for service area analysis.

#### Associating terrestrial facility points with areas/lengths for scoring

Terrestrial access points already were joined with either a public land polygon or a trail cluster. 

- field `join_fid` is used as the unique access feature
- field `join_score` is the area of the associated polygon in hectares for points associated with public land polygons, or the length of associated trail cluster for points associated with trails.

#### Associating aquatic facility points with areas for scoring

Since aquatic access points could not be associated with a defined area or length of public access intuitively like the terrestrial points could with public lands or trails, we generated **aquatic areas** to associate with the points, based on the aquatic access points and the nearby waters. The workflow (in [CreateAquaAccessPolys.py](../CreateAquaAccessPolys.py)) is as follows:

1. We generated an aquatic surface area raster (30m resolution) using all aquatic features from *nhd_area_wtrb* and *nhd_flowline*, plus public fishing lakes and public beach polygons. Water cells were coded 1, and non-water cells were set to NoData (null). This raster layer is called **aqua_rast**.
2. All access points in 'access_a' with  a use code of 1 or 2 were used as sources in a Cost Distance analysis (using ArcGIS Spatial Analyst), with the raster “aqua_rast” serving as the cost surface, simulating travel across the water surface from all sources. The cost distance analysis was run separately for each facil_code, and maximum travel distance was limited as follows:
   - for `facil_code = 'awct'`: used a distance of 5000m
   - for every other facil_code, used a distance of 1000m
3. Access areas created (**separately for each facil_code**)

   - cost distance results were region-grouped and converted to polygons
   - the polygons were called **aqua_accesspolys**

   - The area in hectares was calculated for each distinct aqua_accesspoly
4. Aquatic access points were then joined with their associated access poly, for use in the service area analysis. New fields were added to the **access_a** table:

   - field `gridcode` stores the ID of the unique aqua_accesspoly
   - field `area_ha` is the associated area of the aqua_accesspoly in hectares

 

---

*Last updated: 2018-09-05*