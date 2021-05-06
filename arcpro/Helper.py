# -*- coding: utf-8 -*-
"""
Created: 2018
Last Updated: 2018-09-07
ArcGIS version: ArcGIS Pro
Python version: Python 3.5.3
Author: David Bucklin

Collection of helper functions used by
functions in this repository.
"""

import arcpy
import os
import sys
import numpy
import time
import re
arcpy.CheckOutExtension("Spatial")
from arcpy.sa import *
arcpy.env.overwriteOutput = True


def unique_values(table, field):
   ''' Gets list of unique values in a field.
   Thanks, ArcPy Cafe! https://arcpy.wordpress.com/2012/02/01/create-a-list-of-unique-field-values/'''
   with arcpy.da.SearchCursor(table, [field]) as cursor:
      return sorted({row[0] for row in cursor})


def make_gdb(path):
   ''' Creates a geodatabase if it doesn't exist'''
   path = path.replace("\\", "/")
   if '.gdb' not in path:
      print("Bad geodatabase path name.")
      return False
   folder = path[0:path.rindex("/")]
   name = path[(path.rindex("/")+1):len(path)]
   if not os.path.exists(path):
      try:
         arcpy.CreateFileGDB_management(folder, name)
      except:
         return False
      else:
         print("Geodatabase '" + path + "' created.")
         return True
   else:
      print("Geodatabase '" + path + "' already exists.")
      return True


def make_gdb_name(string):
   '''Makes strings GDB-compliant'''
   nm = re.sub('[^A-Za-z0-9]+', '_', string)
   return nm


def garbagePickup(trashList):
   '''Deletes Arc files in list, with error handling. Argument must be a list.'''
   for t in trashList:
      try:
         arcpy.Delete_management(t)
      except:
         pass
   return


def valToScoreNeg(inRast, minimum, maximum):
   '''Given an input value raster, applies a negative function so that the model score at or below the minimum value is 100,
   with scores decreasing to 0 at the maximum value and beyond.'''
   rast = Con(inRast <= minimum, 100, Con(inRast > maximum, 0, 100 * (maximum - inRast) / (maximum - minimum)))
   return rast


def Ymd():
   ymd = time.strftime('%Y%m%d')
   return ymd


def Hms():
   hms = time.strftime('%H:%M:%S')
   return hms


def nullToZero(table, field):
   cb = '''def fn(x):
      if x is None:
         return 0
      else: 
         return x'''
   arcpy.CalculateField_management(table, field, 'fn(!' + field + '!)', code_block=cb)
   return table


def SpatialCluster_GrpFld(inFeats, searchDist, fldGrpID='grpID', fldGrpBy=None, chain=True):
   """Clusters features based on specified search distance, with optional group-by field. Features within twice
   the search distance of each other will be assigned to the same group. Use 'fldGrpBy' to only group features
   having the save value in the field.

   inFeats = The input features to group
   searchDist = The search distance to use for clustering. This should be half of the max distance allowed to include
      features in the same cluster. E.g., if you want features within 500 m of each other to cluster, enter "250 METERS"
   fldGrpID = The desired name for the output grouping field. If not specified, it will be "grpID".
   fldGrpBy = (optional) Field to group features by; only features with the same value in this column will be grouped,
      if within the search distance.
   chain = Should multi-part polygons be allowed to 'chain' together groups? Relevant only for multi-part
      analyses, where the multiple parts are separated by distances greater than the grouping distance.
   """

   # Delete the GrpID field from the input features, if it already exists.
   arcpy.DeleteField_management(inFeats, fldGrpID)

   # Buffer input features
   print('Buffering input features...')
   if fldGrpBy is not None:
      arcpy.PairwiseBuffer_analysis(inFeats, 'tmp_groups0', searchDist, dissolve_option='LIST', dissolve_field=fldGrpBy)
   else:
      arcpy.PairwiseBuffer_analysis(inFeats, 'tmp_groups0', searchDist, dissolve_option='ALL')

   # Make unique group polygons, associate with original features
   arcpy.MultipartToSinglepart_management("tmp_groups0", "tmp_groups")
   arcpy.CalculateField_management('tmp_groups', fldGrpID, '!OBJECTID!', field_type="LONG")
   print('Intersecting to find groups...')
   arcpy.PairwiseIntersect_analysis([inFeats, 'tmp_groups'], 'tmp_flat_group0')

   if fldGrpBy is not None:
      arcpy.Select_analysis('tmp_flat_group0', 'tmp_flat_group', where_clause=fldGrpBy + ' = ' + fldGrpBy + '_1')
      grpTab = 'tmp_flat_group'
   else:
      grpTab = 'tmp_flat_group0'

   if chain:
      print('Updating group IDs using original FIDs...')
      orid = 'FID_' + os.path.basename(inFeats)
      # orig groups
      go = {a[0]: [] for a in arcpy.da.SearchCursor(grpTab, fldGrpID)}
      [go[a[0]].append(a[1]) for a in arcpy.da.SearchCursor(grpTab, [fldGrpID, orid])]
      # fids
      fo = {a[0]: [] for a in arcpy.da.SearchCursor(grpTab, orid)}
      [fo[a[0]].append(a[1]) for a in arcpy.da.SearchCursor(grpTab, [orid, fldGrpID])]
      # for re-assigning groups
      go2 = {a[0]: -1 for a in arcpy.da.SearchCursor(grpTab, fldGrpID)}
      # Re-group using original FIDS
      for g in go:
         # g is the original group id
         # get fids by group
         fids = go[g]
         # get groups by fids
         grps = []
         g0 = 0
         g1 = 1
         while g0 != g1:
            g0 = len(grps)
            grps = list(set(grps + [i for s in [fo.get(f) for f in fids] for i in s]))
            fids = list(set(fids + [i for s in [go.get(g) for g in grps] for i in s]))
            g1 = len(grps)
         ng = min(grps)
         for a in grps:
            go2[a] = ng
      # update rows with final group
      with arcpy.da.UpdateCursor(grpTab, [fldGrpID]) as curs:
         for r in curs:
            r[0] = go2[r[0]]
            curs.updateRow(r)

   print('Joining ' + fldGrpID + ' to ' + os.path.basename(inFeats) + '...')
   arcpy.JoinField_management(inFeats, 'OBJECTID', grpTab, 'FID_' + os.path.basename(inFeats), [fldGrpID])

   return inFeats


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
      arcpy.Merge_management(['tmp_notimp1', 'tmp_notimp0'], "tmp_notimp")
      # calculate statistics by-servCat
      flds = [a.name for a in arcpy.ListFields('tmp_notimp') if a.name.startswith(fld_prefix) and not a.name.endswith('_perc')]
      [nullToZero('tmp_notimp', f) for f in flds]
      arcpy.Statistics_analysis('tmp_notimp', 'tmp_notimp_stats', [[f, 'SUM'] for f in flds], grpFld)
      [arcpy.AlterField_management('tmp_notimp_stats', 'SUM_' + f, f, clear_field_alias=True) for f in flds]
      # join to tab
      arcpy.JoinField_management(tab, grpFld, 'tmp_notimp_stats', grpFld, flds)
      flds2 = ['pop_total', 'sec_accgreen_acres']
   else:
      # only thing to join is population
      flds2 = ['pop_total']

   print('Joining fields to servCats...')
   arcpy.DeleteField_management(servCatFeat, flds2)
   arcpy.JoinField_management(servCatFeat, grpFld, tab, grpFld, flds2)
   [nullToZero(servCatFeat, f) for f in flds2]
   # arcpy.Delete_management(tab)

   if secPPA:
      print('Calculating servCat green acres...')
      calc = '!focal_accgreen_acres! + !sec_accgreen_acres!'
      arcpy.CalculateField_management(servCatFeat, 'accgreen_acres', calc, field_type="FLOAT")

   return servCatFeat


def servCatPressurePPA(servCatFeat, agaptMin=5, fldPop="pop_total", fldAc="accgreen_acres", prefix=""):

   if prefix != "":
      ag = prefix + '_agapt'
      ppfld = prefix + '_rec_pressure'  # _min' + str(agaptMin)
   else:
      ag = 'agapt'
      ppfld = 'rec_pressure'  # _min' + str(agaptMin)
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

   fldAlias(servCatFeat)
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

   fldAlias(servCatFeat)
   return servCatFeat


def fldAlias(inTab):

   print('Updating table aliases...')
   # Create a master list of fields with alias to apply
   fa = {
      "src_table": "Source feature dataset",
      "src_fid": "Source feature OID",
      "src_name": "Source feature name",
      "a_wct": "Watercraft access",
      "a_fsh": "Fishing access",
      "a_swm": "Swimming access",
      "a_gen": "Unspecified aquatic access",
      "t_trl": "Trail access",
      "t_lnd": "Public land access",
      "use": "Model use flag",
      "use_why": "Model use comment",
      "join_table": "Join table",
      "join_fid": "Join PPA OID",
      "join_name": "Join PPA name",
      "join_score": "Join PPA score",
      "focal_src_table": "Focal source feature dataset",
      "focal_src_name": "Focal source feature name",
      "focal_join_name": "Focal join PPA name",
      "accgreen_acres": "AG (acres)",
      "focal_accgreen_acres": "Focal PPA AG (acres)",
      "sec_accgreen_acres": "Secondary PPA AG (acres)",
      "access": "Catchment/gap flag",
      "group_id": "Feature group ID",
      "ppa_group_id": "PPA group ID",
      "pop_total": "Population",
      "agapt": "AG (acres) per 1000",
      "rec_pressure": "Recreation pressure"
   }
   fld = [a.name for a in arcpy.ListFields(inTab) if a.name in fa.keys()]
   for f in fld:
      arcpy.AlterField_management(inTab, f, new_field_alias=fa[f])
   return inTab

# end