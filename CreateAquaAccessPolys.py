# -*- coding: utf-8 -*-
"""
CreateAquaAccessPolys

Created on Wed Jun 20 13:54:43 2018

@author: David Bucklin

The function RasterizeAll takes water access points, and one or more feature layers representing aqautic areas, and rasterizes them into one layer
with a fixed value for water areas.  This can be used as a cost surface raster for travel along the water network.

The function CreateAccessPolys uses the water areas cost surface raster and water access points to derive "Access area" for each point, given
a maximum travel distance along the water network. The access areas are converted to features and dissolved, and then given a unique ID. Their
attributes are joined back to the points in a new feature class.
"""

import Helper
from Helper import *
from arcpy import env

def RasterizeAll(listFeat, accessPts, out, template, value = 1, erase = "#"):
   '''Rasterizes all feature classes in list into one raster layer,
   with the value assigned in 'value'''
   
   arcpy.env.extent = template
   arcpy.env.snapRaster = template
   arcpy.env.cellSize = template
   arcpy.env.outputCoordinateSystem = template
   arcpy.env.overwriteOutput = True

   list_rast = list()
   # add a rastval field
   for l in listFeat:
      printMsg('Rasterizing file ' + l + '...')
      nm = os.path.basename(l).replace('.shp','') + '_rast'
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
      printMsg('Rasterizing erase features ' + erase + '...')
      erase_rast = os.path.basename(erase).replace('.shp','') + '_rast'
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
   ap = os.path.basename(accessPts).replace('.shp','') + '_rast'
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

def CreateAccessPolys(accessPts, costSurf, outPolys, outPts, maxCost = 5000):
   
   arcpy.env.extent = costSurf
   arcpy.env.snapRaster = costSurf
   arcpy.env.cellSize = costSurf
   arcpy.env.outputCoordinateSystem = costSurf
   arcpy.env.overwriteOutput = True

   printMsg("Running cost distance...")
   cd = CostDistance(accessPts, costSurf, maxCost)
   cd1 = Con(cd, 1, "", "Value >= 0")
   cd1 = RegionGroup(cd1, "EIGHT")
   
   printMsg("Converting to polygons...")
   fc1 = arcpy.RasterToPolygon_conversion (cd1, "r2p", "NO_SIMPLIFY")
   fc2 = arcpy.Dissolve_management(fc1, outPolys, "gridcode") # creates one polygon per gridcode
   
   # join polygon id/area to points
   arcpy.AddField_management(fc2, "area_ha", "FLOAT")
   arcpy.CalculateField_management(fc2, "area_ha", '!shape.area@hectares!',"PYTHON_9.3")
   arcpy.SpatialJoin_analysis(accessPts, fc2, outPts)
   
   garbagePickup([cd, cd1, fc1])
   return fc2

def main():
   
   # set workspace for intermediate outputs
   arcpy.env.workspace = r'C:\David\scratch\scratch_gdb.gdb'
   
   # create aquatic cost surface raster from aquatic features
   # list of feature classes to rasterize
   listFeat = [r'C:\David\projects\rec_model\rec_datasets\derived\terr_aqua_polygon_processing.gdb\nhd_area_wtrb',
            r'C:\David\projects\rec_model\rec_datasets\derived\terr_aqua_polygon_processing.gdb\pub_fish_lake1',
            r'C:\David\projects\rec_model\rec_datasets\derived\terr_aqua_polygon_processing.gdb\nhd_flowline1',
            r'C:\David\projects\rec_model\rec_datasets\derived\terr_aqua_polygon_processing.gdb\public_beaches_polys',
            r'C:\David\projects\rec_model\rec_datasets\derived\terr_aqua_polygon_processing.gdb\nhd_area_canalditch'] # these are now included in nhd_area_wtrb; but need to be handled differently for burn-in
   # included digitized beaches, subsets of NHD waterbody, area, and flowline
   # access pts (use select to exclude use = 0 points)
   arcpy.Select_analysis(r'C:\David\projects\rec_model\source_database\exports\access_a.shp', r'C:\David\projects\rec_model\source_database\exports\access_a_noZero.shp',"use in (1,2)")
   accessPts = r'C:\David\projects\rec_model\source_database\exports\access_a_noZero.shp'
   # template raster
   template = r'C:\David\projects\va_cost_surface\cost_surfaces\costSurf_all.tif'
   # output raster
   out = r'C:\David\projects\rec_model\rec_datasets\derived\terr_aqua_polygon_processing.gdb\aqua_rast_nodam'
   value = 1
   # erase features (will exclude these rasterized features from raster)
   erase = r'C:\David\projects\rec_model\rec_datasets\derived\terr_aqua_polygon_processing.gdb\nhd_line_damweir'
   # run fn
   RasterizeAll(listFeat, accessPts, out, template, value, erase)
   
   ### generate aquatic areas
   import datetime
   dt = str(datetime.date.today()).replace("-","_")
   accessPts = r'C:\David\projects\rec_model\source_database\exports\access_a_noZero.shp'
   costSurf = r'C:\David\projects\rec_model\rec_datasets\derived\terr_aqua_polygon_processing.gdb\aqua_rast_nodam'
   outPolys = r'C:\David\projects\rec_model\rec_datasets\derived\terr_aqua_polygon_processing.gdb\aqua_accesspolys_' + dt
   outPts = r'C:\David\projects\rec_model\source_database\exports\access_a_wAreas_' + dt + '.shp'
   # run fn
   CreateAccessPolys(accessPts, costSurf, outPolys, outPts, maxCost = 5000)

if __name__ == '__main__':
   main()
