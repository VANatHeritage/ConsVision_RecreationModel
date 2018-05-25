## Virginia Recreation Access Model, facilities workflow

DCR-DNH

Author: David Bucklin

Date: 2017-11-17

[TOC]

### Input data 

*Recreation Input datasets*

From VOP Mapper:

- publiclands\_wgs (Polygon)
- trailheads (Point)
- state\_existing (Line)

- Managed\_Trails (Line)

- scenicrivers (Line)

- VA\_public\_access (Point)

From VDGIF:

- Public\_fishing\_lakes (Polygon)
- Stocked\_Trout\_Reaches (Line)
- Birding\_&\_Wildlife\_Trail\_Sites (Point)

- VDGIF\_Maintained\_Boating\_Access\_Locations (Point)

From VIMS:

- PublicBeaches (Line)

*Road centerline data*

From VGIN:

- Virginia\_RCL\_Dataset\_2017Q3.gdb (Line)

> Note: the following road types were excluded from all analyses:
>
> mtfcc IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500')
>
> This excludes driveways, walkways/ped. trails, stairways, service vehicle private drives, bike paths/trails, bridle paths, 4wd vehicular trails.

### Data pre-processing

All feature classes were entered into a PostgreSQL geodatabase without modification, with the exception of **publiclands\_wgs**. This dataset was split into two tables:

-  *pub\_lands\_dissolve*, for terrestrial lands included the following "PUBACCESS" values: (open, open fee, open with restrictions, open/seasonal, weekends
  - Exploded polygons were grouped if they were within 50m of one another
  - this new table was named **pub\_lands\_expl\_union**
-  *pub\_lands\_dissolve\_aqua*, included "PUBACCESS" values: (Canoe only)
  - In the database, pub\_lands\_dissolve\_aqua was merged with public fishing lakes, and all polygons in this set were grouped if they were within 50m of one another
  - this new table was named **pub\_lands\_aqua\_union**

### Generating facilities from recreation datasets

The ArcGIS extension Network Analyst requires point features as inputs for facilities in a service area computation. We divided recreational facilities into two groups: terrestrial and aquatic. The following describes methods and rules used to generate facilities points for each input dataset.

> Note: All methods where facilities were associated with a road (intersecting, or closest point on a facility to a road) excluded limited access roads [mftcc IN ('S1100','S1100HOV','S1640')].

#### Terrestrial facilities

All terrestrial facilities were input into table ***all\_facil***, which has the following fields:

* all\_facil\_id: unique table ID
* facil\_code: type of facility
  * all classified as `terr`; may be further utilized in the future
* src\_table: table of source feature from which the facility point was generated
* src\_id: ID of source feature in src\_table
* src\_cid: combination of source table code name and source table ID
* plxu\_fid: for points associated with a pub\_lands\_expl\_union polygon, the id of that polygon
* plxu\_area: for points associated with a pub\_lands\_expl\_union polygon, the area of that polygon
* road\_dist: distance from point to nearest road
* use\_why: Reason/method for including the point in all\_facil
  * populated during association of points with line/polygon features, and line/polygon features with roads. **Possible values include**: 
    * "boundary intersects road"
    * "closest point on boundary to road"
    * "intersects pub_lands_expl"
    * "intersects pub_lands_expl_union"
    * "solo bwt site"
    * "within 500m managed_trails_union"
    * "within 500m pub_lands_expl"
    * "within 500m pub_lands_expl_union"
    * "within 500m state_trails"
* geom: the point geometry

##### Point generation methods for inclusion in all\_facil:

1. Trailheads (points)

    * Included trailheads that were associated with an intersecting or the nearest terrestrial public lands polygon, or the nearest one up to a distance of 500m
    * Included trailheads not associated with a public lands polygon if they were within 500m of mapped trails (from state\_existing or Managed\_Trails)
    * other trailheads (n=77) were excluded

2. BWT sites (points)

    * Included BWT sites that were associated with an intersecting terrestrial public lands polygon, or the nearest one up to a distance of 500m
    * all remaining BWT sites were included as non-associated sites

3. Public lands (pub\_lands\_expl\_union) [WORKING]

    * For public lands polygons not associated with Trailheads or BWT sites layers, generated points at intersections with roads

    * For public lands polygons not associated with Trailheads or BWT sites layers and without any road intersections, generated a point at the closest point on the polygon boundary to a road

      ​

#### Aquatic facilities

All terrestrial facilities were input into table ***all\_facil***, which has the following fields:

- all\_facil\_id: unique table ID
- facil\_code: type of facility
  - all classified as `aqua`: may be further utilized in the future
- src\_table: table of source feature from which the facility point was generated
- src\_id: ID of source feature in src\_table
- src\_cid: combination of source table code name and source table ID
- plau\_fid: for points associated with a pub\_lands\_aqua\_union polygon, the id of that polygon
- plau\_area: for points associated with a pub\_lands\_aqua\_union polygon, the area of that polygon
- road\_dist: distance from point to nearest road
- use\_why: Reason/method for including the point in all\_facil
  - Populated during association of points with line/polygon features, and line/polygon features with roads. **Possible values include**: 
    - "boundary intersects road"
    - "closest point on boundary to road"
    - "closest point on line to road"
    - "intersects pub_lands_aqua_union"
    - "line intersects road"
    - "solo boat_access site"
    - "solo water_access site"
    - "within 500m pub_lands_aqua_union"
- geom: the point geometry
- nhd\_why: Reasoning behind association with NHD feature
  - For points not associated with pub_lands_aqua_union features. See the section **Associating aquatic facility points with NHD features** below. Possible values:
    - "within 500m of nhdArea StreamRiver type"
    - "within 500m of nhdWaterbody SwampMarsh type"
    - "streamorder of closest nhd reach"
    - "within 500m of nhdArea SeaOcean type"
    - "unassociated facility"
- nhd\_farea: "scored" area for point based on association with NHD feature
- comb\_area: combination of plau\_area and nhd\_farea fields



##### Point generation methods for inclusion in all\_facil\_aqua:

1. Boat/water access (note this includes two different tables, 'boat\_access' and 'water\_access')

    - Included boat/water access sites that associated with an intersecting pub\_lands\_aqau\_union polygon, or the nearest one up to a distance of 500m

    - All remaining boat/water access sites were included as non-associated sites

      > Note: "duplicates" from water\_access that were within 30m of a boat\_access point were excluded

2. BWT sites

    - were associated with an intersecting or the nearest terrestrial pub\_lands\_aqua\_union polygon, up to a distance of 500m

      >  Did **not** include un-associated BWT sites in all_facil_aqua

3. pub\_lands\_aqua\_union (includes Public lakes and canoe-only public lands)

    - For polygons not associated with Boat/water access sites or BWT sites, generated points at intersections with roads

    - For polygons without associated Boat/water access sites or BWT sites and without road intersections, include the closest point on the polygon boundary to a road

4. stocked trout reaches

    - Included points at all intersections with roads, if they were within public lands or within 500m of public lands (terrestrial or aquatic)
    - For stocked\_trout\_reaches lines not intersecting roads, generated a point on the line that was closest to a road, within public lands or within 500m of public lands (terrestrial or aquatic)

5. wild and scenic rivers

    > Note: Only included "Designated" scenic rivers

    -  Included points at all intersections with roads, if they were within public lands or within 500m of public lands (terrestrial or aquatic)

    -  For wild and scenic rivers not intersecting roads, generated a point on the line that was closest to a road, within public lands or within 500m of public lands (terrestrial or aquatic)

6. Public beaches

    - included points at intersections with roads
    - For public beaches lines not intersecting roads, included the closest point on the beach line to a road

##### all\_facil\_aqua Post-processing

###### Associating aquatic facility points with NHD features

In order to attach an "area" value to all facility points for aquatic facilities, we used NHD flowline, area, and waterbody features to generate a "scored" area reflecting the size of the waterbody which which the facility is associated. 

NHD "areas" were only added to points not associated with a pub\_lands\_aqua\_union polygon (lakes, canoe-only areas). The following hierarchical method was used (a given point could only get associated through the first method that applied to it).

1. For a point within 500m of NHDArea polygons with ftype IN ('SeaOcean','BayInlet','Foreshore')

    - nhd\_farea = 10000

2. For points within 500m of NHDArea polygons with ftype = 'StreamRiver'

    - nhd\_farea = 100

3. For points within 500m of NHDWaterbody polygons with ftype = 'SwampMarsh'

    - nhd\_farea = 100

      > Note: these were primarily coastal/estuarine/large river-floodplain areas

4. For points within 500m of a NHD reach

    - nhd\_farea = closest reach streamorder \* 2

      > Note: Stream orders in NHD range from 1-7 in Virginia

5. Not within 500m of an NHD feature from above methods

    - nhd\_farea = 0 (n = 13 facilities)

###### Final "area" score

The field 'comb_area' was the final area score given to the point.

- Points with values in the column 'plau_area' were populated with that area
- Points with values in the column 'nhd_farea' were populated with that "area" score

---

*Last updated: 2018-05-25*