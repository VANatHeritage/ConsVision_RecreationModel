# -*- coding: utf-8 -*-
# TODO: update this from ServiceAreas repo
"""
makeServiceAreas

Created: 2018-07
Last Updated: 2020-10-09
ArcGIS version: ArcGIS Pro
Python version: Python 3.6.6
Author: David Bucklin

Raster-based approach for building service areas,
using a two raster cost-surface +
connection points approach.

Local roads (non-limited access highways)
and limited access highways. Cost distance
is run iteratively on (1) local and (2) limited access
roads until the maximum cost is reached, with connection
points (rampPts) defining where local roads and limited
access roads meet.

Argument definitions:
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
         This option is customized for VA Recreation Model to calculate variable service area times (see codeblock).
      2. an integer value, applied as a constant to the service area raster.
      3. None (empty). The original cost distance raster is returned (value = the cost distance).

FIXME: Major slowdown in ArcGIS Pro with Cost Distance, after upgrading to v.2.3 (from 2.0). See:
 https://community.esri.com/thread/235940-noticing-a-major-slowdown-in-cost-distance-function-following-version-change
 FIXED 2020-10-09: appears to have been improved as of ArcPro 2.6; not 'hanging' anymore.
"""

from Helper import *


def makeServiceAreas(outGDB, accFeat, costRastLoc, costRastHwy, rampPts, rampPtsID, grpFld, maxCost=None, attFld=None):

   if attFld and not maxCost:
      print('Must specify a `maxCost` value if using `attFld`, exiting...')
      return

   arcpy.env.snapRaster = costRastLoc
   arcpy.env.cellSize = costRastLoc
   arcpy.env.extent = costRastLoc
   arcpy.env.outputCoordinateSystem = costRastLoc

   make_gdb(outGDB)
   arcpy.env.workspace = outGDB
   arcpy.SetLogHistory(False)

   # copy access points to gdb
   accFeat = arcpy.CopyFeatures_management(accFeat, 'accFeat_orig')
   grps = unique_values(accFeat, grpFld)

   # assign max costs
   if maxCost:
      if isinstance(maxCost, str):
         arcpy.CalculateField_management(accFeat, 'minutes_SA', '!' + maxCost + '!', field_type="FLOAT")
      else:
         arcpy.CalculateField_management(accFeat, 'minutes_SA', maxCost, 'PYTHON', field_type="FLOAT")
      # dictionary: grps: minutes
      grp_min = {a[0]: a[1] for a in arcpy.da.SearchCursor(accFeat, [grpFld, 'minutes_SA'])}

   for i in grps:
      n = grps.index(i) + 1
      if isinstance(i, str):
         rastout = "grp_" + i + "_servArea"
         cdpts = "grp_" + i + "_inputFeat"
         i_q = "'" + i + "'"
      else:
         rastout = "grp_" + str(int(i)) + "_servArea"
         cdpts = "grp_" + str(int(i)) + "_inputFeat"
         i_q = i
      if arcpy.Exists(rastout):
         # skip already existing
         continue

      print("working on group " + str(i) + " (" + str(n) + " of " + str(len(grps)) + ")...")
      arcpy.env.extent = costRastLoc  # so points don't get excluded due to previous extent setting
      t0 = time.time()
      c = 1  # counter

      arcpy.Select_analysis(accFeat, cdpts, grpFld + " = " + str(i_q))
      print('Number of access pts: ' + arcpy.GetCount_management(cdpts)[0])

      # get service area in minutes
      if maxCost is not None:
         grpMaxCost = grp_min[i]  # round(unique_values(cdpts, 'minutes_SA')[0], 1)
         buffd = str(int(grpMaxCost * 1750)) + ' METERS'  # buffer set to straightline distance at ~65 mph
         print('Cost in minutes: ' + str(grpMaxCost))
         arcpy.Buffer_analysis(cdpts, "buffpts", buffd)
         arcpy.env.extent = "buffpts"
      else:
         grpMaxCost = None

      # local CD
      cd1 = arcpy.sa.CostDistance(cdpts, costRastLoc, grpMaxCost)
      nm = "cd" + str(c)
      cd1.save(nm)
      cds = [nm]

      # values to ramps
      rp1 = arcpy.sa.ExtractValuesToPoints(rampPts, cd1, "rp1", "NONE", "VALUE_ONLY")
      rp1s = arcpy.MakeFeatureLayer_management(rp1, where_clause="RASTERVALU IS NOT NULL")

      if int(arcpy.GetCount_management(rp1s)[0]) == 0:
         # No ramps reached: just output local roads only service area
         if attFld is not None:
            if isinstance(attFld, str):
               areaval = unique_values(cdpts, attFld)[0]
               area = arcpy.sa.Con("cd1", areaval, "", "Value <= " + str(grpMaxCost))
               area.save(rastout)
            elif isinstance(attFld, int):
               area = arcpy.sa.Con("cd1", attFld, "", "Value <= " + str(grpMaxCost))
               area.save(rastout)
         else:
            cd1.save(rastout)
      else:
         # Some ramps reached: Run highways/local loop until there is no improvement in travel time.
         notin = [1]
         while len(notin) != 0:
            print('Limited-access cost distance run # ' + str(int((c+1)/2)) + '...')
            arcpy.CopyFeatures_management(rp1s, "rp1s")

            # highway CD
            cd2 = arcpy.sa.CostDistance("rp1s", costRastHwy, grpMaxCost, source_start_cost="RASTERVALU")
            c += 1
            nm = "cd" + str(c)
            cd2.save(nm)
            cds = cds + [nm]

            rp2 = arcpy.sa.ExtractValuesToPoints(rampPts, cd2, "rp2", "NONE", "VALUE_ONLY")
            # change name to avoid confusion with local ramp points
            arcpy.AlterField_management(rp2, "RASTERVALU", "costLAH", clear_field_alias=True)
            rp2s = arcpy.MakeFeatureLayer_management(rp2, where_clause="costLAH IS NOT NULL")

            # Check for new ramps or ramps reached at least one minute faster after latest run (LAH)
            notin = []
            lahr = {a[0]: a[1] for a in arcpy.da.SearchCursor(rp2s, [rampPtsID, 'costLAH'])}
            locr = {a[0]: a[1] for a in arcpy.da.SearchCursor('rp1s', [rampPtsID, 'RASTERVALU'])}
            for a in lahr:
               if a not in locr:
                  notin.append(a)
               else:
                  if lahr[a] - locr[a] < -1:
                     notin.append(a)
            if len(notin) == 0:
               print('No new ramps reached after LAH, moving on...')
               break

            # back to local
            arcpy.CopyFeatures_management(rp2s, "rp2s")
            cd3 = arcpy.sa.CostDistance("rp2s", costRastLoc, grpMaxCost, source_start_cost="costLAH")

            # write raster
            c += 1
            nm = "cd" + str(c)
            cd3.save(nm)
            cds = cds + [nm]

            rp1 = arcpy.sa.ExtractValuesToPoints(rampPts, cd3, "rp1", "NONE", "VALUE_ONLY")
            rp1s = arcpy.MakeFeatureLayer_management(rp1, where_clause="RASTERVALU IS NOT NULL")

            # Check for new ramps or ramps reached at least one minute faster after latest run (Local)
            # Similar to process earlier, but with names reversed
            notin = []
            locr = {a[0]: a[1] for a in arcpy.da.SearchCursor(rp1s, [rampPtsID, 'RASTERVALU'])}
            lahr = {a[0]: a[1] for a in arcpy.da.SearchCursor('rp2s', [rampPtsID, 'costLAH'])}
            for a in locr:
               if a not in lahr:
                  notin.append(a)
               else:
                  if locr[a] - lahr[a] < -1:
                     notin.append(a)
            # end while loop

         if attFld is not None:
            if isinstance(attFld, str):
               # cell statistics
               areaval = unique_values(cdpts, attFld)[0]
               area = arcpy.sa.Con(arcpy.sa.CellStatistics(cds, "MINIMUM", "DATA"), areaval, "", "Value <= " + str(grpMaxCost))
               area.save(rastout)
            elif isinstance(attFld, int):
               area = arcpy.sa.Con(arcpy.sa.CellStatistics(cds, "MINIMUM", "DATA"), attFld, "", "Value <= " + str(grpMaxCost))
               area.save(rastout)
         else:
            arcpy.sa.CellStatistics(cds, "MINIMUM", "DATA").save(rastout)

      print("Done with group: " + str(i))
      t1 = time.time()
      print('That took ' + str(int(t1 - t0)) + ' seconds.')

      # garbage pickup every 10 runs, last run
      if n == round(n, -1) or n == str(len(grps)):
         print("Deleting files...")
         r = arcpy.ListRasters("cd*")
         fc = arcpy.ListFeatureClasses("rp*")
         fc.append("buffpts")
         garbagePickup(r)
         garbagePickup(fc)

   # reset extent
   arcpy.env.extent = costRastLoc

   return

## end


def main():

   #################################
   arcpy.env.parallelProcessingFactor = "0"  # Adjust to some percent (e.g. 100%) for large extent analyses.
   arcpy.env.mask = r'L:\David\projects\RCL_processing\RCL_processing.gdb\VA_Buff50mi_wgs84'

   # Set up variables
   # Update 2020-10: Tiger 2019 data ready.
   costRastLoc = r'E:\RCL_cost_surfaces\Tiger_2019\cost_surfaces.gdb\costSurf_no_lah'
   costRastHwy = r'E:\RCL_cost_surfaces\Tiger_2019\cost_surfaces.gdb\costSurf_only_lah'
   rampPts = r'E:\RCL_cost_surfaces\Tiger_2019\cost_surfaces.gdb\rmpt_final'
   rampPtsID = 'UniqueID'  # unique ramp segment ID attribute field, since some ramps have multiple points

   # methods for individual service areas
   # facil_date = 't_ttrl_20190225' # suffix of filename
   # outGDB = r'E:\arcpro_wd\rec_model_temp\serviceAreas_modelupdate_Feb2019\access_' + facil_date + '.gdb'
   # accFeat = r'E:\arcpro_wd\rec_model_temp\access_pts.gdb\access_' + facil_date
   # grpFld = 'join_fid'  # [group_id for aquatic; join_fid for terrestrial]; name of attribute field of group for access points
   # maxCost = 60  # maximum cost distance in minutes; if attFld is set to a field name, variable costs will be calculated, but maxCost still applies
   # attFld = 'join_score'  # (optional) name of attribute field containing value to assign to raster for the group. or an integer value to apply
   # makeServiceAreas(outGDB, accFeat, costRastLoc, costRastHwy, rampPts, rampPtsID, grpFld, maxCost, attFld)

   # TESTING: methods for time to closest facility (all points considered at once). Returns actual cost distance in minutes.
   accFeat0 = r'E:\projects\rec_model\rec_model_processing\access_pts.gdb\access_t_tlnd_20190214'
   accFeat = accFeat0 + '_test_2018'
   arcpy.Select_analysis(accFeat0, accFeat, 'join_fid in (1230, 1410, 1585)')
   # accFeat = r'E:\projects\rec_model\rec_model.gdb\access_t_tlnd_20190214_100acres_PocSP_PowSP'
   outGDB = r'E:\projects\rec_model\rec_model_processing\serviceAreas_testing\servAreas_test_3sa.gdb'
   [a.name for a in arcpy.ListFields(accFeat)]
   arcpy.GetCount_management(accFeat)
   grpFld = 'join_fid'
   maxCost = 30  # in minutes
   attFld = None  # 'join_score'  # None will return actual cost distance
   makeServiceAreas(outGDB, accFeat, costRastLoc, costRastHwy, rampPts, rampPtsID, grpFld, maxCost, attFld)

   # Methods for time to closest facility (all points considered at once). Returns actual cost distance in minutes.
   # accPts = r'E:\arcpro_wd\rec_model_temp\access_pts.gdb\access_all_forregional'
   # outGDB = r'E:\arcpro_wd\rec_model_temp\serviceAreas_modelupdate_Feb2019\access_all_60min.gdb'
   # grpFld = 'facil_code'
   # maxCost = 60  # in minutes
   # attFld = None  # will return actual cost distance
   # makeServiceAreas(outGDB, accPts, costRastLoc, costRastHwy, rampPts, rampPtsID, grpFld, maxCost, attFld)


if __name__ == '__main__':
   main()
