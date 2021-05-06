"""
RecFeatures
Created by: David Bucklin
Created on: 2021-01

Processes for handling recreation feature datasets (NOT access points). Includes full workflow for PPAs, trails QA/QC.
"""

from Helper import *
from arcpro.Helper import *
from PrepRecDataset import PrepRecDataset
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


# Geodatabase for recreation datasets
gdb = r'E:\projects\rec_model\rec_datasets\rec_datasets_working_2021.gdb'
roads0 = r'E:\projects\OSM\OSM_RoadsProc.gdb\OSM_Roads_20210422'  # r'L:\David\projects\RCL_processing\Tiger_2020\roads_proc.gdb\all_subset'
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

# END HEADER


### Public lands
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
# State-specific information for VA. In VA, only want to add polygons from a specific source (TPL), likely not covered by the managed lands dataset

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
print("Merging datasets...")
arcpy.Merge_management([padus, mgd], publands, add_source=True)
print("Updating designation types")
arcpy.JoinField_management(publands, 'src_unit_type', dtypes, 'src_unit_type', 'ppa_type')
arcpy.Integrate_management(publands, "1 Meter")  # Decide: integrate, maybe Eliminate?
arcpy.CalculateField_management(publands, 'publands_fid', "!OBJECTID!", field_type="LONG")
lyr = arcpy.MakeFeatureLayer_management(publands)
for q in qs:
   print(q[0])
   arcpy.SelectLayerByAttribute_management(lyr, 'NEW_SELECTION', q[0])
   arcpy.CalculateField_management(lyr, 'ppa_type', q[1])
del lyr
print("Converting to single-part, then re-grouping if within group distance...")
arcpy.MultipartToSinglepart_management(publands, 'tmp_single')
SpatialCluster_GrpFld('tmp_single', "150 Feet", 'group_orig', 'publands_fid', chain=False)
flds = [a.name for a in arcpy.ListFields('tmp_single') if a.type != 'OID' and not a.name.startswith('Shape')]
arcpy.PairwiseDissolve_analysis('tmp_single', publands + '_singlepart', flds)
calcFld(publands + '_singlepart', "src_unit_acres", '!shape.area@ACRES!', field_type="DOUBLE")  # calculate area of single parts. Used to inform naming of final dissolved polygons
# Flatten data, selecting smallest original polygon for attributes (retains the most information)
print("Making flat public lands dataset...")
arcpy.Union_analysis(publands + '_singlepart', 'tmp_union')
arcpy.Sort_management('tmp_union', publands + '_flat', [['ppa_type', 'Ascending'], ['src_unit_acres', 'Ascending']])
arcpy.DeleteIdentical_management(publands + '_flat', fields="Shape")
calcFld(publands + '_flat', 'flat_id', '!OBJECTID!', field_type="LONG")
print("Adding group_id to flat dataset...")
group_dist = "0.5 Meters"
SpatialCluster_GrpFld(publands + '_flat', group_dist, 'group_id', "ppa_type")
# Get group information (attributes of the largest PPA in group)
arcpy.Statistics_analysis(publands + '_flat', 'tmp_group_flat_id', [["flat_id", "MAX"]], "group_id")
arcpy.JoinField_management('tmp_group_flat_id', "MAX_flat_id", publands + '_flat', "flat_id", ['src_unit_nm', 'src_unit_type'])
arcpy.AlterField_management('tmp_group_flat_id', "src_unit_nm", "src_group_nm", new_field_alias="PPA group name")
arcpy.AlterField_management('tmp_group_flat_id', "src_unit_type", "src_group_type", new_field_alias="PPA class")
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
print("Making final dataset, dissolved to groups...")
lyr = arcpy.MakeFeatureLayer_management(publands + "_flat_water", where_clause="water = 0")
arcpy.PairwiseDissolve_analysis(lyr, publands + '_final', ['group_id', 'ppa_type'])
# Join name and type from the largest polygon in the group to the final dataset.
arcpy.JoinField_management(publands + '_final', 'group_id', 'tmp_group_flat_id', 'group_id', ['src_group_nm', 'src_group_type'])
calcFld(publands + '_final', "acres", '!shape.area@ACRES!', field_type="DOUBLE")

# END PPAs

# clean up
arcpy.Delete_management(arcpy.ListFeatureClasses('tmp*'))
arcpy.Delete_management(arcpy.ListTables('tmp*'))


### Process trails data
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
rd_lyr = arcpy.MakeFeatureLayer_management(roads0, where_clause="code in (5111, 5112, 5113, 5114, 5115, 5121, 5122, 5123, 5131, 5132, 5133, 5134, 5135, 5141, 5142, 5143, 5144, 5145, 5146, 5147)")
                                           # where_clause="mtfcc <> 'S1500'")  # TIGER: exclude 4WD road/trails for this
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
PrepRecDataset(trails_group, boundary, r'E:\projects\rec_model\rec_datasets\rec_datasets_v2021.gdb', ['Trail access (non-water)'])


### Fishing lakes
# Select waterbody features for (point) lake datasets, using closest waterbody within a distance
trout_lake = selectRecFeatures('Stocked_Trout_Lakes', nhd_wtrb, "0.25 Miles")
fish_lake = selectRecFeatures('Lake_Centroids', nhd_wtrb, "0.25 Miles")


# clean up
arcpy.Delete_management(arcpy.ListFeatureClasses('tmp*'))
arcpy.Delete_management(arcpy.ListTables('tmp*'))

# end
