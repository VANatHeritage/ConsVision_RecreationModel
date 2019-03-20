#--------------------------------------------------------------------------------------
# DistribPop.py
# Version:  ArcGIS 10.3.1 / Python 2.7.8
# Creation Date: 2018-10-03
# Last Edit: 2019-03-20
# Creator:  Kirsten R. Hazler
#
# Summary:
# Distributes population from census blocks or block groups to pixels assumed to be actually occupied, based on land cover or road density. Yields a raster representing persons per pixel.
#
# Usage:
# IMPORTANT NOTE: If blocks or other census units are clipped to a processing boundary, the population for the remaining polygon fragments MUST be adjusted prior to running a population distribution function. Example: If clipping results in 40% of a polygon's area remaining, the population value should be adjusted to 40% of the original value.
#--------------------------------------------------------------------------------------
# Import Helper module and functions
import Helper
from Helper import *
from arcpy import env

def DistribPop_nlcd(inBlocks, fldPop, inLandCover, inImpervious, inRoads, outPop, tmpDir):
   '''Distributes population from census blocks to developed pixels based on NLCD land cover, yielding a raster representing persons per pixel.
   inBlocks = input shapefile delineating census blocks.
   fldPop = field within inBlocks designating the population for each block 
   inLandCover = NLCD land cover raster
   inImpervious = NLCD imperviousness raster
   inRoads = raster representation of major roads / uninhabitable pixels
   outPop = output raster representing population per pixel
   tmpDir = directory to store intermediate files'''
   
   # Apply environment settings
   arcpy.env.snapRaster = inLandCover
   arcpy.env.cellSize = inLandCover
   arcpy.env.outputCoordinateSystem = inLandCover
   
   # Re-project census blocks to match land cover
   printMsg('Re-projecting census blocks...')
   Blocks_prj = ProjectToMatch (inBlocks, inLandCover)
   
   # Apply more environment settings
   arcpy.env.mask = Blocks_prj
   arcpy.env.extent = Blocks_prj
   
   # Extract developed pixels
   # Criteria: NLCD class in (22, 23, 24) OR NLCD imperviousness gte 10, but with major roads excluded
   lcDev = tmpDir + os.sep + "lcDev.tif"
   rclsString = "0 0;11 0;21 0;22 1;23 1;24 1;31 0;41 0;42 0;43 0;52 0;71 0;81 0;82 0;90 0;95 0"
   printMsg('Reclassifying land cover...')
   arcpy.gp.Reclassify_sa(inLandCover, "Value", rclsString, lcDev, "NODATA")
   
   impDev = tmpDir + os.sep + "impDev.tif"
   rclsString = "0 9.9999 0;9.9999 100 1;100 1000 0"
   printMsg('Reclassifying imperviousness...')
   arcpy.gp.Reclassify_sa(inImpervious, "Value", rclsString, impDev, "NODATA")
   
   nlcdDev = tmpDir + os.sep + "nlcdDev.tif"
   printMsg('Combining land cover and imperviousness...')
   tmpRast = SetNull(((Raster(impDev) == 0) & (Raster(lcDev) == 0)), 1)
   tmpRast.save(nlcdDev)
   
   mskDev = tmpDir + os.sep + "mskDev.tif"
   printMsg('Removing major road pixels...')
   tmpRast = Con(IsNull(inRoads), nlcdDev)
   tmpRast.save(mskDev)
   
   # Convert census blocks to raster zones
   blockZones = tmpDir + os.sep + "blockZones.tif"
   printMsg('Converting census blocks to raster zones...')
   arcpy.PolygonToRaster_conversion(in_features = Blocks_prj, 
                                    value_field = "FID", 
                                    out_rasterdataset = blockZones, 
                                    cell_assignment = "MAXIMUM_AREA", 
                                    priority_field = "NONE", 
                                    cellsize = inLandCover)
   
   # Get the sum of developed cells by zone
   arcpy.env.mask = mskDev
   blockSumDev = tmpDir + os.sep + "blockSumDev"
   printMsg('Summing developed cells within zones...')
   tmpRast = ZonalStatistics(blockZones, "Value", mskDev, "SUM", "DATA")
   tmpRast.save(blockSumDev)
   
   # Convert census blocks to raw population raster
   blockPop = tmpDir + os.sep + "blockPop.tif"
   printMsg('Converting census blocks to raw population raster...')
   arcpy.PolygonToRaster_conversion(in_features = Blocks_prj, 
                                    value_field = fldPop, 
                                    out_rasterdataset = blockPop, 
                                    cell_assignment = "MAXIMUM_AREA", 
                                    priority_field = "NONE", 
                                    cellsize = inLandCover)
   
   # Get persons per pixel by distributing population to developed pixels only
   pixelPop = tmpDir + os.sep + "pixelPop.tif"
   printMsg('Generating final output...')
   tmpRast = Raster(blockPop)/Raster(blockSumDev)
   tmpRast.save(pixelPop)
   
   # Set zeros to nulls
   arcpy.env.mask = Blocks_prj
   tmpRast = SetNull(Raster(pixelPop) == 0, pixelPop)
   tmpRast.save(outPop)
   
   printMsg('Finished.')
   return outPop
   
def DistribPop_roadDens(inBlocks, fldPop, inRoadDens, outPop, tmpDir):
   '''Distributes population from census blocks or other unit to pixels based on road density, yielding a raster representing persons per pixel.
   inBlocks = input shapefile delineating census blocks, block groups, or other census unit.
   fldPop = field within inBlocks designating the population for each block 
   inRoadDens = raster representing road density
   outPop = output raster representing population per pixel
   tmpDir = directory to store intermediate files
   
   IMPORTANT PRE-PROCESSING NOTE: The block group polygons need to be clipped to the processing area prior to processing. Additional steps are needed to ensure correct population numbers derived from the block group data.
      - PRIOR TO CLIPPING: Re-project the merged feature class to albers. Note that the "Shape_Area" field automatically updates, reflecting area in square meters.
      - PRIOR TO CLIPPING: Add a new field, called "Orig_Area". Use the field calculator to populate the Orig_Area field from the Shape_Area field (so the two fields will have identical values).
      - Clip the feature class to the processing buffer. Note that the Shape_Area field will again have automatically updated, and for clipped polygons, will now be lower than the value in Orig_Area. Polygons not clipped (i.e., those completely contained by the processing boundary) should still have the same values in both area fields.
      - Add a new field, called TotPop_clip (long integer).
      - Calculate the TotPop_clip field with this Python formula:  !B01001e1!* !Shape_Area!/ !Orig_Area!
      The TotPop_clip field is the field to use for population, not the original block group population field.
   '''
   
   # Apply environment settings
   arcpy.env.snapRaster = inRoadDens
   arcpy.env.cellSize = inRoadDens
   arcpy.env.extent = inRoadDens
   arcpy.env.mask = inRoadDens
   arcpy.env.outputCoordinateSystem = inRoadDens
   
   # Re-project census blocks to match road density raster
   printMsg('Re-projecting census blocks...')
   Blocks_prj = ProjectToMatch (inBlocks, inRoadDens)
   
   # Apply more environment settings
   arcpy.env.mask = Blocks_prj
   arcpy.env.extent = Blocks_prj
   
   # Convert census blocks to raster zones
   blockZones = tmpDir + os.sep + "blockZones.tif"
   printMsg('Converting census blocks to raster zones...')
   arcpy.PolygonToRaster_conversion(in_features = Blocks_prj, 
                                    value_field = "FID", 
                                    out_rasterdataset = blockZones, 
                                    cell_assignment = "MAXIMUM_AREA", 
                                    priority_field = "NONE", 
                                    cellsize = inRoadDens)
   
   # Get the sum of road density values by zone
   blockSumDens = tmpDir + os.sep + "blockSumDens"
   printMsg('Summing road density values within zones...')
   tmpRast = ZonalStatistics(blockZones, "Value", inRoadDens, "SUM", "DATA")
   tmpRast.save(blockSumDens)
   
   # Get the proportional road density per pixel
   propDens = tmpDir + os.sep + "propDens"
   printMsg('Calculating proportional road density values...')
   tmpRast = Raster(inRoadDens)/Raster(blockSumDens)
   tmpRast.save(propDens)
   
   # Convert census blocks to raw population raster
   blockPop = tmpDir + os.sep + "blockPop.tif"
   printMsg('Converting census blocks to raw population raster...')
   arcpy.PolygonToRaster_conversion(in_features = Blocks_prj, 
                                    value_field = fldPop, 
                                    out_rasterdataset = blockPop, 
                                    cell_assignment = "MAXIMUM_AREA", 
                                    priority_field = "NONE", 
                                    cellsize = inRoadDens)
   
   # Get persons per pixel by distributing population according to proportional road density
   pixelPop = tmpDir + os.sep + "pixelPop.tif"
   printMsg('Distributing population according to road density...')
   tmpRast = Raster(blockPop)*Raster(propDens)
   tmpRast.save(pixelPop)
   
   # Set zeros to nulls
   arcpy.env.mask = inRoadDens
   printMsg('Setting zeros to null...')
   tmpRast = SetNull(Raster(pixelPop) <= 0, pixelPop)
   tmpRast.save(outPop)
   
   printMsg('Finished.')
   return outPop
   


def main():
   # Set up variables
   inBlocks = r'H:\Working\ACS_2016\ACS_2016_5yr_BG.shp'
   fldPop = 'TotPop_clp'
   inRoadDens = r'H:\Working\RecMod\RecModProducts.gdb\Roads_kdens_250'
   outPop = r'H:\Working\RecMod\RecModProducts.gdb\distribPop_kdens'
   tmpDir = r'H:\Working\TMP'
   
   # Specify function to run
   DistribPop_roadDens(inBlocks, fldPop, inRoadDens, outPop, tmpDir)

if __name__ == '__main__':
   main()
