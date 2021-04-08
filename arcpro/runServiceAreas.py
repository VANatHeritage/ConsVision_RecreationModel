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

# Environment Settings (note that snap, cell size, coordinate system, extent are set within makeServiceAreas function)
arcpy.env.mask = r'L:\David\projects\RCL_processing\RCL_processing.gdb\VA_Buff50mi_wgs84'
arcpy.env.overwriteOutput = True

# Cost rasters and ramp points
costRastLoc = r'E:\RCL_cost_surfaces\Tiger_2020\cost_surfaces.gdb\costSurf_no_lah'
costRastHwy = r'E:\RCL_cost_surfaces\Tiger_2020\cost_surfaces.gdb\costSurf_only_lah'
rampPts = r'E:\RCL_cost_surfaces\Tiger_2020\cost_surfaces.gdb\rmpt_final'
rampPtsID = 'UniqueID'  # unique ramp segment ID attribute field, since some ramps have multiple points

# Access features source GDB. Can output data here to use as inputs
accFeatGDB = r'E:\projects\rec_model\rec_model_processing\access_pts.gdb'
# Service areas GDB. Set this as the location for new service area GDBs
servAreaDir = r'E:\projects\rec_model\rec_model_processing\serviceAreas'

# TODO:
#  Park (any size) within a 10-minute walk
#  Large park (1000+ acres) within a 30-minute drive
#  Pedestrian trailhead for large trail network (10+ miles? or one of the “statewide” trails?) within a 30-minute drive
#  x State park within a 60-minute drive (this is a stated goal)
#   - include development SPs (Machimococo, Biscuit Run, Sweet Run)?
#  Variety: at least 3 different parks within a 30-minute drive
#  x Boat access within a 30-minute drive
#  x Fishing access within a 30-minute drive
#  x Swimming access within a 30-minute drive


# 1. Methods for individual service areas (aquatics loop)
arcpy.env.parallelProcessingFactor = "0%"  # Adjust to some percent (e.g. 100%) for large extent analyses.
# original source features
# accFeat0 = r'E:\projects\rec_model\rec_datasets\rec_datasets_working.gdb\public_lands_final_accessAreas'
for d in ['access_points_a_swm_20210406', 'access_points_a_wct_20210406', 'access_points_a_fsh_20210406']:
   accFeat = accFeatGDB + os.sep + d
   # Set run parameters
   outGDB = servAreaDir + os.sep + 'servArea_30min_' + os.path.basename(accFeat) + '.gdb'
   grpFld = 'group_id'  # 'join_fid'
   maxCost = 30
   attFld = None  # 'SUM_accgreen_acres'  # 'join_score'
   makeServiceAreas(outGDB, accFeat, costRastLoc, costRastHwy, rampPts, rampPtsID, grpFld, maxCost, attFld)


# 1. Methods for individual service areas
arcpy.env.parallelProcessingFactor = "0%"  # Adjust to some percent (e.g. 100%) for large extent analyses.
# original source features
accFeat0 = r'E:\projects\rec_model\rec_datasets\rec_datasets_working.gdb\public_lands_final_accessAreas'
# Make the specific access feature sources layer, if necessary
# accFeat = arcpy.MakeFeatureLayer_management(accFeat0, where_clause="use IN (1,2)")   # state parks
accFeat = arcpy.MakeFeatureLayer_management(accFeat0, where_clause="access = 1 AND accgreen_acres > 100")
# decide: acreage limit
#  PPA accgreen acres
#  >100 = 1030
#  >600 = 280
#  >1000 = 197
# Set run parameters
outGDB = servAreaDir + os.sep + 'servArea_30min_' + os.path.basename(accFeat) + '.gdb'
grpFld = 'group_id'  # 'join_fid'
maxCost = 30
attFld = 1  # 'SUM_accgreen_acres'  # 'join_score'
makeServiceAreas(outGDB, accFeat, costRastLoc, costRastHwy, rampPts, rampPtsID, grpFld, maxCost, attFld)


# 2. Methods for drive time to closest facility. No time limit. attFld=None returns actual cost distance in minutes.
arcpy.env.parallelProcessingFactor = "80%"  # Adjust to some percent (e.g. 100%) for large extent analyses.
# PPAs
accFeat0 = r'E:\projects\rec_model\rec_datasets\rec_datasets_working.gdb\public_lands_final_accessAreas'
accFeat = arcpy.Select_analysis(accFeat0, accFeatGDB + os.sep + os.path.basename(accFeat0), "accgreen_acres >= 5")
outGDB = servAreaDir + os.sep + 'driveTime_5acAG_' + os.path.basename(accFeat0) + '.gdb'
# aqautics
# accFeat = r'E:\projects\rec_model\rec_model_processing\access_pts.gdb\access_points_combined_20210406'
# outGDB = servAreaDir + os.sep + 'driveTime_' + os.path.basename(accFeat) + '.gdb'
grpFld = None  # Treats all rows as one group.
maxCost = None
attFld = None
makeServiceAreas(outGDB, accFeat, costRastLoc, costRastHwy, rampPts, rampPtsID, grpFld, maxCost, attFld)

# round values
inRast = outGDB + os.sep + 'grp_1_servArea'
outRast = inRast + '_rnd'
roundRast(inRast, outRast)



# end
