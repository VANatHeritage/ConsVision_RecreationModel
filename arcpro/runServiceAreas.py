# -*- coding: utf-8 -*-
"""
runServiceAreas

Created: 2018-07
Last Updated: 2020-10-23
ArcGIS version: ArcGIS Pro
Python version: Python 3.6.6
Author: David Bucklin

This script imports the makeServiceAreas function
from the ServiceAreas repository.
https://github.com/VANatHeritage/ServiceAreas
Download or git clone the repo, and set the local path to it below.
"""

import sys
import arcpy
sys.path.append(r'E:\git\ServiceAreas')
from makeServiceAreas import *

"""
makeServiceAreas Argument definitions:
   outGDB: Name of output geodatabase, which is created during the process.
   accFeat: Access features to run cost distance process on
   costRastLoc: A cost surface for all local (non-limited access) roads
   costRastHwy: A cost surface for all limited access roads
   rampPts: A point feature class defining connection points between
      local and limited access roads.
   rampPtsID: a unique id corresponding to a given ramp/connection
   grpFld: The grouping attribute field name for accFeat, where one cost distance is run for each group
   maxCost: the maximum cost distance allowed. Can be:
         1. a string indicating the column in 'accFeat' which contains the numeric values to use as maximum costs.
         2. a numeric value indicating the maximum cost to apply to all service areas
         3. None (empty). No maximum distance;
   attFld: Optional. A score value to apply to the service area raster.
      'attFld' can be:
         1. a string indicating the column in 'accFeat' which contains the numeric value to apply.
         2. an integer value, applied as a constant to the service area raster.
         3. None (empty). The original cost distance raster is returned (value = the cost distance).
"""

# Environment Settings
arcpy.env.parallelProcessingFactor = "0"  # Adjust to some percent (e.g. 100%) for large extent analyses.
arcpy.env.mask = r'L:\David\projects\RCL_processing\RCL_processing.gdb\VA_Buff50mi_wgs84'

# Cost rasters and ramp points
costRastLoc = r'E:\RCL_cost_surfaces\Tiger_2019\cost_surfaces.gdb\costSurf_no_lah'
costRastHwy = r'E:\RCL_cost_surfaces\Tiger_2019\cost_surfaces.gdb\costSurf_only_lah'
rampPts = r'E:\RCL_cost_surfaces\Tiger_2019\cost_surfaces.gdb\rmpt_final'
rampPtsID = 'UniqueID'  # unique ramp segment ID attribute field, since some ramps have multiple points

# 1. Methods for individual service areas
facil_date = 't_ttrl_20190225' # suffix of filename
outGDB = r'E:\arcpro_wd\rec_model_temp\serviceAreas_modelupdate_Feb2019\access_' + facil_date + '.gdb'
accFeat = r'E:\arcpro_wd\rec_model_temp\access_pts.gdb\access_' + facil_date
grpFld = 'join_fid'
maxCost = 60
attFld = 'join_score'
makeServiceAreas(outGDB, accFeat, costRastLoc, costRastHwy, rampPts, rampPtsID, grpFld, maxCost, attFld)

# 2. Methods for time to closest facility. Returns actual cost distance in minutes.
accPts = r'E:\arcpro_wd\rec_model_temp\access_pts.gdb\access_all_forregional'
outGDB = r'E:\arcpro_wd\rec_model_temp\serviceAreas_modelupdate_Feb2019\access_all_60min.gdb'
grpFld = 'facil_code'
maxCost = 60
attFld = None
makeServiceAreas(outGDB, accPts, costRastLoc, costRastHwy, rampPts, rampPtsID, grpFld, maxCost, attFld)

# end
