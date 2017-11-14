#--------------------------------------------------------------------------------------
# RecRastFromPolys.py
# Version:  ArcGIS 10.3.1 / Python 2.7.8
# Creation Date: 2017-10-27
# Last Edit: 2017-11-14
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


def RecRastFromPolys(inGDB, inFacilities, fld_area, inSnap, outDir, zeroRast = ''):
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
   if zeroRast == '':
      zeroRast = outFolder + os.sep + 'zeros.tif'
   sumRast = outFolder + os.sep + 'sum.tif'

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

   # Get the list of polygon feature classes in the input GDB
   arcpy.env.workspace = inGDB
   inPolys = arcpy.ListFeatureClasses ('', 'Polygon')
   numPolys = len(inPolys)
   printMsg('There are %s polygons to process.' % str(numPolys))

   # Initialize counter
   myIndex = 1 

   # Initialize lists 
   myFailList = [] # to store IDs of facility groups that fail to get processed
   myRastList = [zeroRast] # to store paths to rasters to be summed

   # Loop through the polygons, creating rasters and updating running sum raster
   for poly in inPolys:
      try:
         t1 = datetime.now()
         
         # Extract the group ID from the feature class names
         id = poly.replace('Polygons_', '')
         printMsg('Working on polygon %s with ID %s' % (str(myIndex), str(id)))
         
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
         
         # Convert to raster and save
         printMsg('Converting to raster...')
         arcpy.env.extent = poly
         tmpRast = outFolder + os.sep + 'tmp%s.tif' % str(id) 
         arcpy.PolygonToRaster_conversion (poly, 'val', tmpRast, 'MAXIMUM_COMBINED_AREA')
         t2 = datetime.now()
         
         myRastList.append(tmpRast)
         printMsg('Completed polygon %s with ID %s' % (str(myIndex), str(id)))
         deltaString = GetElapsedTime(t1, t2)
         printMsg('Elapsed time: %s.' % deltaString)
         
      except:
         printMsg('Processing for polygon %s failed.' % str(id))
         tbackInLoop()
         myFailList.append
         
      finally:
         t1 = datetime.now()
         printMsg('Processing for polygon %s ended at %s' % (str(id), str(t1)))
         myIndex += 1
         
   if len(myFailList) > 0:
      num_Fails = len(myFailList)
      printMsg('\nProcess complete, but the following %s facility IDs failed: %s.' % (str(num_Fails), str(myFailList)))
   
   # Add rasters to create summation raster and save
   printMsg('Summing all rasters. This will take awhile...')
   arcpy.env.extent = inSnap
   t1 = datetime.now()
   newSum = CellStatistics (myRastList, "SUM", "DATA")
   arcpy.CopyRaster_management (newSum, sumRast)   
   t2 = datetime.now()
   deltaString = GetElapsedTime(t1, t2)
   printMsg('Time elapsed to sum and save final output: %s.' % deltaString)
   
   # Cleanup
   printMsg('Deleting temporary rasters...')
   myRastList.remove(zeroRast)
   garbagePickup(myRastList)
   
   # End the timer
   t2 = datetime.now()
   deltaString = GetElapsedTime(t0, t2)
   printMsg('All processing completed: %s' % str(t2))
   printMsg('Total processing time: %s.' % deltaString)
   printMsg('Your output sum raster is %s.' % sumRast)
   
   return sumRast

   ##################################################################################################################
# Use the main function below to run a function directly from Python IDE or command line with hard-coded variables

def main():
   # Set up variables
   inGDB = r'E:\ConsVision_RecMod\Terrestrial\OutputRemnants\na_ServArea\terrestrial\terrestrial.gdb'
   inFacilities = r'E:\ConsVision_RecMod\Terrestrial\Input\TerrestrialFacilities.shp'
   fld_area = 'plxu_area'
   inSnap = r'E:\ConsVision_RecMod\Snap\cs_TrvTm_2011_lam.tif'
   outDir = r'E:\ConsVision_RecMod\Terrestrial\OutputRemnants\na_ServArea\terrestrial'
   zeroRast = r'E:\ConsVision_RecMod\Terrestrial\Output\na_ServArea\terrestrial\raster\zeros.tif'
   
   # Specify function to run
   RecRastFromPolys(inGDB, inFacilities, fld_area, inSnap, outDir, zeroRast)

if __name__ == '__main__':
   main()
