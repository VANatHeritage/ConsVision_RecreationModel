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
   f.write('fileName' + '\t' + 'area_ha' + '\t' + 'pop_total' + '\t' + 'area_pop' + '\n')

   for i in ls:
      print(i)
      t0 = time.time()
      arcpy.env.extent = i
      #arcpy.env.snapRaster = popRast
      #arcpy.env.cellSize = popRast
      #arcpy.env.outputCoordinateSystem = popRast

      # make mask for zonal statistics (value = 1)
      msk = arcpy.sa.ExtractByMask(popRast, i)
      mx = round(float(arcpy.GetRasterProperties_management(msk, "MAXIMUM").getOutput(0))) + 1
      zone = Reclassify(msk, "Value", RemapRange([[0, mx, 1]])) #slow

      # sum population in masked area
      sum = arcpy.sa.ZonalStatistics(zone, "Value", msk, "SUM")
      sumPop = int(float(arcpy.GetRasterProperties_management(sum, "MAXIMUM").getOutput(0)))
      # set sum of population to 1 if less than 1 to avoid dividing by 0
      if sumPop < 1:
         sumPop = 1

      # get area from service area raster
      area_ha = float(arcpy.GetRasterProperties_management(i, "MAXIMUM").getOutput(0))
      area_pop = area_ha/sumPop
      f.write(i + '\t' + str(area_ha) + '\t' + str(sumPop) + '\t' + str(area_pop) + '\n')

      arcpy.env.snapRaster = i
      arcpy.env.cellSize = i
      arcpy.env.outputCoordinateSystem = i

      arcpy.sa.Divide(i, sumPop).save(inGDB + os.sep + 'popadj_' + str(i))

      t1 = time.time()
      print('that took ' + str(t1 - t0) + ' seconds.')

   print('Done, writing table...')
   f.close()   
   arcpy.TableToTable_conversion(file, inGDB, "popAdj_table")
   os.remove(file)
   garbagePickup([msk, zone, sum])
   return

def main():
   # population adjustment rasters (area / population)
   popRast = r'E:\arcpro_wd\pop_data\Population_census\distribPop.tif'
   rastPattern = "*_servArea"
   arcpy.env.workspace = r"E:\arcpro_wd"
   # loop over GDBs. Put all results in one GDB
   gdbl = arcpy.ListWorkspaces("*access_a_aswm*", "FileGDB")

   # loop over gdbs
   for m in gdbl:
      print(m)
      inGDB = m
      adjustServiceAreas(inGDB, popRast, rastPattern)

if __name__ == '__main__':
   main()