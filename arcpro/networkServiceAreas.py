"""
networkServiceAreas
Created by: David Bucklin
Created on: 2021-04-21
ArcGIS version: ArcGIS Pro
Python version: Python 3.x

Network Analyst-based processes for all recreation model analyses. Includes functions for:
   - Service areas by facility group, counting overlaps
   - Catchments (non-overlapping service areas) by facility group
   - Travel time to nearest facility

General usage notes:
- For service areas and catchments, one service area or catchment is developed for each unique value in facil_group.
Fields listed in joinatt will be joined to the output service areas or catchments. If there are multiple points
in the facil_group, note that only one of the facilities' attributes can be joined to the single catchment feature.
- facil_group is not used for networkTravelToNearest, as all facilities are considered one 'group' in that analysis.
- In networkServiceAreas, processing time is greatly increased as minutes limit increases. Solving and counting
overlaps can be very slow for these cases.
- In networkTravelToNearest, increasing the number of breaks will greatly increase processing time, especially if the
upper time limit is high.
- Tried out exclude_sources_from_polygon_generation=["Roads_Hwy"]. When using this and generating polygons with
geometry_at_overlap="SPLIT", there are bad errors in some polygons. Because of this, abandoned use of this option.
"""

# from Helper import *  # python command prompt: propy.bat E:\git\ConsVision_RecreationModel\arcpro\networkServiceAreas.py
from arcpro.Helper import *   # for interactive usage
arcpy.CheckOutExtension("network")

# Default search criteria for OSM roads.
# search_criteria defines which feature classes are used to locate points (default is only on Roads_Local lines).
# search_query defines the subset of road types where points can be located (default only driveable roads).
search_att = {
   'search_criteria': [["Roads_Local", "SHAPE"], ["Roads_Hwy", "NONE"], ["Ramp_Points", "NONE"], ["RoadsNet_ND_Junctions", "NONE"]],
   'search_query': [["Roads_Local", '"code" IN (5112, 5113, 5114, 5115, 5121, 5122, 5123, 5132, 5133, 5134, 5135, 5141, 5142, 5143, 5144, 5145, 5146, 5147)']]
}


def networkServiceAreas(net, facil, facil_group, outSA, joinatt=['src_table', 'src_name', 'join_name', 'accgreen_acres'],
                        minutes=[30], poly_trim="0.3 Miles", dist_from_roads="1 Mile",
                        search_criteria=search_att["search_criteria"], search_query=search_att["search_query"],
                        rastTemplate=None, travTypeName="Drive", travDir="TO_FACILITIES"):
   '''
   Generate individual service areas by facil_group, and count overlaps.
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
   :return: outSA
   '''
   print('Making analysis layer at ' + Hms() + '...')
   # coulddo: add dummy +5 minute distance ring? Update: no, doesn't seem to change much.
   arcpy.MakeServiceAreaAnalysisLayer_na(net, "ServiceAreas", travTypeName, travDir, cutoffs=minutes,
                                         output_type="POLYGONS", polygon_detail="STANDARD",
                                         geometry_at_overlaps="OVERLAP", geometry_at_cutoffs="RINGS",
                                         polygon_trim_distance=poly_trim)
   print('Adding locations at ' + Hms() + '...')
   arcpy.AddLocations_na("ServiceAreas", "Facilities", facil,
                         "Name " + facil_group + " #", dist_from_roads, facil_group,
                         search_criteria, "MATCH_TO_CLOSEST", "CLEAR", "NO_SNAP", "5 Meters", "EXCLUDE", search_query)
   print('Solving service areas at ' + Hms() + '...')
   arcpy.Solve_na("ServiceAreas", "SKIP", "TERMINATE")
   print('Dissolving services areas by ' + facil_group + ' at ' + Hms() + '...')
   # This preserves original copy of service area polygons, with facility group ID
   arcpy.CopyFeatures_management(r"ServiceAreas\Polygons", outSA + '_orig')
   arcpy.CalculateField_management(outSA + '_orig', facil_group, "int(!Name!.split(' : ')[0])", field_type="LONG")
   arcpy.Select_analysis(outSA + '_orig', 'tmp_sel', "ToBreak <= " + str(max(minutes)))
   arcpy.Dissolve_management('tmp_sel', outSA, facil_group, multi_part="MULTI_PART")
   if rastTemplate:
      print('Counting service areas overlaps at ' + Hms() + '...')
      arcpy.CountOverlappingFeatures_analysis(outSA, outSA + '_ct_poly', 1)
      print('Rasterizing overlap counts at ' + Hms() + '...')
      with arcpy.EnvManager(outputCoordinateSystem=rastTemplate, snapRaster=rastTemplate, cellSize=rastTemplate, extent=rastTemplate, mask=rastTemplate):
         arcpy.PolygonToRaster_conversion(outSA + '_ct_poly', 'COUNT_', 'tmp_rast', "CELL_CENTER", cellsize=rastTemplate)
         arcpy.sa.Con(arcpy.sa.IsNull('tmp_rast'), 0, 'tmp_rast').save(outSA + '_ct')  # Note: env.mask applies to this, but not PolygonToRaster.
      arcpy.BuildPyramids_management(outSA + '_ct')
      arcpy.Delete_management(['tmp_rast', outSA + '_ct_poly'])

   jf = [a.name for a in arcpy.ListFields(facil) if a.name in joinatt]
   if len(jf) > 0:
      print('Joining attributes to service areas...')
      arcpy.JoinField_management(outSA, facil_group, facil, facil_group, jf)
   fldAlias(outSA)

   # Clean up (all) service area datasets in current GDB
   ls = arcpy.ListDatasets('ServiceArea*')
   arcpy.Delete_management(ls)

   return outSA


def networkCatchments(net, facil, facil_group, outSA, boundary, joinatt=['src_table', 'src_name', 'join_name', 'accgreen_acres'],
                      minutes=30, poly_trim="0.3 Miles", dist_from_roads="1 Mile",
                      search_criteria=search_att["search_criteria"], search_query=search_att["search_query"],
                      travTypeName="Drive", travDir="TO_FACILITIES"):
   '''
   Generate non-overlapping service catchments, by facil_group.
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
   :return: outSA
   '''
   # Search_criteria is used to only locate points on certain road types (default on only Roads_Local).
   # Search_query is further used to subset the road types where points can be located (default only driveable roads).
   print('Making analysis layer at ' + Hms() + '...')
   arcpy.MakeServiceAreaAnalysisLayer_na(net, "ServiceAreas", travTypeName, travDir, cutoffs=[minutes],
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
   arcpy.CopyFeatures_management(r"ServiceAreas\Polygons", outSA + '_SAPoly')
   arcpy.CalculateField_management(outSA + '_SAPoly', facil_group, "int(!Name!.split(' : ')[0])", field_type="LONG")
   arcpy.Dissolve_management(outSA + '_SAPoly', 'tmp_cat0', facil_group, multi_part="MULTI_PART")

   print('Cleaning up edges of catchments...')
   # Cleans up overlaps at edges, potentially also where a catchment completely surrounds/overlaps another catchment.
   # Uses a flatten procedure, sorting first to preserve the smaller catchment in areas of overlap.
   arcpy.Sort_management('tmp_cat0', 'tmp_cat1', [['Shape_Area', 'Ascending']])
   arcpy.Union_analysis('tmp_cat1', 'tmp_cat2')
   arcpy.DeleteIdentical_management('tmp_cat2', fields="Shape")
   arcpy.Dissolve_management('tmp_cat2', outSA + '_orig', facil_group, multi_part="MULTI_PART")

   print('Adding gaps at ' + Hms() + '...')
   arcpy.Clip_analysis(outSA + '_orig', boundary, 'tmp_cat')
   arcpy.Erase_analysis(boundary, 'tmp_cat', 'gaps0')
   if arcpy.GetCount_management('gaps0')[0] != '0':
      arcpy.RepairGeometry_management("gaps0", "DELETE_NULL", "ESRI")
      arcpy.MultipartToSinglepart_management('gaps0', 'gaps1')
      # Add incrementing ID (negative value)
      arcpy.AddField_management('gaps1', facil_group, 'LONG')
      n = 0
      with arcpy.da.UpdateCursor('gaps1', facil_group) as curs:
         for r in curs:
            n -= 1
            r[0] = n
            curs.updateRow(r)
      arcpy.Append_management('gaps1', 'tmp_cat', "NO_TEST")
      arcpy.AlterField_management('tmp_cat', facil_group, 'servCat_' + facil_group, 'Service Catchment ID')
      # Eliminate small gaps (< 1 sq mile)
      lyr = arcpy.MakeFeatureLayer_management('tmp_cat')
      # eliminate -1 polygons below size cutoff (decide) to clean up small holes between service catchments
      # Adjusted to 100,000 sq meters (i.e. 0.1 sq km)
      arcpy.SelectLayerByAttribute_management(lyr, "NEW_SELECTION", 'servCat_' + facil_group + ' < 0 AND Shape_Area < 100000')
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
   arcpy.Delete_management(['gaps0'])

   return outSA


def networkTravelToNearest(net, facil, outSA, minutes=list(range(5, 121, 5)),
                           poly_trim="0.3 Miles", dist_from_roads="1 Mile",
                           search_criteria=search_att["search_criteria"], search_query=search_att["search_query"],
                           rastTemplate=None, travTypeName="Drive", travDir="TO_FACILITIES"):
   '''
   Calculate travel time to nearest facility. No grouping in this analysis.
   :param net: Network dataset
   :param facil: Facilities (points)
   :param outSA: Output service area layer base name
   :param minutes: List of travel-time breaks
   :param poly_trim: Polygon trim distance for service areas (equivalent to a buffer around roads)
   :param dist_from_roads: Search distance limit for starting point from facilities to roads
   :param search_criteria: Layer criteria for searching for staring point for facilities
   :param search_query: Layer-specific criteria (queries) for searching for staring point for facilities
   :param rastTemplate: Raster template for overlap raster (coordinate system)
   :return: outSA
   '''
   # Search_criteria is used to only locate points on certain road types (default on only Roads_Local).
   # Search_query is further used to subset the road types where points can be located (default only driveable roads).
   print('Making analysis layer at ' + Hms() + '...')
   arcpy.MakeServiceAreaAnalysisLayer_na(net, "ServiceAreas", travTypeName, travDir, cutoffs=minutes,
                                         output_type="POLYGONS", polygon_detail="STANDARD",
                                         geometry_at_overlaps="DISSOLVE", #  "DISSOLVE",  # "SPLIT",  # "OVERLAP"
                                         geometry_at_cutoffs="RINGS",
                                         polygon_trim_distance=poly_trim)
   print('Adding locations at ' + Hms() + '...')
   arcpy.AddLocations_na("ServiceAreas", "Facilities", facil,
                         "Name OBJECTID #", dist_from_roads, "OBJECTID",
                         search_criteria, "MATCH_TO_CLOSEST", "CLEAR", "NO_SNAP", "5 Meters", "EXCLUDE", search_query)
   print('Solving service areas at ' + Hms() + '...')
   arcpy.Solve_na("ServiceAreas", "SKIP", "TERMINATE")
   arcpy.CopyFeatures_management(r"ServiceAreas\Polygons", outSA)

   # make minutes and priority fields
   arcpy.CalculateField_management(outSA, 'minutes', '!FromBreak! + ' + str(min(minutes)), field_type="LONG")
   maxval = max([a[0] for a in arcpy.da.SearchCursor(outSA, 'minutes')]) + 1
   arcpy.CalculateField_management(outSA, 'priority', str(maxval) + ' - !minutes!', field_type="LONG")
   if rastTemplate:
      print('Rasterizing travel time breaks at ' + Hms() + '...')
      with arcpy.EnvManager(outputCoordinateSystem=rastTemplate, snapRaster=rastTemplate, cellSize=rastTemplate, extent=rastTemplate, mask=rastTemplate):
         arcpy.PolygonToRaster_conversion(outSA, 'minutes', 'tmp_rast', "CELL_CENTER", priority_field="priority", cellsize=rastTemplate)
         arcpy.sa.ExtractByMask('tmp_rast', rastTemplate).save(outSA + '_rast')
      arcpy.BuildPyramids_management(outSA + '_rast')

   # Clean up (all) service area datasets in current GDB
   ls = arcpy.ListDatasets('ServiceArea*')
   arcpy.Delete_management(ls)

   return outSA


def adjustCatchments(inLayer, rasterize_id, outLayer, roadMask, finalMask):

   print("Adjusting catchments using road mask...")
   arcpy.PolygonToRaster_conversion(inLayer, rasterize_id, 'tmp_rasterize', cellsize=roadMask)
   print('Masking to roadMask...')
   arcpy.sa.ExtractByMask('tmp_rasterize', roadMask).save('tmp_mask')

   with arcpy.EnvManager(mask=finalMask, extent=finalMask):
      print("Allocating by euclidean distance to final mask...")
      arcpy.sa.EucAllocation('tmp_mask').save('tmp_alloc')
      print('Converting raster to polygon feature class `' + outLayer + '`...')
      arcpy.RasterToPolygon_conversion('tmp_alloc', outLayer, "NO_SIMPLIFY", 'Value', 'MULTIPLE_OUTER_PART')
      arcpy.AlterField_management(outLayer, 'gridcode', rasterize_id, clear_field_alias=True)

   print('Joining fields...')
   jf1 = ['access', 'focal_src_table', 'focal_src_name', 'focal_join_name', 'focal_accgreen_acres']
   jf = [a.name for a in arcpy.ListFields(inLayer) if a.name in jf1]
   arcpy.JoinField_management(outLayer, rasterize_id, inLayer, rasterize_id, jf)

   return outLayer


def finalizeLayer(inLayer, outLayer, finalMask, roadMask=None, rasterize_value=None):

   print('Finalizing layer ' + inLayer + '...')

   if rasterize_value is not None:
      # catchments: already have been processed. Just rasterize, and then apply final mask
      print('Rasterizing field ' + rasterize_value + '...')
      arcpy.PolygonToRaster_conversion(inLayer, rasterize_value, 'tmp_rasterize', cellsize=finalMask)
      with arcpy.EnvManager(mask=finalMask, extent=finalMask):
         arcpy.sa.ExtractByMask('tmp_rasterize', finalMask).save(outLayer + '_final')
   else:
      # other datasets: mask to roads, then allocate.
      print('Masking to roadMask...')
      arcpy.sa.ExtractByMask(inLayer, roadMask).save(outLayer)
      arcpy.BuildPyramids_management(outLayer)
      with arcpy.EnvManager(mask=finalMask, extent=finalMask):
         print("Allocating by euclidean distance to final mask...")
         arcpy.sa.EucAllocation(outLayer).save(outLayer + '_final')

   arcpy.BuildPyramids_management(outLayer + '_final')
   return outLayer + '_final'


def reclassLayer(inLayer, outLayer, remap=arcpy.sa.RemapRange([[0, 20, 1], [20, 40, 2], [40, 60, 3], [60, 80, 4], [80, 100, 5]])):

   print('Reclassifying ' + inLayer + '...')
   arcpy.sa.Reclassify(inLayer, 'Value', remap).save(outLayer)
   arcpy.BuildRasterAttributeTable_management(outLayer, 'OVERWRITE')
   arcpy.AddField_management(outLayer, 'label', field_type="TEXT")
   need_rng = [[1, "Very Low Need"], [2, "Low Need"], [3, "Moderate Need"], [4, "High Need"], [5, "Very High Need"]]
   with arcpy.da.UpdateCursor(outLayer, ['Value', 'label']) as curs:
      for i in curs:
         val = [n[1] for n in need_rng if n[0] == i[0]][0]
         i[1] = val
         curs.updateRow(i)
   arcpy.BuildPyramids_management(outLayer)



def main():

   # HEADER

   # GDBs are created within analyses, in this folder
   basedir = r'E:\projects\rec_model\rec_model_processing\serviceAnalyses_NA'
   # projdir = os.path.join(basedir, 'recAnalyses_20210506')
   projdir = os.path.join(basedir, 'recAnalyses_' + Ymd())

   if not os.path.exists(projdir):
      print('Creating directory ' + projdir + '.')
      os.mkdir(projdir)

   # Set raster template for rasterized results
   rastTemplate = r'L:\David\projects\RCL_processing\RCL_processing.gdb\SnapRaster_albers_wgs84'
   # rastTemplate = r'E:\projects\rec_model\rec_model_processing\input_recmodel.gdb\census_blocks_populated_rast'

   arcpy.env.outputCoordinateSystem = rastTemplate
   arcpy.env.snapRaster = rastTemplate
   arcpy.env.cellSize = rastTemplate
   arcpy.env.extent = rastTemplate
   arcpy.env.overwriteOutput = True

   # Boundary used in catchments for gap-filling, euclidean allocation for catchments
   bnd = r'E:\projects\rec_model\rec_model_processing\input_recmodel.gdb\landMask_studyArea'
   # RoadClip is used to adjust service layers, prior to euclidean allocation.
   roadClip = r'E:\projects\OSM\OSM_RoadsProc.gdb\OSM_Roads_20210422_qtrMileBuff'
   roadMask = roadClip + '_rast'
   # This is the FINAL mask to Virginia. Used as a euclidean allocation mask for non-catchment layers.
   VAMask = r'E:\projects\rec_model\rec_model_processing\input_recmodel.gdb\jurisbnd_mask'

   # population and impervious rasters
   popRast = r'E:\projects\rec_model\rec_model_processing\input_recmodel.gdb\distribPop_kdens_OSM_2021_blkMask'
   impRast = r'L:\David\GIS_data\NLCD\nlcd_2016\nlcd_2016ed_Impervious_albers.gdb\imperv_2016'

   # Network
   net = r'E:\projects\OSM\network\OSM_RoadsNet_Albers.gdb\RoadsNet\RoadsNet_ND'
   arcpy.env.outputCoordinateSystem = net

   # Master access point layers
   ppa_pt0 = r'E:\projects\rec_model\rec_model_processing\access_pts.gdb\access_points_t_lnd_20210428'
   # Add field accgreen_acres to access points (used in catchments)
   # arcpy.CalculateField_management(ppa_pt0, 'accgreen_acres', '!join_score!', field_type="DOUBLE")

   # Water access
   aqua_pt0 = r'E:\projects\rec_model\rec_model_processing\access_pts.gdb\access_points_combined_20210428'

   # END HEADER


   ### Water access
   outGDB = os.path.join(projdir, 'recAnalyses_waterAccess.gdb')
   make_gdb(outGDB)
   arcpy.env.workspace = outGDB
   facil_group = 'group_id'

   # Copy access points with 'identicals' removed
   facil = arcpy.Select_analysis(aqua_pt0, os.path.basename(aqua_pt0))[0]
   arcpy.DeleteIdentical_management(facil, ["Shape", facil_group], "5 Meters")  # To reduce number of SAs

   ## Catchments
   outSA = 'servCat_waterAccess_30min'
   if not arcpy.Exists(outSA):
      networkCatchments(net, facil, facil_group, outSA, boundary=bnd, minutes=30)
      # update: adjust here (clip to roads + euclidean allocation, convert back to polygon)
      adjustCatchments(outSA, 'servCat_' + facil_group, outSA + '_adjust', roadMask, bnd)
      servCatStats(outSA + '_adjust', 'servCat_' + facil_group, popRast)
      servCatPressure(outSA + '_adjust', fldPop="pop_total", fldScore="access", per=10000)
   final = finalizeLayer(outSA + '_adjust', 'aqRecPres', VAMask, rasterize_value='rec_pressure')
   reclassLayer(final, final + '_rcl', arcpy.sa.RemapRange([[0, 20, 1], [20, 40, 2], [40, 60, 3], [60, 80, 4], [80, 100, 5]]))

   ## Travel time 
   # 105 minutes is enough to cover entire study area
   # Grouping is not used for Travel time to nearest.
   outSA = 'travelTime_waterAccess'
   if not arcpy.Exists(outSA):
      networkTravelToNearest(net, facil, outSA, minutes=list(range(5, 106, 5)), rastTemplate=rastTemplate)
   final = finalizeLayer(outSA + '_rast', 'aqProx', VAMask, roadMask)
   reclassLayer(final, final + '_rcl', arcpy.sa.RemapRange([[0, 15, 1], [15, 25, 2], [25, 40, 3], [40, 60, 4], [60, 100000, 5]]))

   ## Service areas
   outSA = 'servArea_waterAccess_30min'
   if not arcpy.Exists(outSA):
      networkServiceAreas(net, facil, facil_group, outSA, minutes=[30], rastTemplate=rastTemplate)
   final = finalizeLayer(outSA + '_ct', 'aqAccOpts', VAMask, roadMask)
   reclassLayer(final, final + '_rcl', arcpy.sa.RemapRange([[0, 0.5, 5], [0.5, 5, 4], [5, 10, 3], [10, 20, 2], [20, 100000, 1]]))


   # Overlap by-activity, aquatics. 30 minute limit.
   outSA = 'servedArea_waterAccess_activities_30min_ct'
   if not arcpy.Exists(outSA):
      # Get service areas layer
      sas = 'servArea_waterAccess_30min'

      # Loop over facility types
      typs = ['a_wct', 'a_fsh', 'a_swm']
      for t in typs:
         print(t)
         group_ids = list(set([str(a[0]) for a in arcpy.da.SearchCursor(aqua_pt0, ['group_id', t]) if a[1] == 1]))
         arcpy.Select_analysis(sas, 'tmp_sa', "group_id IN (" + ",".join(group_ids) + ")")
         arcpy.CalculateField_management('tmp_sa', 'rast', 1, field_type="SHORT")
         with arcpy.EnvManager(outputCoordinateSystem=rastTemplate, snapRaster=rastTemplate, cellSize=rastTemplate, extent=rastTemplate):
            arcpy.PolygonToRaster_conversion('tmp_sa', 'rast', 'tmp_' + t, "CELL_CENTER", cellsize=rastTemplate)
      # Sum rasters
      rls = ['tmp_' + a for a in typs]
      with arcpy.EnvManager(outputCoordinateSystem=rastTemplate, snapRaster=rastTemplate, cellSize=rastTemplate, extent=rastTemplate, mask=rastTemplate):
         arcpy.sa.CellStatistics(rls, 'SUM').save('tmp_rast')
         arcpy.sa.Con(arcpy.sa.IsNull('tmp_rast'), 0, 'tmp_rast').save(outSA)
   final = finalizeLayer(outSA, 'aqActOpts', VAMask, roadMask)
   reclassLayer(final, final + '_rcl', arcpy.sa.RemapRange([[0, 0.5, 5], [0.5, 1, 4], [1, 2, 3], [2, 3, 2]]))  # note: no Very Low class for this.

   # Clean up
   arcpy.Delete_management(arcpy.ListFeatureClasses("tmp_*") + arcpy.ListRasters("tmp_*") + arcpy.ListTables("tmp_*"))


   ### PPAs
   outGDB = os.path.join(projdir, 'recAnalyses_PPA.gdb')
   make_gdb(outGDB)
   arcpy.env.workspace = outGDB
   facil_group = 'ppa_group_id'

   # Copy access points with 'identicals' removed
   ppa_pt = arcpy.Select_analysis(ppa_pt0, os.path.basename(ppa_pt0))[0]
   arcpy.DeleteIdentical_management(ppa_pt, ["Shape", facil_group], "5 Meters")  # To reduce number of SA

   ## Catchments
   # PPA (25 acres)
   outSA = 'servCat_PPA_25ac_30min'
   if not arcpy.Exists(outSA):
      # Select secondary PPA
      ppa = r'E:\projects\rec_model\rec_datasets\rec_datasets_working_2021.gdb\public_lands_final_accessAreas'
      sec_ppa = arcpy.Select_analysis(ppa, 'secPPA', where_clause="accgreen_acres > 0 AND accgreen_acres < 25")[0]
      arcpy.AlterField_management(sec_ppa, 'access', 'ppa_access', clear_field_alias=True)  # change field name to avoid conflict w/same field in catchments.
      # run catchments
      facil = arcpy.Select_analysis(ppa_pt, os.path.basename(ppa_pt) + '_25ac', where_clause="accgreen_acres >= 25")[0]
      networkCatchments(net, facil, facil_group, outSA, boundary=roadClip, minutes=30)
      # update: adjust catchments here
      adjustCatchments(outSA, 'servCat_' + facil_group, outSA + '_adjust', roadMask, bnd)
      servCatStats(outSA + '_adjust', 'servCat_' + facil_group, popRast, sec_ppa, impRast)
      agapt(outSA + '_adjust')
      servCatPressure(outSA + '_adjust', fldPop="pop_total", fldScore="accgreen_acres", per=100)
   final = finalizeLayer(outSA + '_adjust', 'teRecPres', VAMask, rasterize_value='rec_pressure')
   reclassLayer(final, final + '_rcl', arcpy.sa.RemapRange([[0, 20, 1], [20, 40, 2], [40, 60, 3], [60, 80, 4], [80, 100, 5]]))

   # Travel time to nearest (5 acres)
   outSA = 'travelTime_PPA_5ac'
   if not arcpy.Exists(outSA):
      facil = arcpy.Select_analysis(ppa_pt, os.path.basename(ppa_pt) + '_5ac', where_clause="accgreen_acres >= 5")[0]
      networkTravelToNearest(net, facil, outSA, minutes=list(range(5, 106, 5)), rastTemplate=rastTemplate)
   final = finalizeLayer(outSA + '_rast', 'teProx', VAMask, roadMask)
   reclassLayer(final, final + '_rcl', arcpy.sa.RemapRange([[0, 15, 1], [15, 25, 2], [25, 40, 3], [40, 60, 4], [60, 100000, 5]]))

   # Service Areas
   # PPA (100 acres)
   outSA = 'servArea_PPA_100ac_30min'
   if not arcpy.Exists(outSA):
      facil = arcpy.Select_analysis(ppa_pt, os.path.basename(ppa_pt) + '_100ac', where_clause="accgreen_acres >= 100")[0]
      networkServiceAreas(net, facil, facil_group, outSA, minutes=[30], rastTemplate=rastTemplate)
   final = finalizeLayer(outSA + '_ct', 'teLocOpts', VAMask, roadMask)
   reclassLayer(final, final + '_rcl', arcpy.sa.RemapRange([[0, 0.5, 5], [0.5, 5, 4], [5, 10, 3], [10, 20, 2], [20, 100000, 1]]))

   # PPA (600 acres)
   outSA = 'servArea_PPA_600ac_60min'
   if not arcpy.Exists(outSA):
      facil = arcpy.Select_analysis(ppa_pt, os.path.basename(ppa_pt) + '_600ac', where_clause="accgreen_acres >= 600")[0]
      networkServiceAreas(net, facil, facil_group, outSA, minutes=[60], rastTemplate=rastTemplate)
   final = finalizeLayer(outSA + '_ct', 'teRegOpts', VAMask, roadMask)
   reclassLayer(final, final + '_rcl', arcpy.sa.RemapRange([[0, 0.5, 5], [0.5, 5, 4], [5, 10, 3], [10, 20, 2], [20, 100000, 1]]))

   # Clean up
   arcpy.Delete_management(arcpy.ListFeatureClasses("tmp_*") + arcpy.ListRasters("tmp_*") + arcpy.ListTables("tmp_*"))


if __name__ == '__main__':
   main()

# end
