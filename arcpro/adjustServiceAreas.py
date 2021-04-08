"""
adjustServiceAreas
Created: 2018-09
Last Updated: 2019-02-19
ArcGIS version: ArcGIS Pro
Python version: Python 3.5.3
Author: David Bucklin

Adjust service area values by another raster.

Creates a new raster for each service area raster (created using runServiceAreas.py)
with its original score divided by total population within the service area.

It outputs a new service area raster for each original (with a 'popAdj_' prefix),
and a feature class will all vectorized service areas and the attributes:
   sa_id: original group ID number
   sa_score: service area original score
   sa_sumpop: sum of population within service area
   sa_scoreperpop: [sa_score / sa_sumpop]
   sa_minutes: minutes used in service area creation

Argument definitions:
   inGDB: Name of input GDB storing service area rasters
   popRast: The population raster
   rastPattern: character string defining a subset of service area rasters
      to process from `inGDB` (default  = '*servArea')
   feats: Name of the feature class used for generating service areas (should be `accFeat_orig`)
   grpFld: Name of the column in feats, where one raster service area was generated per group
   attFld: Name of the column in feats used in scoring (e.g. `acres` for parks)
"""

from arcpro.Helper import *


def adjustServiceAreas(inGDB, popRast, rastPattern='*_servArea',
                       feats='accFeat_orig', grpFld='OBJECTID', attFld='acres'):

   arcpy.env.workspace = inGDB
   arcpy.env.overwriteOutput = True
   ls = arcpy.ListRasters(rastPattern)

   arcpy.env.outputCoordinateSystem = popRast
   arcpy.env.cellSize = popRast
   arcpy.env.snapRaster = popRast
   arcpy.env.extent = feats

   # make 'parks' (rec features) raster
   parkRast = feats + '_rast'
   arcpy.FeatureToRaster_conversion(feats, grpFld, parkRast, popRast)

   # make a new unique ID field, to join with later on
   newID = 'unique_ID'
   arcpy.CalculateField_management(feats, newID, '!' + grpFld + '!', field_type='LONG')

   # Make table to loop over, with one row per unique ID. Assumes that attFld has one unique value per group.
   rec_feats = arcpy.Statistics_analysis(feats, feats + '_PopScores', statistics_fields=[[attFld, "COUNT"]],
                                         case_field=[newID, attFld])
   fld_add = [['pop_total', 'FLOAT', 'Population in service area'],
              ['score_per1k', 'FLOAT', 'Acres per 1000 persons'],
              ['comb_score', 'FLOAT', 'Combined acres'],
              ['comb_score_per1k', 'FLOAT', 'Combined acres per 1000 persons']]
   arcpy.AddFields_management(rec_feats, fld_add)

   print('There are ' + str(len(ls)) + ' rasters in GDB to process.')

   # This contains lookup list of groups/scores
   rec_feats_scores = [a for a in arcpy.da.SearchCursor(rec_feats, [newID, attFld])]

   # for i in ls:
   fld = [newID, attFld] + [f[0] for f in fld_add]
   with arcpy.da.UpdateCursor(rec_feats, fld) as uc:
      for u in uc:
         i = 'grp_' + str(u[0]) + '_servArea'
         if i not in ls:
            print('Raster `' + i + '` does not exist, skipping...')
         else:
            print(i)
         t0 = time.time()
         if u[2] is not None:
            print('Stats already calculated for `' + i + '`, skipping...')
            continue

         # this was adjusted raster name; DEPRECATED
         # i_nm = i.split('_')[1]
         # finalrast = inGDB + os.sep + 'popAdj_' + str(i_nm)
         # if arcpy.Exists(finalrast):
         #    print('File exists, skipping...')
         #    continue

         # set extent to input raster
         arcpy.env.snapRaster = i
         arcpy.env.cellSize = i
         arcpy.env.outputCoordinateSystem = i

         # make masked population raster
         msk = arcpy.sa.ExtractByMask(popRast, i)
         arr = arcpy.RasterToNumPyArray(msk, nodata_to_value=0)
         sumPop = arr.sum()
         # set sum of population to 1 if less than 1 to avoid dividing by 0
         if sumPop < 1:
            sumPop = 1
         else:
            sumPop = int(round(sumPop))

         # get minutes used for SA
         # sapt = 'grp_' + i_nm + '_inputFeat'
         # minutes_sa = unique_values(sapt, 'minutes_SA')[0]
         # if minutes_sa > 60:
         #    minutes_sa = 60

         # get area from service area raster
         # acres = unique_values(sapt, 'acres')[0]
         # score = float(arcpy.GetRasterProperties_management(i, "MAXIMUM").getOutput(0))

         # UPDATE 2020-10: find other parks in SA, sum their area and add to target area
         msk = arcpy.sa.ExtractByMask(parkRast, i)
         arr = arcpy.RasterToNumPyArray(msk, nodata_to_value=-1)
         oids = [a for a in numpy.unique(arr) if a != -1]

         # write stats
         # single-facility score
         u[2] = sumPop
         u[3] = u[1] / (sumPop/1000)

         # combined-facility score
         comb_score = sum([a[1] for a in rec_feats_scores if a[0] in oids])
         u[4] = comb_score
         u[5] = comb_score / (sumPop/1000)
         uc.updateRow(u)

         # arcpy.sa.Con(i, score_pop, i, "Value > 0").save(finalrast)

         # convert to polygon, with attributes (not doing for now; too slow)
         # arcpy.sa.Int(finalrast).save('SAint')
         # sapoly = arcpy.RasterToPolygon_conversion('SAint', 'SApoly', "NO_SIMPLIFY", "VALUE") #, create_multipart_features="MULTIPLE_OUTER_PART") # doesn't work...
         # ct = 0
         # while int(arcpy.GetCount_management(sapoly).getOutput(0)) > 1:
         #    ct = ct+1
         #    print(ct)
         #    sapoly = arcpy.Dissolve_management(sapoly, 'SAPoly' + str(ct), ["GRIDCODE"], multi_part="MULTI_PART")
         # flds = ['sa_id','sa_score','sa_sumpop','sa_scoreperpop','sa_minutes']
         # typ = ['SHORT','FLOAT','FLOAT','FLOAT','FLOAT']
         # vals = [int(''.join(filter(str.isdigit, i))), score, sumPop, score_pop, minutes_sa]
         # for fld in [0,1,2,3,4]:
         #    arcpy.AddField_management(sapoly, flds[fld], typ[fld])
         #    arcpy.CalculateField_management(sapoly, flds[fld], vals[fld])
         # # append to feature class
         # arcpy.Append_management(sapoly, "all_SA_polys", "NO_TEST")

         t1 = time.time()
         print('That took ' + str(t1 - t0) + ' seconds.')

   print('Done, joining scores to `' + feats + '`...')
   # arcpy.TableToTable_conversion(file, inGDB, "popAdj_table")
   arcpy.JoinField_management(feats, newID, rec_feats, newID,  [f[0] for f in fld_add])
   # os.remove(file)
   garbagePickup([msk])
   return


def main():

   arcpy.env.parallelProcessingFactor = "0"  # Adjust to some percent (e.g. 100%) for large extent analyses.
   arcpy.env.mask = r'L:\David\projects\RCL_processing\RCL_processing.gdb\VA_Buff50mi_wgs84'

   # create population adjustment rasters (e.g. area / population)
   arcpy.env.overwriteOutput = True
   popRast = r'E:\projects\rec_model\rec_model_processing\input_recmodel.gdb\distribPop_kdens_2020'
   arcpy.env.workspace = r'E:\projects\rec_model\rec_model_processing\serviceAreas_testing'
   # arcpy.env.workspace = r'E:\arcpro_wd\rec_model_temp\serviceAreas_modelupdate_Feb2019'

   # loop over GDBs. Put all results in same GDB
   # gdbl = arcpy.ListWorkspaces("access_t_ttrl*", "FileGDB")
   gdbl = arcpy.ListWorkspaces("servAreas_test_100ac_Richmond*")
   m = gdbl[0]
   print(m)
   inGDB = m

   # copy template polys to gdb (not using this currently)
   # arcpy.CopyFeatures_management(r'E:\arcpro_wd\rec_model_temp\input_recmodel.gdb\template_SApolys', inGDB + os.sep + 'all_SA_polys')

   # regional scoring: used join_fid (unique park) /join_score (acres)
   grpFld = "join_fid"
   attFld = "join_score"
   adjustServiceAreas(inGDB, popRast, grpFld=grpFld, attFld=attFld)

if __name__ == '__main__':
   main()