# -*- coding: utf-8 -*-
"""
makeServiceAreas

Created: 2018-07
Last Updated: 2018-09-07
ArcGIS version: ArcGIS Pro
Python version: Python 3.5.3
Author: David Bucklin

Raster-based approach for building service areas,
using a two raster cost-surface +
connection points approach.

Local roads (non-limited access highways)
and limited access highways. Cost distance
is run iteratively on (1) local and (2) limited access
roads until the maximum cost is reached, with connection
points defining where local roads and limited
access roads meet.

Argument definitions:
outGDB: Name of output geodatabase, is created during the process.
   Note that once 500 groups are processed, a new geodatabase with the
   same name plus a sequential number is created.
accPts: Access features to run cost distance process on
costRastLoc: A cost surface for all local (non-limited access) roads
costRastHwy: A cost surface for all limited access roads
rampPts: A point feature class defining connection points between
   local and limited access roads.
rampPtsID: a unique id corresponding to a given ramp/connection
maxCost: the maximum cost distance allowed
grpFld: The grouping attribute field name for accPts, where one cost distance is
   run for each group
attFld: Optional. The attribute field name in accPts. The value in this
   column is given to the output raster for the group. Otherwise,
   the cost distance is returned.

"""

import Helper
from Helper import *
from arcpy import env

def makeServiceAreas(outGDB, accPts, costRastLoc, costRastHwy, rampPts, rampPtsID, maxCost, grpFld, attFld = None):

   import arcpy
   arcpy.env.snapRaster = costRastLoc
   arcpy.env.cellSize = costRastLoc
   arcpy.env.extent = costRastLoc
   arcpy.env.overwriteOutput = True
   arcpy.env.outputCoordinateSystem = costRastLoc

   make_gdb(outGDB)
   arcpy.env.workspace = outGDB
   arcpy.SetLogHistory(False)

   grps = unique_values(accPts, grpFld)
   buffd = str(int(maxCost * 1900)) + ' METERS'
   # buffer for extent-assumes metered projection and straight-line max distance at 70 mph (~35 miles at 30 minutes)
   gdbct = 1

   for i in grps:
      n = grps.index(i) + 1
      if n / 500 > gdbct:
         newGDB = re.sub('[0-9]*.gdb$', '', outGDB) + str(int(gdbct)) + ".gdb"
         make_gdb(newGDB)
         arcpy.env.workspace = newGDB
         gdbct = gdbct + 1

      print("working on group " + str(i) + "...")
      arcpy.env.extent = costRastLoc  # so points don't get excluded due to previous extent setting
      t0 = time.time()
      c = 1  # counter

      cdpts = "grp" + str(int(i)) + "_inputPts"
      tmpGrp = arcpy.MakeFeatureLayer_management(accPts, cdpts, grpFld + " = " + str(i))
      arcpy.CopyFeatures_management(tmpGrp, cdpts)

      arcpy.Buffer_analysis(cdpts, "buffpts", buffd)
      arcpy.env.extent = "buffpts"

      # local CD
      cd1 = arcpy.sa.CostDistance(cdpts, costRastLoc, maxCost, None, None, None, None, None, None)
      nm = "cd" + str(c)
      cd1.save(nm)
      # values to ramps
      rp1 = arcpy.sa.ExtractValuesToPoints(rampPts, cd1, "rp1", "NONE", "VALUE_ONLY")
      rp1s = arcpy.MakeFeatureLayer_management(rp1, where_clause="RASTERVALU IS NOT NULL")

      print("# of access pts: " + arcpy.GetCount_management(cdpts)[0])

      if int(arcpy.GetCount_management(rp1s)[0]) == 0:
         if attFld:
            areaval = unique_values(cdpts, attFld)[0]
            area = arcpy.sa.Con("cd1", areaval, "", "Value <= " + str(maxCost))
            area.save("grp" + str(int(i)) + "_servArea")
         else:
            cd1.save("grp" + str(int(i)) + "_servArea")
      else:
         # run highways CD if cd1 reaches any ramps
         notin = [1]
         allr = []
         while len(notin) != 0:
            print('Limited-access cost distance run # ' + str(int((c+1)/2)) + '...')
            arcpy.CopyFeatures_management(rp1s, "rp1s")
            # highway CD
            cd2 = arcpy.sa.CostDistance("rp1s", costRastHwy, maxCost, None, None, "RASTERVALU", None, None, None)

            c = c + 1
            nm = "cd" + str(c)
            cd2.save(nm)

            rp2 = arcpy.sa.ExtractValuesToPoints(rampPts, cd2, "rp2", "NONE", "VALUE_ONLY")
            rp2s = arcpy.MakeFeatureLayer_management(rp2, where_clause="RASTERVALU IS NOT NULL")

            # back to local
            if int(arcpy.GetCount_management(rp2s)[0]) != 0:
               used_ramps2 = unique_values(rp2s, rampPtsID)
               arcpy.CopyFeatures_management(rp2s, "rp2s")
               cd3 = arcpy.sa.CostDistance("rp2s", costRastLoc, maxCost, None, None, "RASTERVALU", None, None, None)
            else:
               cd3 = cd2

            # write raster
            c = c + 1
            nm = "cd" + str(c)
            cd3.save(nm)

            allr = list(set(allr + used_ramps2))

            rp1 = arcpy.sa.ExtractValuesToPoints(rampPts, cd3, "rp1", "NONE", "VALUE_ONLY")
            rp1s = arcpy.MakeFeatureLayer_management(rp1, where_clause="RASTERVALU IS NOT NULL")
            allr2 = unique_values(rp1s, rampPtsID)

            notin = []
            for r in allr2:
               if r not in allr:
                  notin.append(r)

         # list of cd rasters
         cds = list(range(1, c + 1))
         newls = ["cd" + str(s) for s in cds]
         newls = ';'.join(newls)

         if attFld:
            # cell statistics
            areaval = unique_values(cdpts, attFld)[0]
            area = arcpy.sa.Con(arcpy.sa.CellStatistics(newls, "MINIMUM", "DATA"), areaval, "", "Value <= " + str(maxCost))
            area.save("grp" + str(int(i)) + "_servArea")
         else:
            arcpy.sa.CellStatistics(newls, "MINIMUM", "DATA").save("grp" + str(int(i)) + "_servArea")

      print("Done with group: " + str(i))
      t1 = time.time()
      print('That took ' + str(int(t1 - t0)) + ' seconds.')

      # garbage pickup every 10 runs
      if n == round(n, -1):
         print("Deleting files...")
         del ([rp1, rp1s, rp2, rp2s, cd1, cd2, cd3])
         r = arcpy.ListRasters("cd*")
         fc = arcpy.ListFeatureClasses("rp*")
         fc.append("buffpts")
         garbagePickup(r)
         garbagePickup(fc)
   return

## end

def main():
   # Set up variables
   outGDB = r'E:\arcpro_wd\access_a_afsh_serviceAreas.gdb'
   accPts = r'E:\arcpro_wd\rec_model_temp\access_a_wAreas1km_afsh_2018_08_21.shp'
   costRastLoc = r'E:\arcpro_wd\rec_model_temp\costSurf_no_lah.tif'
   costRastHwy = r'E:\arcpro_wd\rec_model_temp\costSurf_only_lah.tif'
   rampPts = r'E:\arcpro_wd\rec_model_temp\rmpt3.shp'
   maxCost = 30   # in minutes
   grpFld = 'gridcode' # group for access points (e.g., all points are related to one feature)
   attFld = 'area_ha'
   rampPtsID = 'UniqueID'  # unique ramp segment ID, since some ramps have multiple points
   makeServiceAreas(outGDB, accPts, costRastLoc, costRastHwy, rampPts, rampPtsID, maxCost, grpFld, attFld)

if __name__ == '__main__':
   main()
