"""
RecFeatures
Created by: David Bucklin
Created on: 2021-01

working: Processes for handling recreation feature datasets (NOT access points).
"""


from Helper import *
from arcpro.Helper import *
from PrepRecDataset import PrepRecDataset
import os
import time
import arcpy
master_template = os.path.join(os.getcwd(), "data", "templates.gdb", "template_access")


def selectRecFeatures(pts, feats, join_dist):

   out = os.path.basename(pts) + '_feat' + os.path.basename(feats)
   feat_fld = [a.name for a in arcpy.ListFields(feats) if a.type != 'OID' and not a.name.startswith('Shape')]
   feat_lyr = arcpy.MakeFeatureLayer_management(feats)
   arcpy.SelectLayerByLocation_management(feat_lyr, "WITHIN_A_DISTANCE", pts, join_dist)
   arcpy.CopyFeatures_management(feat_lyr, 'tmp_recfeat')
   del feat_lyr
   calcFld('tmp_recfeat', 'FEAT_FID', "!OBJECTID!", field_type="LONG")
   arcpy.CopyFeatures_management('tmp_recfeat', 'tmp_recfeat_copy')
   if len(feat_fld) > 0:
      arcpy.DeleteField_management('tmp_recfeat', feat_fld)
   arcpy.SpatialJoin_analysis(pts, 'tmp_recfeat', 'tmp_pt1', "JOIN_ONE_TO_ONE", "KEEP_ALL",
                              match_option="CLOSEST", search_radius=join_dist, distance_field_name="join_dist")
   feat_lyr = arcpy.MakeFeatureLayer_management('tmp_recfeat_copy')
   arcpy.AddJoin_management(feat_lyr, 'FEAT_FID', 'tmp_pt1', 'FEAT_FID', 'KEEP_COMMON')
   arcpy.CopyFeatures_management(feat_lyr, out)
   del feat_lyr
   arcpy.Delete_management(arcpy.ListFeatureClasses("tmp_*"))

   return out


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
   return feats


def addMetrics_nlcd(feats, feats_id, raster, fld_prefix="imp", mask=None):
   """This function is a wrapper around ZonalStatisticsAsTable, allowing to set a mask just for the summary,
   and change the name of the summary field."""
   arcpy.env.cellSize = raster
   arcpy.env.snapRaster = raster

   print('Calculating zonal statistics...')
   if mask:
      envmask = arcpy.env.mask
      arcpy.env.mask = mask
      print("Using mask `" + mask + "`...")
   arcpy.sa.ZonalStatisticsAsTable(feats, feats_id, raster, 'tmp_zs', "DATA", "MEAN")
   print('Joining and calculating raster area/percentages...')
   calcFld('tmp_zs', fld_prefix + '_perc', "!MEAN!", field_type="FLOAT")
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


# Geodatabase for recreation datasets
gdb = r'E:\projects\rec_model\rec_datasets\rec_datasets_working.gdb'
roads0 = r'L:\David\projects\RCL_processing\Tiger_2020\roads_proc.gdb\all_subset'
# Base geodatabase (NHD_Merged.gdb) are layers including all states within 50-mile buffer.
nhd_flow = r'E:\projects\rec_model\rec_datasets\rec_datasets_working.gdb\NHD_Flowline'
nhd_areawtrb = r'E:\projects\rec_model\rec_datasets\rec_datasets_working.gdb\NHD_AreaWaterbody_diss'
nhd_wtrb = r'L:\David\GIS_data\NHD\NHD_Merged.gdb\NHDWaterbody'  # this can be used for lakes-only analyses
boundary = r'L:\David\projects\RCL_processing\RCL_processing.gdb\VA_Buff50mi_wgs84'

# environments
arcpy.env.workspace = gdb
arcpy.env.outputCoordinateSystem = master_template
arcpy.env.overwriteOutput = True
arcpy.env.transferDomains = True

### Fishing lakes
# Select waterbody features for (point) lake datasets, using closest waterbody within a distance
# trout_lake = selectRecFeatures('Stocked_Trout_Lakes', nhd_wtrb, "0.25 Miles")
# fish_lake = selectRecFeatures('Lake_Centroids', nhd_wtrb, "0.25 Miles")

### Public lands
# working: Public lands
publands = 'public_lands'  # base name for layer to create

# DCR managed lands (from Dave Boyd)
# https://vdcr.maps.arcgis.com/home/item.html?id=88e2e381ec634b3aabb7cbe43480d72f
mgd0 = r'E:\projects\rec_model\rec_datasets\DCR_PRR\DCR_rec_data.gdb\Public_Access_Lands_2021'
q_mgd = "Access IN ('OPEN', 'OPEN WITH RESTRICTIONS') AND MATYPE NOT IN ('Boy Scout Reservation', 'Military Installation') AND TRACT NOT IN ('water', 'Buggs Island Lake')"
# q_mgd = "Access <> 'CLOSED' AND MATYPE NOT IN ('Boy Scout Reservation', 'Military Installation') AND TRACT NOT IN ('water', 'Buggs Island Lake')"

# PAD-US
# Query selects open or restricted access polygons. Select by source which might not be in the managed lands dataset
padus0 = r'L:\David\GIS_data\PAD\PAD_US2_1_GDB\PAD_US2_1.gdb\PADUS2_1Fee'
q_padus = "Pub_Access IN ('OA', 'RA') AND Des_Tp <> 'MIL' AND (State_Nm <> 'VA' OR (Agg_Src = 'TPL_PADUS2_1_PADUS_DataDelivery_gdb' AND State_Nm = 'VA'))"
      # AND (Agg_Src = 'TPL_PADUS2_1_PADUS_DataDelivery_gdb' AND State_Nm = 'VA')" # VA-only
# Second line is state-specific information. In VA, only want to add polygons from a specific source (TPL), likely not covered by the managed lands dataset

# standardized access field
cb_acc = '''def fn(acc):
   if acc.lower() == 'open' or acc.lower() == 'oa':
      return '1: Open access'
   else:
      return '2: Access with restrictions'
'''
dtypes = arcpy.ExcelToTable_conversion(r'E:\projects\rec_model\R\managed_lands_Des_Tp_grouped_review.xlsx', 'tmp_dtypes')
# TODO: queries for adjusting certain types to a non-default ppa_type. Access type also used (anything <OPEN access resets value to a 2).
qs = [["src_unit_nm LIKE '%School%' AND NOT src_unit_nm LIKE '%Park'", 2],
      ["(src_unit_nm LIKE '%Battlefield%' AND src_unit_type = 'National Park') OR src_unit_nm LIKE '%Military Park%'", 2],
      ["src_unit_access = '2: Access with restrictions'", 2]]
# above: contains school but doesn't end in park (i.e. would not select 'School Park', but would select 'Park School')

# merge public lands from padus and managed lands
print("Selecting public lands...")
pad_lyr = arcpy.MakeFeatureLayer_management(padus0)
arcpy.SelectLayerByLocation_management(pad_lyr, "INTERSECT", boundary)
arcpy.SelectLayerByAttribute_management(pad_lyr, "SUBSET_SELECTION", q_padus)
arcpy.FeatureClassToFeatureClass_conversion(pad_lyr, arcpy.env.workspace, "tmp_pad")
calcFld("tmp_pad", 'src_unit_type', '!Des_Tp!', field_type="TEXT")  # need to do this here to get domain desc.
# Clip is necessary since there are some large multi-polygons in PADUS
padus = arcpy.Clip_analysis("tmp_pad", boundary, os.path.basename(padus0) + '_public_lands')
calcFld(padus, 'src_unit_nm', '!Unit_Nm!', field_type="TEXT")
calcFld(padus, 'src_unit_access', 'fn(!Pub_Access!)', code_block=cb_acc, field_type="TEXT")
# VA Managed lands
mgd = arcpy.Select_analysis(mgd0, os.path.basename(mgd0) + '_public_lands', q_mgd)
calcFld(mgd, 'src_unit_nm', '!LABEL!', field_type="TEXT")
calcFld(mgd, 'src_unit_access', 'fn(!Access!)', code_block=cb_acc, field_type="TEXT")
calcFld(mgd, 'src_unit_type', '!MATYPE!', field_type="TEXT")
# Merge datasets
arcpy.Merge_management([padus, mgd], publands, add_source=True)
# arcpy.CopyFeatures_management(mgd, publands)
arcpy.JoinField_management(publands, 'src_unit_type', dtypes, 'src_unit_type', 'ppa_type')
arcpy.Integrate_management(publands, "1 Meter")  # Decide: integrate, maybe Eliminate?
arcpy.CalculateField_management(publands, 'publands_fid', "!OBJECTID!", field_type="LONG")
# update unique types (e.g. schools, battlefields, etc)
lyr = arcpy.MakeFeatureLayer_management(publands)
# decide: other adjustments?
for q in qs:
   print(q[0])
   arcpy.SelectLayerByAttribute_management(lyr, 'NEW_SELECTION', q[0])
   arcpy.CalculateField_management(lyr, 'ppa_type', q[1])
del lyr
arcpy.MultipartToSinglepart_management(publands, 'tmp_single')
# Re-group by original ID, if within group distance
SpatialCluster_GrpFld('tmp_single', "150 Feet", 'group_orig', 'publands_fid', chain=False)
flds = [a.name for a in arcpy.ListFields('tmp_single') if a.type != 'OID' and not a.name.startswith('Shape')]
arcpy.PairwiseDissolve_analysis('tmp_single', publands + '_singlepart', flds)
calcFld(publands + '_singlepart', "src_unit_acres", '!shape.area@ACRES!', field_type="DOUBLE")  # calculate area of single parts. Used to inform naming of final dissolved polygons
# Flatten data, selecting smallest original polygon for attributes
print("Making flat public lands dataset...")
arcpy.Union_analysis(publands + '_singlepart', 'tmp_union')
arcpy.Sort_management('tmp_union', publands + '_flat', [['ppa_type', 'Ascending'], ['src_unit_acres', 'Ascending']])  # sort by PPA type, then acres
arcpy.DeleteIdentical_management(publands + '_flat', fields="Shape")
calcFld(publands + '_flat', 'flat_id', '!OBJECTID!', field_type="LONG")
flds = [a.name for a in arcpy.ListFields(publands + '_flat') if a.type != 'OID' and not a.name.startswith('Shape')]
# Add group id to polygons (basically just dissolve, but using 1m group distance).
# Decide: group distance?
group_dist = "0.5 Meters"
print("Adding group_id to flat dataset...")
SpatialCluster_GrpFld(publands + '_flat', group_dist, 'group_id', "ppa_type")
# Get group information, to join to final dataset
arcpy.Statistics_analysis(publands + '_flat', 'tmp_group_flat_id', [["flat_id", "MAX"]], "group_id")  # will return the largest polygon's (flat_id) in the group (by group_id)
arcpy.JoinField_management('tmp_group_flat_id', "MAX_flat_id", publands + '_flat', "flat_id", ['src_unit_nm', 'src_unit_type'])
arcpy.AlterField_management('tmp_group_flat_id', "src_unit_nm", "src_group_nm", new_field_alias="PPA group name")
arcpy.AlterField_management('tmp_group_flat_id', "src_unit_type", "src_group_type", new_field_alias="PPA class")

# Identity with NHD water areas
print("Identifying water areas...")
arcpy.Identity_analysis(publands + '_flat', nhd_areawtrb, 'tmp_water')
cb = '''def fn(fld):
   if fld == -1:
      return 0
   else:
      return 1'''
calcFld('tmp_water', 'water', "fn(!FID_" + os.path.basename(nhd_areawtrb) + "!)", code_block=cb, field_type="SHORT")
arcpy.PairwiseDissolve_analysis('tmp_water', publands + "_flat_water",
                                ['src_unit_nm', 'src_unit_access', 'water', 'group_id', 'ppa_type'])

# make summary table with group and group complex name
print("Making final dataset, dissolved to groups...")
# make group-dissolved layer for model
lyr = arcpy.MakeFeatureLayer_management(publands + "_flat_water", where_clause="water = 0")
arcpy.PairwiseDissolve_analysis(lyr, publands + '_final', ['group_id', 'ppa_type'])
# Join name and type from the largest polygon in the group to the final dataset.
arcpy.JoinField_management(publands + '_final', 'group_id', 'tmp_group_flat_id', 'group_id', ['src_group_nm', 'src_group_type'])
calcFld(publands + '_final', "acres", '!shape.area@ACRES!', field_type="DOUBLE")

# clean up
arcpy.Delete_management(arcpy.ListFeatureClasses('tmp*'))
arcpy.Delete_management(arcpy.ListTables('tmp*'))

###

print("Summarizing impervious surface in PPAs...")
feats = publands + '_final_imp'
arcpy.CopyFeatures_management(publands + '_final', feats)
# feats = 'public_lands_final_SEVA'
feats_id = 'group_id'
# lc = r'L:\David\GIS_data\NLCD\nlcd_2016\nlcd_2016ed_LandCover_albers.gdb\lc_2016'
lc = r'L:\David\GIS_data\VA_Landcover\mosaic\VA_landcover1m\va_landcover_1m.tif'
imperv = r'L:\David\GIS_data\NLCD\nlcd_2016\nlcd_2016ed_Impervious_albers.gdb\imperv_2016'
canopy = r'L:\David\GIS_data\NLCD\treecan2016.tif\treecan2016.tif'


# TESTING ONLY
# arcpy.env.extent = feats

# Add impervious metrics to parks
# addCoverMetrics(feats, feats_id, lc, imp=['21', '22'])  # impervious classes are 21/22 in VA Land Cover.
addMetrics_nlcd(feats, feats_id, imperv, fld_prefix="imp")
addMetrics_nlcd(feats, feats_id, canopy, fld_prefix="can")
# Join fields from imp layer
arcpy.JoinField_management(publands + '_final', feats_id, publands + '_final_imp', feats_id, ['notimp_acres', 'can_acres'])

# coulddo: classification based on impervious/non-impervious area.
# cb = '''def fn(ia, ip, na, np):
#    if ip > 5 or (ip > 1 and ia > 5):
#       if na > 20 and na + ia > 30:
#          return 'Open space/Developed mix PPA'
#       else:
#          return 'Developed PPA'
#    else:
#       if na > 20 and na + ia > 30:
#          return 'Open space or natural area PPA'
#       else:
#          return 'Small open space PPA'
# '''
# calc = 'fn(!imp_acres!, !imp_perc!, !notimp_acres!, !notimp_perc!)'
# calcFld(feats, 'ppa_class', calc, code_block=cb)
# # non-impervious cover
# cb = '''def fn(na):
#    if na is None or na < 5:
#       return '0 - 5 green acres'
#    elif na < 10:
#       return '5 - 10 green acres'
#    elif na < 20:
#       return '10 - 20 green acres'
#    elif na < 50:
#       return '20 - 50 green acres'
#    elif na < 100:
#       return '50 - 100 green acres'
#    elif na < 500:
#       return '100 - 500 green acres'
#    elif na < 1000:
#       return '500 - 1000 green acres'
#    else:
#       return '1000+ green acres'
# '''
# calc = 'fn(!notimp_acres!)'
# calcFld(feats, 'cover_class', calc, code_block=cb)

###

# Process trails data
trails0 = r'E:\projects\rec_model\rec_datasets\rec_datasets_v2021.gdb\prep_VATrails_2021_20210317'
trails_final = trails0 + '_final'
'''
Trail_Type: For use in model. Used to set 'use' column.
USE = 0
('Road shoulder', 'Unpaved Road',  'Shoulder', 'Road sharrow', 'UnpavedRoad', 'road sharrow', 'Sidewalk', 'Sharrow', 'On-road bike lane', 'Striped Bike lane', 'Protected bike lane', 'Buffered Bike Lane', 'Cart Path', 'Cycle Track', 'Bike Blvd',  'Bike lane', 'Bridge')
USE = 1
('8-14 foot Shared use Path', 'Accessible Route','4-8 foot path', 'Bike+Ped',  'Other', 'Interpretive', '8-14 foot Shared use path', 'Path', 'Paved', 'Interpretive trail', '1-4 foot path',  '<Null>', 'RiparianTrail', 'Multi-use', None, '8-14 foor Shared use Path', ' ', 'Singletrack', 'Track', 'Accessible',  '1-4 foot Shared use Path', 'SharedUse', 'Boardwalk', 'Protected land', 'Single', 'Other type or unknown')
'''

# 1. Identify trails on/directly adjacent to auto roads (within 100 feet (30.5 meters) at all points along trail feature)
trl_lyr = arcpy.MakeFeatureLayer_management(trails0, where_clause='use <> -1')
rd_lyr = arcpy.MakeFeatureLayer_management(roads0, where_clause="mtfcc <> 'S1500'")  # exclude 4WD road/trails for this
arcpy.SelectLayerByLocation_management(trl_lyr, 'WITHIN_A_DISTANCE', rd_lyr, "30.5 Meters")
arcpy.GeneratePointsAlongLines_management(trl_lyr, 'trl_pts', 'DISTANCE', Distance='100 meters', Include_End_Points="END_POINTS")
arcpy.GetCount_management('trl_pts')
arcpy.Near_analysis('trl_pts', rd_lyr, "30.5 Meters")
arcpy.Statistics_analysis('trl_pts', 'trl_pts_rd', [["NEAR_DIST", "MAX"], ["NEAR_DIST", "MIN"]], "ORIG_FID")
# IDs of trails with furthest point from road < 100 feet (those which have points with near dist = -1)
ids = [str(a[0]) for a in arcpy.da.SearchCursor('trl_pts_rd', ['ORIG_FID', "MAX_NEAR_DIST", "MIN_NEAR_DIST"]) if a[2] != -1]
# Output table of likely on road trails
arcpy.TableSelect_analysis('trl_pts_rd', 'trl_likely_road', "ORIG_FID IN (" + ','.join(ids) + ")")
# Update master trails layer
arcpy.SelectLayerByAttribute_management(trl_lyr, "NEW_SELECTION", "OBJECTID IN (" + ','.join(ids) + ")")
arcpy.CalculateField_management(trl_lyr, "on_road", "1", field_type="SHORT")
arcpy.CalculateField_management(trl_lyr, "use", "0")
arcpy.CalculateField_management(trl_lyr, "use_why", "'road-adjacent segment'")
del trl_lyr, rd_lyr

# 2. Identify exact duplicates to set use = 0
trl_lyr = arcpy.MakeFeatureLayer_management(trails0, where_clause='use <> -1')
arcpy.FindIdentical_management(trl_lyr, 'trl_dup', 'Shape')
arcpy.JoinField_management('trl_dup', 'IN_FID', trails0, 'OBJECTID', 'use')
arcpy.Statistics_analysis('trl_dup', 'trl_dup_use', [["use", "MIN"], ["IN_FID", "MIN"]], "FEAT_SEQ")
arcpy.JoinField_management('trl_dup', 'FEAT_SEQ', 'trl_dup_use', 'FEAT_SEQ', ['MIN_use', 'MIN_IN_FID'])
# find in_fid where in_fid != min_in_fid. These should be assigned as duplicates.
ids = [str(a[0]) for a in arcpy.da.SearchCursor('trl_dup', ['IN_FID', 'MIN_IN_FID', 'use', 'MIN_use']) if a[0] != a[1]]
arcpy.CopyFeatures_management(trails0, 'trails_dup')
arcpy.SelectLayerByAttribute_management(trl_lyr, "NEW_SELECTION", "OBJECTID IN (" + ','.join(ids) + ")")
arcpy.CalculateField_management(trl_lyr, 'duplicate', "'duplicate'", field_type="TEXT")
arcpy.CalculateField_management(trl_lyr, 'use', '0')
del trl_lyr

# 3a. Create final layer with only use=1 trails (singlepart)
trl_lyr = arcpy.MakeFeatureLayer_management(trails0, where_clause='use = 1')
arcpy.MultipartToSinglepart_management(trl_lyr, 'tmp_trl_sing')
arcpy.Integrate_management('tmp_trl_sing', "1 Meter")
arcpy.CountOverlappingFeatures_analysis('tmp_trl_sing', 'tmp_trl_sng_over')
arcpy.SpatialJoin_analysis('tmp_trl_sng_over', 'tmp_trl_sing', 'tmp_trl_sj', "JOIN_ONE_TO_MANY", match_option="WITHIN")
arcpy.Sort_management('tmp_trl_sj', trails_final, [["join_score", "DESCENDING"]])
arcpy.DeleteIdentical_management(trails_final, "TARGET_FID")
arcpy.GetCount_management(trails_final)
arcpy.CalculateField_management(trails_final, 'join_score', '!Shape.length@MILES!')
# 3b. Group into networks
trails_group = os.path.basename(trails_final).replace('prep_', '') + '_group'
SpatialCluster_GrpFld(trails_final, '150 Feet', 'group_id', chain=False)
arcpy.PairwiseDissolve_analysis(trails_final, trails_group, 'group_id')
PrepRecDataset(trails_group, boundary, r'E:\projects\rec_model\rec_datasets\rec_datasets_v2021.gdb', ['t_trl'])

# clean up
arcpy.Delete_management(arcpy.ListFeatureClasses('tmp*'))
arcpy.Delete_management(arcpy.ListTables('tmp*'))

###

# Public lands, accessible area
publands_final = publands + '_final'
feats_id = 'group_id'

# Calculate accessible area (ROADS)
roads_all = r'L:\David\projects\RCL_processing\Tiger_2020\roads_proc.gdb\all_centerline'
# For road access in public lands: exclude limited access, other highways, ramps, private drives, and internal census use classes
acc_lyr = arcpy.MakeFeatureLayer_management(roads_all, where_clause="MTFCC NOT IN ('S1100', 'S1200', 'S1630', 'S1740', 'S1750')")
addMetrics_accessAcres(publands_final, acc_lyr, "rdacc", "300 Feet", internal=True)

# OSM minor roads+trails data. These are likely to include roads/paths not in Tiger
osm_all = r'E:\projects\OSM\VA_50mile_20210329.gdb\VA_50mile_osm_line_nonstandard'
addMetrics_accessAcres(publands_final, osm_all, "osmacc", "300 Feet", internal=True)

# Calculate accessible area (TRAILS)
trails0 = r'E:\projects\rec_model\rec_datasets\rec_datasets_v2021.gdb\prep_VATrails_2021_20210317'
# Note: use = -1 are non-existent (proposed) trails, so are the only ones excluded here.
acc_lyr = arcpy.MakeFeatureLayer_management(trails0, where_clause="use <> -1")
addMetrics_accessAcres(publands_final, acc_lyr, "trlacc", "300 Feet")

# Calculate accessible area (ACCESS POINTS)
accPts = r'E:\projects\rec_model\rec_datasets\rec_datasets_v2021.gdb\access_points'
acc_lyr = arcpy.MakeFeatureLayer_management(accPts, where_clause="use = 1 AND src_table <> 'LocalParkInventory_2021_QC'")
addMetrics_accessAcres(publands_final, acc_lyr, "ptacc", "300 Feet")

# Calculate accessible area (TRAILS+INTERNAL TIGER+INTERNAL OSM+ACCESS POINTS). Uses already-created access features.
# arcpy.Merge_management([publands_final + '_rdacc', publands_final + '_trlacc', publands_final + '_ptacc'], 'tmp_merge')
arcpy.Merge_management([publands_final + '_rdacc', publands_final + '_osmacc', publands_final + '_trlacc', publands_final + '_ptacc'], 'tmp_merge')
addMetrics_accessAcres(publands_final, 'tmp_merge', "rdtrlacc")

print('Calculating accessible non-impervious acres...')
imperv = r'L:\David\GIS_data\NLCD\nlcd_2016\nlcd_2016ed_Impervious_albers.gdb\imperv_2016'
feats = publands_final + '_rdtrlacc'
# join to get group_id field and other attributes from PPAs.
arcpy.JoinField_management(feats, 'FID_' + publands_final, publands_final, 'OBJECTID', ['group_id'])
# coulddo: convert rdltrlacc to single-part?
addMetrics_nlcd(feats, "group_id", imperv, fld_prefix="impacc")
# join metric back to original PPAs
arcpy.DeleteField_management(publands_final, ['notimpacc_acres'])
arcpy.JoinField_management(publands_final, feats_id, feats, feats_id, ['notimpacc_acres'])
arcpy.AlterField_management(publands_final, 'notimpacc_acres', 'accgreen_acres', 'Accessible greenspace (acres)')

# update those with no non-imp access area (this could be because no access area exists, or it was too small to calculate zonal statistics).
lyr = arcpy.MakeFeatureLayer_management(publands_final)
arcpy.SelectLayerByAttribute_management(lyr, 'NEW_SELECTION', "accgreen_acres IS NULL")
arcpy.CalculateField_management(lyr, "accgreen_acres", "min(!notimp_acres!, 5)")
del lyr
# The remaining were calculated to have 0 non-impervious acres. These will be set to 0.
nullToZero(publands_final, 'accgreen_acres')

print('Making a layer with both accessible/non-accessible area...')
arcpy.Identity_analysis(publands_final, publands_final + '_rdtrlacc', 'tmp_access', "ONLY_FID")
arcpy.CalculateField_management('tmp_access', 'access', 'max(min(!FID_' + publands_final + '_rdtrlacc!, 1), 0)', field_type="SHORT")
ids = [str(a[0]) for a in arcpy.da.SearchCursor('tmp_access', [feats_id, 'access']) if a[1] == 1]
# update non-accessible areas=0 for PPA with some accessible area
lyr = arcpy.MakeFeatureLayer_management('tmp_access', where_clause="access = 0 AND " + feats_id + " IN (" + ",".join(ids) + ")")
arcpy.CalculateField_management(lyr, 'accgreen_acres', '0')
del lyr
arcpy.CopyFeatures_management(publands_final + '_accessAreas', publands_final + '_accessAreas_old')
arcpy.PairwiseDissolve_analysis('tmp_access', publands_final + '_accessAreas', ['ppa_type', 'src_group_nm', 'src_group_type', 'group_id', 'access', 'rdtrlacc_acres', 'accgreen_acres'])
arcpy.CalculateField_management(publands_final + '_accessAreas', 'rdtrlacc_acres', '!rdtrlacc_acres! * !access!')
nullToZero(publands_final + '_accessAreas', 'rdtrlacc_acres')


# clean up
arcpy.Delete_management(arcpy.ListFeatureClasses('tmp*'))
arcpy.Delete_management(arcpy.ListTables('tmp*'))

# end
