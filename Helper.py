"""
Helper.py
Version:  ArcGIS Pro / Python 3.x
Creators: Kirsten R. Hazler, David Bucklin
Creation Date: 2017-10-24
Last Edit: 2022-07-07

Summary:
Imports standard modules, applies standard settings, and defines a collection of helper functions.

As of 2022-07-07, generic helper functions are imported from external modules. This script should contain only
objects, functions, and settings specific to this repo.
"""

# Import modules
from helper_arcpy import *
import arcpy
import os
import sys
import traceback
import numpy
import time
import re

arcpy.CheckOutExtension("Spatial")
from arcpy.sa import *

scratchGDB = arcpy.env.scratchGDB
arcpy.env.overwriteOutput = True
arcpy.env.maintainAttachments = False


def servCatStats(servCatFeat, grpFld, popRast, secPPA=None, impRast=None, ppa_access="ppa_access"):
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
      arcpy.PairwiseIntersect_analysis([secPPA, servCatFeat], 'tmp_sec0')
      arcpy.CalculateField_management('tmp_sec0', 'propOrig', "!Shape_Area! / !ShapeArea_secPPA!", field_type="FLOAT")

      print('Calculating impervious statistics for secondary PPAs...')
      fld_prefix = 'sec_'
      # Calculate zonal stats for access areas with ppa_access=1, by servCat
      arcpy.Select_analysis('tmp_sec0', 'tmp_sel', ppa_access + " = 1")
      arcpy.PairwiseDissolve_analysis('tmp_sel', 'tmp_notimp1', [grpFld])
      arcpy.CalculateField_management('tmp_notimp1', fld_prefix + 'acres', '!Shape_Area! / 4046.856',
                                      field_type="FLOAT")
      arcpy.sa.ZonalStatisticsAsTable('tmp_notimp1', grpFld, impRast, 'tmp_zs', "DATA", "MEAN")
      arcpy.CalculateField_management('tmp_zs', fld_prefix + 'impacc_perc', "!MEAN!", field_type="FLOAT")
      arcpy.JoinField_management('tmp_notimp1', grpFld, 'tmp_zs', grpFld, fld_prefix + 'impacc_perc')
      calc = '((!' + fld_prefix + 'impacc_perc! / 100) * !Shape_Area!) / 4046.856'
      arcpy.CalculateField_management('tmp_notimp1', fld_prefix + 'impacc_acres', calc, field_type="FLOAT")
      calc = '((1- (!' + fld_prefix + 'impacc_perc! / 100)) * !Shape_Area!) / 4046.856'
      arcpy.CalculateField_management('tmp_notimp1', fld_prefix + 'accgreen_acres', calc, field_type="FLOAT")
      calc = '100 - !' + fld_prefix + 'impacc_perc!'
      arcpy.CalculateField_management('tmp_notimp1', fld_prefix + 'notimpacc_perc', calc, field_type="FLOAT")
      # Calculates secondary accgreen_acres for ppa_access=0 (proportional to amount of PPA intersected).
      # Then dissolve to servCat, summarizing total notimpacres.
      arcpy.Select_analysis('tmp_sec0', 'tmp_sel', ppa_access + " = 0")
      arcpy.CalculateField_management('tmp_sel', fld_prefix + 'accgreen_acres', '!accgreen_acres! * !propOrig!',
                                      field_type="FLOAT")
      arcpy.PairwiseDissolve_analysis('tmp_sel', 'tmp_notimp0', [grpFld],
                                      statistics_fields=[[fld_prefix + "accgreen_acres", "SUM"]])
      arcpy.AlterField_management('tmp_notimp0', 'SUM_' + fld_prefix + "accgreen_acres", fld_prefix + "accgreen_acres",
                                  clear_field_alias=True)

      # combine notimp stats from ppa_access=1 and ppa_access=0 areas
      arcpy.Merge_management(['tmp_notimp1', 'tmp_notimp0'], "tmp_notimp")
      # calculate statistics by-servCat
      flds = [a.name for a in arcpy.ListFields('tmp_notimp') if
              a.name.startswith(fld_prefix) and not a.name.endswith('_perc')]
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

   if secPPA:
      print('Calculating servCat green acres...')
      calc = '!focal_accgreen_acres! + !sec_accgreen_acres!'
      arcpy.CalculateField_management(servCatFeat, 'accgreen_acres', calc, field_type="FLOAT")

   return servCatFeat


def agapt(servCatFeat, fldPop="pop_total", fldAc="accgreen_acres", prefix=""):
   if prefix != "":
      ag = prefix + '_agapt'
   else:
      ag = 'agapt'
   print('Calculating `' + ag + '` field...')
   arcpy.DeleteField_management(servCatFeat, [ag])
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

   return servCatFeat


def servCatPressure(servCatFeat, fldPop="pop_total", fldScore="access", per=10000, fldPressure="rec_pressure"):
   # Note: 'per' is the number of persons per unit of fldScore, which denotes the middle of the scoring range (50).

   print('Calculating `' + fldPressure + '`...')
   arcpy.DeleteField_management(servCatFeat, [fldPressure])

   if fldScore == 'access':
      # aquatic access point adjustment
      adj = str(0.01)
   else:
      # PPA adjustment
      adj = str(1)

   # calculate pressure
   mid = str((1 / per) * 50)
   calc = "min(100, round(" + mid + " * !" + fldPop + "! / (" + adj + " + !" + fldScore + "!)))"
   arcpy.CalculateField_management(servCatFeat, fldPressure, calc, field_type="LONG")

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


##################################################################################################################
# Use the main function below to run a function directly from Python IDE or command line with hard-coded variables

def main():
   # Set up variables
   inFeats = r'E:\ConsVision_RecMod\Terrestrial\Input\TerrestrialFacilities.shp'
   # fldID =  'FID'
   searchDist = '250 METERS'
   fldGrpID = 'grpID_500m'

   # Specify function to run
   SpatialCluster(inFeats, searchDist, fldGrpID)


if __name__ == '__main__':
   main()
