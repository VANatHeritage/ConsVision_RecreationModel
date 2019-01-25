# -*- coding: utf-8 -*-
"""
scoreRastLog

Created: 2018-08
Last Updated: 2018-09-12
ArcGIS version: ArcGIS Pro
Python version: Python 3.5.3
Author: David Bucklin

Produce a score raster (integer from 1-100) using
log10 adjustment from a continuous values raster,
given an optional maximum value ('maxVal'), which
is used as the baseline for scoring. Values at above
maxVal are given a score of 100.

Allows burn-in features, given a value specified in burnField, in two ways:
burnSimple = True : features are burned in only, with values from 'burnField'.
burnSimple = False : features are burned in with a distance decay buffer
   around the features, with a base value as specified in burnField.
   Features themselves are always applied a value of 101 using this method.

"""

import Helper
from Helper import *
from arcpy import env

def scoreRastLog(inRast, outRast, mask, maxVal = None, burnFeatures = None, burnField = None, burnSimple = True):

   import numpy
   import arcpy
   arcpy.env.snapRaster = inRast
   arcpy.env.cellSize = inRast
   arcpy.env.extent = inRast
   arcpy.env.mask = mask
   arcpy.env.overwriteOutput = True
   arcpy.env.outputCoordinateSystem = inRast
   arcpy.CheckOutExtension("Spatial")

   if maxVal is None:
      maxVal = float(arcpy.GetRasterProperties_management(inRast, "MAXIMUM").getOutput(0))

   # calculate log of maximum value
   mx = numpy.log10(maxVal)

   if burnFeatures is not None:
      print('Rasterizing features...')
      arcpy.FeatureToRaster_conversion(burnFeatures, burnField, 'bpoly1')
      if not burnSimple:
         print('Combining burn scores and model scores...')
         arcpy.sa.CellStatistics(["bpoly1", inRast], "MAXIMUM", "DATA").save('inRast')
         inRast = Raster('inRast')
         # make a constant '101' raster for burn in areas
         modelBurn = Reclassify('bpoly1', "Value", RemapRange([[0, 10000000, 101]]))
         modelBurn.save('modelBurn')

   # score model
   print('Scoring model...')
   arcpy.sa.Log10(inRast).save("log1")
   log1 = Raster("log1")
   arcpy.sa.Con(log1, 100, arcpy.sa.Con(log1, 1, (log1/mx)*100, "Value <= " + str(mx/100)), "Value >= " + str(mx)).save("log2")
      # set values >= max to 100, values <= max/100 to 1, others to score
   log2 = Raster("log2")
   arcpy.sa.Con(arcpy.sa.IsNull(log2), 0, arcpy.sa.Int(log2 + 0.5)).save("log3")
      # set NULL to 0, less than 1 to 1, and all other values 0-100 integer
   modResc = Raster("log3")

   # burn features
   if burnFeatures is not None:
      print('Combining burn features and model scores...')
      if burnSimple:
         # just burn value into final output
         arcpy.sa.CellStatistics(["bpoly1",modResc],"MAXIMUM","DATA").save(outRast)
      else:
         # get model values for burn areas
         arcpy.sa.ExtractByMask(modResc, modelBurn).save('bpoly2')

         # Euclidean allocation/distance
         modelEucAllo = EucAllocation('bpoly2', 2414, 'bpoly2', out_distance_raster='modelEucDist')
         modelEucAllo.save('modelEucAllo')
         modelEucDist = Raster('modelEucDist')

         # valToScoreNeg from Helper.py (distance decay multiple value)
         modelDistScore = valToScoreNeg(modelEucDist, 45, 2414)
         modelDistScore.save('modelDistScore')

         # calculate scores in Buffer zones, convert to integer
         Int((modelEucAllo * (modelDistScore / 100)) + 0.5).save('modelBuffScore')
         modelBuffScore = Raster('modelBuffScore')

         # take maximum of buffer scores, burn in scores, and original model scores
         modelFinal = CellStatistics([modelBuffScore, modelBurn, modResc], "MAXIMUM")
         modelFinal.save(outRast)
   else:
      modResc.save(outRast)

   print('Done.')
   return outRast


def main():

   # sub-components
   for comp in ['a_aswm','a_afsh']:
      maxVal = 100000  # maximum value (to =100 in final scoring) from values from inRast
      # optional
      burnFeatures = r'E:\arcpro_wd\rec_model_temp\input_recmodel.gdb\burn_waterareas'
      burnField = 'rast'
      burnFeatures = r'E:\arcpro_wd\rec_model_temp\pub_lands_terr_open.shp' # vatrails_cluster
      burnField = 'area_ha' # length_km
      burnSimple = False  # True for aquatic burn in, just apply 101 value.
      # False for applying distance-decay scored burn around features (terrestrial only)

      # shouldn't change
      inRast = r'E:\arcpro_wd\score_rasts\raw_scores.gdb\sum_access_' + comp + '_serviceAreas'
      outRast = r'E:\arcpro_wd\score_rasts\rec_model_scores.gdb\score_' + comp + '_' + str(maxVal) + 'max'
      mask = r'E:\arcpro_wd\rec_model_temp\jurisbnd_lam.shp'
      gdb = r"E:\arcpro_wd\temp_gdb.gdb"
      arcpy.env.workspace = gdb

      # run fn
      scoreRastLog(inRast, outRast, mask, maxVal, burnFeatures, burnField, burnSimple)

   ####

   # component final score rasters
   arcpy.env.workspace = r'E:\arcpro_wd\score_rasts\rec_model_scores.gdb'

   # terrestrial
   # take mean of two subs, but carry over 101 value from both subs
   ls = ['score_t_ttrl_1000max', 'score_t_tlnd_100000max']
   CellStatistics(ls, "MAXIMUM").save("tmax")
   Int(Con("tmax", 101, CellStatistics(ls, "MEAN"), "Value = 101") + 0.5).save("score_terrestrial_mean_1")
   garbagePickup(["tmax"])

   # aquatic
   # take the mean of 3 subs with known access type (awct, afsh, aswm), and then mwax of result and (agen) score
   ls = ['score_a_awct_10000max', 'score_a_afsh_1000max', 'score_a_aswm_1000max']
   Int(CellStatistics([CellStatistics(ls, "MEAN"), 'score_a_agen_10000max'], "MAXIMUM") + 0.5).save("score_aquatic_mean")

if __name__ == '__main__':
   main()