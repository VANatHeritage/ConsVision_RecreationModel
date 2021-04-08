"""
servCats
Created by: David Bucklin
Created on: 2021-03-22

This script runs a service catchment (i.e. parkshed) analysis for a set of PPA polygons.

Instructions: Delineate servCats for PPA with >= 25 accessible green acres. (If this results in an excessive number of
PPA parksheds, maybe set the threshold higher, to 50 or 100. This is mainly to demo the process right now, and the
threshold is subject to change based on feedback.)
   For each parkshed, calculate:
   - population
   - accessible green acres of focal park
   - total accessible green acres of focal park PLUS accessible green acres of other parks (any size) within the parkshed
   - AGAPT = total accessible green acres per thousand people
   - park pressure = 500/AGAPT (set anything above 100 to 100; feel free to experiment with different formulas for pressure).
"""

from arcpro.Helper import *


def servCat(feats, costRast, servCatFeat, grpFld=None, maxCost="", fill=False):
   # feats='ppa_focal'
   # costRast
   # servCatFeat
   # grpFld="group_id"
   # maxCost = 30
   # fill = True

   if grpFld is None:
      grpFld = [a.name for a in arcpy.ListFields(feats) if a.type == 'OID'][0]
   print('Using ' + grpFld + ' field as cost allocation source_field.')

   servCatRast = servCatFeat + '_rast'
   ngrp = len(set([a[0] for a in arcpy.da.SearchCursor(feats, grpFld)]))
   print('Running cost allocation for ' + str(ngrp) + ' features...')

   ca = arcpy.sa.CostAllocation(feats, costRast, maxCost, source_field=grpFld)
   # Note: CostAllocation is a 'legacy' fn in 2021. DistanceAllocation is a more expansive function and can do cost
   # allocation as well. In testing the two processes give equivalent but not identical results. Cost allocation seemed
   # a bit faster in execution, so sticking with it until deprecated. DistanceAllocation call is below.
   # https://pro.arcgis.com/en/pro-app/latest/tool-reference/spatial-analyst/distance-allocation.htm
   # ca = arcpy.sa.DistanceAllocation(feats, in_cost_raster=costRast, source_field=grpFld,
   #                           source_maximum_accumulation=maxCost)
   if fill:
      print('Filling in NoData areas...')
      arcpy.sa.Con(arcpy.sa.IsNull(ca), -1, ca, "Value = 1").save(servCatRast)
   else:
      ca.save(servCatRast)
   print('Converting raster to polygon...')
   # arcpy.RasterToPolygon_conversion(servCatRast, servCatFeat, "NO_SIMPLIFY", "Value", "MULTIPLE_OUTER_PART")
   ps = arcpy.RasterToPolygon_conversion(servCatRast, servCatFeat + '_noFill', "NO_SIMPLIFY", "Value", "SINGLE_OUTER_PART")
   if fill:
      lyr = arcpy.MakeFeatureLayer_management(servCatFeat + '_noFill')
      arcpy.SelectLayerByAttribute_management(lyr, "NEW_SELECTION", "gridcode = -1")
      if int(arcpy.GetCount_management(lyr)[0]) > 0:
         arcpy.CalculateField_management(lyr, "gridcode", "!OBJECTID! * -1")
         # eliminate -1 polygons <1 square mile in size, adding to servCat with largest shared boundary
         arcpy.SelectLayerByAttribute_management(lyr, "NEW_SELECTION", "gridcode <= -1 AND Shape_Area < 2589990")
         ps = arcpy.Eliminate_management(lyr, 'tmp_elim')
   arcpy.AlterField_management(ps, 'gridcode', 'servCat_' + grpFld, clear_field_alias=True)
   arcpy.PairwiseDissolve_analysis(ps, servCatFeat, 'servCat_' + grpFld)

   print('Joining attributes to servCat features...')
   jf = [a.name for a in arcpy.ListFields(feats) if not a.name.startswith(('Shape', 'FID_')) and a.type != 'OID' and a.name != grpFld]
   arcpy.JoinField_management(servCatFeat, 'servCat_' + grpFld, feats, grpFld, jf)
   jf2 = [[a, 'focal_' + a] for a in jf]
   for i in jf2:
      arcpy.AlterField_management(servCatFeat, i[0], i[1], clear_field_alias=True)
      if i[1].endswith('_acres'):
         nullToZero(servCatFeat, i[1])

   arcpy.Delete_management(ca)
   return servCatFeat


def servCatStats(servCatFeat, grpFld, popRast, secPPA=None, impRast=None):

   # servCatFeat='servCat'
   # grpFld = "servCat_group_id"
   # secPPA = 'ppa_secondary'

   print('Calculating population statistics...')
   tab = servCatFeat + '_stats'
   arcpy.sa.ZonalStatisticsAsTable(servCatFeat, grpFld, popRast, tab, statistics_type="SUM")
   arcpy.CalculateField_management(tab, 'pop_total', 'round(!SUM!)', field_type="LONG")

   if secPPA:
      print('Intersecting secondary PPAs with servCats...')
      arcpy.CalculateField_management(secPPA, 'ShapeArea_secPPA', '!Shape_Area!', field_type="FLOAT")
      arcpy.PairwiseIntersect_analysis([servCatFeat, secPPA], 'tmp_sec0')
      arcpy.CalculateField_management('tmp_sec0', 'propOrig', "!Shape_Area! / !ShapeArea_secPPA!", field_type="FLOAT")

      print('Calculating impervious statistics for secondary PPAs...')
      fld_prefix = 'sec_'
      # Calculate zonal stats for access areas with access=1, by servCat
      arcpy.Select_analysis('tmp_sec0', 'tmp_sel', "access = 1")
      arcpy.PairwiseDissolve_analysis('tmp_sel', 'tmp_notimp1', [grpFld])
      arcpy.CalculateField_management('tmp_notimp1', fld_prefix + 'acres', '!Shape_Area! / 4046.856', field_type="FLOAT")
      arcpy.sa.ZonalStatisticsAsTable('tmp_notimp1', grpFld, impRast, 'tmp_zs', "DATA", "MEAN")
      arcpy.CalculateField_management('tmp_zs', fld_prefix + 'impacc_perc', "!MEAN!", field_type="FLOAT")
      arcpy.JoinField_management('tmp_notimp1', grpFld, 'tmp_zs', grpFld, fld_prefix + 'impacc_perc')
      calc = '((!' + fld_prefix + 'impacc_perc! / 100) * !Shape_Area!) / 4046.856'
      arcpy.CalculateField_management('tmp_notimp1', fld_prefix + 'impacc_acres', calc, field_type="FLOAT")
      calc = '((1- (!' + fld_prefix + 'impacc_perc! / 100)) * !Shape_Area!) / 4046.856'
      arcpy.CalculateField_management('tmp_notimp1', fld_prefix + 'accgreen_acres', calc, field_type="FLOAT")
      calc = '100 - !' + fld_prefix + 'impacc_perc!'
      arcpy.CalculateField_management('tmp_notimp1', fld_prefix + 'notimpacc_perc', calc, field_type="FLOAT")
      # Calculates secondary accgreen_acres for access=0 (proportional to amount of PPA intersected).
      # Then dissolve to servCat, summarizing total notimpacres.
      arcpy.Select_analysis('tmp_sec0', 'tmp_sel', "access = 0")
      arcpy.CalculateField_management('tmp_sel', fld_prefix + 'accgreen_acres', '!accgreen_acres! * !propOrig!', field_type="FLOAT")
      arcpy.PairwiseDissolve_analysis('tmp_sel', 'tmp_notimp0', [grpFld], statistics_fields=[[fld_prefix + "accgreen_acres", "SUM"]])
      arcpy.AlterField_management('tmp_notimp0', 'SUM_' + fld_prefix + "accgreen_acres", fld_prefix + "accgreen_acres", clear_field_alias=True)

      # combine notimp stats from access=1 and access=0 areas
      arcpy.Merge_management(['tmp_notimp0', 'tmp_notimp1'], "tmp_notimp")
      # calculate statistics by-servCat
      flds = [a.name for a in arcpy.ListFields('tmp_notimp') if a.name.startswith(fld_prefix) and not a.name.endswith('_perc')]
      [nullToZero('tmp_notimp', f) for f in flds]
      arcpy.Statistics_analysis('tmp_notimp', 'tmp_notimp_stats', [[f, 'SUM'] for f in flds], grpFld)
      [arcpy.AlterField_management('tmp_notimp_stats', 'SUM_' + f, f, clear_field_alias=True) for f in flds]
      # join to tab
      arcpy.JoinField_management(tab, grpFld, 'tmp_notimp_stats', grpFld, flds)
      flds2 = ['pop_total'] + flds
   else:
      # only thing to join is population
      flds2 = ['pop_total']

   print('Joining fields to servCats...')

   arcpy.DeleteField_management(servCatFeat, flds2)
   arcpy.JoinField_management(servCatFeat, grpFld, tab, grpFld, flds2)
   [nullToZero(servCatFeat, f) for f in flds2]

   if secPPA:
      print('Calculating servCat green acres...')
      calc = '!focal_accgreen_acres! + !sec_accgreen_acres!'
      arcpy.CalculateField_management(servCatFeat, 'accgreen_acres', calc, field_type="FLOAT")

   return servCatFeat


def servCatPressurePPA(servCatFeat, agaptMin=5, fldPop="pop_total", fldAc="accgreen_acres", prefix=""):

   if prefix != "":
      ag = prefix + '_agapt'
      ppfld = prefix + '_park_pressure_min' + str(agaptMin)
   else:
      ag = 'agapt'
      ppfld = 'park_pressure_min' + str(agaptMin)
   print('Calculating `' + ag + '` and `' + ppfld + '` fields...')
   arcpy.DeleteField_management(servCatFeat, [ag, ppfld])
   cb = '''def fn(pop, ac):
      if ac == 0:
         return 0
      else:
         if pop > 0:
            return ac / (pop / 1000)
         else:
            return None'''
   calc = 'fn(!' + fldPop + '!, !' + fldAc + '!)'
   arcpy.CalculateField_management(servCatFeat, ag, calc, code_block=cb, field_type="FLOAT")
   cb = '''def fn(x, n):
      if x is not None:
         y = n / x
         if y > 1:
            return 100
         else:
            return round(y * 100)
      else:
         return None'''
   calc = 'fn(!' + ag + '!, ' + str(agaptMin) + ')'
   arcpy.CalculateField_management(servCatFeat, ppfld, calc, code_block=cb, field_type="LONG")

   return servCatFeat


def servCatPressureAq(servCatFeat, fldPop="pop_total", fldAcc="access", per=10000):
   # Add a pressure score: Aquatic Recreation Pressure = MIN[100, ((Pop in catchment)/200)]
   # fldAcc is binary 1/0 indicating access or not. If 0, pressure score value will be Null.
   # per is a population where the pressure score be 50 (e.g. 1 access point per 10,000 persons in the catchment, will

   # calculate midpoint score (50)
   mid = str(per/50)
   pfld = 'rec_pressure'
   print('Calculating `' + pfld + '`...')
   arcpy.DeleteField_management(servCatFeat, [pfld])
   cb = '''def fn(pop, acc, mid):
      if acc == 0:
         return None
      else:
         return round(min(100, pop / mid))'''
   calc = 'fn(!' + fldPop + '!, !' + fldAcc + '!,' + str(mid) + ')'
   arcpy.CalculateField_management(servCatFeat, pfld, calc, code_block=cb, field_type="LONG")

   return servCatFeat



# HEADER

costRast = r'E:\RCL_cost_surfaces\Tiger_2020\cost_surfaces.gdb\costSurf_no_lah'
costRastWalk = r'E:\RCL_cost_surfaces\Tiger_2020\cost_surfaces.gdb\costSurf_walk'
popRast = r'E:\projects\rec_model\rec_model_processing\input_recmodel.gdb\distribPop_kdens_2020'
impRast = r'L:\David\GIS_data\NLCD\nlcd_2016\nlcd_2016ed_Impervious_albers.gdb\imperv_2016'

# Envs
arcpy.env.outputCoordinateSystem = costRast
arcpy.env.snapRaster = costRast
arcpy.env.cellSize = costRast
arcpy.env.extent = costRast
arcpy.env.mask = costRast
arcpy.env.overwriteOutput = True
arcpy.env.parallelProcessingFactor = "75%"  # Adjust to some percent (e.g. 100%) for large extent analyses.
# TESTING - limit extent
# arcpy.env.extent = r'E:\projects\rec_model\rec_model.gdb\public_lands_final_TEST'

# END HEADER

# 1. PPAs
ppa = r'E:\projects\rec_model\rec_datasets\rec_datasets_working.gdb\public_lands_final_accessAreas'  # public_lands_final | public_lands_final_rdtrlacc
ppaID = 'group_id'

# create Geodatabase
dt = Ymd()
out_gdb = r'E:\projects\rec_model\rec_model_processing\serviceCatchments' + os.sep + 'PPA_servCats_' + dt + '.gdb'
make_gdb(out_gdb)
arcpy.env.workspace = out_gdb

# select PPA to use in analysis. Exclude polygons with 0 accessible greenspace acres.
lyr = arcpy.MakeFeatureLayer_management(ppa, where_clause="accgreen_acres > 0")
# NOTE: some PPA have no access area but still have some notimpacc area (<=5 acres).
# These are identified in this layer by access = 0. For those, the full PPA is used. In summarizing (servCatStats),
# the area assigned to the servCat in proportion to the PPA area in the servCat.
arcpy.SelectLayerByAttribute_management(lyr, "NEW_SELECTION", 'accgreen_acres >= 25')
arcpy.CopyFeatures_management(lyr, 'ppa_focal')
arcpy.SelectLayerByAttribute_management(lyr, "SWITCH_SELECTION")
arcpy.CopyFeatures_management(lyr, 'ppa_secondary')

# Run servCat
servCatFeat = 'servCat'
servCat('ppa_focal', costRast, servCatFeat, "group_id", maxCost=30, fill=True)
arcpy.CopyFeatures_management(servCatFeat, servCatFeat + '_stats')
# Add metrics for population and non-impervious acres of secondary PPA
servCatStats(servCatFeat + '_stats', 'servCat_group_id', popRast,  'ppa_secondary', impRast)
# Calculate AGAPT (accesible green acres per 1000 persons) and park pressure score, which normalizes agapt using agaptMin as base score: (agaptMin / agapt) * 100.
servCatPressurePPA(servCatFeat + '_stats', agaptMin=5)
servCatPressurePPA(servCatFeat + '_stats', agaptMin=2)
# Calculate pressure for focal (focal) park only. Note usage of 'prefix' which will be appended to the new fields.
servCatPressurePPA(servCatFeat + '_stats', agaptMin=5, fldAc="focal_accgreen_acres", prefix="focal")

# end PPA

# 2. Aquatic access points

# create Geodatabase
# dt = Ymd()
out_gdb = r'E:\projects\rec_model\rec_model_processing\serviceCatchments' + os.sep + 'aquatic_servCats.gdb'
make_gdb(out_gdb)
arcpy.env.workspace = out_gdb
# access features
feats = r'E:\projects\rec_model\rec_model_processing\access_pts.gdb\access_points_combined_20210406'
servCatFeat = 'servCat_aqua'

# Run service catchments
servCat(feats, costRast, servCatFeat, "group_id", maxCost=30, fill=True)
# make a binary 1/0 field indicating in a service catchment (1) or a gap (0)
arcpy.CalculateField_management(servCatFeat, 'access', "min(max(!servCat_group_id!, 0), 1)", field_type="SHORT")
arcpy.CopyFeatures_management(servCatFeat, servCatFeat + '_stats')
# Add metrics for population
servCatStats(servCatFeat + '_stats', 'servCat_group_id', popRast)
# Calculate pressure score
servCatPressureAq(servCatFeat + '_stats')

# end aquatic

# clean up
arcpy.Delete_management(arcpy.ListFeatureClasses("tmp_*"))
arcpy.Delete_management(arcpy.ListTables("tmp_*"))

# end
