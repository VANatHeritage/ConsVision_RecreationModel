# General Workflow for Recreation model

Author: David Bucklin

Date : 2018-05-25

---

[TOC]

## Gather input datasets

Spatial datasets representing recreational amenities and roads in Virginia were gathered from multiple sources.

#### From [VOP_mapper](http://dswcapps.dcr.virginia.gov/dnh/vop/vopmapper.htm):

- publiclands\_wgs
- trailheads
- state\_existing
- Managed\_Trails
- scenicrivers
- VA\_public\_access (boat access)

> Shapefiles were sent by David Boyd, who managed VOP Mapper for DCR.

#### From [VDGIF](https://www.dgif.virginia.gov/gis/data/download/):

- Public_fishing_lakes
- Stocked_Trout_Reaches
- Birding_and_Wildlife_Trail_Sites
- VDGIF\_Maintained\_Boating\_Access\_Locations

#### From VIMS:

- PublicBeachesExtents

> Shapefiles sent by GIS specialist at VIMs. Note that dataset has not been updated by VIMs since 2000.

#### From [VGIN](http://vgin.maps.arcgis.com/home/item.html?id=cd9bed71346d4476a0a08d3685cb36ae): 

- Virginia\_RCL\_Dataset\_2017Q3.gdb

All datasets were entered into a PostgreSQL database named **rec_model_source**.

## Set up road Network Dataset

The road centerline dataset was used to generate an ArcGIS Network Analyst Network Dataset. This was accomplished using a wizard tool in ArcMap 10.3.

The general workflow for setting up the network dataset is described in the [RCL-Tools](https://github.com/VANatHeritage/RCL-Tools/blob/master/NetworkAnalyst-Setup.txt) repository. For this analysis, we excluded the following roads/trails types from the Network Dataset:

>  mtfcc IN ('S9999','S1710','S1720','S1740','S1820','S1830','S1500')

This excludes driveways, walkways/ped. trails, stairways, service vehicle private drives, bike paths/trails, bridle paths, and 4wd vehicular trails.

## Generate recreational "facilities" (access points)

In the **rec_model_source** database, a series of spatial SQL queries were executed to generate access points to use as *facilities* in the Service Area Analysis, and associate points with areas (Public Lands for terrestrial; Public fishing lakes, Canoe-only public lands, or NHD features for aquatic), based on intersection or distance to the area feature.

The queries are found in the script [all_facil.sql](https://github.com/VANatHeritage/ConsVision_RecreationModel/blob/master/sql/all_facil.sql).

Facilities were categorized as either **terrestrial** or **aquatic**, based on their primary recreational usage, or their location, if usage was uncertain (Birding and Wildlife trails). A full description of the workflow is found in the [facilities.md](./facilities.md) document. 

#### Terrestrial recreational sites input datasets

- Trailheads
- BWT sites
- Trails
- Public Lands

The final dataset was named **all_facil**, which include ***4751 points***.

#### Aquatic recreational sites input datasets

- Boating and water access locations
- BWT sites (those adjacent to public waters)
- Public fishing lakes
- Canoe-only public lands
- Stocked trout reaches
- Wild and scenic rivers (Designated only)
- Public Beaches

The final dataset was named **all_facil_aqua**, which included ***1392 points***.

## Run Service Area Analysis

Points in the **all_facil**  and **all_facil_aqua** datasets were given group IDs using a 500m separation distance (field name `grpID_500m`). For each group a Service Area Analysis was run in ArcGIS using Network Analyst. Service area polygons were generated for each group using a Service Area of **30 minutes** (drive time). Service areas were not generated for facilities that were more than **500m** from the nearest road.

This process was done in the python script [RunServiceAreaAnalysisLoop.py](../RunServiceAreaAnalysisLoop.py). 

For each unique group, the following output datasets were created:

- Facilities (input points)
- Lines (roads included in the Service Area Network)
- Polygons (Areas included in the Service Area network)

## Combine service areas

Once all groups of recreational facilities had 30-minute Service Area polygons, they were combined in the script [RecRastFromPolys.py](../RecRastFromPolys.py).

For each Service Area Polygon, a raster dataset was generated using the following steps:

1. identify all facilities points associated with the service area
2. sum the total area (in hectares) of unique facilities associated with these points (if points associated with area)
3. calculate a **score** based on this area
   - score = `sqrt(hectares + 0.01)`
   - the 0.01 allowed for a minimal score for Services Areas to facilities that were not associated to any area-based recreational sites
   - scores above 100 were rounded down to 100.

Once rasters were generated from all Service Areas, a **Summary Raster** (`sum.tif`) was generated by summing all individual Service Area rasters.

## Finalize recreation model 

The script [RecModelFinalize.py](../RecModelFinalize.py) performs the following steps to finalize the recreation model:

- burn-in recreational features (polygons or lines) with a value of **101**.

- calculate scores around borders of burned-in recreational areas using a distance-decay function based on the **original feature's area score**, decaying based on **walking speed**. Areas within 2414 meters (30 minutes at walking speed) or recreational areas were affected.

- rescale the final model (outside burned-in 101 areas) from **0 - 100**.

  - For the terrestrial component, areas with scores above **1000** were set to the max value (100). Values between 1-1000 were linear rescaled from 0 - 100 and converted to integer, e.g.:

    > Con("TerrRawSum.tif">1000,100, 100*"TerrRawSum.tif"/1000)

  - For the aquatic component, areas with scores above **100** were set to the max value (100). Values between 1-100 were linear rescaled from 0 - 100 and converted to integer, e.g.:

    > Con("AquaRawSum.tif">100,100, 100*"AquaRawSum.tif"/100)

---

*Last updated 2018-05-25*.