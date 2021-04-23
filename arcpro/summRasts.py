# -*- coding: utf-8 -*-
"""
summRasts

Created: 2018-08
Last Updated: 2018-09-07
ArcGIS version: ArcGIS Pro
Python version: Python 3.5.3
Author: David Bucklin

Generic function to summarize large groups (i.e. 100s) of rasters (using cell statistics), potentially stored across
(one or multiple) geodatabases in 'inFolder'. Can specify optional patterns for geodatabase name, and raster name
within those geodatabases.

Rasters are processed by-geodatabase, and then in sub-groups within a geodatabase as specified by 'maxRasts'. Because
of this, this function should not be used for certain statistics where all rasters need to be considered together at
once (e.g. MEAN, VARIETY).

Argument definitions:
   inFolder: The folder containing the geodatabase(s)
   outRast: The output summary raster
   rastExt: Template raster with the extent for the final summary raster
   wdPattern: Character string defining a subset of geodatabases in
      inFolder to process
   rastPatter: Character string defining a subset of rasters in the
      geodatabases to process
   stat: summary statistic, one of ["SUM"|"MINIMUM"|"MAXIMUM"]
   maxRasts: number of rasters in sub-groups, processing limit.
"""

from arcpro.Helper import *


def summRasts(inFolder, outRast, rastExt, wdPattern="*", rastPattern="*", stat="SUM", maxRasts=200):

   arcpy.env.snapRaster = rastExt
   arcpy.env.cellSize = rastExt
   arcpy.env.extent = rastExt
   arcpy.env.overwriteOutput = True
   arcpy.env.outputCoordinateSystem = rastExt

   # set up wildcards
   base = wdPattern
   rp = rastPattern

   # list workspaces
   dir = inFolder
   arcpy.env.workspace = dir
   gdbs = arcpy.ListWorkspaces(base)

   sumlist = []

   for g in gdbs:
      t0 = time.time()
      arcpy.env.workspace = g
      # list all SA rasters
      rls1 = arcpy.ListRasters(rp)

      # raw sum - areas
      print("There are " + str(len(rls1)) + " rasters in workspace.")
      if len(rls1) > maxRasts:
         # make original index
         n = [0, maxRasts]
         while n[0] < len(rls1):
            rls = rls1[n[0]:n[1]]
            print(rls)
            print("Summarizing " + str(len(rls)) + " sub-group rasters in workspace " + g + "...")
            area = Float(CellStatistics(rls, stat, "DATA"))
            subnm = "sub_sum" + str(int(n[0]))
            area.save(subnm)
            sumlist.append(g + os.sep + subnm)
            # make next index
            n = [x + maxRasts for x in n]
      else:
         rls = rls1
         print("Summarizing " + str(len(rls)) + " sub-group rasters in workspace " + g + "...")
         area = Float(CellStatistics(rls, stat, "DATA"))
         area.save("sub_sum0")
         sumlist.append(g + os.sep + "sub_sum0")

      print('Done with ' + g + '.')
      t1 = time.time()
      print('That took ' + str(int((t1 - t0) / 60)) + ' minutes.')

   if len(sumlist) > 1:
      print('Summarizing ' + str(len(sumlist)) + ' sub-group rasters...')
      arcpy.env.workspace = dir
      areafinal = Float(CellStatistics(sumlist, stat, "DATA"))
   else:
      areafinal = Raster(sumlist[0])

   areafinal.save(outRast)
   print('Done.')
   return outRast


def main():
   ## following creation of service areas in loopSAs, sum all the SA (service area) rasters
   ## these can be in multiple gdbs, use wdPattern to select them

   inGDB = 'servArea_100ac_30min_public_lands_final_accessAreas.gdb'
   stat = "SUM"
   inFolder = r'E:\projects\rec_model\rec_model_processing\serviceAreas'
   outGDB = 'serviceArea_summary.gdb'
   arcpy.CreateFileGDB_management(inFolder, outGDB)
   rtype = 'servArea'  # 'popAdj'   # pattern for rasters to summarize

   rastPattern = '*' + rtype + '*'
   outRast = os.path.join(inFolder, outGDB, stat.lower() + '_' + inGDB.replace('.gdb', ''))
   # full raster extent
   rastExt = r'E:\RCL_cost_surfaces\Tiger_2020\cost_surfaces.gdb\costSurf_no_lah'
   wdPattern = inGDB
   summRasts(inFolder, outRast, rastExt, wdPattern, rastPattern, stat=stat, maxRasts=100)
   # arcpy.sa.Int(outRast).save(outRast + '_int')
   # arcpy.BuildPyramidsandStatistics_management(inFolder + os.sep + outGDB)

if __name__ == '__main__':
   main()