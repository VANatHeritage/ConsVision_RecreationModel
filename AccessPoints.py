"""
AccessPoints
Created by: David Bucklin
Created on: 2021-01

This script contains processes for managing access points used in the Recreation Access Model. A template dataset
is stored at `./data/templates.gdb/template_access` and is necessary for this script. It assumes that
individual access point datasets have been generated using the tool in PrepRecDataset.py (this is done in ArcPro).

Functions include:
   updateFacilCodes: assign attributes for specific recreation types to individual recreation datasets
   appendAccessPoints: append an individual access point dataset to the master dataset
   generateAccessPoints: internal fn to generate access points from features based on distance to near features
   assocRecFeatures: associate recreation features to access points in the master dataset, and generate one point per
      unassociated feature
   assocAccessPoints: associate access point master dataset with recreation features (PPA), updating `join_` attributes
      and generating points for unassociated join features
   finalizeAccessPoints: output subsets of access points from the master dataset, by recreation access type
"""

from Helper import *
from arcpro.Helper import *
import os
import time
import arcpy
master_template = os.path.join(os.getcwd(), "data", "templates.gdb", "template_access")
# Note: Use 'tmp_' prefix used for all temporary datasets. Generally deleted at end of functions.


def updateFacilCodes(fc, query, facil_code, update_to=1):

   if len(facil_code[0]) == 1:
      facil_code = [facil_code]
   print('Doing update of ' + fc + ' with query `' + query + '` for attributes `' + '`, `'.join(facil_code) + '`.')
   flds = [a.name for a in arcpy.ListFields(fc)]
   lyr = arcpy.MakeFeatureLayer_management(fc, where_clause=query)
   nrow = arcpy.GetCount_management(lyr)
   if nrow == 0:
      print('Warning: no rows selected. Check query.')
   else:
      for fld in facil_code:
         if fld not in flds:
            print('Field ' + fld + ' does not exist, will add it...')
         print('Updating ' + str(nrow) + ' rows for attribute ' + fld + ' to value = ' + str(update_to) + '...')
         arcpy.CalculateField_management(lyr, fld, '"' + str(update_to) + '"', field_type="SHORT")
   del lyr
   return fc


def appendAccessPoints(pts, master, apply=True):

   # Check table names
   tab_pts = [a[0] for a in arcpy.da.SearchCursor(pts, 'src_table')][0]
   tabs_master = list(set([a[0] for a in arcpy.da.SearchCursor(master, 'src_table')]))
   if tab_pts in tabs_master:
      # check if src_table already exsits in the master table. If it does, delete those rows.
      print('Deleting existing access points originating from table `' + tab_pts + '`...')
      lyr = arcpy.MakeFeatureLayer_management(master, where_clause="src_table = '" + tab_pts + "'")
      arcpy.DeleteRows_management(lyr)
      del lyr
   if apply:
      print('Appending rows from `' + tab_pts + '`...')
      arcpy.Append_management(pts, master, "NO_TEST") #, expression="use = 1")  # Don't exclude use = 0
   return master


def generateAccessPoints(feats, near_to=None, out='tmp_generated_pts'):

   arcpy.CopyFeatures_management(feats, 'tmp_unassoc')
   print("Generating access points for " + str(arcpy.GetCount_management('tmp_unassoc')) + " unassociated features...")

   if arcpy.Describe('tmp_unassoc').shapeType == 'Polygon':
      arcpy.EliminatePolygonPart_management('tmp_unassoc', 'tmp_fill', "PERCENT", part_area_percent=50,
                                            part_option="CONTAINED_ONLY")
      arcpy.FeatureToLine_management('tmp_fill', 'tmp_line')
      f_lyr = arcpy.MakeFeatureLayer_management('tmp_line')
   else:
      f_lyr = arcpy.MakeFeatureLayer_management('tmp_unassoc')
   if not near_to:
      # This should generate one pt per feature (on/in the feature near center)
      arcpy.FeatureToPoint_management(f_lyr, out, "INSIDE")
   else:
      # get all intersections with those intersecting near_to
      arcpy.SelectLayerByLocation_management(f_lyr, "INTERSECT", near_to)
      arcpy.PairwiseIntersect_analysis([f_lyr, near_to], 'tmp_ints', output_type="POINT")
      arcpy.MultipartToSinglepart_management('tmp_ints', 'tmp_feat')
      arcpy.CalculateField_management('tmp_feat', 'NEAR_DIST', '0', field_type="FLOAT")
      arcpy.SelectLayerByAttribute_management(f_lyr, "SWITCH_SELECTION")
      print("Finding nearest point to near_to features...")
      arcpy.FeatureVerticesToPoints_management(f_lyr, 'tmp_feat0a', "DANGLE")  # "ALL" is too many points
      arcpy.GeneratePointsAlongLines_management(f_lyr, 'tmp_feat0b', 'DISTANCE', Distance='300 Feet',
                                                Include_End_Points='END_POINTS')
      arcpy.Merge_management(['tmp_feat0a', 'tmp_feat0b'], 'tmp_feat0')
      # features > 1 mile distant will not receive an access point
      arcpy.Near_analysis('tmp_feat0', near_to, "1 Mile")
      arcpy.Select_analysis('tmp_feat0', 'tmp_feat1', "NEAR_DIST >= 0")
      arcpy.Append_management('tmp_feat1', 'tmp_feat', "NO_TEST")
      # Now reduce points to one per input feature
      arcpy.Sort_management('tmp_feat', out, [["src_fid", "ASCENDING"], ["NEAR_DIST", "ASCENDING"]])
      arcpy.DeleteIdentical_management(out, ["src_fid"])
      # coulddo: Add one centroid point for those features not within the near distance of near_to
      # arcpy.SelectLayerByAttribute_management(f_lyr, "SWITCH_SELECTION")
      # arcpy.FeatureToPoint_management(f_lyr, "tmp_feat2", "INSIDE")
      # arcpy.Append_management('tmp_feat2', 'tmp_feat', "NO_TEST")

      # Assign use attributes
      arcpy.CalculateField_management(out, "use", "2")
      arcpy.CalculateField_management(out, "use_why", "'access point generated'")

   return out


def assocRecFeatures(feats, master, facil_codes, join_dist, near_to=None):
   # updates access point facil_code(s) when within the `join_dist` of a recreation feature. Will generate
   # one point per unassociated feature, based on relationship with near_to features.

   # feats='prep_VATrails_2021_20210317_final_group_20210324'
   # facil_codes='t_trl'
   # join_dist='300 Feet'
   # near_to=roads

   if not isinstance(facil_codes, list):
      facil_codes = [facil_codes]

   # This will delete existing points in the master table, which originated from the current table.
   appendAccessPoints(feats, master, apply=False)

   # Set up layers
   # Note: only update use = 1 here (exclude generated points (2))
   m_lyr = arcpy.MakeFeatureLayer_management(master, where_clause="use = 1")
   f_lyr = arcpy.MakeFeatureLayer_management(feats, where_clause="use > 0")
   arcpy.SelectLayerByLocation_management(m_lyr, "WITHIN_A_DISTANCE", f_lyr, join_dist)
   for f in facil_codes:
      print("Updating " + str(arcpy.GetCount_management(m_lyr)) + " points with type " + f + "...")
      arcpy.CalculateField_management(m_lyr, f, '1')
      # use_why could get messy if updating multiple times with the same dataset. Shouldn't be an issue with use though.
      arcpy.CalculateField_management(m_lyr, "use_why", "'" + f + ":within " + join_dist + " of: " + os.path.basename(feats) + ". '")
   arcpy.SelectLayerByAttribute_management(m_lyr, "CLEAR_SELECTION")

   # add access points for unassociated features
   arcpy.SelectLayerByLocation_management(f_lyr, "WITHIN_A_DISTANCE", m_lyr, join_dist, invert_spatial_relationship=True)
   del m_lyr
   if int(arcpy.GetCount_management(f_lyr)[0]) > 0:
      gen = generateAccessPoints(f_lyr, near_to)
      appendAccessPoints(gen, master)

   return master


def assocAccessPoints(master, join, join_dist, facil_codes=[], only_unjoined=True, near_to=None):
   # update access point 'join_' fields with join features (PPAs)

   if not isinstance(facil_codes, list):
      facil_codes = [facil_codes]

   if only_unjoined:
      lyr = arcpy.MakeFeatureLayer_management(master, where_clause='use > 0 AND join_table IS NULL')
      if arcpy.GetCount_management(lyr) == '0':
         print('All points already joined, returning with no changes...')
         return master
   else:
      # remove existing points originating from table
      appendAccessPoints(join, master, apply=False)
      lyr = arcpy.MakeFeatureLayer_management(master, where_clause='use > 0')

   print('Joining `' + os.path.basename(master) + '` with features `' +
         os.path.basename(join) + '` at a distance of `' + join_dist + '`.')
   join_lyr = arcpy.MakeFeatureLayer_management(join, where_clause="use > 0")
   # Keep all points; this will mean that all included points are updated (which depends on only_unjoined)
   arcpy.SpatialJoin_analysis(lyr, join_lyr, 'tmp_sj', "JOIN_ONE_TO_ONE", join_type="KEEP_ALL", match_option="CLOSEST",
                              search_radius=join_dist, distance_field_name="join_dist_1")
   flds = ['src_table', 'src_fid', 'src_name', "join_score", "join_dist"]
   flds1 = [f + '_1' for f in flds]
   del lyr
   arcpy.JoinField_management(master, 'OBJECTID', 'tmp_sj', 'TARGET_FID', flds1)
   # coulddo: use only_unjoined again?
   if only_unjoined:
      # only allow update of un-joined points
      lyr = arcpy.MakeFeatureLayer_management(master, where_clause='use > 0 AND join_table IS NULL')
   else:
      lyr = arcpy.MakeFeatureLayer_management(master, 'use > 0')
   # add join fields from joined source fields
   for f in flds:
      cf = f.replace('src_', 'join_')
      arcpy.CalculateField_management(lyr, cf, "!" + f + "_1!")
   # now update facil_codes only for joined access points
   arcpy.SelectLayerByAttribute_management(lyr, "NEW_SELECTION", "src_table_1 IS NOT NULL")
   nrow = arcpy.GetCount_management(lyr)[0]
   for f in facil_codes:
      print('Updating ' + nrow + ' rows for facil_code `' + f + '`...')
      arcpy.CalculateField_management(lyr, f, '1')
   del lyr
   arcpy.DeleteField_management(master, flds1)

   if not only_unjoined:
      # get IDs of un-associated features (not associated with a use > 0 access point)
      assoc = [str(a[0]) for a in arcpy.da.SearchCursor(master, ['join_fid', 'use']) if a[1] > 0 and a[0] is not None]
      f_lyr = arcpy.MakeFeatureLayer_management(join, where_clause="src_fid NOT IN (" + ",".join(assoc) + ")")
      gen = generateAccessPoints(f_lyr, near_to)
      for f in ['src_fid', 'src_table', 'src_name']:
         arcpy.CalculateField_management(gen, f.replace('src_', 'join_'), "!" + f + "!")
      appendAccessPoints(gen, master)
   # clean up
   arcpy.Delete_management('tmp_sj')

   return master


def finalizeAccessPoints(master, out_gdb, facil_codes="all", group_dist=None, snap_to=None, snap_dist="300 Feet",
                         combine=False):

   dt = time.strftime("%Y%m%d")
   src_gdb = os.path.basename(os.path.dirname(arcpy.Describe(master).catalogPath))
   if facil_codes == "all":
      facil_codes = [a.name for a in arcpy.ListFields(master) if a.name.startswith(('a_', 't_'))]
   else:
      if not isinstance(facil_codes, list):
         facil_codes = [facil_codes]
   lso = []
   for t in facil_codes:
      print('Working on ' + t + '...')
      # decide: use = 2 are the 'generated' points for features, so want to include those
      lyr = arcpy.MakeFeatureLayer_management(master, where_clause=t + " = 1 AND use IN (1,2)")
      if arcpy.GetCount_management(lyr)[0] == '0':
         print('No points for ' + t)
         del lyr
         continue
      temp = 'tmp_' + t
      out = out_gdb + os.sep + os.path.basename(master) + '_' + t + '_' + dt
      arcpy.CopyFeatures_management(lyr, temp)
      del lyr
      # add src_gdb column
      arcpy.CalculateField_management(temp, 'src_gdb', "'" + src_gdb + "'", field_type="TEXT")
      if snap_to:
         # snap before grouping
         print('Snapping points to nearest feature (within ' + snap_dist + ') of snap_to features...')
         arcpy.Snap_edit(temp, [[snap_to, "EDGE", snap_dist]])
      # add group_id
      if group_dist is not None:
         print("Grouping access points...")
         dist = str(float(group_dist.split(" ")[0]) / 2) + " " + group_dist.split(" ")[1]
         SpatialCluster_GrpFld(temp, dist, fldGrpID='group_id', chain=False)
      else:
         # get group_id from join_fid (e.g. unique park, trail, etc)
         arcpy.CalculateField_management(temp, "group_id", "!join_fid!", field_type="LONG")
      arcpy.CopyFeatures_management(temp, out)
      arcpy.DeleteIdentical_management(out, ["Shape", "group_id"])
      print('Output feature class: `' + out + '`...')
      lso.append(out)
   if combine and len(lso) > 1:
      out = out_gdb + os.sep + os.path.basename(master) + '_combined_' + dt
      print('Combining access points in feature class ' + out + '...')
      arcpy.Merge_management(lso, out)
      arcpy.DeleteField_management(out, "group_id")
      if group_dist is not None:
         print("Grouping access points...")
         dist = str(float(group_dist.split(" ")[0]) / 2) + " " + group_dist.split(" ")[1]
         SpatialCluster_GrpFld(out, dist, fldGrpID='group_id', chain=False)
      else:
         # get group_id from join_fid (e.g. unique park, trail, etc)
         arcpy.CalculateField_management(out, "group_id", "!join_fid!", field_type="LONG")
      # remove exact duplicate points
      arcpy.DeleteIdentical_management(out, ["Shape", "src_table", "src_fid"])
   # clean up
   fcs = arcpy.ListFeatureClasses("tmp_*")
   arcpy.Delete_management(fcs)
   return


### HEADER

# Geodatabase which contains all recreation datasets
gdb = r'E:\projects\rec_model\rec_datasets\rec_datasets_v2021.gdb'

# public access parks/protected areas
# TODO: make sure to make new prepped PPAs, when public_lands_final is updated.
ppa = gdb + os.sep + 'prep_public_lands_final_20210426'
ppa_nm = [a[0] for a in arcpy.da.SearchCursor(ppa, 'src_table')][0]

# Roads and NHD data
# TIGER (deprecated)
# roads0 = r'L:\David\projects\RCL_processing\Tiger_2020\roads_proc.gdb\all_subset_no_lah'
# roads = arcpy.MakeFeatureLayer_management(roads0, where_clause="MTFCC <> 'S1630'")
# OSM Roads - for locating generated points. Exclude motorways and trunks.
roads0 = r'E:\projects\OSM\OSM_RoadsProc.gdb\OSM_Roads_20210422'
roads = arcpy.MakeFeatureLayer_management(roads0, where_clause="code NOT IN (5111, 5112, 5131, 5132)")
nhd_flow = r'L:\David\GIS_data\NHD\NHD_Merged.gdb\NHDFlowline'
nhd_areawtrb = r'E:\projects\rec_model\rec_datasets\rec_datasets_working.gdb\NHD_AreaWaterbody_diss'

# Make a new access points master dataset in the geodatabase
master = gdb + os.sep + 'access_points'
if not arcpy.Exists(master):
   print('Creating new master access point dataset:', master, '...')
   arcpy.CopyFeatures_management(master_template, master)
else:
   # make a copy of master dataset as it exists now
   arch = master + '_archived' + Ymd()
   print('Archiving existing access points to layer `' + arch + '`')
   arcpy.CopyFeatures_management(master, arch)

# environments
arcpy.env.workspace = gdb
arcpy.env.outputCoordinateSystem = master_template

# GDB where finalized access point datasets are output
accfinal_gdb = r'E:\projects\rec_model\rec_model_processing\access_pts.gdb'


# END HEADER


# 1. working: Assign facility types [src_table, query, access type] in this list.
# These are ONLY for cases where a subset of the table is considered for the type. Global assignments of a
# type (e.g. trail access for trailheads data, boat access for boat ramps data) happen in PrepRecDataset.py.
table_facil = [['DGIF_WMA_Facilities', "TYPE = 'Boat Ramp'", "a_wct"],
               ['DGIF_WMA_Facilities', "TYPE = 'Fishing Pier'", "a_fsh"],
               ['DGIF_WMA_Facilities', "TYPE IN ('Parking')", "t_lnd"],
               ['Fishing_Access_Sites', "AccessType IS NOT NULL AND AccessType <> 'Fishing Pier'", "a_wct"],
               # ['DGIF_WMA_Facilities', "TYPE IN ('Gate', 'Seasonal Gate')", ("t_trl", "t_lnd")], # decide: gates as access points?
               ['dcrWaterAccess2020_upd', "FISHING = 'Y'", "a_fsh"],
               ['dcrWaterAccess2020_upd', "SWIMMING = 'Y'", "a_swm"],
               ['dcrWaterAccess2020_upd', "TRAIL = 'Y'", "t_trl"],
               ['PFA', "CANOE_ACCE = 'Y'", "a_wct"],
               ['boatLaunches_DNR_200410_utm83', "handicapfa LIKE 'Y%'", "a_fsh"],
               # Coulddo: local park points being reviewed...may be polygons. May have different attributes. Use as below for now.
               ['LocalParkInventory_2021_QC', "WATER_ACCESS in ('CANOE SLIDE','BOAT RAMP', 'ALL')", "a_wct"],
               ['LocalParkInventory_2021_QC', "WATER_ACCESS in ('PIER', 'ALL')", "a_fsh"],
               ['LocalParkInventory_2021_QC', "SWIMMING_AREA = 'BEACH'", "a_swm"],
               ['LocalParkInventory_2021_QC', "TRAIL_TYPE IN ('BIKE', 'FITNESS', 'HIKING', 'HORSE', 'MULTI-USE')", "t_trl"],
               ['Birding_Wildlife_Trail_Sites', "facil_fix LIKE '%boat_ramp%' OR facil_fix LIKE '%kayak%'", "a_wct"],
               ['Birding_Wildlife_Trail_Sites', "facil_fix LIKE '%trail%'", "t_trl"],
               ['Public_Access_Sites_2009-2019', "Boat IN ('Yes', 'yes', 'Carry')", "a_wct"],
               ['Public_Access_Sites_2009-2019', "Fish IN ('Yes', 'yes')", "a_fsh"],
               ['Public_Access_Sites_2009-2019', "Swim IN ('Yes', 'yes')", "a_swm"],
               ['TWRA_BoatLaunchAccess', "FishingPie = 'Yes'", "a_fsh"],
               ['TWRA_FishingAccess', "CanoeLandi = 'Yes'", "a_wct"],
               [ppa_nm, "trlacc_acres IS NOT NULL", "t_trl"]]
ls = arcpy.ListFeatureClasses('prep_*')
for i in ls:
   if 'src_table' not in [a.name for a in arcpy.ListFields(i)]:
      continue
   src = [a[0] for a in arcpy.da.SearchCursor(i, 'src_table')][0]
   facil = [a for a in table_facil if a[0] == src]
   for f in facil:
      updateFacilCodes(i, f[1], f[2])
   print('Done updating ' + i + '.')


# 2. Loop over access point datasets, appending to the master dataset
ls = arcpy.ListFeatureClasses('prep_*', "Point")
exist = list(set([a[0] for a in arcpy.da.SearchCursor(master, 'src_table')]))
for i in ls:
   t = [a[0] for a in arcpy.da.SearchCursor(i, 'src_table')][0]
   if t not in exist:
      appendAccessPoints(i, master)
   else:
      print('Table ' + i + ' already in master dataset, skipping...')


# 3. Associate and make one-point-per for un-assoc recreation features (lands, trail networks, stocked trout reaches)
ls = arcpy.ListFeatureClasses('prep_*', "Line") + arcpy.ListFeatureClasses('prep_*', "Polygon")
ls
# Note: these can run for 5-10 minutes each, if many features are unassociated and need to have points generated.
# Fishing lakes/streams
assocRecFeatures('prep_Stocked_Trout_Reaches_20210119', master, 'a_fsh', '300 Feet', near_to=roads)
assocRecFeatures('prep_Lake_Centroids_featNHDWaterbody_20210119', master, 'a_fsh', '300 Feet', near_to=roads)
assocRecFeatures('prep_Stocked_Trout_Lakes_featNHDWaterbody_20210119', master, 'a_fsh', '300 Feet', near_to=roads)
assocRecFeatures('prep_publicFishingAreas_DNR_200204_ll83_20210401', master, 'a_fsh', '300 Feet', near_to=roads)
# Trails
trails_group = 'prep_VATrails_2021_20210317_final_group_20210325'
# update to set use = 1 for networks >=1 mile in length
arcpy.CalculateField_management(trails_group, 'use', "min(math.floor(!join_score!), 1)")
assocRecFeatures(trails_group, master, 't_trl', '300 Feet', near_to=roads)


# 4a. Update access points `join_` fields from the PPAs. Also generates one point per unassociated PPA.
# [a.name for a in arcpy.ListFields(ppa)]
arcpy.CalculateField_management(ppa, 'join_score', '!accgreen_acres!')
assocAccessPoints(master, join=ppa, join_dist='300 Feet', facil_codes=['t_lnd'], only_unjoined=False, near_to=roads)

# 4b. Create a new PPA layer with facil_code counts added
flds = ['t_lnd', 't_trl', 'a_wct', 'a_fsh', 'a_swm', 'a_gen']
ppa_facil = 'public_lands_facil_' + Ymd()
lyr = arcpy.MakeFeatureLayer_management(master, where_clause="use IN (1, 2)")
arcpy.Statistics_analysis(lyr, 'stats_facil_codes', [[f, "SUM"] for f in flds], case_field="join_fid")
del lyr
arcpy.CopyFeatures_management(ppa, ppa_facil)
arcpy.JoinField_management(ppa_facil, 'src_fid', 'stats_facil_codes', 'join_fid', ['SUM_' + f for f in flds])
for f in flds:
   print(f)
   nullToZero(ppa_facil, f)
   nullToZero(ppa_facil, 'SUM_' + f)
   arcpy.CalculateField_management(ppa_facil, f, '!' + f + '! + !SUM_' + f + '!')
cb = " + ".join(["max(0, min(1, !" + f + "!))" for f in flds])
arcpy.CalculateField_management(ppa_facil, 'facil_variety', cb, field_type="LONG")
nullToZero(ppa_facil, 'facil_variety')
# NOTE: Delete field can corrupt the feature class randomly.
arcpy.DeleteField_management(ppa_facil, ['SUM_' + f for f in flds])
[a.name for a in arcpy.ListFields(ppa_facil)]


# 5. update aquatic access points if not within 0.25 Miles of a waterbody or stream.
lyr = arcpy.MakeFeatureLayer_management(master, where_clause="(a_wct = 1 OR a_swm = 1 OR a_fsh = 1 OR a_gen = 1)")
arcpy.SelectLayerByAttribute_management(lyr, "NEW_SELECTION")
arcpy.SelectLayerByLocation_management(lyr, "WITHIN_A_DISTANCE", nhd_flow, "0.25 Miles", "REMOVE_FROM_SELECTION")
arcpy.SelectLayerByLocation_management(lyr, "WITHIN_A_DISTANCE", nhd_areawtrb, "0.25 Miles", "REMOVE_FROM_SELECTION")
# Update aquatic-related access types to 0, if not within 0.25 miles of water feature.
if arcpy.GetCount_management(lyr)[0] != '0':
   [arcpy.CalculateField_management(lyr, i, '0') for i in ['a_wct', 'a_fsh', 'a_gen', 'a_swm']]
   arcpy.CalculateField_management(lyr, 'use_why', "'QC: Not near NHD features; removed aquatic access types.'")
del lyr


# 6. Make final access points datasets
# Note: points could be use=1 in the master dataset, but with no associated access types. These will not be in
# finalized datasets, since these are based off of specific access type(s).

# Public land access
# decide: snap here? how to group? Just by distance or with join_fid from PPA?
finalizeAccessPoints(master, accfinal_gdb, facil_codes='t_lnd', group_dist=None)
outpts = accfinal_gdb + os.sep + os.path.basename(master) + '_t_lnd_' + Ymd()
# join the AG acres and group_id from PPAs (rename it ppa_group_id).
arcpy.JoinField_management(outpts, 'join_fid', ppa, 'src_fid', ['accgreen_acres', 'group_id'])
arcpy.AlterField_management(outpts, 'group_id_1', 'ppa_group_id', clear_field_alias=True)

# Water access
finalizeAccessPoints(master, accfinal_gdb, facil_codes=['a_swm', 'a_wct', 'a_fsh'], group_dist="0.25 Miles", combine=True)
outpts = accfinal_gdb + os.sep + 'access_points_combined_' + Ymd()
flds = ['a_wct', 'a_fsh', 'a_swm']
arcpy.Statistics_analysis(outpts, 'facil', [[f, "SUM"] for f in flds], case_field="group_id")
cb = " + ".join(["max(0, min(1, !SUM_" + f + "!))" for f in flds])
arcpy.CalculateField_management('facil', 'group_facil_a_variety', cb, field_type="LONG")
nullToZero('facil', 'group_facil_a_variety')
arcpy.JoinField_management(outpts, 'group_id', 'facil', 'group_id', 'group_facil_a_variety')


# end
