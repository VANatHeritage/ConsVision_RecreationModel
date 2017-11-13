#--------------------------------------------------------------------------------------
# RecRastFromPolys.py
# Version:  ArcGIS 10.3.1 / Python 2.7.8
# Creation Date: 2017-10-27
# Last Edit: 2017-11-09
# Creator:  Kirsten R. Hazler
#
# Summary:
# Creates a summary raster from a set of Network Analyst Service Area polygons.
#
# Usage:
# First create the polygons using RunServiceAreaAnalysisLoop.py
#--------------------------------------------------------------------------------------


# Import Helper module and functions
import Helper
from Helper import *
from arcpy import env


def RecRastFromPolys(inGDB, inFacilities, fld_area, inSnap, outDir):
   '''Creates a summary raster from a set of Network Analyst Service Area polygons. These must have been first generated with the "RecServiceAreas" function.
   inGDB = Input geodatabase containing service area polygons
   inFacilities = Feature class with points used to generate service area polygons
   fld_area = The field in inFacilities containing the area of the public lands polygon associated with each point
   inSnap = Input Template raster used to set cell size and alignment
   outDir = Directory to contain outputs'''
   
   # Apply environment settings
   arcpy.env.snapRaster = inSnap
   arcpy.env.cellSize = inSnap
   arcpy.env.mask = inSnap
   arcpy.env.outputCoordinateSystem = inSnap
   arcpy.env.extent = inSnap

   # Designate output folder
   outFolder = outDir + os.sep + 'raster'
   if not os.path.exists(outFolder):
      os.makedirs(outFolder)
   else: 
      pass

   # Start the timer
   t0 = datetime.now()
   printMsg('Processing started: %s' % str(t0))

   # Set up some output variables
   zeroRast = outFolder + os.sep + 'zeros.tif'
   sumRast = outFolder + os.sep + 'sum.tif'
   tmpRast = outFolder + os.sep + 'tmp.tif'

   # Define a function for converting area (assumed in hectares) to scores
   def ScoreArea(area):
      import math
      score = 25*math.log(area + 2, 10)
      if score > 100:
         score = 100
      return score
   
   # Create running zeros and running sum rasters
   if arcpy.Exists(zeroRast):
      printMsg('Zero raster already exists. Proceeding to next step...')
   else:
      printMsg('Initializing running sum raster with zeros...')
      zeros = CreateConstantRaster(0.0)
      zeros.save(zeroRast)
      printMsg('Zero raster created.')
   arcpy.CopyRaster_management (zeroRast, sumRast)
   printMsg('Running sum raster created.')

   # Get the list of polygon feature classes in the input GDB
   arcpy.env.workspace = inGDB
   inPolys = arcpy.ListFeatureClasses ('', 'Polygon')
   numPolys = len(inPolys)
   printMsg('There are %s polygons to process.' % str(numPolys))

   # Initialize counter
   myIndex = 1 

   # Initialize empty list to store IDs of facility groups that fail to get processed
   myFailList = []

   # Loop through the polygons, creating rasters and updating running sum raster
   for poly in inPolys:
      try:
         printMsg('Working on polygon %s' % str(myIndex))
         t1 = datetime.now()
         
         # Extract the group ID from the feature class names
         id = poly.replace('Polygons_', '')
         
         # Get the corresponding Facilities feature class
         # Subset to include only those used to generate service area
         facPts = inGDB + os.sep + 'Facilities_' + id
         where_clause = "Status = 0" # Status is 'OK'
         arcpy.MakeFeatureLayer_management (facPts, 'lyrPts', where_clause)

         # Perform a spatial join to get the full attributes
         arcpy.SpatialJoin_analysis ('lyrPts', inFacilities, 'tmpPts', 'JOIN_ONE_TO_ONE', 'KEEP_COMMON', '', 'ARE_IDENTICAL_TO')
         
         # Sum the areas of polygons represented by points
         areas = unique_values('tmpPts', fld_area)
         SumArea = sum(areas)
         
         # Get score for area
         score = ScoreArea(SumArea)
         
         # Add and populate value field with score
         printMsg('Adding and populating raster value field...')
         poly = inGDB + os.sep + poly
         arcpy.AddField_management (poly, 'val', 'DOUBLE')
         arcpy.CalculateField_management (poly, 'val', score, 'PYTHON')
         
         # Convert to raster
         printMsg('Converting to raster...')
         arcpy.env.extent = poly
         arcpy.PolygonToRaster_conversion (poly, 'val', tmpRast, 'MAXIMUM_COMBINED_AREA')
         
         # Add to running sum raster and save
         printMsg('Adding to running sum raster...')
         arcpy.env.extent = inSnap
         newSum = CellStatistics ([sumRast, tmpRast], "SUM", "DATA")
         arcpy.CopyRaster_management (newSum, sumRast)
         t2 = datetime.now()
         
         printMsg('Completed polygon %s' % str(myIndex))
         deltaString = GetElapsedTime(t1, t2)
         printMsg('Elapsed time: %s.' % deltaString)
         
      except:
         printMsg('Processing for polygon %s failed.' % str(myIndex))
         tbackInLoop()
         myFailList.append
      finally:
         t1 = datetime.now()
         printMsg('Processing for polygon %s ended at %s' % (str(myIndex), str(t1)))
         myIndex += 1
         
   if len(myFailList) > 0:
      num_Fails = len(myFailList)
      printMsg('\nProcess complete, but the following %s facility IDs failed: %s.' % (str(num_Fails), str(myFailList)))
      
   # End the timer
   t3 = datetime.now()
   deltaString = GetElapsedTime(t0, t3)
   printMsg('All features completed: %s' % str(t2))
   printMsg('Total processing time: %s.' % deltaString)
   printMsg('Your output sum raster is %s.' % sumRast)
   
   return sumRast

   ##################################################################################################################
# Use the main function below to run a function directly from Python IDE or command line with hard-coded variables

def main():
   # Set up variables
   inGDB = r'C:\Testing\ConsVisionRecMod\Subsets\TestOutput\na_ServArea\terrestrial\terrestrial.gdb'
   inFacilities = r'C:\Testing\ConsVisionRecMod\TestSubset.shp'
   fld_area = 'plxu_area'
   inSnap = r'C:\Testing\ConsVisionRecMod\Statewide\cs_TrvTm_2011_lam.tif'
   outDir = r'C:\Testing\ConsVisionRecMod\Subsets\TestOutput\na_ServArea\terrestrial'
   
   # Specify function to run
   RecRastFromPolys(inGDB, inFacilities, fld_area, inSnap, outDir)

if __name__ == '__main__':
   main()
