'''
AccessPoints
Created by: David Bucklin
Created on: 2021-01

This script contains processes for managing access points used in the Recreation Access Model. A template dataset
is stored at `./data/templates.gdb/template_access` and is necessary for this script. It assumes that
individual access point datasets have been generated using the tool in PrepRecDataset.py (this is done in ArcPro).

Functions include:
   updateAccessPoints: assign attributes for specific recreation types to individual access point datasets
   assocAccessPoints: final step for individual access points dataset, optionally join with recreation features
   appendAccessPoints: append an individual access point dataset to the master dataset'
   assocRecFeatures: associate recreation features to access points in the master dataset, and generate one point per
      unassociated feature
   finalizeAccessPoints: output subsets of access points from the master dataset, by recreation access type

TODO:
'''

from Helper import *
import os
import time
import arcpy
master_template = os.path.join(os.getcwd(), "data", "templates.gdb", "template_access")
# Note: Use 'tmp_' prefix used for all temporary datasets. Generally deleted at end of functions.


def updateAccessPoints(fc, query, facil_code):

   if len(facil_code[0]) == 1:
      facil_code = [facil_code]
   print('Doing update of ' + fc + ' with query `' + query + '` to for attributes `' + '`, `'.join(facil_code) + '`.')
   flds = [a.name for a in arcpy.ListFields(fc)]
   lyr = arcpy.MakeFeatureLayer_management(fc, where_clause=query)
   nrow = arcpy.GetCount_management(lyr)
   if nrow == 0:
      print('Warning: no row selected. Check query.')
   else:
      for fld in facil_code:
         if fld not in flds:
            print('Field ' + fld + ' does not exist, will add it...')
         print('Updating ' + str(nrow) + ' rows for attribute ' + fld + '...')
         arcpy.CalculateField_management(lyr, fld, "1", field_type="SHORT")
   del lyr
   return fc


def assocAccessPoints(src, join=None, join_dist=None, keep_only_joined=False):

   fld_exist = [a.name for a in arcpy.ListFields(src)]
   out = 'tmp_' + os.path.basename(src)
   # ONLY select use=1 points. This will allow further setting of this attribute.
   src_lyr = arcpy.MakeFeatureLayer_management(src, where_clause="use = 1")
   if join is not None:
      if keep_only_joined:
         # Todo: not sure this will be used. See assocRecFeatures
         keep = "KEEP_COMMON"
      else:
         keep = "KEEP_ALL"
      arcpy.SpatialJoin_analysis(src_lyr, join, out, "JOIN_ONE_TO_ONE", keep,
                                 match_option="CLOSEST", search_radius=join_dist, distance_field_name="join_dist")
      # add join fields from joined source fields
      arcpy.CalculateField_management(out, "join_table", "!src_table_1!", field_type="TEXT")
      arcpy.CalculateField_management(out, "join_fid", "!src_fid_1!", field_type="LONG")
      arcpy.CalculateField_management(out, "join_name", "!src_name_1!", field_type="TEXT")
      arcpy.CalculateField_management(out, "join_score", "!join_score_1!", field_type="DOUBLE")
      # update use fields
      lyr = arcpy.MakeFeatureLayer_management(out, where_clause='join_dist = -1')
      arcpy.CalculateField_management(lyr, 'use', "0")
      arcpy.CalculateField_management(lyr, 'use_why', "'not within join distance'")

      # Note that join_score and join_dist will already exist, so do not need changing.
   else:
      arcpy.CopyFeatures_management(src_lyr, out)
      if 'join_score' not in fld_exist:
         arcpy.CalculateField_management(out, 'join_score', "1", field_type="LONG")

   return out


def appendAccessPoints(pts, master, append=True):

   # Check table names
   tab_pts = [a[0] for a in arcpy.da.SearchCursor(pts, 'src_table')][0]
   tabs_master = list(set([a[0] for a in arcpy.da.SearchCursor(master, 'src_table')]))
   if tab_pts in tabs_master:
      # check if src_table already exsits in the master table. If it does, delete those rows.
      print('Deleting existing rows in access points for table `' + tab_pts + '`...')
      lyr = arcpy.MakeFeatureLayer_management(master, where_clause="src_table = '" + tab_pts + "'")
      arcpy.DeleteRows_management(lyr)
      del lyr
   if append:
      print('Appending rows from `' + tab_pts + '`...')
      arcpy.Append_management(pts, master, "NO_TEST")  # , expression="use = 1")  # Don't exclude use = 0. These could get assoc with a rec feature in assocAccessFeature

   return master


def assocRecFeatures(feats, master, type, join_dist, snap_to=None):

   # update an access point to use=1 and with a particular type when within `join_dist` of feature
   appendAccessPoints(feats, master, append=False)
   m_lyr = arcpy.MakeFeatureLayer_management(master)
   f_lyr = arcpy.MakeFeatureLayer_management(feats)
   arcpy.SelectLayerByLocation_management(m_lyr, "WITHIN_A_DISTANCE", f_lyr, join_dist)
   print("Updating " + str(arcpy.GetCount_management(m_lyr)) + " points with type " + type + "...")
   arcpy.CalculateField_management(m_lyr, type, "1")
   arcpy.CalculateField_management(m_lyr, "use", "1")
   # coulddo: could get messy if updating multiple times with the same dataset. Shouldn't be an issue w/ use columns though.
   arcpy.CalculateField_management(m_lyr, "use_why", "'" + type + ":within " + join_dist + " of: " + os.path.basename(feats) + ". '")
   arcpy.SelectLayerByAttribute_management(m_lyr, "CLEAR_SELECTION")
   # add access points for unassociated features
   arcpy.SelectLayerByLocation_management(f_lyr, "WITHIN_A_DISTANCE", m_lyr, join_dist, invert_spatial_relationship=True)
   if int(arcpy.GetCount_management(lyr)[0]) > 0:
      print("Generating access points for " + str(arcpy.GetCount_management(f_lyr)) + " unassociated features...")
      # coulddo: Previous method.
      #  were grouped using a 0.25 mile grouping distance (would do this prior to this step)
      #  for streams not already associated with an access point, generated one point each:
      #  for streams intersecting roads - the closest point on road intersections to the stream centroid
      #  for streams not intersecting roads - the closest point on the stream to a road
      if arcpy.Describe(f_lyr).shapeType == 'Polygon':
         arcpy.EliminatePolygonPart_management(f_lyr, 'tmp_fill', "PERCENT", part_area_percent=50, part_option="CONTAINED_ONLY")
         arcpy.FeatureToLine_management('tmp_fill', 'tmp_line')
         f_lyr = arcpy.MakeFeatureLayer_management('tmp_line')
      arcpy.FeatureToPoint_management(f_lyr, "tmp_feat", "INSIDE")  # This should generate one pt per feature (on/in the feature near center)
      if snap_to:
         # This will use an intersection with roads as the one point for the feature (for those that actually intersect)
         p_lyr = arcpy.MakeFeatureLayer_management("tmp_feat")
         arcpy.SelectLayerByLocation_management(f_lyr, "INTERSECT", snap_to, selection_type="SUBSET_SELECTION")
         arcpy.SelectLayerByLocation_management(p_lyr, "INTERSECT", f_lyr)
         arcpy.PairwiseIntersect_analysis([f_lyr, snap_to], 'tmp_ints', output_type="POINT")
         arcpy.Snap_edit(p_lyr, [['tmp_ints', "EDGE", "10 Miles"]])
         del p_lyr
      arcpy.DeleteIdentical_management('tmp_feat', 'Shape')
      arcpy.CalculateField_management('tmp_feat', "use", "2")
      arcpy.CalculateField_management('tmp_feat', "use_why", "'access point generated'")
      del m_lyr
   appendAccessPoints('tmp_feat', master)

   return master


def finalizeAccessPoints(master, out_gdb, type="all", group_dist=None, snap_to=None, snap_dist="100 Meters"):

   dt = time.strftime("%Y%m%d")
   src_gdb = os.path.basename(os.path.dirname(arcpy.Describe(master).catalogPath))
   if type == "all":
      codes = [a.name for a in arcpy.ListFields(master) if a.name.startswith(('a_', 't_'))]
   else:
      codes = [type]
   for t in codes:
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
      # add group_id
      if group_dist is not None:
         print("Grouping access points...")
         dist = str(float(group_dist.split(" ")[0]) / 2) + " " + group_dist.split(" ")[1]
         SpatialCluster(temp, dist, fldGrpID='group_id')
      else:
         # get group_id from join_fid (e.g. unique park, trail, etc)
         arcpy.CalculateField_management(temp, "group_id", "!join_fid!", field_type="LONG")
      # TODO: add minutes_sa (?)
      # TODO: check for road_distance? exclude?
      if snap_to:
         print('Snapping points to nearest feature (within ' + snap_dist + ') from `' + os.path.basename(snap_to) + '`.')
         arcpy.Snap_edit(temp, [[snap_to, "EDGE", snap_dist]])
      arcpy.CopyFeatures_management(temp, out)
      print('Output feature class: `' + out + '`...')
   # clean up
   fcs = arcpy.ListFeatureClasses("tmp_*")
   arcpy.Delete_management(fcs)
   return



# Geodatabase which contains all recreation datasets
gdb = r'E:\projects\rec_model\rec_datasets\rec_datasets_v2021.gdb'

# Roads and NHD data
roads = r'L:\David\projects\RCL_processing\Tiger_2019\roads_proc.gdb\all_subset_no_lah'
nhd_flow = r'L:\David\GIS_data\NHD\NHD_Merged.gdb\NHDFlowline'
nhd_areawtrb = r'E:\projects\rec_model\rec_datasets\rec_datasets_working.gdb\NHD_AreaWaterbody_diss'

# Make a new access points master dataset in the geodatabase
master = gdb + os.sep + 'access_points_TESTING'
if not arcpy.Exists(master):
   print('Creating new master access point dataset:', master, '...')
   arcpy.CopyFeatures_management(master_template, master)

# environments
arcpy.env.workspace = gdb
arcpy.env.outputCoordinateSystem = master_template
arcpy.env.overwriteOutput = True

# 1. working: master table/query/facility list.
#  - land should be only assigned through rec features (public lands).
#  - trails (assign only through features? Might be an issue with many missing trails in data)
# These are ONLY for cases where a subset of the table is considered for the type. Global assignments of a
# type (e.g. trail access for trailheads data, boat access for boat ramps data) happen in PrepRecDataset.py.
table_facil = [['DGIF_WMA_Facilities', "TYPE = 'Boat Ramp'", "a_wct"],
               ['DGIF_WMA_Facilities', "TYPE = 'Fishing Pier'", "a_fsh"],
               ['DGIF_WMA_Facilities', "TYPE IN ('Gate', 'Seasonal Gate', 'Parking')", ("t_trl", "t_lnd")],   # decide: gates as access points?
               ['dcrWaterAccess2020_upd', "FISHING = 'Y'", "a_fsh"],
               ['dcrWaterAccess2020_upd', "SWIMMING = 'Y'", "a_swm"],
               # todo: local park points being reviewed...
               # ['LocalParkInventory_2021_QC', "WATER_ACCESS in ('CANOE SLIDE','BOAT RAMP', 'ALL')", "a_wct"],
               # ['LocalParkInventory_2021_QC', "WATER_ACCESS in ('PIER', 'ALL')", "a_fsh"],
               # ['LocalParkInventory_2021_QC', "SWIMMING_AREA = 'BEACH'", "a_swm"],
               # ['LocalParkInventory_2021_QC', "TRAIL_TYPE IN ('BIKE', 'FITNESS', 'HIKING', 'HORSE', 'MULTI-USE')", "t_trl"],
               ['Birding_Wildlife_Trail_Sites', "facil_fix LIKE '%boat_ramp%' OR facil_fix LIKE '%kayak%'", "a_wct"],
               ['Birding_Wildlife_Trail_Sites', "facil_fix LIKE '%trail%'", "t_trl"]]
ls = arcpy.ListFeatureClasses('prep_*', "Point")
for i in ls:
   src = [a[0] for a in arcpy.da.SearchCursor(i, 'src_table')][0]
   facil = [a for a in table_facil if a[0] == src]
   for f in facil:
      updateAccessPoints(i, f[1], f[2])
   print('Done updating ' + i + '.')


# 2. Loop over access point datasets
ls = arcpy.ListFeatureClasses('prep_*', "Point")
ls_join = [['bla', None, '0.25 Miles']]  # testing; for land and trail association.
for i in ls:
   if i in [a[0] for a in ls_join]:
      ap = assocAccessPoints(i[0], i[1], i[2])
   else:
      ap = assocAccessPoints(i)
   appendAccessPoints(ap, master)
   arcpy.Delete_management(ap)

# 3. Associate and make one-point-per for un-assoc recreation features (lands, trail networks, stocked trout reaches)
ls = arcpy.ListFeatureClasses('prep_*', "Line") + arcpy.ListFeatureClasses('prep_*', "Polygon")
ls
# One run per dataset
assocRecFeatures('prep_Stocked_Trout_Reaches_20210119', master, 'a_fsh', '0.25 Miles', snap_to=roads)
assocRecFeatures('prep_Lake_Centroids_featNHDWaterbody_20210119', master, 'a_fsh', '0.25 Miles', snap_to=roads)
assocRecFeatures('prep_Stocked_Trout_Lakes_featNHDWaterbody_20210119', master, 'a_fsh', '0.25 Miles', snap_to=roads)


# TODO: set criteria for exclusion based on join_score (e.g. small trails, parks)?

# 4. Make final access pionts datasets. One per access type.
# Note: some points may be in the master dataset, but with no associated types. These will not be in any final datasets.
out_gdb = r'E:\projects\rec_model\rec_model_processing\access_pts.gdb'
finalizeAccessPoints(master, out_gdb, group_dist="0.25 Miles")  # , snap_to=roads decide: snap here or when generating access points?


# end
