# ---------------------------------------------------------------------------
# Helper.py
# Version:  ArcGIS Pro / Python 3.x
# Creators: Kirsten R. Hazler, David Bucklin
# Creation Date: 2017-10-24 
# Last Edit: 2021-07-12

# Summary:
# Imports standard modules, applies standard settings, and defines a collection of helper functions to be called by other scripts.

# Import modules
print('Importing modules, including arcpy, which takes way longer than it should...')
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


def countFeatures(features):
   '''Gets count of features'''
   count = int((arcpy.GetCount_management(features)).getOutput(0))
   return count


def garbagePickup(trashList):
   '''Deletes Arc files in list, with error handling. Argument must be a list.'''
   for t in trashList:
      try:
         arcpy.Delete_management(t)
      except:
         pass
   return


def GetElapsedTime(t1, t2):
   """Gets the time elapsed between the start time (t1) and the finish time (t2)."""
   delta = t2 - t1
   (d, m, s) = (delta.days, delta.seconds / 60, delta.seconds % 60)
   (h, m) = (m / 60, m % 60)
   deltaString = '%s days, %s hours, %s minutes, %s seconds' % (str(d), str(h), str(m), str(s))
   return deltaString


def printMsg(msg):
   arcpy.AddMessage(msg)
   print(msg)
   return


def printWrng(msg):
   arcpy.AddWarning(msg)
   print('Warning: ' + msg)
   return


def printErr(msg):
   arcpy.AddError(msg)
   print('Error: ' + msg)
   return


def ProjectToMatch(fcTarget, csTemplate):
   """Project a target feature class to match the coordinate system of a template dataset"""
   # Get the spatial reference of your target and template feature classes
   srTarget = arcpy.Describe(fcTarget).spatialReference  # This yields an object, not a string
   srTemplate = arcpy.Describe(csTemplate).spatialReference

   # Get the geographic coordinate system of your target and template feature classes
   gcsTarget = srTarget.GCS  # This yields an object, not a string
   gcsTemplate = srTemplate.GCS

   # Compare coordinate systems and decide what to do from there. 
   if srTarget.Name == srTemplate.Name:
      printMsg('Coordinate systems match; no need to do anything.')
      return fcTarget
   else:
      printMsg('Coordinate systems do not match; proceeding with re-projection.')
      if fcTarget[-3:] == 'shp':
         fcTarget_prj = fcTarget[:-4] + "_prj.shp"
      else:
         fcTarget_prj = fcTarget + "_prj"
      if gcsTarget.Name == gcsTemplate.Name:
         printMsg('Datums are the same; no geographic transformation needed.')
         arcpy.Project_management(fcTarget, fcTarget_prj, srTemplate)
      else:
         printMsg('Datums do not match; re-projecting with geographic transformation')
         # Get the list of applicable geographic transformations
         # This is a stupid long list
         transList = arcpy.ListTransformations(srTarget, srTemplate)
         # Extract the first item in the list, assumed the appropriate one to use
         geoTrans = transList[0]
         # Now perform reprojection with geographic transformation
         arcpy.Project_management(fcTarget, fcTarget_prj, srTemplate, geoTrans)
      printMsg("Re-projected data is %s." % fcTarget_prj)
      return fcTarget_prj


def TabToDict(inTab, fldKey, fldValue):
   '''Converts two fields in a table to a dictionary'''
   codeDict = {}
   with arcpy.da.SearchCursor(inTab, [fldKey, fldValue]) as sc:
      for row in sc:
         key = sc[0]
         val = sc[1]
         codeDict[key] = val
   return codeDict


def JoinFields(ToTab, fldToJoin, FromTab, fldFromJoin, addFields):
   '''An alternative to arcpy's JoinField_management, which is unbearably slow.
   
   ToTab = The table to which fields will be added
   fldToJoin = The key field in ToTab, used to match records in FromTab
   FromTab = The table from which fields will be copied
   fldFromJoin = the key field in FromTab, used to match records in ToTab
   addFields = the list of fields to be added'''

   codeblock = '''def getFldVal(srcID, fldDict):
      try:
         fldVal = fldDict[srcID]
      except:
         fldVal = None
      return fldVal'''

   for fld in addFields:
      printMsg('Working on "%s" field...' % fld)
      fldObject = arcpy.ListFields(FromTab, fld)[0]
      fldDict = TabToDict(FromTab, fldFromJoin, fld)
      printMsg('Established data dictionary.')
      expression = 'getFldVal(!%s!, %s)' % (fldToJoin, fldDict)
      srcFields = arcpy.ListFields(ToTab, fld)
      if len(srcFields) == 0:
         arcpy.AddField_management(ToTab, fld, fldObject.type, '', '', fldObject.length)
      printMsg('Calculating...')
      arcpy.CalculateField_management(ToTab, fld, expression, 'PYTHON', codeblock)
      printMsg('"%s" field done.' % fld)
   return ToTab


def SpatialCluster(inFeats, searchDist, fldGrpID='grpID'):
   '''Clusters features based on specified search distance. Features within twice the search distance of each other will be assigned to the same group.
   inFeats = The input features to group
   searchDist = The search distance to use for clustering. This should be half of the max distance allowed to include features in the same cluster. E.g., if you want features within 500 m of each other to cluster, enter "250 METERS"
   fldGrpID = The desired name for the output grouping field. If not specified, it will be "grpID".'''

   # Get the name of the OID field
   fldID = [a.name for a in arcpy.ListFields(inFeats) if a.type == 'OID'][0]

   # Initialize trash items list
   trashList = []

   # Delete the GrpID field from the input features, if it already exists.
   try:
      arcpy.DeleteField_management(inFeats, fldGrpID)
   except:
      pass

   # Buffer input features
   printMsg('Buffering input features')
   outBuff = scratchGDB + os.sep + 'outBuff'
   arcpy.Buffer_analysis(inFeats, outBuff, searchDist, dissolve_option='ALL')
   trashList.append(outBuff)

   # Explode multipart  buffers
   printMsg('Exploding buffers')
   explBuff = scratchGDB + os.sep + 'explBuff'
   arcpy.MultipartToSinglepart_management(outBuff, explBuff)
   trashList.append(explBuff)

   # Add and populate grpID field in buffers
   printMsg('Adding and populating grouping field in buffers')
   arcpy.AddField_management(explBuff, fldGrpID, 'LONG')
   arcpy.CalculateField_management(explBuff, fldGrpID, '!OBJECTID!', 'PYTHON')

   # Spatial join buffers with input features
   printMsg('Performing spatial join between buffers and input features')
   joinFeats = scratchGDB + os.sep + 'joinFeats'
   arcpy.SpatialJoin_analysis(inFeats, explBuff, joinFeats, 'JOIN_ONE_TO_ONE', 'KEEP_ALL', '', 'WITHIN')
   trashList.append(joinFeats)

   # Join grpID field to input features
   # This employs a custom function because arcpy is stupid slow at this
   JoinFields(inFeats, fldID, joinFeats, 'TARGET_FID', [fldGrpID])

   # Cleanup: delete buffers, spatial join features
   garbagePickup(trashList)

   printMsg('Processing complete.')

   return inFeats


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


def tbackInLoop():
   '''Standard error handling routing to add to bottom of scripts'''
   tb = sys.exc_info()[2]
   tbinfo = traceback.format_tb(tb)[0]
   pymsg = "PYTHON ERRORS:\nTraceback Info:\n" + tbinfo + "\nError Info:\n " + str(sys.exc_info()[1])
   msgs = arcpy.GetMessages(1)
   msgList = [pymsg, msgs]

   # printWrng(msgs)
   printWrng(pymsg)
   printMsg(msgs)

   return msgList


def unique_values(table, field):
   ''' Gets list of unique values in a field.
   Thanks, ArcPy Cafe! https://arcpy.wordpress.com/2012/02/01/create-a-list-of-unique-field-values/'''
   with arcpy.da.SearchCursor(table, [field]) as cursor:
      return sorted({row[0] for row in cursor})


def valToScoreNeg(inRast, minimum, maximum):
   '''Given an input value raster, applies a negative function so that the model score at or below the minimum value is 100, 
   with scores decreasing to 0 at the maximum value and beyond.'''
   rast = Con(inRast <= minimum, 100, Con(inRast > maximum, 0, 100 * (maximum - inRast) / (maximum - minimum)))
   return rast


def CleanFeatures(inFeats, outFeats):
   '''Repairs geometry, then explodes multipart polygons to prepare features for geoprocessing.'''

   # Process: Repair Geometry
   arcpy.RepairGeometry_management(inFeats, "DELETE_NULL")

   # Have to add the while/try/except below b/c polygon explosion sometimes fails inexplicably.
   # This gives it 10 tries to overcome the problem with repeated geometry repairs, then gives up.
   counter = 1
   while counter <= 10:
      try:
         # Process: Multipart To Singlepart
         arcpy.MultipartToSinglepart_management(inFeats, outFeats)

         counter = 11

      except:
         arcpy.AddMessage("Polygon explosion failed.")
         # Process: Repair Geometry
         arcpy.AddMessage("Trying to repair geometry (try # %s)" % str(counter))
         arcpy.RepairGeometry_management(inFeats, "DELETE_NULL")

         counter += 1

         if counter == 11:
            arcpy.AddMessage("Polygon explosion problem could not be resolved.  Copying features.")
            arcpy.CopyFeatures_management(inFeats, outFeats)

   return outFeats


def CleanClip(inFeats, clipFeats, outFeats, scratchGDB="in_memory"):
   '''Clips the Input Features with the Clip Features.  The resulting features are then subjected to geometry repair and exploded (eliminating multipart polygons)'''
   # # Determine where temporary data are written
   # msg = getScratchMsg(scratchGDB)
   # arcpy.AddMessage(msg)

   # Process: Clip
   tmpClip = scratchGDB + os.sep + "tmpClip"
   arcpy.Clip_analysis(inFeats, clipFeats, tmpClip)

   # Process: Clean Features
   CleanFeatures(tmpClip, outFeats)

   # Cleanup
   if scratchGDB == "in_memory":
      garbagePickup([tmpClip])

   return outFeats


def calcFld(inTab, fldName, expression, code_block=None, field_type="TEXT"):
   '''Wrapper for CalculateField, which also adds the field. Will delete existing column to ensure
   field_type. Can be swapped with base fn after ArcGIS Pro version 2.5+'''
   if fldName in [a.name for a in arcpy.ListFields(inTab)]:
      arcpy.DeleteField_management(inTab, fldName)
   arcpy.AddField_management(inTab, fldName, field_type)
   arcpy.CalculateField_management(inTab, fldName, expression, expression_type="PYTHON", code_block=code_block)
   return inTab


def make_gdb(path):
   ''' Creates a geodatabase if it doesn't exist'''
   path = path.replace("\\", "/")
   if '.gdb' not in path:
      print("Bad geodatabase path name.")
      return False
   folder = path[0:path.rindex("/")]
   name = path[(path.rindex("/") + 1):len(path)]
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
