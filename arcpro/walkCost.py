# Walking cost distance to nearest local park
# Considers all parks at once (not individual service areas)
#

from arcpro.Helper import *

# set up input data
facil_date = 't_tlnd_20190214'  # table name for features (public lands, trails) or points (aquatic access points)
accFeat = r'E:\projects\rec_model\rec_model_processing\access_pts.gdb\access_' + facil_date  # points
# accFeat = r'E:\projects\rec_model\rec_model_processing\rec_source_datasets.gdb\' + facil_date  # features
maxCost = None
costRastWalk = r'E:\RCL_cost_surfaces\Tiger_2018\cost_surfaces.gdb\costSurf_walk'
outRast = r'E:\arcpro_wd\rec_model_temp\serviceAreas_modelupdate_Feb2019\local_access_walkNearest.gdb\walkNearest_access_' + facil_date

# run cost distance
arcpy.env.workspace = r'E:\proc\scratch.gdb'
arcpy.env.snapRaster = costRastWalk
arcpy.env.cellSize = costRastWalk
arcpy.env.extent = costRastWalk
arcpy.env.overwriteOutput = True
arcpy.env.outputCoordinateSystem = costRastWalk

cd = arcpy.sa.CostDistance(accFeat, costRastWalk, maxCost)
# cd = outRast + '_orig'

# get highways/ramps areas
Con(IsNull(cd), 0.01233, None).save("costfill")

# applies value of nearest cell value (int) + 1
CostAllocation(Int(Raster(cd) + 1), in_cost_raster="costfill").save("costalloc")

# final raster, adds filled in values
Con(IsNull(cd), Float("costalloc"), cd).save(outRast)  # adds filled-in allocated values to no-data areas

# end
