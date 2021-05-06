#--------------------------------------------------------------------------------------
# DistribPop.py
# Version:  ArcGIS 10.3.1 / Python 2.7.8
# Creation Date: 2018-10-03
# Last Edit: 2021-02-02
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
import arcpy.sa

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
   popMask = optional raster mask, NoData areas will not have population allocated
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


def makePopMask_blocks(blocks, snapMask, out, clause="POP10 > 0"):
   ''' Makes a feature and raster mask from census blocks, indicating where population CAN be allocated. Default is to
   include only blocks where population is greater than 0.

   :param blocks: Census blocks feature class
   :param snapMask: Raster defining extent, snap, cellsize, mask
   :param out: Output feature class. Rasterized mask will have use this name with a '_rast' suffix.
   :param clause: clause used to select census blocks to include
   :return: raster mask
   '''

   print('Buffering blocks by 10 meters...')
   lyr = arcpy.MakeFeatureLayer_management(blocks, where_clause=clause)
   # This is to ensure small blocks don't get left out of rasterized surface.
   arcpy.PairwiseBuffer_analysis(lyr, 'tmp_buff', "10 Meters")
   print('Dissolving blocks...')
   arcpy.PairwiseDissolve_analysis('tmp_buff', out, multi_part="MULTI_PART")
   arcpy.CalculateField_management(out, 'pop', 1, field_type="SHORT")
   print('Created feature mask `' + out + '`.')

   with arcpy.EnvManager(snapRaster=snapMask, cellSize=snapMask, mask=snapMask, outputCoordinateSystem=snapMask, extent=snapMask):
      arcpy.PolygonToRaster_conversion(out, 'pop', 'tmp_rast', "MAXIMUM_AREA", cellsize=snapMask)
      arcpy.sa.ExtractByMask('tmp_rast', snapMask).save(out + '_rast')
   print('Created raster mask `' + out + '_rast' + '`.')

   # Clean up
   arcpy.DeleteField_management(out, 'pop')
   arcpy.BuildPyramids_management(out + '_rast')
   arcpy.Delete_management(['tmp_rast', 'tmp_buff'])

   return out + '_rast'


def makePopMask_custom(feats, featBoundary, inRaster, outMask):
   '''Makes a raster mask indicating where population CAN be allocated, from input features indicating where NOT
   to allocate population (e.g. water, parks). All area covered by features given to `feats` will become NoData
   in the final mask.

   feats = List of feature classes indicating exclusion features
   featBoundary = Feature class defining project domain. Will be used as the processing mask.
   inRaster = template raster
   outMask = output raster
   '''

   arcpy.env.outputCoordinateSystem = inRaster
   arcpy.env.snapRaster = inRaster
   arcpy.env.cellSize = inRaster
   arcpy.env.extent = inRaster
   arcpy.env.mask = featBoundary

   printMsg("Merging datasets...")
   arcpy.Merge_management(feats, 'popMask_feats')
   calcFld('popMask_feats', 'rast', '1', field_type="SHORT")
   lyr = arcpy.MakeFeatureLayer_management('popMask_feats')
   arcpy.SelectLayerByLocation_management(lyr, "INTERSECT", featBoundary)
   printMsg("Rasterizing features...")
   arcpy.PolygonToRaster_conversion(lyr, 'rast', 'popMask_rast0', cellsize=inRaster)
   printMsg("Creating raster mask...")
   arcpy.sa.SetNull(arcpy.sa.IsNull('popMask_rast0'), 1, "Value = 0").save(outMask)
   arcpy.BuildPyramids_management(outMask)

   return outMask


def main():

   # Set up variables
   arcpy.env.workspace = r'E:\projects\rec_model\rec_model_processing\input_recmodel.gdb'
   arcpy.env.overwriteOutput = True
   snap = r'L:\David\projects\RCL_processing\RCL_processing.gdb\SnapRaster_albers_wgs84'
   arcpy.env.outputCoordinateSystem = snap
   arcpy.env.snapRaster = snap
   arcpy.env.cellSize = snap
   arcpy.env.extent = snap

   # Deprecated: using census blocks instead
   # Make population mask. Features indicate exclusion areas for poplation. They will be NoData in the PopMask.
   # feats = [r'E:\projects\rec_model\rec_datasets\rec_datasets_working.gdb\NHD_AreaWaterbody_diss',
   #          r'E:\projects\rec_model\rec_datasets\rec_datasets_working.gdb\public_lands_final']
   # featBoundary = r'L:\David\projects\RCL_processing\RCL_processing.gdb\VA_Buff50mi_wgs84'
   # inRaster = r'E:\projects\OSM\OSM_RoadsProc.gdb\OSM_Roads_20210422_kdens'  # r'L:\David\projects\RCL_processing\Tiger_2020\roads_proc.gdb\Roads_kdens_250_noZero'
   # popMask = 'population_mask_raster'
   # makePopMask_custom(feats, featBoundary, inRaster, popMask)

   # Make population mask from census blocks (where population > 0)
   popMask = 'census_blocks_populated'
   blocks = r'L:\David\GIS_data\US_CENSUS_TIGER\Census_2010_block_pop\censusBlocks_2010.gdb\census_blocks'
   makePopMask_blocks(blocks, snap, popMask)

   # Make a buffered roads + populated census blocks mask. For use later as a Service Area clipping mask
   roadBuff = r'E:\projects\OSM\OSM_RoadsProc.gdb\OSM_Roads_20210422_qtrMileBuff'
   arcpy.PairwiseIntersect_analysis([popMask, roadBuff], popMask + '_roadClip')
   # make raster version (just combine the two existing raster versions; quicker than rasterizing features).
   arcpy.sa.CellStatistics([popMask + '_rast', roadBuff + '_rast'], "MAXIMUM", "NODATA").save(popMask + '_roadClip_rast')
   arcpy.BuildPyramids_management(popMask + '_roadClip_rast')

   # Make population density raster
   inBlocks = r'E:\projects\rec_model\rec_model_processing\input_recmodel.gdb\ACS_2015_2019_5yr_BG'  # r'H:\Working\ACS_2016\ACS_2016_5yr_BG.shp'
   fldPop = 'total_pop_clip'  # 'TotPop_clp'
   # inRoadDens = r'L:\David\projects\RCL_processing\Tiger_2020\roads_proc.gdb\Roads_kdens_250_noZero'  # r'H:\Working\RecMod\RecModProducts.gdb\Roads_kdens_250'
   inRoadDens = r'E:\projects\OSM\OSM_RoadsProc.gdb\OSM_Roads_20210422_kdens'
   outPop = r'E:\projects\rec_model\rec_model_processing\input_recmodel.gdb\distribPop_kdens_OSM_2021_blkMask'  # r'H:\Working\RecMod\RecModProducts.gdb\distribPop_kdens'
   tmpDir = r'D:\scratch\raster'  # r'H:\Working\TMP'

   # Specify function to run
   DistribPop_roadDens(inBlocks, fldPop, inRoadDens, outPop, tmpDir, popMask)

   # QA/QC: double-check that sums match reasonably:
   a = arcpy.RasterToNumPyArray(outPop, nodata_to_value=0)
   print('Raster sum of population: ' + str(a.sum()) + '.')
   print('Polygon sum of population: ' + str(sum([a[0] for a in arcpy.da.SearchCursor(inBlocks, fldPop)])) + '.')

if __name__ == '__main__':
   main()
