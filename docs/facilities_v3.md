# Virginia Recreation Access Model

**DCR-DNH**

**Purpose:** Overview of data sources and processing steps, for development of recreation access point datasets used in analyses for the Recreation Access Model

**Author**: David Bucklin

**Model year**: 2021

---
[TOC]
---


## Source datasets

### Recreation datasets

#### DCR (PRR and DNH)

- Public_Access_Lands_2021 (Polygon)
  - Represents all public lands in Virginia, with a `ACCESS` column specifying level of access generally
- dcrWaterAccess2020_upd
  - public-access recreation sites and amenities, focused on water access. Includes attributes which indicate specific types of activities available.
  - see the duplicate field; for DCR, only want the lowest ORIG_FID of duplicates
- VATRAILS2020.gdb (Line). Acquired via pers. comm. Jennifer Wampler.
  - Trailheads (Point)
  - LocalTrails, RegionalTrails, StateTrails, FederalTrails (Line)
- Local Park Inventory ([Feature Service](https://services1.arcgis.com/PxUNqSbaWFvFgHnJ/arcgis/rest/services/LocalParks/FeatureServer))
  - This point dataset has attributes on facilities at local (municipalities) parks. Not always spatially precise on location of the facilities, but it has a lot of useful attributes

#### Virginia Dept. of Wildlife Resources (VDWR)

>  All data from DWR is available [here](https://dwr.virginia.gov/gis/data/).

- Public\_fishing\_lakes (Point)
- Stocked\_Trout\_Reaches (Line)
- Stocked_Trout_Lakes (Point)
- Birding\_&\_Wildlife\_Trail\_Sites (Point)
  - these have a list of facilities, to identify boat ramps, trail access, among many other facilities. Spatial accuracy seems pretty good. May want to use these to identify parks not in managed lands or local parks datasets.
- Boating_Access_Sites (Point)
  - have a `NO_OFRAMPS` attribute which could be useful
- DGIF_WMA_Facilities (Point)
  - points of access for DGIF's wildlife management area 
- Fishing_Piers (Point)

#### Other data sources

From Virginia Institute of Marine Science (VIMS):

- PublicBeaches (Line)

From USGS/Conservation Biology Institute:

- Protected Areas Database, v2.1 [(link)](https://www.usgs.gov/core-science-systems/science-analytics-and-synthesis/gap/science/pad-us-data-download?qt-science_center_objects=0#qt-science_center_objects)

Water access datasets (various sources):

- Chesapeake Bay: Public Access Sites (2009-2019) [(link)](https://data-chesbay.opendata.arcgis.com/datasets/public-access-sites-2009-2019)
- North Carolina: BAA [(link)](https://www.nconemap.gov/datasets/ncwrc::baa) and PFA [(link)](https://www.nconemap.gov/datasets/ncwrc::pfa)
- West Virginia: Boat Launches [(link)](https://wvgis.wvu.edu/data/dataset.php?ID=88)  and Public Fishing Areas [(link)](https://wvgis.wvu.edu/data/dataset.php?ID=194)
- Tennessee: Boating Ramps & Access [(link)](https://www.tn.gov/twra/boating/ramps-and-access.html)
- Kentucky: Fishing access sites [(link)](https://kygeoportal.ky.gov/geoportal/catalog/search/resource/details.page?uuid=%7BAF984DFA-6682-44FA-A9C0-BED216E1989D%7D)

### Road/path centerline data

From OpenStreetMap: 
  - roads data from [Geofabrik](http://download.geofabrik.de/north-america/us.html), downloaded as shapefile for each state in the study area.

Road/path segments were assigned a speed (SPEED_MPH) and travel time in minute (TT_MIN). A Network Dataset was created from this dataset, using TT_MIN as the accumulation attribute. This dataset was used for all travel time-based analyses.

Road/path data were also used for:
  - calculation of available area within PPAs
  - placement of 'generated' access points for recreation features

### Aquatic features 

From the National Hydrography Dataset (NHD), high resolution (1:24,000):

- derived the feature class *NHD_AreaWaterbody* by merging:
  - NHDArea
    - definition query: `FTYPE IN (445, 460, 312 , 364, 336)`: BayInlet, Foreshore, SeaOcean, StreamRiver; CanalDitch
  - NHDWaterbody
    - definition query: `FTYPE IN (390, 436, 493)`: LakePond, Reservoir, Estuary
- NHDFlowline
    - definition query: `FTYPE IN (460, 558 ,336)`: ArtificialPath, StreamRiver, CanalDitch

Aquatic features were used for:
- erasing open water areas from PPAs (NHD_AreaWaterbody only)
- QA/QC of water access points
  
## Recreation Data processing

### Pre-processing

Some polygon and line datasets are considered **Recreational Features**, and generally required some pre-processing prior to use in the the model. These steps are included in the script file [RecFeatures.py](../RecFeatures.py).

**public_lands_final**: This dataset represents all parks and protected areas (PPAs) with public access. It combines data from the two original protected areas datasets, and is planarized (flattened), dissolving boundaries between overlapping PPAs from the original datasets. Polygons in the dataset are attributed with a unique **group_id**, and inherits the name of the largest source polygon from the original dataset. This dataset is the starting point for all subsequent PPA analyses. For each polygon, the following attributes were calculated (using acres as the area unit):

  - Total area
  - Greenspace area
  - Available area
  - Available greenspace

### Standardizing input datasets

Each recreation dataset was run through the [PrepRecDataset](../PrepRecDataset.py) function, adding a standard set of attributes to each dataset. 

> The [PrepRecDataset](../PrepRecDataset.py) function can be imported into ArcGIS Pro as a script tool.

Six fields describing the type(s) of recreation available at the feature or access point were added, and attributed with 1 (access for that type) or 0 (no access for that type):

- **a_awct** : watercraft (motorboat, kayak, canoe, etc.) access
- **a_afsh**: fishing access 
- **a_aswm**: swimming access (*pools not included*)
- **a_agen**: un-specified water access
- **t_ttrl**: terrestrial trails access
- **t_tlnd**: public land access

If all features in a given dataset represented access for a given type (e.g. trail access for trail features, fishing access for fishing piers), the attributes were assigned during the preparation

### Making access point datasets

The script file [AccessPoints.py](../AccessPoints.py)  was used to combine all recreation datasets into a 'master' access points dataset. Key aspects of this workflow include:
  - assignment of access types for subsets of features in a given recreation dataset, based on the dataset's attributes
  - assignment of access types to access points, based on proximity to recreation features datasets
  - generation of one access point per un-associated recreation feature, using intersection or proximity to roads to determine placement of the point
  - association of access points with PPAs, where the 'join_' attributes of access points are updated with attributes from PPAs.
  - creating output access point datasets for usage as Facilities in network analyses, which include only points for given access type(s). For the 2021 model, two datasets were generated:
    1. access points for watercraft, fishing, or swimming access. A `group_id` field was added, where all points within 0.25 miles of one another are assigned the same value.
    2. access points for PPAs (t_lnd = 1). The `ppa_group_id` field is inherited from the `group_id` field of **public_lands_final**, and is used for grouping in the network analyses.

------

*Last updated: 2021-04-26*