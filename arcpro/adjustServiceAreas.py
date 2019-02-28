"""
adjustServiceAreas
Created: 2018-09
Last Updated: 2019-02-19
ArcGIS version: ArcGIS Pro
Python version: Python 3.5.3
Author: David Bucklin

Adjust service area values by another raster.

Creates a new raster for each service area raster (created using makeServiceAreas.py)
with its original score divided by total population within the service area.

It outputs a new service area raster for each original (with a 'popAdj_' prefix),
and a feature class will all vectorized service areas and the attributes:
   sa_id: original group ID number
   sa_score: service area original score
   sa_sumpop: sum of population within service area
   sa_scoreperpop: [sa_score / sa_sumpop]
   sa_minutes: minutes used in service area creation

Argument definitions:
   inGDB: Name of input GDB storing service area rasters
   popRast: The population raster
   rastPattern: character string defining a subset of service area rasters
      to process from `inGDB` (default  = '*servArea')
"""

import arcpro.Helper
from arcpro.Helper import *
from arcpy import env
import numpy

def adjustServiceAreas(inGDB, popRast, rastPattern = '*_servArea'):
   import arcpy
   arcpy.env.workspace = inGDB
   arcpy.env.overwriteOutput = True
   from arcpy import sa
   ls = arcpy.ListRasters(rastPattern)

   print('There are ' + str(len(ls)) + ' rasters in GDB to process.')

   file = "popSum.txt"
   if os._exists(file):
      os.remove(file)
   f = open(file, 'w')
   f.write('fileName' + '\t' + 'score' + '\t' + 'pop_total' + '\t' + 'score_pop' + '\t' + 'score_per10k' + '\t' + 'minutes_SA' + '\n')

   for i in ls:
      print(i)
      t0 = time.time()
      i_nm = i.split('_')[0]
      finalrast = inGDB + os.sep + 'popAdj_' + str(i_nm)
      if arcpy.Exists(finalrast):
         print('File exists, skipping...')
         continue

      # set extent to input raster
      arcpy.env.extent = i

      # make masked population raster
      msk = arcpy.sa.ExtractByMask(popRast, i)

      arr = arcpy.RasterToNumPyArray(msk, nodata_to_value=0)
      sumPop = arr.sum()

      # set sum of population to 1 if less than 1 to avoid dividing by 0
      if sumPop < 1:
         sumPop = 1
      else:
         sumPop = int(round(sumPop))

      # get minutes used for SA
      sapt = i_nm + '_inputPts'
      minutes_sa = unique_values(sapt, 'minutes_SA')[0]
      if minutes_sa > 60:
         minutes_sa = 60

      # get area from service area raster
      score = float(arcpy.GetRasterProperties_management(i, "MAXIMUM").getOutput(0))
      score_pop = score/sumPop
      score_per_10k = score / (sumPop/10000)
      f.write(i + '\t' + str(score) + '\t' + str(sumPop) + '\t' + str(score_pop) + '\t' + str(score_per_10k) + '\t' + str(minutes_sa) + '\n')

      arcpy.env.snapRaster = i
      arcpy.env.cellSize = i
      arcpy.env.outputCoordinateSystem = i

      arcpy.sa.Con(i, score_pop, i, "Value > 0").save(finalrast)

      # convert to polygon, with attributes (not doing for now; too slow)
      # arcpy.sa.Int(finalrast).save('SAint')
      # sapoly = arcpy.RasterToPolygon_conversion('SAint', 'SApoly', "NO_SIMPLIFY", "VALUE") #, create_multipart_features="MULTIPLE_OUTER_PART") # doesn't work...
      # ct = 0
      # while int(arcpy.GetCount_management(sapoly).getOutput(0)) > 1:
      #    ct = ct+1
      #    print(ct)
      #    sapoly = arcpy.Dissolve_management(sapoly, 'SAPoly' + str(ct), ["GRIDCODE"], multi_part="MULTI_PART")
      # flds = ['sa_id','sa_score','sa_sumpop','sa_scoreperpop','sa_minutes']
      # typ = ['SHORT','FLOAT','FLOAT','FLOAT','FLOAT']
      # vals = [int(''.join(filter(str.isdigit, i))), score, sumPop, score_pop, minutes_sa]
      # for fld in [0,1,2,3,4]:
      #    arcpy.AddField_management(sapoly, flds[fld], typ[fld])
      #    arcpy.CalculateField_management(sapoly, flds[fld], vals[fld])
      # # append to feature class
      # arcpy.Append_management(sapoly, "all_SA_polys", "NO_TEST")

      t1 = time.time()
      print('that took ' + str(t1 - t0) + ' seconds.')

   print('Done, writing table...')
   f.close()
   arcpy.TableToTable_conversion(file, inGDB, "popAdj_table")
   os.remove(file)
   garbagePickup([msk])
   return

def main():
   # population adjustment rasters (e.g. area / population)
   arcpy.env.overwriteOutput = True
   popRast = r'E:\arcpro_wd\rec_model_temp\input_recmodel.gdb\distribPop_kdens'
   arcpy.env.workspace = r'E:\arcpro_wd\rec_model_temp\serviceAreas_modelupdate_Feb2019'
   # loop over GDBs. Put all results in same GDB
   gdbl = arcpy.ListWorkspaces("access_t_ttrl*", "FileGDB")

   m = gdbl[0]
   print(m)
   inGDB = m
   # copy template polys to gdb (not using this currently)
   # arcpy.CopyFeatures_management(r'E:\arcpro_wd\rec_model_temp\input_recmodel.gdb\template_SApolys', inGDB + os.sep + 'all_SA_polys')
   adjustServiceAreas(inGDB, popRast)


if __name__ == '__main__':
   main()