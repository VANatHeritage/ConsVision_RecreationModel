# -*- coding: utf-8 -*-
"""
# RecModFinalize.py
# Version:  ArcGIS 10.3.1 / Python 2.7.8
# Creation Date: 2017-11-21
# Last Edit: 2017-11-21
# Creator:  David Bucklin
#
# Summary:
# Finalizes recreation model raster with burn-in values for recrational features.
# A distance decay function applies scores to cells within a distance of features,
# if greater than the original model value.
#
# Usage:
# Create input polygon and/or line recreational feature shapefiles, with an area field
"""

import Helper
from Helper import *
from arcpy import env

def RecModFinalize(wd, scratch, inMod, inPoly, inLine, mask, inPolyAreaFld, inLineAreaFld, modMaxRescale, eucMin, eucMax):
   
   # create new scratch GDB, set as workspace
   arcpy.CreateFileGDB_management(wd, scratch + str(".gdb"))
   arcpy.env.workspace = wd + str(os.sep) + scratch + str(".gdb")
   
   arcpy.env.mask = inMod
   arcpy.env.extent = inMod
   arcpy.env.snapRaster = inMod
   arcpy.env.cellSize = inMod
   arcpy.env.outputCoordinateSystem = inMod
   arcpy.env.overwriteOutput = True
   
   inMod = Raster(inMod)
   # rescale model
   modResc = Con(inMod>modMaxRescale, 100, 100*(inMod/modMaxRescale))
   modResc.save('modResc')
   
   # convert line features to raster
   lRas = []
   
   if inLine:
       bline = arcpy.PolylineToRaster_conversion(inLine, inLineAreaFld, 'bline')
       lRas.append(bline)
   
   # create rasters for each NHD and lake polygon features
   inpoly1 = arcpy.Select_analysis(inPoly, 'nhd', where_clause = 'table <> \'pub_lands_aqua_union\'')
   bpoly1 = arcpy.PolygonToRaster_conversion(inpoly1, inPolyAreaFld, 'bpoly1')
   inpoly2 = arcpy.Select_analysis(inPoly, 'lake', where_clause = 'table = \'pub_lands_aqua_union\'')
   bpoly2 = arcpy.PolygonToRaster_conversion(inpoly2, inPolyAreaFld, 'bpoly2')
   lRas.append(bpoly1)
   lRas.append(bpoly2)
   
   # combine rasters and take square root, converting to integer
   modelSrc = CellStatistics(lRas, "MAXIMUM")
   modelSrc = SquareRoot(modelSrc)
   modelSrc = Con(modelSrc, 100, modelSrc, 'VALUE > 100')
   modelSrc = Int(modelSrc + 0.5)
   
   modelSrc.save('modelSrc')
   
   # create modelBurn with constant 101 value
   modelBurn = Reclassify(modelSrc, "Value", RemapRange([[0,1000000,101]]))
   modelBurn.save('modelBurn')
   
   # Euclidean allocation/distance
   modelEucAllo = EucAllocation(modelSrc, eucMax, modelSrc, out_distance_raster = 'modelEucDist')
   modelEucAllo.save('modelEucAllo')
   modelEucDist = Raster('modelEucDist')
   
   # valToScoreNeg from Helper.py (distance decay multiple value)   
   modelDistScore = valToScoreNeg(modelEucDist, eucMin, eucMax)
   modelDistScore.save('modelDistScore')
   
   # calculate scores in Buffer zones
   modelBuffScore = modelEucAllo * (modelDistScore/100)
   modelBuffScore.save('modelBuffScore')
   
   # set processing extent for final output using mask
   arcpy.env.mask = mask
   arcpy.env.extent = mask
   
   # take maximum of buffer scores, burn in scores, and original model scores
   modelFinal = CellStatistics([modelBuffScore, modelBurn, modResc], "MAXIMUM")
   modelFinal.save('modelFinal')


def main():
   # Set up variables
   wd = r'D:\David\arcmap_wd\finalize'      # directory to output final raster
   scratch = "scratch_fn"                   # new scractch GDB in 'wd'
   inMod = r'D:\David\arcmap_wd\finalize\final_aqua_sumraster.tif'
   inPoly = r'D:\David\arcmap_wd\finalize\aqua_poly_out.shp'
   inLine = r'D:\David\arcmap_wd\finalize\aqua_line_out.shp'
   mask = r'I:\DNHGIS\ConservationVision\Recreation_2017\ProductionMaps\ConsVisionRefLayers.gdb\jurisbnd'
   inPolyAreaFld = "aq_area"
   inLineAreaFld = "aq_area"
   modMaxRescale = 100 
   eucMin = 45
   eucMax = 2414

   # Specify function to run
   RecModFinalize(wd, scratch, inMod, inPoly, inLine, mask, inPolyAreaFld, inLineAreaFld, modMaxRescale, eucMin, eucMax)

if __name__ == '__main__':
   main()