# -*- coding: utf-8 -*-
"""
summRasts

Created: 2018-08
Last Updated: 2018-09-07
ArcGIS version: ArcGIS Pro
Python version: Python 3.5.3
Author: David Bucklin

Generic function to summarize large groups
of rasters(using cell statistics).
stored across (multiple) geodatabases in 'outFolder'.
Can specify optional patterns for geodatabase
name, and raster name within those geodatabases.

Rasters are processed by geodatabase, and then in
sub-groups within a geodatabase as specified by
'maxRasts'.  Because of this, this function
should not be used for certain statistics
where all rasters need to be considered together at once (e.g., MEAN, MEDIAN, etc).
Will work for SUM, MIN, MAX.

"""

import Helper
from Helper import *
from arcpy import env

def summRasts(outFolder, outRast, rastExt, wdPattern="*", rastPattern="*", stat="SUM", maxRasts=100):
   arcpy.env.snapRaster = rastExt
   arcpy.env.cellSize = rastExt
   arcpy.env.extent = rastExt
   arcpy.env.overwriteOutput = True
   arcpy.env.outputCoordinateSystem = rastExt
   arcpy.CheckOutExtension("Spatial")

   # set up wildcards
   base = wdPattern
   rp = rastPattern

   # list workspaces
   dir = outFolder
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
         n = [0, maxRasts]
         while n[0] < len(rls1):
            rls = rls1[n[0]:n[1]]
            print("Summing " + str(len(rls)) + " sub-group rasters in workspace " + g + "...")
            area = Float(CellStatistics(rls, stat, "DATA"))
            subnm = "sub_sum" + str(int(n[0]))
            area.save(subnm)
            sumlist.append(g + os.sep + subnm)
            n = [x + maxRasts for x in n]
      else:
         rls = rls1
         print("Summing " + str(len(rls)) + " sub-group rasters in workspace " + g + "...")
         area = Float(CellStatistics(rls, stat, "DATA"))
         area.save("sub_sum0")
         sumlist.append(g + os.sep + "sub_sum0")

      print('Done with ' + g + '.')
      t1 = time.time()
      print('That took ' + str(int((t1 - t0) / 60)) + ' minutes.')

   print('Summing ' + str(len(sumlist)) + ' sub-group rasters...')
   arcpy.env.workspace = dir
   areafinal = Float(CellStatistics(sumlist, stat, "DATA"))
   areafinal.save(outRast)
   print('Done.')
   return

def main():
   # following creation of service areas in loopSAs, sum all the SA (service area) rasters
   # these can be in multiple gdbs, use wdPattern to select them
   typs = ['t_ttrl','t_tlnd','a_agen','a_awct','a_aswm']
   for typ in typs:
      outFolder = r'E:\arcpro_wd'
      outRast = r'sum_access_' + typ + '_serviceAreas.tif'
      # full raster extent
      rastExt = r'E:\arcpro_wd\rec_model_temp\costSurf_no_lah.tif'
      wdPattern = '*access_' + typ + '_serviceAreas*'
      rastPattern = '*_servArea*'
      summRasts(outFolder, outRast, rastExt, wdPattern, rastPattern, stat="SUM", maxRasts = 200)

if __name__ == '__main__':
   main()