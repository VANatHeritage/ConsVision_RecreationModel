# -*- coding: utf-8 -*-
"""
CreateAquaAccessPolys

Created on Wed Jun 20 13:54:43 2018

@author: David Bucklin

This script takes water access points, and one-many feature layers representing aqautic areas, and rasterizes them into one layer.

Access areas across this aquatic raster layer can then be derived from the access points, using a given travel distance from the points.
"""

import Helper
from Helper import *
from arcpy import env

def RasterizeAll(listFeat = [], accessPts = '', out = '', template = '', value = 1, erase = "#"):
   '''Rasterizes all feature classes in list into one raster layer,
   with the value assigned in 'value'''
   
   arcpy.env.extent = template
   arcpy.env.snapRaster = template
   arcpy.env.cellSize = template
   arcpy.env.outputCoordinateSystem = template
   arcpy.env.overwriteOutput = True
   
   sgdb = arcpy.env.scratchGDB

   list_rast = list()
   # add a rastval field
   for l in listFeat:
      printMsg('Rasterizing file ' + l + '...')
      nm = sgdb + os.sep + os.path.basename(l).replace('.shp','') + '_rast'
      arcpy.AddField_management(l, 'rastval', 'DOUBLE')
      arcpy.CalculateField_management (l, 'rastval', value, 'PYTHON')
      if arcpy.Describe(l).Name == "nhd_area_canalditch":
         # these are skinny linear features so need to use maximum area to make sure they are continuous
         # default polygon to raster conversion is only to rasterize cells with centers covered
         arcpy.PolygonToRaster_conversion(l, 'rastval', nm, "MAXIMUM_AREA", 'rastval', template)
      else:
         arcpy.FeatureToRaster_conversion (l, 'rastval', nm, template)
      list_rast.append(nm)
   # combine all rasters
   out_rast = CellStatistics(list_rast, 'MAXIMUM', 'DATA')
   
   # erase features if given
   if erase != "#":
      printMsg('Rasterizing file ' + erase + '...')
      erase_rast = sgdb + os.sep + os.path.basename(erase).replace('.shp','') + '_rast'
      arcpy.AddField_management(erase, 'rastval', 'DOUBLE')
      arcpy.CalculateField_management (erase, 'rastval', 1, 'PYTHON')
      arcpy.FeatureToRaster_conversion (erase, 'rastval', erase_rast, template)
      # reverse to create mask
      erase_mask = Con(IsNull(erase_rast), 0, erase_rast)
      erase_mask2 = SetNull(erase_mask, 1, "VALUE = 1")
      # mask original
      out_rast = ExtractByMask(out_rast, erase_mask2)
      # clean up
      garbagePickup([erase_rast, erase_mask])
      arcpy.DeleteField_management(erase, 'rastval')
      
   # add access points
   printMsg('Rasterizing file ' + accessPts + '...')
   ap = sgdb + os.sep + os.path.basename(accessPts).replace('.shp','') + '_rast'
   arcpy.AddField_management(accessPts, 'rastval', 'DOUBLE')
   arcpy.CalculateField_management (accessPts, 'rastval', value, 'PYTHON')
   arcpy.FeatureToRaster_conversion (accessPts, 'rastval', ap, template)
   
   # final raster, with access points "burned in"
   out_rast = CellStatistics([out_rast, ap], 'MAXIMUM', 'DATA')
   out_rast.save(out)
   
   garbagePickup(list_rast)
   garbagePickup(ap)
   
   # delete temp fields
   listFeat.append(accessPts)
   for l in listFeat:
      arcpy.DeleteField_management(l, 'rastval')
      
   return out_rast

def CreateAccessPolys(feat, costSurf, out, maxCost = 5000):
   
   arcpy.env.extent = costSurf
   arcpy.env.snapRaster = costSurf
   arcpy.env.cellSize = costSurf
   arcpy.env.outputCoordinateSystem = costSurf
   arcpy.env.overwriteOutput = True
   
   # did this in arcpro since it was one time and a fast process
   printMsg("Running cost distance...")
   cd = CostDistance(feat, costSurf, maxCost)
   cd1 = Con(cd, 1, "", "Value >= 0")
   
   printMsg("Converting to polygons...")
   # region group
   fc1 = arcpy.RasterToPolygon_conversion (cd1, out, "NO_SIMPLIFY")
   # dissolve 
   
   # garbagePickup([cd, cd1])
   return fc1

def main():
   # Set up variables
   listFeat = [r'C:\David\projects\rec_model\rec_datasets\derived\terr_aqua_polygon_processing.gdb\nhd_area_wtrb',
            r'C:\David\projects\rec_model\rec_datasets\derived\terr_aqua_polygon_processing.gdb\pub_fish_lake1',
            r'C:\David\projects\rec_model\rec_datasets\derived\terr_aqua_polygon_processing.gdb\nhd_flowline1',
            r'C:\David\projects\rec_model\rec_datasets\derived\terr_aqua_polygon_processing.gdb\nhd_flowline_canalditch',
            r'C:\David\projects\rec_model\rec_datasets\derived\terr_aqua_polygon_processing.gdb\public_beaches_polys',
            r'C:\David\projects\rec_model\rec_datasets\derived\terr_aqua_polygon_processing.gdb\nhd_area_canalditch']
   # included digitized beaches, subsets of NHD waterbody, area, and flowline
   accessPts = r'C:\David\projects\rec_model\source_database\exports\access_a_noZero.shp'
   template = r'C:\David\projects\va_cost_surface\cost_surfaces\costSurf_all.tif'
   out = r'C:\David\projects\rec_model\rec_datasets\derived\terr_aqua_polygon_processing.gdb\aqua_rast_nodam'
   value = 1
   erase = r'C:\David\projects\rec_model\rec_datasets\derived\terr_aqua_polygon_processing.gdb\nhd_line_damweir'
   RasterizeAll(listFeat, accessPts, out, template, value, erase)
   
   # Specify function to run
   # costSurf = RasterizeAll(listFeat, out, template)
   costSurf = r'C:\David\projects\rec_model\rec_datasets\derived\terr_aqua_polygon_processing.gdb\aqua_rast_nodam'
   feat = r'C:\David\projects\rec_model\source_database\exports\access_a.shp'
   out = r'C:\David\projects\rec_model\rec_datasets\derived\terr_aqua_polygon_processing.gdb\aqua_accesspolys_test'
   aqPolys = CreateAccessPolys(feat, costSurf, out, maxCost = 5000)

#if __name__ == '__main__':
#   main()
