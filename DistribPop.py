#--------------------------------------------------------------------------------------
# DistribPop.py
# Version:  ArcGIS 10.3.1 / Python 2.7.8
# Creation Date: 2018-10-03
# Last Edit: 2019-02-19
# Creator:  Kirsten R. Hazler
#
# Summary:
# Distributes population from census blocks or block groups to pixels assumed to be actually occupied, based on land
# cover or road density. Yields a raster representing persons per pixel.
#
# Usage:
# IMPORTANT NOTE: If blocks or other census units are clipped to a processing boundary, the population for the
# remaining polygon fragments MUST be adjusted prior to running a population distribution function. Example:
# If clipping results in 40% of a polygon's area remaining, the population value should be adjusted to 40% of
# the original value.
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
   
def DistribPop_roadDens(inBlocks, fldPop, inRoadDens, outPop, tmpDir, popMask=None):
   '''Distributes population from census blocks or other unit to pixels based on road density, yielding a raster representing persons per pixel.
   inBlocks = input shapefile delineating census blocks, block groups, or other census unit.
   fldPop = field within inBlocks designating the population for each block 
   inRoadDens = raster representing road density
   outPop = output raster representing population per pixel
   tmpDir = directory to store intermediate files
   popMask = optional raster mask defining where population can be distributed
   '''
   
   # Apply environment settings
   arcpy.env.snapRaster = inRoadDens
   arcpy.env.cellSize = inRoadDens
   arcpy.env.extent = inRoadDens
   arcpy.env.outputCoordinateSystem = inRoadDens
   if popMask:
      # This becomes processing mask. Note that env.mask does not apply to PolygonToRaster, but will apply to all
      # other raster operations.
      arcpy.env.mask = popMask
   else:
      arcpy.env.mask = inRoadDens
   
   # Re-project census blocks to match road density raster
   printMsg('Re-projecting census blocks...')
   Blocks_prj = ProjectToMatch (inBlocks, inRoadDens)
   fld_id = [a.name for a in arcpy.ListFields(Blocks_prj) if a.type == 'OID'][0]
   
   # Apply more environment settings
   # arcpy.env.mask = Blocks_prj
   # arcpy.env.extent = Blocks_prj
   
   # Convert census blocks to raster zones
   blockZones = tmpDir + os.sep + "blockZones.tif"
   printMsg('Converting census blocks to raster zones...')
   arcpy.PolygonToRaster_conversion(in_features = Blocks_prj, 
                                    value_field = fld_id, 
                                    out_rasterdataset = blockZones,
                                    cell_assignment = "MAXIMUM_AREA", 
                                    priority_field = "NONE", 
                                    cellsize = inRoadDens)

   # Get the sum of road density values by zone
   blockSumDens = tmpDir + os.sep + "blockSumDens.tif"
   printMsg('Summing road density values within zones...')
   tmpRast = ZonalStatistics(blockZones, "Value", inRoadDens, "SUM", "DATA")
   tmpRast.save(blockSumDens)
   
   # Get the proportional road density per pixel
   propDens = tmpDir + os.sep + "propDens.tif"
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
   tmpRast = SetNull(pixelPop, pixelPop, "Value <= 0")
   tmpRast.save(outPop)
   arcpy.BuildPyramids_management(outPop)
   
   printMsg('Finished.')
   return outPop


def makePopMask(feats, inRaster, outMask):
   '''Makes a mask indicating where population CAN be allocated. All area within features given to `feats`
   will be NoData in the final mask.

   feats = List of feature classes indicating exclusion features
   inRaster = template raster
   outMask = output raster
   '''

   arcpy.env.outputCoordinateSystem = inRaster
   arcpy.env.snapRaster = inRaster
   arcpy.env.cellSize = inRaster
   arcpy.env.extent = inRaster

   printMsg("Merging datasets...")
   arcpy.Merge_management(feats, 'popMask_feats')
   arcpy.CalculateField_management('popMask_feats', 'rast', '1', field_type="SHORT")
   arcpy.PolygonToRaster_conversion('popMask_feats', value_field='rast',
                                    out_rasterdataset='popMask_rast0',
                                    cellsize=inRaster)
   printMsg("Creating raster mask...")
   arcpy.sa.SetNull(arcpy.sa.IsNull('popMask_rast0'), 1, "Value = 0").save(outMask)

   return outMask


def main():
   # Set up variables
   arcpy.env.workspace = r'E:\projects\rec_model\rec_model_processing\input_recmodel.gdb'
   inBlocks = r'E:\projects\rec_model\rec_model_processing\input_recmodel.gdb\ACS_2014_2018_5yr_BG_Clip'  # r'H:\Working\ACS_2016\ACS_2016_5yr_BG.shp'
   fldPop = 'total_pop_clip'  # 'TotPop_clp'
   inRoadDens = r'L:\David\projects\RCL_processing\Tiger_2019\roads_proc.gdb\Roads_kdens_250_noZero'  # r'H:\Working\RecMod\RecModProducts.gdb\Roads_kdens_250'
   outPop = r'E:\projects\rec_model\rec_model_processing\input_recmodel.gdb\distribPop_kdens_2019rd'  # r'H:\Working\RecMod\RecModProducts.gdb\distribPop_kdens'
   tmpDir = r'E:\projects\rec_model\rec_model_processing\_temp'  # r'H:\Working\TMP'

   # Make population mask
   mask_features = [r'E:\projects\rec_model\rec_model.gdb\CensusBlocks_noLand',
                    r'E:\projects\rec_model\rec_datasets\rec_datasets_prep_clean\rec_datasets.gdb\prep_VA_PUBLIC_ACCESS_LANDS_20190201_diss2']
   popMask = 'population_mask_raster'
   makePopMask(mask_features, inRoadDens, popMask)
   
   # Specify function to run
   DistribPop_roadDens(inBlocks, fldPop, inRoadDens, outPop, tmpDir, popMask)

if __name__ == '__main__':
   main()
