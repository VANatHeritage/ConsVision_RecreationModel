#--------------------------------------------------------------------------------------
# DistribPop.py
# Version:  ArcGIS 10.3.1 / Python 2.7.8
# Creation Date: 2018-10-03
# Last Edit: 2018-10-03
# Creator:  Kirsten R. Hazler
#
# Summary:
# Distributes population from census blocks to developed pixels, yielding a raster representing persons per pixel.
#
# Usage:
# 
#--------------------------------------------------------------------------------------
# Import Helper module and functions
import Helper
from Helper import *
from arcpy import env

def DistribPop(inBlocks, fldPop, inLandCover, inImpervious, inRoads, outPop, tmpDir):
   '''Distributes population from census blocks to developed pixels, yielding a raster representing persons per pixel.
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
   expression = 'SetNull(("%s" == 0) & ("%s" == 0),1)' %(impDev, lcDev)
   printMsg('Combining land cover and imperviousness...')
   arcpy.gp.RasterCalculator_sa(expression, nlcdDev)
   
   mskDev = tmpDir + os.sep + "mskDev.tif"
   expression = 'Con(IsNull("%s"),"%s")' % (inRoads, nlcdDev)
   printMsg('Removing major road pixels...')
   arcpy.gp.RasterCalculator_sa(expression, mskDev)
   
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
   arcpy.gp.ZonalStatistics_sa(blockZones, "Value", mskDev, blockSumDev, "SUM", "DATA")
   
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
   expression = '"%s" / "%s"' % (blockPop, blockSumDev)
   printMsg('Generating final output...')
   arcpy.gp.RasterCalculator_sa(expression, outPop)
   
   return outPop
   
   # Use the main function below to run a function directly from Python IDE or command line with hard-coded variables

def main():
   # Set up variables
   inBlocks = r'H:\Backups\GIS_Data_VA\TIGER\TABBLOCK_POPHU\2010\tabblock2010_51_pophu\tabblock2010_51_pophu.shp'
   fldPop = 'POP10'
   inLandCover = r'H:\Backups\DCR_Work_DellD\GIS_Data_VA_proc\Finalized\NLCD_VA_2011ed.gdb\nlcd_2011_lc'
   inImpervious = r'H:\Backups\DCR_Work_DellD\GIS_Data_VA_proc\Finalized\NLCD_VA_2011ed.gdb\nlcd_2011_imp'
   inRoads = r'C:\Users\xch43889\Documents\Working\ConsVision\RecMod\TIF_VALAM\costSurf_only_lah.tif'
   outPop = r'C:\Users\xch43889\Documents\Working\ConsVision\RecMod\TIF_VALAM\distribPop.tif'
   tmpDir = r'C:\Users\xch43889\Documents\Working\ConsVision\RecMod\TMP'
   
   # Specify function to run
   DistribPop(inBlocks, fldPop, inLandCover, inImpervious, inRoads, outPop, tmpDir)

if __name__ == '__main__':
   main()