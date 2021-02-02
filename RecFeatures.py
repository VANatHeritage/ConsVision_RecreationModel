'''
RecFeatures
Created by: David Bucklin
Created on: 2021-01

Processes for handling recreation feature datasets (NOT access points).

TODO:
'''


from Helper import *
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
   print('Joining and calculation rasterious area/percentages...')
   calcFld('tmp_zs', fld_prefix + '_perc', "!MEAN!", field_type="FLOAT")
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
   arcpy.JoinField_management(feats, feats_id, "tmp_lc_tab", feats_id, fld_join)

   return feats


# working geodatabase for recreation datasets
gdb = r'E:\projects\rec_model\rec_datasets\rec_datasets_working.gdb'
roads0 = r'L:\David\projects\RCL_processing\Tiger_2019\roads_proc.gdb\all_subset'
roads = arcpy.MakeFeatureLayer_management(roads0)  #, where_clause="mtfcc NOT IN ('S1710','S1720','S1750')")
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
trout_lake = selectRecFeatures('Stocked_Trout_Lakes', nhd_wtrb, "0.25 Miles")
fish_lake = selectRecFeatures('Lake_Centroids', nhd_wtrb, "0.25 Miles")


### Public lands
# working: Public lands
publands = 'public_lands'  # base name for layer to create

# https://vdcr.maps.arcgis.com/home/item.html?id=88e2e381ec634b3aabb7cbe43480d72f
# DCR managed lands (from Dave Boyd)
mgd0 = r'E:\projects\rec_model\rec_datasets\DCR_PRR\DCR_rec_data.gdb\Public_Access_Lands_2021'
q_mgd = "Access <> 'CLOSED' AND MATYPE NOT IN ('Boy Scout Reservation', 'Military Installation')"
#  previously used (until Dave Boyd updated data): OR (PUBACCESS = 'unknown' And MATYPE IN ('NPS Holding', 'USFS Holding'))) "

# PAD-US
# Query selects open or restricted access polygons. Those with a DCR source are excluded in favor of the managed lands dataset
padus0 = r'L:\David\GIS_data\PAD\PAD_US2_1_GDB\PAD_US2_1.gdb\PADUS2_1Fee'
q_padus = "Pub_Access IN ('OA', 'RA') AND Des_Tp <> 'MIL' " \
          "AND GIS_Src NOT IN ('http://www.dcr.virginia.gov/natural_heritage/cldownload.shtml', 'VADCR_conslands_2017', 'conslands_dd83')"
          #"AND State_Nm = 'VA' " \ Decide: use lands outside VA
# standardized access field
cb_acc = '''def fn(acc):
   if acc.lower() == 'open' or acc.lower() == 'oa':
      return '1: Open access'
   else:
      return '2: Access with restrictions'
'''
dtypes = arcpy.ExcelToTable_conversion(r'E:\projects\rec_model\R\managed_lands_Des_Tp_review.xlsx', 'tmp_dtypes')

# merge public lands from padus and managed lands
print("Selecting public lands...")
pad_lyr = arcpy.MakeFeatureLayer_management(padus0)
arcpy.SelectLayerByAttribute_management(pad_lyr, "NEW_SELECTION", q_padus)
arcpy.SelectLayerByLocation_management(pad_lyr, "INTERSECT", boundary, selection_type="SUBSET_SELECTION")
arcpy.FeatureClassToFeatureClass_conversion(pad_lyr, arcpy.env.workspace, "tmp_pad")
calcFld("tmp_pad", 'src_unit_type', '!Des_Tp!', field_type="TEXT")  # need to do this here to get domain desc.
# Clip is necessary since there are some large multi-polygons in PADUS
padus = arcpy.Clip_analysis("tmp_pad", boundary, os.path.basename(padus0) + '_public_lands')
calcFld(padus, 'src_unit_nm', '!Unit_Nm!', field_type="TEXT")
calcFld(padus, 'src_unit_access', 'fn(!Pub_Access!)', code_block=cb_acc, field_type="TEXT")
mgd = arcpy.Select_analysis(mgd0, os.path.basename(mgd0) + '_public_lands', q_mgd)
calcFld(mgd, 'src_unit_nm', '!LABEL!', field_type="TEXT")
calcFld(mgd, 'src_unit_access', 'fn(!Access!)', code_block=cb_acc, field_type="TEXT")
calcFld(mgd, 'src_unit_type', '!MATYPE!', field_type="TEXT")
# Merge datasets
arcpy.Merge_management([padus, mgd], publands, add_source=True)
arcpy.JoinField_management(publands, 'src_unit_type', dtypes, 'src_unit_type', 'ppa_type')
arcpy.Integrate_management(publands, "1 Meter")  # Decide: integrate, maybe Eliminate?
arcpy.MultipartToSinglepart_management(publands, publands + '_singlepart')
calcFld(publands + '_singlepart', "src_unit_acres", '!shape.area@ACRES!', field_type="DOUBLE")  # calculate area of single parts. Used to inform naming of final dissolved polygons
# Flatten data, selecting smallest original polygon for attributes
print("Making flat public lands dataset...")
arcpy.Union_analysis(publands + '_singlepart', 'tmp_union')
arcpy.Sort_management('tmp_union', publands + '_flat', [['src_unit_acres', 'Ascending'], ['ppa_type', 'Ascending']])  # order smallest to largest, then by ppa type (1=park).
arcpy.DeleteIdentical_management(publands + '_flat', fields="Shape")
calcFld(publands + '_flat', 'flat_id', '!OBJECTID!', field_type="LONG")
flds = [a.name for a in arcpy.ListFields(publands + '_flat') if a.type != 'OID' and not a.name.startswith('Shape')]
# Add group id to polygons:
# Decide: group distance?
group_dist = "1 Meter"
print("Adding group_id to flat dataset...")
arcpy.PairwiseBuffer_analysis(publands + '_flat', 'tmp_groups0', group_dist, dissolve_option="ALL")  # TODO: group by ppa_type?
arcpy.MultipartToSinglepart_management("tmp_groups0", "tmp_groups")
calcFld('tmp_groups', 'group_id', '!OBJECTID!', field_type="LONG")
# arcpy.SpatialJoin_analysis(publands + '_flat', 'tmp_groups', 'tmp_flat_group', "JOIN_ONE_TO_ONE", "KEEP_ALL", match_option="WITHIN")
arcpy.PairwiseIntersect_analysis([publands + '_flat', 'tmp_groups'], 'tmp_flat_group')  # much faster than spatial join
arcpy.Statistics_analysis('tmp_flat_group', 'tmp_group_flat_id', [["flat_id", "MAX"]], "group_id")  # will return the largest polygon's (flat_id) in the group (by group_id)
arcpy.JoinField_management('tmp_group_flat_id', "MAX_flat_id", publands + '_flat', "flat_id", 'src_unit_nm')
arcpy.AlterField_management('tmp_group_flat_id', "src_unit_nm", "src_group_nm", new_field_alias="PPA group name")

# Identity with NHD water areas
print("Identifying water areas...")
arcpy.Identity_analysis('tmp_flat_group', nhd_areawtrb, 'tmp_water')
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
arcpy.PairwiseDissolve_analysis(lyr, publands + '_final', 'group_id')
# arcpy.DeleteField_management(publands + '_final', 'src_group_nm')
arcpy.JoinField_management(publands + '_final', 'group_id', 'tmp_group_flat_id', 'group_id', 'src_group_nm')
calcFld(publands + '_final', "acres", '!shape.area@ACRES!', field_type="DOUBLE")

# clean up
arcpy.Delete_management(arcpy.ListFeatureClasses('tmp*'))
arcpy.Delete_management(arcpy.ListTables('tmp*'))


# working: land cover/impervious summary in PPAs
feats = 'public_lands_final_imp'
arcpy.CopyFeatures_management('public_lands_final', feats)
# feats = 'public_lands_final_SEVA'
feats_id = 'group_id'
# lc = r'L:\David\GIS_data\NLCD\nlcd_2016\nlcd_2016ed_LandCover_albers.gdb\lc_2016'
lc = r'L:\David\GIS_data\VA_Landcover\mosaic\VA_landcover1m\va_landcover_1m.tif'
imperv = r'L:\David\GIS_data\NLCD\nlcd_2016\nlcd_2016ed_Impervious_albers.gdb\imperv_2016'
canopy = r'L:\David\GIS_data\NLCD\treecan2016.tif\treecan2016.tif'


# TESTING ONLY
# arcpy.env.extent = feats

# Add impervious metrics to parks
# addCoverMetrics(feats, feats_id, lc, imp=['21', '22']) #  NLCD (Low22/Med23/High24)
addMetrics_nlcd(feats, feats_id, imperv, fld_prefix="imp")
addMetrics_nlcd(feats, feats_id, canopy, fld_prefix="can")
# coulddo: classification based on impervious/non-impervious area.
cb = '''def fn(ia, ip, na, np):
   if ip > 5 or (ip > 1 and ia > 5):
      if na > 20 and na + ia > 30:
         return 'Open space/Developed mix PPA'
      else:
         return 'Developed PPA'
   else:
      if na > 20 and na + ia > 30:
         return 'Open space or natural area PPA'
      else:
         return 'Small open space PPA'
'''
calc = 'fn(!imp_acres!, !imp_perc!, !notimp_acres!, !notimp_perc!)'
calcFld(feats, 'ppa_class', calc, code_block=cb)
# non-impervious cover
cb = '''def fn(na):
   if na is None or na < 5:
      return '0 - 5 green acres'
   elif na < 10:
      return '5 - 10 green acres'
   elif na < 20: 
      return '10 - 20 green acres'
   elif na < 50:
      return '20 - 50 green acres'
   elif na < 100:
      return '50 - 100 green acres'
   elif na < 500:
      return '100 - 500 green acres'
   elif na < 1000:
      return '500 - 1000 green acres'
   else:
      return '1000+ green acres'
'''
calc = 'fn(!notimp_acres!)'
calcFld(feats, 'cover_class', calc, code_block=cb)


### TODO: Trails
trails = 'trails'  # base name for layer to create
# working
