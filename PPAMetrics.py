"""
PPAMetrics
Created by: David Bucklin
Created on: 2021-01

Processes for adding impervious area percentages, available area, and available greenspace for PPAs.
"""

from Helper import *
from arcpro.Helper import *
from PrepRecDataset import PrepRecDataset


def addMetrics_accessAcres(feats, access_lyr, fld_prefix, access_dist=None, internal=False):

   fld = fld_prefix + '_acres'
   access_feats = feats + '_' + fld_prefix
   if access_dist is not None:
      if internal:
         print("Finding intersection of access features and " + os.path.basename(feats) + "...")
         arcpy.PairwiseIntersect_analysis([feats, access_lyr], 'tmp_internal')
         arcpy.CalculateField_management('tmp_internal', 'internalacc_id', '!FID_' + os.path.basename(feats) + '!', field_type="LONG")
         # access_lyr = arcpy.MakeFeatureLayer_management('tmp_internal')
         arcpy.PairwiseBuffer_analysis('tmp_internal', 'tmp_buff', access_dist, dissolve_option="LIST", dissolve_field='internalacc_id')
      else:
         print("Selecting access features within " + access_dist + " of " + os.path.basename(feats) + "...")
         arcpy.SelectLayerByLocation_management(access_lyr, "WITHIN_A_DISTANCE", feats, search_distance=access_dist)
         arcpy.PairwiseBuffer_analysis(access_lyr, 'tmp_buff', access_dist, dissolve_option="ALL")
      print('Creating access area feature class ' + access_feats + '...')
      arcpy.PairwiseIntersect_analysis([feats, 'tmp_buff'], access_feats)
      if internal:
         # Delete parts of buffers which are NOT in the intersecting PPA (e.g. extend into a neighboring PPA)
         lyr = arcpy.MakeFeatureLayer_management(access_feats)
         arcpy.SelectLayerByAttribute_management(lyr, "NEW_SELECTION", "FID_" + os.path.basename(feats) + " <> internalacc_id")
         arcpy.DeleteRows_management(lyr)
         del lyr
   else:
      print('Creating access area feature class ' + access_feats + '...')
      arcpy.PairwiseDissolve_analysis(access_lyr, 'access_area')
      arcpy.PairwiseIntersect_analysis([feats, 'access_area'], access_feats, join_attributes="ONLY_FID")
   print("Calculating access acres in field `" + fld + "`...")
   arcpy.CalculateField_management(access_feats, fld, '!Shape.area@ACRES!', field_type="FLOAT")
   arcpy.DeleteField_management(feats, fld)
   arcpy.JoinField_management(feats, "OBJECTID", access_feats, "FID_" + os.path.basename(feats), fld)
   arcpy.Delete_management(['tmp_buff'])
   return access_feats


def addMetrics_nlcd(feats, feats_id, raster, fld_prefix="imp", mask=None):
   """This function is a wrapper around ZonalStatisticsAsTable, allowing to set a mask just for the summary,
   and change the name of the summary field."""
   arcpy.env.cellSize = raster
   arcpy.env.snapRaster = raster

   exstFld = [a.name for a in arcpy.ListFields(feats)]
   print('Calculating zonal statistics...')
   if mask:
      envmask = arcpy.env.mask
      arcpy.env.mask = mask
      print("Using mask `" + mask + "`...")
   arcpy.sa.ZonalStatisticsAsTable(feats, feats_id, raster, 'tmp_zs', "DATA", "MEAN")
   print('Joining and calculating raster area/percentages...')
   calcFld('tmp_zs', fld_prefix + '_perc', "!MEAN!", field_type="FLOAT")
   if fld_prefix + '_perc' in exstFld:
      arcpy.DeleteField_management(feats, fld_prefix + '_perc')
   arcpy.JoinField_management(feats, feats_id, 'tmp_zs', feats_id, fld_prefix + '_perc')
   calc = '((!' + fld_prefix + '_perc! / 100) * !Shape_Area!) / 4046.856'
   calcFld(feats, fld_prefix + '_acres', calc, field_type="FLOAT")
   calc = '((1- (!' + fld_prefix + '_perc! / 100)) * !Shape_Area!) / 4046.856'
   calcFld(feats, 'not' + fld_prefix + '_acres', calc, field_type="FLOAT")
   # add percentage fields
   calc = '100 - !' + fld_prefix + '_perc!'
   calcFld(feats, 'not' + fld_prefix + '_perc', calc, field_type="FLOAT")
   # set mask back to original
   if mask:
      arcpy.env.mask = envmask

   return feats


def addMetrics_lc(feats, feats_id, lc, imp=['21', '22'], water=[]):
   # Summarizes impervious, non-impervious, and water area and percentage within polygons
   arcpy.env.cellSize = lc
   arcpy.env.snapRaster = lc

   print("Tabulating land covers...")
   arcpy.sa.TabulateArea(feats, feats_id, lc, "Value", "tmp_lc_tab", lc)

   # TODO: specific cover types?
   print("Calculating areas and percentages...")
   flds = [a.name for a in arcpy.ListFields("tmp_lc_tab") if a.name.startswith('VALUE_')]
   f_imp = [a for a in flds if a.endswith(tuple(imp))]
   f_notimp = [a for a in flds if not a.endswith(tuple(imp + water))]
   calc = '(!' + '! + !'.join(f_imp) + '!) / 4046.856'
   calcFld("tmp_lc_tab", "imp_acres", calc, field_type="FLOAT")
   calc = '(!' + '! + !'.join(f_notimp) + '!) / 4046.856'
   calcFld("tmp_lc_tab", "notimp_acres", calc, field_type="FLOAT")
   # add percentage fields
   calc = "(!imp_acres! / (!imp_acres! + !notimp_acres!)) * 100"
   calcFld("tmp_lc_tab", "imp_perc", calc, field_type="FLOAT")
   calc = "(!notimp_acres! / (!imp_acres! + !notimp_acres!)) * 100"
   calcFld("tmp_lc_tab", "notimp_perc", calc, field_type="FLOAT")
   fld_join = ["imp_acres", "imp_perc", "notimp_acres", "notimp_perc"]
   # add water fields
   if len(water) > 0:
      calc = '(!VALUE_' + '! + !VALUE_'.join(water) + '!) / 4046.856'
      calcFld("tmp_lc_tab", "water_acres", calc, field_type="FLOAT")
      calc = "(!water_acres! / (!imp_acres! + !notimp_acres! + !water_acres!)) * 100"
      calcFld("tmp_lc_tab", "water_perc", calc, field_type="FLOAT")
      fld_join + ["water_acres", "water_perc"]
   print('Joining fields...')
   arcpy.DeleteField_management(feats, fld_join)
   arcpy.JoinField_management(feats, feats_id, "tmp_lc_tab", feats_id, fld_join)

   return feats


# HEADER

# Geodatabase for recreation datasets
gdb = r'E:\projects\rec_model\rec_datasets\rec_datasets_working_2021.gdb'
roads0 = r'E:\projects\OSM\OSM_RoadsProc.gdb\OSM_Roads_20210422' # r'L:\David\projects\RCL_processing\Tiger_2020\roads_proc.gdb\all_subset'
# Base geodatabase (NHD_Merged.gdb) are layers including all states within 50-mile buffer.
nhd_flow = r'E:\projects\rec_model\rec_datasets\rec_datasets_working.gdb\NHD_Flowline'
nhd_areawtrb = r'E:\projects\rec_model\rec_datasets\rec_datasets_working.gdb\NHD_AreaWaterbody_diss'
nhd_wtrb = r'L:\David\GIS_data\NHD\NHD_Merged.gdb\NHDWaterbody'  # this can be used for lakes-only analyses
boundary = r'L:\David\projects\RCL_processing\RCL_processing.gdb\VA_Buff50mi_wgs84'

# land cover, impervious, canopy
# lc = r'L:\David\GIS_data\NLCD\nlcd_2016\nlcd_2016ed_LandCover_albers.gdb\lc_2016'
# lc = r'L:\David\GIS_data\VA_Landcover\mosaic\VA_landcover1m\va_landcover_1m.tif'
imperv = r'L:\David\GIS_data\NLCD\nlcd_2016\nlcd_2016ed_Impervious_albers.gdb\imperv_2016'
canopy = r'L:\David\GIS_data\NLCD\treecan2016.tif\treecan2016.tif'

# PPA dataset
publands_final = 'public_lands_final'
feats_id = 'group_id'

# Output GDB for prepped layers
prep_gdb = r'E:\projects\rec_model\rec_datasets\rec_datasets_v2021.gdb'

# environments
arcpy.env.workspace = gdb
arcpy.env.outputCoordinateSystem = publands_final
arcpy.env.overwriteOutput = True
arcpy.env.transferDomains = True

# END HEADER


### PPA attribution
# This section is for calculating various attributes of PPAs, including greenspace, available area, and available
# greenspace. The master access points should have been already generated (steps 1 and 2 in that script), so that
# those points can be used in the available area calculation.

print("Summarizing impervious surface in PPAs...")
feats = publands_final + '_imp'
arcpy.CopyFeatures_management(publands_final, feats)

# Add impervious and canopy metrics to parks
# addCoverMetrics(feats, feats_id, lc, imp=['21', '22'])  # impervious classes are 21/22 in VA Land Cover.
addMetrics_nlcd(feats, feats_id, imperv, fld_prefix="imp")
addMetrics_nlcd(feats, feats_id, canopy, fld_prefix="can")

# Join key fields to PPA layer
arcpy.JoinField_management(publands_final, feats_id, publands_final + '_imp', feats_id, ['notimp_acres', 'can_acres'])

## Available area

# ROADS-TIGER (deprecated:use OSM only)
# roads_all = r'L:\David\projects\RCL_processing\Tiger_2020\roads_proc.gdb\all_centerline'
# # For road access in public lands: exclude limited access, other highways, ramps, private drives, and internal census use classes
# acc_lyr = arcpy.MakeFeatureLayer_management(roads_all, where_clause="MTFCC NOT IN ('S1100', 'S1200', 'S1630', 'S1740', 'S1750')")
# addMetrics_accessAcres(publands_final, acc_lyr, "rdacc", "300 Feet", internal=True)

# OSM roads+trails data.
osm_all = r'E:\projects\OSM\OSM_RoadsProc.gdb\OSM_Roads_20210422'
acc_lyr = arcpy.MakeFeatureLayer_management(osm_all, where_clause="code NOT IN (5111, 5112, 5131, 5132)")  # only exclude motorway/trunk and their link roads
addMetrics_accessAcres(publands_final, osm_all, "osmacc", "300 Feet", internal=True)

# TRAILS
trails0 = r'E:\projects\rec_model\rec_datasets\rec_datasets_v2021.gdb\prep_VATrails_2021_20210317'
# Note: use = -1 are non-existent (e.g. proposed) trails.
acc_lyr = arcpy.MakeFeatureLayer_management(trails0, where_clause="use <> -1")
addMetrics_accessAcres(publands_final, acc_lyr, "trlacc", "300 Feet")

# ACCESS POINTS
accPts = r'E:\projects\rec_model\rec_datasets\rec_datasets_v2021.gdb\access_points'
# Note: Local park inventory excluded here, since they don't seem to represent actual access points, rather centroids of parks.
acc_lyr = arcpy.MakeFeatureLayer_management(accPts, where_clause="use = 1 AND src_table <> 'LocalParkInventory_2021_QC'")
addMetrics_accessAcres(publands_final, acc_lyr, "ptacc", "300 Feet")

print('Calculating available, non-impervious acres...')
# TOTAL ACCESSIBLE AREA (TRAILS+INTERNAL OSM+ACCESS POINTS). Uses already-created access features.
arcpy.Merge_management([publands_final + '_osmacc', publands_final + '_trlacc', publands_final + '_ptacc'], 'tmp_merge')
feats = addMetrics_accessAcres(publands_final, 'tmp_merge', fld_prefix="available")
arcpy.JoinField_management(feats, 'FID_' + publands_final, publands_final, 'OBJECTID', feats_id)
# coulddo: convert rdltrlacc to single-part?
addMetrics_nlcd(feats, feats_id, imperv, fld_prefix="impacc")
# join metric back to original PPAs
arcpy.JoinField_management(publands_final, feats_id, feats, feats_id, 'notimpacc_acres')
arcpy.AlterField_management(publands_final, 'notimpacc_acres', 'accgreen_acres', 'Available greenspace (acres)')

# Update those with NULL accgreen_acres. This could be because no access area exists, or PPA was too small to calculate zonal statistics.
lyr = arcpy.MakeFeatureLayer_management(publands_final)
arcpy.SelectLayerByAttribute_management(lyr, 'NEW_SELECTION', "accgreen_acres IS NULL")
arcpy.CalculateField_management(lyr, "accgreen_acres", "min(!notimp_acres!, 5)")
del lyr
# The remaining were calculated to have 0 non-impervious acres. These will be set to 0.
nullToZero(publands_final, 'accgreen_acres')

print('Making a layer with both accessible/non-accessible area...')
arcpy.Identity_analysis(publands_final, publands_final + '_available', 'tmp_access', "ONLY_FID")
arcpy.CalculateField_management('tmp_access', 'access', 'max(min(!FID_' + publands_final + '_available!, 1), 0)', field_type="SHORT")
ids = [str(a[0]) for a in arcpy.da.SearchCursor('tmp_access', [feats_id, 'access']) if a[1] == 1]
# update accgreen_acres for the in-accessible areas (access = 0), for those PPA with some accessible area
lyr = arcpy.MakeFeatureLayer_management('tmp_access', where_clause="access = 0 AND " + feats_id + " IN (" + ",".join(ids) + ")")
arcpy.CalculateField_management(lyr, 'accgreen_acres', '0')
del lyr
arcpy.PairwiseDissolve_analysis('tmp_access', publands_final + '_accessAreas', ['ppa_type', 'src_group_nm', 'src_group_type', 'group_id', 'access', 'available_acres', 'accgreen_acres'])
arcpy.CalculateField_management(publands_final + '_accessAreas', 'available_acres', '!available_acres! * !access!')
nullToZero(publands_final + '_accessAreas', 'available_acres')

# create prepped dataset (can do here, or in ArcPro Map after review).
prep = PrepRecDataset(publands_final, boundary, prep_gdb, ["Land access"], 'src_group_nm')
# Set join_score to acc_green_acres (default join_score is Shape_Area)
arcpy.CalculateField_management(prep, 'join_score', '!accgreen_acres!')


# clean up
arcpy.Delete_management(arcpy.ListFeatureClasses('tmp*'))
arcpy.Delete_management(arcpy.ListTables('tmp*'))
