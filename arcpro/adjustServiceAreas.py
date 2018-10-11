"""
adjustServiceAreas
Created: 2018-09
Last Updated: 2018-10-04
ArcGIS version: ArcGIS Pro
Python version: Python 3.5.3
Author: David Bucklin

# Adjust service area values by another raster.
# This was created to adjust service area scores
# (created using makeServiceAreas.py)
# by population. It sums total value of popRast
# within the area of an input raster, and then
# divides: [input raster / total population]. It outputs
# a new service area raster with the adjusted value and a
# table in inGDB with three columns:
# (inputGDB, rastername, adjusted score).
"""

import Helper
from Helper import *
from arcpy import env
import numpy

def adjustServiceAreas(inGDB, popRast, rastPattern):
   import arcpy
   arcpy.env.workspace = inGDB
   arcpy.env.overwriteOutput = True
   from arcpy import sa
   ls = arcpy.ListRasters(rastPattern)

   file = "popSum.txt"
   if os._exists(file):
      os.remove(file)
   f = open(file, 'w')
   f.write('fileName' + '\t' + 'score' + '\t' + 'pop_total' + '\t' + 'score_pop' + '\t' + 'acres_per10k' + '\n')

   for i in ls:
      print(i)
      t0 = time.time()
      arcpy.env.extent = i
      #arcpy.env.snapRaster = popRast
      #arcpy.env.cellSize = popRast
      #arcpy.env.outputCoordinateSystem = popRast

      # make masked population raster
      msk = arcpy.sa.ExtractByMask(popRast, i)

      arr = arcpy.RasterToNumPyArray(msk, nodata_to_value=0)
      sumPop = arr.sum()

      # set sum of population to 1 if less than 1 to avoid dividing by 0
      if sumPop < 1:
         sumPop = 1
      else:
         sumPop = int(round(sumPop))

      # get area from service area raster
      area_ha = float(arcpy.GetRasterProperties_management(i, "MAXIMUM").getOutput(0))
      area_pop = area_ha/sumPop
      acres_per_10k = (area_ha * 2.47105) / (sumPop/10000)
      f.write(i + '\t' + str(area_ha) + '\t' + str(sumPop) + '\t' + str(area_pop) + '\t' + str(acres_per_10k) + '\n')

      arcpy.env.snapRaster = i
      arcpy.env.cellSize = i
      arcpy.env.outputCoordinateSystem = i

      arcpy.sa.Con(i, acres_per_10k, i, "Value > 0").save(inGDB + os.sep + 'acresPer10k_' + str(i))
      arcpy.sa.Con(i, area_pop, i, "Value > 0").save(inGDB + os.sep + 'popAdj_' + str(i))

      t1 = time.time()
      print('that took ' + str(t1 - t0) + ' seconds.')

   print('Done, writing table...')
   f.close()   
   arcpy.TableToTable_conversion(file, inGDB, "popAdj_table")
   os.remove(file)
   garbagePickup([msk])
   return

def main():
   # population adjustment rasters (area / population)
   popRast = r'E:\arcpro_wd\pop_data\Population_census\distribPop_noZeros.tif'
   rastPattern = "*_servArea"
   arcpy.env.workspace = r"E:\arcpro_wd"
   # loop over GDBs. Put all results in same GDB
   gdbl = arcpy.ListWorkspaces("access_t_tlnd_stateparks_uniq.gdb", "FileGDB")

   # loop over gdbs
   for m in gdbl:
      print(m)
      inGDB = m
      adjustServiceAreas(inGDB, popRast, rastPattern)


if __name__ == '__main__':
   main()