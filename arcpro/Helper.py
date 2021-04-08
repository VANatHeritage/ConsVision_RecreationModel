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


# end