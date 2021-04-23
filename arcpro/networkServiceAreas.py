'''
networkServiceAreas

Network Analyst-based processes for all recreation model analyses. Includes functions for:
   - Service areas
   - Travel time to nearest
   - Catchments (non-overlapping service areas)

Created: 2021-04-21
Last Updated: 2021-04-23
ArcGIS version: ArcGIS Pro
Python version: Python 3.6.6
Author: David Bucklin
'''

from arcpro.Helper import *
arcpy.CheckOutExtension("network")


def networkServiceAreas(net, facil, facil_group, outSA, joinatt=['src_name', 'join_name', 'accgreen_acres'], minutes=30, poly_trim="300 Feet", dist_from_roads="1 Mile",
                        search_criteria=[["Roads_Local", "SHAPE"], ["Roads_Hwy", "NONE"], ["Ramp_Points", "NONE"], ["RoadsNet_ND_Junctions", "NONE"]],
                        search_query=[["Roads_Local", '"code" IN (5112, 5113, 5114, 5115, 5121, 5122, 5123, 5132, 5133, 5134, 5135, 5141, 5142, 5143, 5144, 5145, 5146, 5147)']],
                        rastTemplate=None):
   '''
   Generate individual service areas, and count overlaps
   :param net: Network dataset
   :param facil: Facilities (points)
   :param facil_group:  Facility grouping field name
   :param outSA: Output service area layer base name
   :param minutes: Minute limit for service areas
   :param poly_trim: Polygon trim distance for service areas (equivalent to a buffer around roads)
   :param dist_from_roads: Search distance limit for starting point from facilities to roads
   :param search_criteria: Layer criteria for searching for staring point for facilities
   :param search_query: Layer-specific criteria (queries) for searching for staring point for facilities
   :param rastTemplate: Raster template for overlap raster (coordinate system)
   :return:
   '''
   # Search_criteria is used to only locate points on certain road types (default on only Roads_Local).
   # Search_query is further used to subset the road types where points can be located (default only driveable roads).
   print('Making analysis layer at ' + Hms() + '...')
   arcpy.MakeServiceAreaAnalysisLayer_na(net, "ServiceAreas", "Drive", "TO_FACILITIES", cutoffs=[minutes],
                                         output_type="POLYGONS", polygon_detail="STANDARD",
                                         geometry_at_overlaps="OVERLAP", geometry_at_cutoffs="DISKS",
                                         polygon_trim_distance=poly_trim)
   print('Adding locations at ' + Hms() + '...')
   arcpy.AddLocations_na("ServiceAreas", "Facilities", facil,
                         "Name " + facil_group + " #", dist_from_roads, facil_group,
                         search_criteria, "MATCH_TO_CLOSEST", "CLEAR", "NO_SNAP", "5 Meters", "EXCLUDE", search_query)
   print('Solving service areas at ' + Hms() + '...')
   arcpy.Solve_na("ServiceAreas", "SKIP", "TERMINATE")
   print('Dissolving services areas by ' + facil_group + ' at ' + Hms() + '...')
   arcpy.CopyFeatures_management(r"ServiceAreas\Polygons", outSA + '_orig')
   arcpy.CalculateField_management(outSA + '_orig', facil_group, "int(!Name!.split(' : ')[0])", field_type="LONG")
   arcpy.Dissolve_management(outSA + '_orig', outSA, facil_group, multi_part="MULTI_PART")
   print('Counting service areas overlaps at ' + Hms() + '...')
   arcpy.CountOverlappingFeatures_analysis(outSA, outSA + '_ct_poly', 1)
   if rastTemplate:
      print('Rasterizing overlap counts at ' + Hms() + '...')
      # note: mask env not used in Poly2Rast
      with arcpy.EnvManager(outputCoordinateSystem=rastTemplate, snapRaster=rastTemplate, cellSize=rastTemplate, extent=rastTemplate, mask=rastTemplate):
         arcpy.PolygonToRaster_conversion(outSA + '_ct_poly', 'COUNT_', 'r0', cellsize=rastTemplate)
         arcpy.sa.Con(arcpy.sa.IsNull('r0'), 0, 'r0').save(outSA + '_ct')
      arcpy.BuildPyramids_management(outSA + '_ct')
      arcpy.Delete_management(outSA + '_ct_poly')

   jf = [a.name for a in arcpy.ListFields(facil) if a.name in joinatt]
   if len(jf) > 0:
      print('Joining attributes to service areas...')
      arcpy.JoinField_management(outSA, facil_group, facil, facil_group, jf)

   # Clean up (all) service area datasets in current GDB
   ls = arcpy.ListDatasets('ServiceArea*')
   arcpy.Delete_management(ls)

   return outSA


def networkTravelToNearest(net, facil, facil_group, outSA, minutes=list(range(5, 121, 5)), poly_trim="300 Feet", dist_from_roads="1 Mile",
                        search_criteria=[["Roads_Local", "SHAPE"], ["Roads_Hwy", "NONE"], ["Ramp_Points", "NONE"], ["RoadsNet_ND_Junctions", "NONE"]],
                        search_query=[["Roads_Local", '"code" IN (5112, 5113, 5114, 5115, 5121, 5122, 5123, 5132, 5133, 5134, 5135, 5141, 5142, 5143, 5144, 5145, 5146, 5147)']],
                        rastTemplate=None):
   '''
   Generate individual service areas, and count overlaps
   :param net: Network dataset
   :param facil: Facilities (points)
   :param facil_group:  Facility grouping field name
   :param outSA: Output service area layer base name
   :param minutes: List of travel-time breaks
   :param poly_trim: Polygon trim distance for service areas (equivalent to a buffer around roads)
   :param dist_from_roads: Search distance limit for starting point from facilities to roads
   :param search_criteria: Layer criteria for searching for staring point for facilities
   :param search_query: Layer-specific criteria (queries) for searching for staring point for facilities
   :param rastTemplate: Raster template for overlap raster (coordinate system)
   :return:
   '''
   # Search_criteria is used to only locate points on certain road types (default on only Roads_Local).
   # Search_query is further used to subset the road types where points can be located (default only driveable roads).
   print('Making analysis layer at ' + Hms() + '...')
   arcpy.MakeServiceAreaAnalysisLayer_na(net, "ServiceAreas", "Drive", "TO_FACILITIES", cutoffs=minutes,
                                         output_type="POLYGONS", polygon_detail="STANDARD",
                                         geometry_at_overlaps="DISSOLVE", geometry_at_cutoffs="RINGS",
                                         polygon_trim_distance=poly_trim)
   print('Adding locations at ' + Hms() + '...')
   arcpy.AddLocations_na("ServiceAreas", "Facilities", facil,
                         "Name " + facil_group + " #", dist_from_roads, facil_group,
                         search_criteria, "MATCH_TO_CLOSEST", "CLEAR", "NO_SNAP", "5 Meters", "EXCLUDE", search_query)
   print('Solving service areas at ' + Hms() + '...')
   arcpy.Solve_na("ServiceAreas", "SKIP", "TERMINATE")
   arcpy.CopyFeatures_management(r"ServiceAreas\Polygons", outSA)
   arcpy.CalculateField_management(outSA, 'minutes', '!ToBreak!', field_type="LONG")
   if rastTemplate:
      print('Rasterizing travel time breaks at ' + Hms() + '...')
      with arcpy.EnvManager(outputCoordinateSystem=rastTemplate, snapRaster=rastTemplate, cellSize=rastTemplate, extent=rastTemplate, mask=rastTemplate):
         arcpy.PolygonToRaster_conversion(outSA, 'minutes', 'r0', cellsize=rastTemplate)
      arcpy.BuildPyramids_management(outSA + '_rast')

   # Clean up (all) service area datasets in current GDB
   ls = arcpy.ListDatasets('ServiceArea*')
   arcpy.Delete_management(ls)

   return outSA


def networkCatchments(net, facil, facil_group, outSA, boundary, joinatt=['src_name', 'join_name', 'accgreen_acres'], minutes=30, poly_trim="300 Feet", dist_from_roads="1 Mile",
                        search_criteria=[["Roads_Local", "SHAPE"], ["Roads_Hwy", "NONE"], ["Ramp_Points", "NONE"], ["RoadsNet_ND_Junctions", "NONE"]],
                        search_query=[["Roads_Local", '"code" IN (5112, 5113, 5114, 5115, 5121, 5122, 5123, 5132, 5133, 5134, 5135, 5141, 5142, 5143, 5144, 5145, 5146, 5147)']]):
   '''
   Generate individual service areas, and count overlaps
   :param net: Network dataset
   :param facil: Facilities (points)
   :param facil_group: Facility grouping field name
   :param outSA: Output service area layer base name
   :param boundary: Feature class boundary (used for filling in gaps in catchments)
   :param minutes: Minute limit for service areas
   :param joinatt: Attributes from input facilities (facil) to join to output catchments (outSA)
   :param poly_trim: Polygon trim distance for service areas (equivalent to a buffer around roads)
   :param dist_from_roads: Search distance limit for starting point from facilities to roads
   :param search_criteria: Layer criteria for searching for staring point for facilities
   :param search_query: Layer-specific criteria (queries) for searching for staring point for facilities
   :return:
   '''
   # Search_criteria is used to only locate points on certain road types (default on only Roads_Local).
   # Search_query is further used to subset the road types where points can be located (default only driveable roads).
   print('Making analysis layer at ' + Hms() + '...')
   arcpy.MakeServiceAreaAnalysisLayer_na(net, "ServiceAreas", "Drive", "TO_FACILITIES", cutoffs=[minutes],
                                         output_type="POLYGONS", polygon_detail="STANDARD",
                                         geometry_at_overlaps="SPLIT", geometry_at_cutoffs="RINGS",
                                         polygon_trim_distance=poly_trim)
   print('Adding locations at ' + Hms() + '...')
   arcpy.AddLocations_na("ServiceAreas", "Facilities", facil,
                         "Name " + facil_group + " #", dist_from_roads, facil_group,
                         search_criteria, "MATCH_TO_CLOSEST", "CLEAR", "NO_SNAP", "5 Meters", "EXCLUDE", search_query)
   print('Solving service catchments at ' + Hms() + '...')
   arcpy.Solve_na("ServiceAreas", "SKIP", "TERMINATE")
   print('Dissolving services catchments by ' + facil_group + ' at ' + Hms() + '...')
   arcpy.CopyFeatures_management(r"ServiceAreas\Polygons", outSA + '_orig')
   arcpy.CalculateField_management(outSA + '_orig', facil_group, "int(!Name!.split(' : ')[0])", field_type="LONG")
   arcpy.Dissolve_management(outSA + '_orig', 'tmp_cat0', facil_group, multi_part="MULTI_PART")
   print('Cleaning up edges...')
   # fixed: overlaps at edges, potentially also where a catchment completely surrounds another catchment.
   # Use flatten procedure, sorting first to preserve smaller catchments.
   arcpy.Sort_management('tmp_cat0', 'tmp_cat1', [['Shape_Area', 'Ascending']])
   arcpy.Union_analysis('tmp_cat1', 'tmp_cat2')
   arcpy.DeleteIdentical_management('tmp_cat2', fields="Shape")
   arcpy.Dissolve_management('tmp_cat2', 'tmp_cat', facil_group, multi_part="MULTI_PART")

   print('Adding gaps at ' + Hms() + '...')
   arcpy.Erase_analysis(boundary, 'tmp_cat', 'gaps0')
   if arcpy.GetCount_management('gaps0')[0] != '0':
      arcpy.MultipartToSinglepart_management('gaps0', 'gaps1')
      fld = [a.name for a in arcpy.ListFields('gaps1') if a.type == 'OID'][0]
      arcpy.CalculateField_management('gaps1', facil_group, "!" + fld + "! * -1", field_type="LONG")
      arcpy.Append_management('gaps1', 'tmp_cat', "NO_TEST")
      arcpy.AlterField_management('tmp_cat', facil_group, 'servCat_' + facil_group, clear_field_alias=True)
      # Eliminate small gaps (< 1 sq mile)
      lyr = arcpy.MakeFeatureLayer_management('tmp_cat')
      # eliminate -1 polygons <1 square mile in size, adding to servCat with largest shared boundary
      arcpy.SelectLayerByAttribute_management(lyr, "NEW_SELECTION", 'servCat_' + facil_group + ' < 0 AND Shape_Area < 2589990')
      if int(arcpy.GetCount_management(lyr)[0]) > 0:
         arcpy.Eliminate_management(lyr, outSA)
      else:
         arcpy.CopyFeatures_management('tmp_cat', outSA)
      del lyr
   else:
      arcpy.CopyFeatures_management(outSA + '_orig', outSA)
   # Add binary access field indicating if a catchment (1) or gap (0)
   arcpy.CalculateField_management(outSA, 'access', "min(max(!servCat_" + facil_group + "!, 0), 1)", field_type="SHORT")

   # jf = [a.name for a in arcpy.ListFields(facil) if not a.name.startswith(('Shape', 'FID_')) and a.type != 'OID' and a.name != facil_group]
   jf = [a.name for a in arcpy.ListFields(facil) if a.name in joinatt]
   if len(jf) > 0:
      print('Joining attributes to catchment features...')
      arcpy.JoinField_management(outSA, 'servCat_' + facil_group, facil, facil_group, jf)
      jf2 = [[a, 'focal_' + a] for a in jf]
      for i in jf2:
         arcpy.AlterField_management(outSA, i[0], i[1], clear_field_alias=True)
         if i[1].endswith('_acres'):
            nullToZero(outSA, i[1])

   # Clean up (all) service area datasets in current GDB
   ls = arcpy.ListDatasets('ServiceArea*')
   arcpy.Delete_management(ls)
   arcpy.Delete_management(['gaps0', 'gaps1'])

   return outSA



# HEADER

# outGDB = r'E:\projects\rec_model\rec_model_processing\serviceAreas_testing\DEMO_202104.gdb'

# Set output geodatabase depending on analysis
outGDB = r'E:\projects\rec_model\rec_model_processing\serviceAreas_NA\recServiceAnalyses_2021.gdb'
# outGDB = r'E:\projects\rec_model\rec_model_processing\serviceAreas_NA\recCatchments_2021.gdb'
# outGDB = r'E:\projects\rec_model\rec_model_processing\serviceAreas_NA\recWaterActivities_2021.gdb'
# outGDB = r'E:\projects\rec_model\rec_model_processing\serviceAreas_NA\recTravelTime_2021.gdb'
make_gdb(outGDB)
arcpy.env.workspace = outGDB

# Set raster template for rasterized results
rastTemplate = r'E:\RCL_cost_surfaces\Tiger_2020\cost_surfaces.gdb\costSurf_no_lah'
# boundary (used in catchments)
bnd = r'L:\David\projects\RCL_processing\RCL_processing.gdb\VA_Buff50mi_wgs84'
# population and impervious rasters
popRast = r'E:\projects\rec_model\rec_model_processing\input_recmodel.gdb\distribPop_kdens_2020'
impRast = r'L:\David\GIS_data\NLCD\nlcd_2016\nlcd_2016ed_Impervious_albers.gdb\imperv_2016'

# Network
net = r'E:\projects\OSM\network\OSM_RoadsNet_Albers.gdb\RoadsNet\RoadsNet_ND'
arcpy.env.outputCoordinateSystem = net
arcpy.env.overwriteOutput = True

# Master access point layers
ppa_pt = r'E:\projects\rec_model\rec_model_processing\access_pts.gdb\access_points_t_lnd_20210409'
# ppa_pt = 'PPA_demo_accesspt'
# Add field accgreen_acres to access points (used in catchments)
# arcpy.CalculateField_management(ppa_pt, 'accgreen_acres', '!join_score!', field_type="DOUBLE")

# Water access
aqua_pt = r'E:\projects\rec_model\rec_model_processing\access_pts.gdb\access_points_combined_20210406'
# aqua_pt = 'water_accesspt'

# PPA available area, for use in catchments
ppa = r'E:\projects\rec_model\rec_datasets\rec_datasets_working.gdb\public_lands_final_accessAreas'
# ppa = 'PPA_demo_available_area'
sec_ppa = arcpy.Select_analysis(ppa, 'secPPA', where_clause="accgreen_acres > 0 AND accgreen_acres < 25")[0]

# END HEADER


### Service areas
for m in [15, 30, 45]:
   # Water access
   facil = arcpy.Select_analysis(aqua_pt, os.path.basename(aqua_pt))[0]
   facil_group = 'group_id'
   outSA = 'servArea_waterAccess_' + str(m) + 'min'
   networkServiceAreas(net, facil, facil_group, outSA, minutes=m, rastTemplate=rastTemplate)

   # PPA (100 acres)
   facil = arcpy.Select_analysis(ppa_pt, os.path.basename(ppa_pt) + '_100ac', where_clause="join_score >= 100")[0]
   facil_group = 'ppa_group_id'
   outSA = 'servArea_PPA_100ac_' + str(m) + 'min'
   networkServiceAreas(net, facil, facil_group, outSA, minutes=m, rastTemplate=rastTemplate)
   # PPA (600 acres)
   facil = arcpy.Select_analysis(ppa_pt, os.path.basename(ppa_pt) + '_600ac', where_clause="join_score >= 600")[0]
   facil_group = 'ppa_group_id'
   outSA = 'servArea_PPA_600ac_' + str(m*2) + 'min'
   networkServiceAreas(net, facil, facil_group, outSA, minutes=m*2, rastTemplate=rastTemplate)


### Catchments
for m in [15, 30, 45]:
   print(str(m))
   # Water access
   facil = arcpy.Select_analysis(aqua_pt, os.path.basename(aqua_pt))[0]
   facil_group = 'group_id'
   outSA = 'servCat_waterAccess_' + str(m) + 'min'
   networkCatchments(net, facil, facil_group, outSA, bnd, minutes=m)
   servCatStats(outSA, 'servCat_' + facil_group, popRast)
   servCatPressureAq(outSA)

   # PPA (25 acres)
   facil = arcpy.Select_analysis(ppa_pt, os.path.basename(ppa_pt) + '_25ac', where_clause="join_score >= 25")[0]
   facil_group = 'ppa_group_id'
   outSA = 'servCat_PPA_25ac_' + str(m) + 'min'
   networkCatchments(net, facil, facil_group, outSA, bnd, minutes=m)
   servCatStats(outSA, 'servCat_' + facil_group, popRast, sec_ppa, impRast)
   servCatPressurePPA(outSA)

ls = arcpy.ListFeatureClasses('tmp*') + arcpy.ListTables('tmp*')
arcpy.Delete_management(ls)


### Travel time to nearest
# Note: 15 min for just 10 groups to 120 minutes. Not sure how this will work for full dataset.
# 120 Minutes should cover most of state, though.
# aquatic
facil = arcpy.Select_analysis(aqua_pt, os.path.basename(aqua_pt))[0]
facil_group = 'group_id'
outSA = 'tt_waterAccess_1min'
networkTravelToNearest(net, facil, facil_group, outSA, minutes=list(range(5, 121, 5)), rastTemplate=rastTemplate)

# PPA (5 acres)
facil = arcpy.Select_analysis(ppa_pt, os.path.basename(ppa_pt) + '_5ac', where_clause="join_score >= 5")[0]
facil_group = 'ppa_group_id'
outSA = 'tt_PPA_5ac'
networkTravelToNearest(net, facil, facil_group, outSA, minutes=list(range(5, 121, 5)), rastTemplate=rastTemplate)


### Overlap by-activity, aquatics. 30 minute limit.
typs = ['a_wct', 'a_fsh', 'a_swm']
for a in typs:
   print(a)
   facil = arcpy.Select_analysis(aqua_pt, os.path.basename(aqua_pt) + '_' + a, a + ' = 1')[0]
   facil_group = 'use'  # This is a constant, will make everything one group.
   outSA = 'servedArea_waterAccess_' + a + '_30min'
   networkTravelToNearest(net, facil, facil_group, outSA, minutes=[30], rastTemplate=None)
# Count overlapping and convert to raster
out = 'servedArea_waterAccess_activities_30min'
arcpy.CountOverlappingFeatures_analysis(['servedArea_waterAccess_' + a + '_30min' for a in typs], out, 1)
arcpy.AlterField_management(out, 'COUNT_FC', 'water_activity_ct', clear_field_alias=True)
with arcpy.EnvManager(outputCoordinateSystem=rastTemplate, snapRaster=rastTemplate, cellSize=rastTemplate):
   arcpy.PolygonToRaster_conversion(out, 'water_activity_ct', out + '_rast', cellsize=rastTemplate)
arcpy.BuildPyramids_management(out + '_rast')
