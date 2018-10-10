#--------------------------------------------------------------------------------------
# AssessRecOpps.py
# Version:  ArcGIS 10.3.1 / Python 2.7.8
# Creation Date: 2018-10-04
# Last Edit: 2018-10-09
# Creator:  Kirsten R. Hazler
#
# Summary:
# Assesses adequacy of recreation opportunities based on facilities' service areas, population, and specified benchmark standards.
#
# Usage:
# 
#--------------------------------------------------------------------------------------
# Import Helper module and functions
import Helper
from Helper import *
from arcpy import env

def CreateBenchmark(inPop, inVal, outBenchmark):
   '''NOTE: We can eliminate this function; it is redundant/obsolete.
   Creates a raster indicating the desired level of recreational access, based on a per-person "rule of thumb" value and the population size. The output raster is a benchmark against which actual estimated recreation access is compared.
   
   inPop = input continuous raster representing population per pixel. This may have been generated by the "DistribPop" function, or other means. Pixel values should represent the number of persons within the pixel.
   
   inVal = input value representing the desired area (or length) of recreational facilities, per person. 
      For parks, the value suggested is 10 acres per 1000 people = 0.010 acres/person = 0.004 ha/person. This is based on communications with DCR-PRR staff; see "rule of thumb" email chain started 10/3/2018
      
      For trails, the value suggested is 1 mile per 2500 people = 1.61 km per 2500 people = 0.0006 km/person. This is based on the "Trails, Nature" line item in a chart provided by DCR-PRR staff; see email from J. Wampler on 10/5/2018.
         
   outBenchmark = output raster with benchmark values for desired recreation access, weighted by population.
   '''
   
   # Apply environment settings
   arcpy.env.extent = inPop
   arcpy.env.mask = inPop
   
   # Calculate benchmark raster
   printMsg('Calculating benchmark raster.')
   tmpRast = Raster(inPop) * float(inVal)
   tmpRast.save(outBenchmark)
   
   printMsg('Finished.')
   return outBenchmark

def QuantRecOpps(inDir, inPop, outRecPP, tmpDir, zeroRast = ''):
   '''Quantifies recreation opportunities accessed per person, based on facilities' service areas and population.
   
   inDir = input folder containing service area rasters to be processed. It is assumed these are continuous rasters in TIF format. Each service area should be coded with the value (e.g., area or trail length) of the entity, and the raster should be coded NoData (null) outside the service area.
   
   inPop = input continuous raster representing population per pixel. This may have been generated by the "DistribPop" function, or other means. Pixel values should represent the number of persons within the pixel.
   
   outRecPP = output raster representing per-person sum of available recreation access (area or length)
   
   [eliminated variable] outRecOpps = output raster representing population-weighted sum of available recreation access (area or length). This is the raster to be compared against the benchmark raster.
   
   tmpDir = directory to contain temporary outputs
   
   zeroRast = a raster coded with zeros whereever the "inPop" raster is non-null
   '''
   
   # Apply environment settings
   arcpy.env.snapRaster = inPop
   arcpy.env.cellSize = inPop
   arcpy.env.extent = inPop
   arcpy.env.mask = inPop
   
   # Set up some output variables
   if zeroRast == '':
      zeroRast = tmpDir + os.sep + 'zeros.tif'
      
   # Create baseline zeros raster
   if arcpy.Exists(zeroRast):
      printMsg('Zero raster already exists. Proceeding to next step...')
   else:
      printMsg('Creating zero raster...')
      tmpRast = Con(inPop, 0)
      tmpRast.save(zeroRast)
      printMsg('Zero raster created.')
      
   # Initialize some objects
   arcpy.env.workspace = inDir
   ServAreas = arcpy.ListRasters() # List of service areas to process
   myRastList = [zeroRast] # List to store paths to rasters to be summed
   myFailList = [] # List to store names of rasters failing to be processed
   myIndex = 1 # counter
   
   # For each service area:
   for sa in ServAreas:
      try:
         arcpy.env.extent = sa
         printMsg('Working on %s...' % sa) 
      
         # Integerize the service area
         intSA = tmpDir + os.sep + "intSA.tif"
         tmpRast = Con(sa,1)
         tmpRast.save(intSA)
         printMsg('Service area integerized.')

         # Get sum of population within service area
         sumPop = tmpDir + os.sep + "sumPop.tif"
         tmpRast = ZonalStatistics(intSA, "Value", inPop, "SUM", "DATA") 
         tmpRast.save(sumPop)
         printMsg('Population summed.')
         
         # Get the recreation area (or length) per person
         recPP = tmpDir + os.sep + "recPP_%05d.tif" % myIndex
         tmpRast = Raster(sa)/Raster(sumPop)
         tmpRast.save(recPP)
         printMsg('Per person rec opps calculated.')
         
         myRastList.append(recPP)
         printMsg('Processing for %s complete.' % sa)
         
      except:
         printMsg('Processing for %s failed.' % sa)
         myFailList.append(sa)
         
      finally:
         myIndex += 1
         try:
            del sa, intSA, sumPop, recPP
         except:
            pass
   
   # Sum the areas (or lengths) accessed per person
   printMsg('Summing all rasters to get per-person recreation access. This will take awhile...')
   arcpy.env.extent = inPop
   tmpRast = CellStatistics(myRastList, "SUM", "DATA")
   tmpRast.save(outRecPP)
   printMsg('Finished summing rasters.')
   
   # # Calculate the population-weighted areas (or lengths) accessed
   # printMsg('Calculating population-weighted recreation access...')
   # tmpRast = Raster(inPop)* Raster(outRecPP)
   # tmpRast.save(outRecOpps)
   printMsg('Mission accomplished.')
   
   return outRecPP
   
def AssessRecOpps(inBenchVal, inPop, inRecPP, outDir, outBasename):
   '''Compares estimated recreation access to a benchmark to determine where recreation resources meet or exceed desired levels, and where attention is needed to offer additional resources.
   
   [eliminated variable] inBenchmark = input raster with benchmark values for desired recreation access (area or length), weighted by population.
   
   inBenchVal = input value representing the desired area (or length) of recreational facilities, per person. 
      For parks, the value suggested is 10 acres per 1000 people = 0.010 acres/person = 0.004 ha/person. This is based on communications with DCR-PRR staff; see "rule of thumb" email chain started 10/3/2018
      
      For trails, the value suggested is 1 mile per 2500 people = 1.61 km per 2500 people = 0.0006 km/person. This is based on the "Trails, Nature" line item in a chart provided by DCR-PRR staff; see email from J. Wampler on 10/5/2018.
   
   inPop = input continuous raster representing population per pixel. This may have been generated by the "DistribPop" function, or by other means. Pixel values should represent the number of persons within the pixel.
   
   [eliminated variable] inRecOpps = input raster representing population-weighted sum of available recreation access (area or length). 
   
   inRecPP = input raster representing per-person sum of available recreation access (area or length)
   
   outDir = directory to contain output products
   
   outBasename = basename (string) for output products
   '''
   
   printMsg('Calculating the Recreation Access Score...')
   tmpRast1 = 100*Raster(inRecPP)/(float(inBenchVal))
   tmpRast2 = Con(tmpRast1 > 100, 100, tmpRast1)
   RecPercentPP = outDir + os.sep + outBasename + "_RecScore.tif"
   tmpRast2.save(RecPercentPP)
   
   printMsg('Calculating the Recreation Need...')
   tmpRast3 = Con(Raster(RecPercentPP) < 100, Raster(inPop) * (float(inBenchVal) - Raster(inRecPP)))
   RecNeed = outDir + os.sep + outBasename + "_RecNeed.tif"
   tmpRast3.save(RecNeed)
   
   # Possibly add further steps here to classify and symbolize output?
   
   printMsg('Finished.')
   return (RecPercentPP, RecNeed)
   
# Use the main function below to run functions directly from Python IDE or command line with hard-coded variables

def main():
   # Set up variables
   inPop = r'C:\Users\xch43889\Documents\Working\ConsVision\RecMod\TIF_VALAM\distribPop_noZeros.tif'
   inBenchVal = 0.004
   outBenchmark = r'C:\Users\xch43889\Documents\Working\ConsVision\RecMod\TIF_VALAM\terrLengthBenchmark.tif'
   inDir = r'C:\Users\xch43889\Documents\Working\ConsVision\RecMod\example_serviceareas'
   outRecPP = r'C:\Users\xch43889\Documents\Working\ConsVision\RecMod\TIF_VALAM\outRecPP.tif'
   outRecOpps = r'C:\Users\xch43889\Documents\Working\ConsVision\RecMod\TIF_VALAM\outRecOpps.tif'
   tmpDir = r'C:\Users\xch43889\Documents\Working\ConsVision\RecMod\TMP'
   outRecAssessment = r'C:\Users\xch43889\Documents\Working\ConsVision\RecMod\TIF_VALAM\terrRecAssess_DiffPP.tif'
   outDir = r'C:\Users\xch43889\Documents\Working\ConsVision\RecMod\TIF_VALAM'
   outBasename = "TerrArea"
      
   # Specify function(s) to run
   # CreateBenchmark(inPop, inVal, outBenchmark)
   # QuantRecOpps(inDir, inPop, outRecPP, tmpDir, zeroRast = '')
   AssessRecOpps(inBenchVal, inPop, outRecPP, outDir, outBasename)
   

if __name__ == '__main__':
   main()
