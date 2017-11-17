## Virginia Recreation Access Model, facilities workflow

DCR-DNH

Author: David Bucklin

Date: 2017-11-17

### Input data 

*Recreation Input datasets*

From VOP Mapper:

- publiclands\_wgs (Polygon)
- trailheads (Point)
- state\_existing (Line)

- Managed\_Trails (Line)

- scenicrivers (Line)

- VA\_public\_access (Point

From VDGIF:

- Public\_fishing\_lakes (Polygon)
- Stocked\_Trout\_Reaches (Line)
- Birding\_&\_Wildlife\_Trail\_Sites (Point)

- VDGIF\_Maintained\_Boating\_Access\_Locations (Point)

From VIMS:

- PublicBeaches (Line)

*Road centerline data*

- Virginia\_RCL\_Dataset\_2017Q3.gdb

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

Network analyst requires point features as inputs for facilities in a service area computation. We divided recreational facilities into two groups: terrestrial and aquatic. The following describes methods and rules used to generate facilities points for each input dataset.

> Note: All methods where facilities were associated with a road (intersecting, or closest point on a facility to a road) excluded limited access roads [ mftcc IN ('S1100','S1100HOV','S1640') ].

#### Terrestrial facilities

All terrestrial facilities were input into table ***all\_facil***, which has the following fields:

* all\_facil\_id: unique table ID
* facil\_code: type of facility
* src\_table: table of source feature from which the facility point was generated
* src\_id : ID of source feature in src\_table
* src\_cid : combination of source table code name and source table ID
* plxu\_fid : for points associated with a pub\_lands\_expl\_union polygon, the id of that polygon
* plxu\_area : for points associated with a pub\_lands\_expl\_union polygon, the area of that polygon
* road\_dist: distance from point to nearest road
* use\_why: Reason/method for including the point in all\_facil
* geom (the point geometry)

##### Point generation methods for inclusion in all\_facil:

1.  Trailheads (points)

    * were associated with an intersecting or the nearest terrestrial public lands polygon, up to a distance of 500m
    * non-associated trailheads that were within 500m of mapped trails (from state\_existing or Managed\_Trails) were included
    * other trailheads (n=77) were excluded

2.  BWT sites (points)

    * were associated with an intersecting or the nearest terrestrial public lands polygon, up to a distance of 500m
    * all remaining BWT sites were included as solo sites

3.  Public lands (pub\_lands\_expl\_union)

    * For public lands polygons still not included in all\_facil, include all polygon boundary intersections with roads (excluding limited access roads)

    * For public lands polygons still not included in all\_facil, include the closest point on the polygon boundary to a road

      ​

#### Aquatic facilities

All terrestrial facilities were input into table ***all\_facil***, which has the following fields:

- all\_facil\_id: unique table ID
- facil\_code: type of facility
- src\_table: table of source feature from which the facility point was generated
- src\_id : ID of source feature in src\_table
- src\_cid : combination of source table code name and source table ID
- plau\_fid : for points associated with a pub\_lands\_aqua\_union polygon, the id of that polygon
- plau\_area : for points associated with a pub\_lands\_aqua\_union polygon, the area of that polygon
- road\_dist: distance from point to nearest road
- use\_why: Reason/method for including the point in all\_facil
- geom (the point geometry)
- nhd\_why: Reasoning behind association with NHD feature
- nhd\_farea: "scored" area for point based on association with NHD feature
- comb\_area: combination of plau\_area and nhd\_farea fields



##### Point generation methods for inclusion in all\_facil\_aqua:

1.  Boat/water access (note this includes two different tables, 'boat\_access' and 'water\_access')

    - were associated with an intersecting or the nearest terrestrial pub\_lands\_aqau\_union polygon, up to a distance of 500m

    - un-associated points were included as solo sites

      > Note: "duplicates" from water\_access that were within 30m of a boat\_access point were excluded

2.  BWT sites

    - were associated with an intersecting or the nearest terrestrial pub\_lands\_aqua\_union polygon, up to a distance of 500m

3.  pub\_lands\_aqua\_union (Public lakes and canoe-only lands)

    - For pub\_lands\_aqua\_union still not included in all\_facil\_aqua, include all polygon boundary intersections with roads (excluding limited access roads)
    - For pub\_lands\_aqua\_union still not included in all\_facil\_aqua, include the closest point on the polygon boundary to a road

4.  stock trout reaches

    - Include all intersections with roads, that also fall within 500m of public lands (terrestrial or aquatic)
    - For stocked\_trout\_reaches still not included in all\_facil\_aqua, include the closest point on the line to a road, that also falls within 500m of public lands

5.  wild and scenic rivers

    -  Include all intersections with roads, that also fall within 500m of public lands (terrestrial or aquatic)

    - For wild and scenic rivers still not included in all\_facil\_aqua, include the closest point on the line to a road, that also falls within 500m of public lands

      > Note: Only included "Designated" scenic rivers

6.  Public beaches

    a.  included intersections with roads

    b.  For public beaches still not included in all\_facil\_aqua, include the closest point on the beach line to road

##### all\_facil\_aqua Post-processing: Associating aquatic facility points with NHD features

NHD "areas"were added to points not associated with a pub\_lands\_aqua\_union polygon. The following hierarchical method was used (a given point could only get associated through the first method that applied to it).

1.  For a point within 500m of NHDArea polygons with ftype IN ('SeaOcean','BayInlet','ForeShore')

    - nhd\_farea = 10000

2.  For points within 500m of NHDArea polygons with ftype = 'StreamRiver'

    - nhd\_farea = 100

3.  For points within 500m of NHDWaterbody polygons with ftype = 'SwampMarsh

    - nhd\_farea = 100

      > Note: these were primarily coastal/estuarine/large river-floodplain areas

4.  For points within 500m of a NHD reach

    -  nhd\_farea = closest reach streamorder \* 2

5.  Not within 500m of an NHD feature from above methods

    - nhd\_farea = 0 (n = 13 facilities)
