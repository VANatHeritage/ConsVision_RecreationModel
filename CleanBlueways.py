# ----------------------------------------------------------------------------------------
# CleanBlueways.py
# Version:  ArcGIS 10.3.1 / Python 2.7.8
# Creation Date: 2018-11-05
# Last Edit: 2019-02-19
# Creator(s):  Kirsten R. Hazler

# Summary:
# Derived from the script CreateSCU.py (in ConSite-Tools), which was created for delineating Stream Conservation Units (SCUs). This is an adaptation designed to deal with poorly mapped blueways (water trails), which are assumed generally to be along main flowlines in NHD LakePond or StreamRiver polygons. There are some blueways originally mapped near the edge of large water bodies, which should not be redrawn along flowlines; these will still need to be dealt with manually.

# Usage Tips:
# "It ain't perfect, but it's pretty good."

# Dependencies:
# This set of functions will not work if the hydro network is not set up properly! The network geodatabase VA_HydroNet.gdb has been set up manually, not programmatically.

# The Network Analyst extension is required for some functions, which will fail if the license is unavailable.

# Note that the restrictions (contained in "r" variable below) for traversing the network must have been defined in the HydroNet itself (manually). If any additional restrictions are added, the HydroNet must be rebuilt or they will not take effect. For water trails, I set the restriction to allow travel only along ArtificialPath flowlines.

# Syntax:  
# 
# ----------------------------------------------------------------------------------------

# Import modules
import Helper
from Helper import *
from arcpy.sa import *

def MakeRouteLayer_bw(in_hydroNet):
   '''Creates a Network Analyst route layer needed for blueways delineation. This tool only needs to be run the first time you run the suite of blueways delineation functions. After that, the output layers can be reused repeatedly for the subsequent tools in the blueways delineation sequence.
   Parameters:
   - in_hydroNet = Input hydrological network dataset
   '''
   arcpy.CheckOutExtension("Network")
   
   # Set up some variables
   descHydro = arcpy.Describe(in_hydroNet)
   nwDataset = descHydro.catalogPath
   catPath = os.path.dirname(nwDataset) # This is where hydro layers will be found
   hydroDir = os.path.dirname(catPath)
   hydroDir = os.path.dirname(hydroDir) # This is where output layer files will be saved
   nwLines = catPath + os.sep + "NHDLine"
   qry = "FType = 343" # DamWeir only
   arcpy.MakeFeatureLayer_management (nwLines, "lyr_DamWeir", qry)
   in_Lines = "lyr_DamWeir"
   lyrBluewayTrace = hydroDir + os.sep + "naBluewayTrace.lyr"
   
   # Create route layer
   # Restrict route generation to ArtificialPath flowlines using "r" variable
   r = "NoCanalDitches;NoConnectors;NoPipelines;NoUndergroundConduits;NoCoastline;NoStreamRiver"
   printMsg('Creating route analysis layer...')
   routeLayer = arcpy.MakeRouteLayer_na(in_network_dataset=nwDataset, 
      out_network_analysis_layer="naRoutes", 
      impedance_attribute="Length", 
      find_best_order="FIND_BEST_ORDER", 
      ordering_type="PRESERVE_NONE", 
      time_windows="NO_TIMEWINDOWS", 
      accumulate_attribute_name="Length", 
      UTurn_policy="ALLOW_DEAD_ENDS_AND_INTERSECTIONS_ONLY", 
      restriction_attribute_name=r, hierarchy="NO_HIERARCHY", 
      hierarchy_settings="", 
      output_path_shape="TRUE_LINES_WITHOUT_MEASURES", 
      start_date_time="")
   
   # Add dam barriers to route layer and save
   printMsg('Adding dam barriers to route layer...')
   barriers = arcpy.AddLocations_na(in_network_analysis_layer="naRoutes", 
      sub_layer="Line Barriers", 
      in_table=in_Lines, 
      field_mappings="Name Permanent_Identifier #", 
      search_tolerance="100 Meters", 
      sort_field="", 
      search_criteria="NHDFlowline SHAPE_MIDDLE_END;HydroNet_ND_Junctions NONE", 
      match_type="MATCH_TO_CLOSEST", 
      append="CLEAR", 
      snap_to_position_along_network="SNAP", 
      snap_offset="0 Meters", 
      exclude_restricted_elements="INCLUDE", 
      search_query="NHDFlowline #;HydroNet_ND_Junctions #")
         
   printMsg('Saving route layer to %s...' %lyrBluewayTrace)      
   arcpy.SaveToLayerFile_management("naRoutes", lyrBluewayTrace) 
   del barriers
      
   del routeLayer
   
   arcpy.CheckInExtension("Network")
   
   return lyrBluewayTrace

def MakeRoutePts_bw(in_hydroNet, in_blueways, out_points, out_cleanBlueways = None):
   '''Given a set of blueway features, creates start and end points."
   Parameters:
   - in_hydroNet = Input hydrological network dataset
   - in_blueways = Input blueways. If this includes any multi-part features, then out_cleanBlueways should also be specified.
   - out_points = Output feature class containing points generated from blueways
   - out_cleanBlueways [optional] = output clean (single-part) version of blueways. If this is not specified (i.e., left as None, it is assumed that in_blueways is already a clean single-part dataset.
   '''
   if out_cleanBlueways != None:
      printMsg('Exploding multiparts...')
      arcpy.MultipartToSinglepart_management(in_blueways, out_cleanBlueways)
      in_blueways = out_cleanBlueways
   printMsg('Generating route endpoints...')
   arcpy.FeatureVerticesToPoints_management(in_blueways, out_points, "BOTH_ENDS")
   printMsg('Finished.')
   return out_points
   
def CreateLines_bw(out_Lines, in_Points, in_routeLayer, clusterDist = "402.336 METERS", out_Scratch = arcpy.env.scratchGDB):
   '''Loads endpoints derived from blueways, solves the route layer for each group of points, and combines routes based on cluster distance.
   Parameters:
   - out_Lines = Output lines representing Stream Conservation Units
   - in_PF = Input Procedural Features
   - in_Points = Input feature class containing points generated from procedural features
   - in_downTrace = Network Analyst service layer set up to run downstream
   - in_upTrace = Network Analyst service layer set up to run upstream
   - out_Scratch = Geodatabase to contain intermediate outputs'''
   
   arcpy.CheckOutExtension("Network")
   
   # timestamp
   t0 = datetime.now()
   
   # Set up some variables
   if out_Scratch == "in_memory":
      # recast to save to disk, otherwise there is no OBJECTID field for queries as needed
      outScratch = arcpy.env.scratchGDB
   printMsg('Casting strings to layer objects...')
   in_upTrace = arcpy.mapping.Layer(in_upTrace)
   in_downTrace = arcpy.mapping.Layer(in_downTrace)
   descDT = arcpy.Describe(in_downTrace)
   nwDataset = descDT.network.catalogPath
   catPath = os.path.dirname(nwDataset) # This is where hydro layers will be found
   hydroDir = os.path.dirname(catPath)
   hydroDir = os.path.dirname(hydroDir) # This is where output layer files will be saved
   lyrDownTrace = hydroDir + os.sep + 'naDownTrace.lyr'
   lyrUpTrace = hydroDir + os.sep + 'naUpTrace.lyr'
   downLines = out_Scratch + os.sep + 'downLines'
   upLines = out_Scratch + os.sep + 'upLines'
   outDir = os.path.dirname(out_Lines)
  
   # Load all points as facilities into both service layers; search distance 500 meters
   printMsg('Loading points into service layers...')
   for sa in [[in_downTrace,lyrDownTrace], [in_upTrace, lyrUpTrace]]:
      inLyr = sa[0]
      outLyr = sa[1]
      naPoints = arcpy.AddLocations_na(in_network_analysis_layer=inLyr, 
         sub_layer="Facilities", 
         in_table=in_Points, 
         field_mappings="Name FID #", 
         search_tolerance="500 Meters", 
         sort_field="", 
         search_criteria="NHDFlowline SHAPE;HydroNet_ND_Junctions NONE", 
         match_type="MATCH_TO_CLOSEST", 
         append="CLEAR", 
         snap_to_position_along_network="SNAP", 
         snap_offset="0 Meters", 
         exclude_restricted_elements="EXCLUDE", 
         search_query="NHDFlowline #;HydroNet_ND_Junctions #")
   printMsg('Completed point loading.')
   
   del naPoints
  
   # Solve upstream and downstream service layers; save out lines and updated layers
   for sa in [[in_downTrace, downLines, lyrDownTrace], [in_upTrace, upLines, lyrUpTrace]]:
      inLyr = sa[0]
      outLines = sa[1]
      outLyr = sa[2]
      printMsg('Solving service area for %s...' % inLyr)
      arcpy.Solve_na(in_network_analysis_layer=inLyr, 
         ignore_invalids="SKIP", 
         terminate_on_solve_error="TERMINATE", 
         simplification_tolerance="")
      inLines = arcpy.mapping.ListLayers(inLyr, "Lines")[0]
      printMsg('Saving out lines...')
      arcpy.CopyFeatures_management(inLines, outLines)
      arcpy.RepairGeometry_management (outLines, "DELETE_NULL")
      printMsg('Saving updated %s service layer to %s...' %(inLyr,outLyr))      
      arcpy.SaveToLayerFile_management(inLyr, outLyr)
   
   # Make feature layers for downstream lines
   qry = "ToCumul_Length <= 1609" 
   arcpy.MakeFeatureLayer_management (downLines, "downLTEbreak", qry)
   qry = "ToCumul_Length > 1609"
   arcpy.MakeFeatureLayer_management (downLines, "downGTbreak", qry)
   
   # Merge the downstream segments <= 1609 with the upstream segments
   printMsg('Merging primary segments...')
   mergedLines = out_Scratch + os.sep + 'mergedLines'
   arcpy.Merge_management (["downLTEbreak", upLines], mergedLines)
   
   # Erase downstream segments > 1609 that overlap the merged segments
   printMsg('Erasing irrelevant downstream extension segments...')
   erasedLines = out_Scratch + os.sep + 'erasedLines'
   arcpy.Erase_analysis ("downGTbreak", mergedLines, erasedLines)
   
   # Dissolve (on Facility ID) the remaining downstream segments > 1609
   printMsg('Dissolving remaining downstream extension segments...')
   dissolvedLines = out_Scratch + os.sep + 'dissolvedLines'
   arcpy.Dissolve_management(erasedLines, dissolvedLines, "FacilityID", "", "SINGLE_PART", "DISSOLVE_LINES")
   
   # From dissolved segments, select only those intersecting 2+ merged downstream/upstream segments
   ### Conduct nearest neighbor analysis with zero distance (i.e. touching)
   printMsg('Analyzing adjacency of extension segments to primary segments...')
   nearTab = out_Scratch + os.sep + 'nearTab'
   arcpy.GenerateNearTable_analysis(dissolvedLines, mergedLines, nearTab, "0 Meters", "NO_LOCATION", "NO_ANGLE", "ALL", "2", "PLANAR")
   
   #### Find out if segment touches at least two neighbors
   printMsg('Counting neighbors...')
   countTab = out_Scratch + os.sep + 'countTab'
   arcpy.Statistics_analysis(nearTab, countTab, "NEAR_FID COUNT", "IN_FID")
   qry = "FREQUENCY = 2"
   arcpy.MakeTableView_management(countTab, "connectorTab", qry)
   
   ### Get list of segments meeting the criteria, cast as a query and make feature layer
   printMsg('Extracting extension segments with at least two primary neighbors...')
   valList = unique_values("connectorTab", "IN_FID")
   if len(valList) > 0:
      qryList = str(valList)
      qryList = qryList.replace('[', '(')
      qryList = qryList.replace(']', ')')
      qry = "OBJECTID in %s" % qryList
   else:
      qry = "OBJECTID = -1"
   arcpy.MakeFeatureLayer_management (dissolvedLines, "extendLines", qry)
   
   # Grab additional segments that may have been missed within large PFs in wide water areas
   nhdFlowline = catPath + os.sep + "NHDFlowline"
   clpLine = out_Scratch + os.sep + 'clpLine'
   qry = "FType in (460, 558)" # StreamRiver and ArtificialPath only
   arcpy.MakeFeatureLayer_management (nhdFlowline, "StreamRiver_Line", qry)
   CleanClip("StreamRiver_Line", in_PF, clpLine)
   
   # Merge and dissolve the connected segments; ESRI does not make this simple
   printMsg('Merging primary segments with selected extension segments...')
   comboLines = out_Scratch + os.sep + 'comboLines'
   arcpy.Merge_management (["extendLines", mergedLines, clpLine], comboLines)
   
   printMsg('Buffering segments...')
   buffLines = out_Scratch + os.sep + 'buffLines'
   arcpy.Buffer_analysis(comboLines, buffLines, "1 Meters", "FULL", "ROUND", "ALL") 
   
   printMsg('Exploding buffers...')
   explBuff = outDir + os.sep + 'explBuff'
   arcpy.MultipartToSinglepart_management(buffLines, explBuff)
   
   printMsg('Grouping segments...')
   arcpy.AddField_management(explBuff, "grpID", "LONG")
   arcpy.CalculateField_management(explBuff, "grpID", "!OBJECTID!", "PYTHON")
   
   joinLines = out_Scratch + os.sep + 'joinLines'
   fldMap = 'grpID "grpID" true true false 4 Long 0 0, First, #, %s, grpID, -1, -1' % explBuff
   arcpy.SpatialJoin_analysis(comboLines, explBuff, joinLines, "JOIN_ONE_TO_ONE", "KEEP_ALL", fldMap, "INTERSECT")
   
   printMsg('Dissolving segments by group...')
   arcpy.Dissolve_management(joinLines, out_Lines, "grpID", "", "MULTI_PART", "DISSOLVE_LINES")
   
   # timestamp
   t1 = datetime.now()
   ds = GetElapsedTime (t0, t1)
   printMsg('Completed function. Time elapsed: %s' % ds)

   arcpy.CheckInExtension("Network")
   
   return (out_Lines, lyrDownTrace, lyrUpTrace)
   
def CreatePolys_scu(in_Lines, in_hydroNet, out_Polys, out_Scratch = arcpy.env.scratchGDB):
   '''Converts linear SCUs to polygons, including associated NHD StreamRiver polygons
   Parameters:
   - in_Lines = Input line feature class representing Stream Conservation Units
   - in_hydroNet = Input hydrological network dataset
   - out_Polys = Output polygon feature class representing Stream Conservation Units (without catchment area)
   - out_Scratch = Geodatabase to contain intermediate outputs
   '''
   
   # timestamp
   t0 = datetime.now()
   
   # Create empty feature class to store polygons
   sr = arcpy.Describe(in_Lines).spatialReference
   appendPoly = out_Scratch + os.sep + 'appendPoly'
   printMsg('Creating empty feature class for polygons')
   if arcpy.Exists(appendPoly):
      arcpy.Delete_management(appendPoly)
   arcpy.CreateFeatureclass_management (out_Scratch, 'appendPoly', "POLYGON", in_Lines, '', '', sr)
   
   # Set up some variables:
   descHydro = arcpy.Describe(in_hydroNet)
   nwDataset = descHydro.catalogPath
   catPath = os.path.dirname(nwDataset) # This is where hydro layers will be found
   nhdArea = catPath + os.sep + "NHDArea"
   nhdFlowline = catPath + os.sep + "NHDFlowline"
   
   # Make some feature layers   
   qry = "FType in (460, 558)" # StreamRiver and ArtificialPath only
   arcpy.MakeFeatureLayer_management (nhdFlowline, "StreamRiver_Line", qry)
   qry = "FType = 460" # StreamRiver only
   arcpy.MakeFeatureLayer_management (nhdArea, "StreamRiver_Poly", qry)
   
   # Variables used in-loop:
   bufferLines = out_Scratch + os.sep + 'bufferLines'
   splitPts = out_Scratch + os.sep + 'splitPts'
   tmpPts = out_Scratch + os.sep + 'tmpPts'
   tmpPts2 = out_Scratch + os.sep + 'tmpPts2'
   bufferPts = out_Scratch + os.sep + 'bufferPts'
   mbgPoly = out_Scratch + os.sep + 'mbgPoly'
   mbgBuffer = out_Scratch + os.sep + 'mbgBuffer'
   clipRiverPoly = out_Scratch + os.sep + 'clipRiverPoly'
   noGapPoly = out_Scratch + os.sep + "noGapPoly"
   clipRiverLine = out_Scratch + os.sep + 'clipRiverLine'
   clipLines = out_Scratch + os.sep + 'clipLines'
   perpLine1 = out_Scratch + os.sep + 'perpLine1'
   perpLine2 = out_Scratch + os.sep + 'perpLine2'
   perpLine = out_Scratch + os.sep + 'perpLine'
   perpClip = out_Scratch + os.sep + 'perpClip'
   splitPoly = out_Scratch + os.sep + 'splitPoly'
   mergePoly = out_Scratch + os.sep + 'mergePoly'
   tmpPoly = out_Scratch + os.sep + 'tmpPoly'
      
   with  arcpy.da.SearchCursor(in_Lines, ["SHAPE@", "grpID"]) as myLines:
      for line in myLines:
         shp = line[0]
         id = line[1]
         arcpy.env.Extent = shp
         
         printMsg('Working on %s...' % str(id))
         
         # Buffer linear SCU by at least half of cell size in flow direction raster (5 m)
         # This serves as the minimum polygon representing the SCU (in the absence of any nhdArea features)
         printMsg('Creating minimum buffer around linear SCU...')
         arcpy.Buffer_analysis(shp, bufferLines, "5 Meters", "", "ROUND", "ALL")

         # Generate large buffer polygon around linear SCU
         # Use this to clip nhdArea and nhdFlowline
         printMsg('Creating maximum buffer around linear SCU...')
         arcpy.Buffer_analysis(shp, mbgBuffer, "5000 Meters", "", "ROUND", "ALL")
         printMsg('Clipping NHD to buffer...')
         CleanClip("StreamRiver_Poly", mbgBuffer, clipRiverPoly)
         # Also need to fill any holes in polygons to avoid aberrant results
         arcpy. EliminatePolygonPart_management (clipRiverPoly, noGapPoly, "PERCENT", "", 99, "CONTAINED_ONLY")
         arcpy.MakeFeatureLayer_management (noGapPoly, "clipRiverPoly")
         CleanClip("StreamRiver_Line", mbgBuffer, clipRiverLine)
         
         # # Generate points at ends of linear SCU
         # printMsg('Generating split points at end of SCUs...')
         # arcpy.FeatureVerticesToPoints_management(shp, splitPts, "DANGLE") 
                  
         # Generate points where buffered linear SCU intersects Flowlines
         printMsg('Generating split points...')
         arcpy.Intersect_analysis ([bufferLines, clipRiverLine], tmpPts, "", "", "POINT")
         arcpy.MultipartToSinglepart_management (tmpPts, splitPts)

         # Select only the points within clipped StreamRiver polygons
         arcpy.MakeFeatureLayer_management (splitPts, "splitPts")
         arcpy.SelectLayerByLocation_management("splitPts", "COMPLETELY_WITHIN", "clipRiverPoly")
         c = countSelectedFeatures("splitPts")
         if c > 0:
            # Buffer points and use them to clip flowlines
            printMsg('Buffering split points...')
            arcpy.Buffer_analysis("splitPts", bufferPts, "1 Meters")
            printMsg('Clipping flowlines at split points...')
            CleanClip(nhdFlowline, bufferPts, clipLines)
            
            # Add geometry attributes to clipped segments
            printMsg('Adding geometry attributes...')
            arcpy.AddGeometryAttributes_management(clipLines, "CENTROID;LINE_BEARING")
            arcpy.AddField_management(clipLines, "PERP_BEARING1", "DOUBLE")
            arcpy.AddField_management(clipLines, "PERP_BEARING2", "DOUBLE")
            arcpy.AddField_management(clipLines, "DISTANCE", "DOUBLE")
            expression = "PerpBearing(!BEARING!)"
            code_block1='''def PerpBearing(bearing):
               p = bearing + 90
               if p > 360:
                  p -= 360
               return p'''
            code_block2='''def PerpBearing(bearing):
               p = bearing - 90
               if p < 0:
                  p += 360
               return p'''
            arcpy.CalculateField_management(clipLines, "PERP_BEARING1", expression, "PYTHON_9.3", code_block1)
            arcpy.CalculateField_management(clipLines, "PERP_BEARING2", expression, "PYTHON_9.3", code_block2)
            arcpy.CalculateField_management(clipLines, "DISTANCE", 10, "PYTHON_9.3")

            # Generate lines perpendicular to segment
            # These need to be really long to cut wide rivers near Chesapeake
            printMsg('Creating perpendicular lines at split points...')
            for l in [["PERP_BEARING1", perpLine1],["PERP_BEARING2", perpLine2]]:
               bearingFld = l[0]
               outLine = l[1]
               arcpy.BearingDistanceToLine_management(clipLines, outLine, "CENTROID_X", "CENTROID_Y", "DISTANCE", "KILOMETERS", bearingFld, "DEGREES", "GEODESIC", "", sr)
            arcpy.Merge_management ([perpLine1, perpLine2], perpLine)
            
            # Clip perpendicular lines to clipped StreamRiver
            CleanClip(perpLine, "clipRiverPoly", perpClip)
            arcpy.MakeFeatureLayer_management (perpClip, "perpClip")
            
            # Select lines intersecting the point buffers
            arcpy.SelectLayerByLocation_management("perpClip", "INTERSECT", bufferPts, "", "NEW_SELECTION")
            
            # Remove from selection any lines < 5m from scuLine
            arcpy.SelectLayerByLocation_management("perpClip", "WITHIN_A_DISTANCE", shp, "4.9 Meters", "REMOVE_FROM_SELECTION")
            
            # Select clipped StreamRiver polygons containing selected lines
            arcpy.SelectLayerByLocation_management("clipRiverPoly", "CONTAINS", "perpClip", "", "NEW_SELECTION")
            
            # Use selected lines to split clipped StreamRiver polygons
            printMsg('Splitting river polygons with perpendiculars...')
            arcpy.FeatureToPolygon_management("perpClip;clipRiverPoly", splitPoly)
            arcpy.MakeFeatureLayer_management (splitPoly, "splitPoly")
            
            # Select split StreamRiver polygons containing scuLines
            # Two selection criteria needed to capture all
            arcpy.SelectLayerByLocation_management("splitPoly", "CROSSED_BY_THE_OUTLINE_OF", shp, "", "NEW_SELECTION")
            arcpy.SelectLayerByLocation_management("splitPoly", "CONTAINS", shp, "", "ADD_TO_SELECTION")
            
            # Merge/dissolve polygons in with baseline buffered scuLines
            printMsg('Merging and dissolving shapes...')
            arcpy.Merge_management ([bufferLines, "splitPoly"], mergePoly)
            arcpy.Dissolve_management (mergePoly, tmpPoly, "", "", "SINGLE_PART")
            
         else:
            tmpPoly = bufferLines
            
         # Append to output
         printMsg('Appending shape to output...')
         arcpy.Append_management (tmpPoly, appendPoly, "NO_TEST")
         
   # Dissolve final output
   printMsg('Dissolving final shapes...')
   arcpy.Dissolve_management (appendPoly, out_Polys, "", "", "SINGLE_PART")
   
   # timestamp
   t1 = datetime.now()
   ds = GetElapsedTime (t0, t1)
   printMsg('Completed function. Time elapsed: %s' % ds)

   return out_Polys
   
def CreateFlowBuffers_scu(in_Polys, fld_ID, in_FlowDir, out_Polys, maxDist, out_Scratch = arcpy.env.scratchGDB):
   '''Delineates catchment buffers around polygon SCUs based on flow distance down to features (rather than straight distance)
   Parameters:
   - in_Polys = Input polygons representing unbuffered Stream Conservation Units
   - fld_ID = The field in the input Procedural Features containing the Source Feature ID
   - in_FlowDir = Input raster representing D8 flow direction
   - out_Polys = Output polygon feature class representing Stream Conservation Units with catchment buffers
   - maxDist = Maximum buffer distance (used to truncate catchments)
   - out_Scratch = Geodatabase to contain intermediate outputs
   
   Note that scratchGDB is used rather than in_memory b/c process inexplicably yields incorrect output otherwise.
   '''
   
   # timestamp
   t0 = datetime.now()
   
   arcpy.CheckOutExtension("Spatial")
   
   # Get cell size and output spatial reference from in_FlowDir
   cellSize = (arcpy.GetRasterProperties_management(in_FlowDir, "CELLSIZEX")).getOutput(0)
   srRast = arcpy.Describe(in_FlowDir).spatialReference
   linUnit = srRast.linearUnitName
   printMsg('Cell size of flow direction raster is %s %ss' %(cellSize, linUnit))
   printMsg('Flow modeling is strongly dependent on cell size.')

   # Set environment setting and other variables
   arcpy.env.snapRaster = in_FlowDir
   (num, units, procDist) = multiMeasure(maxDist, 3)

   # Check if input features and input flow direction have same spatial reference.
   # If so, just make a copy. If not, reproject features to match raster.
   srFeats = arcpy.Describe(in_Polys).spatialReference
   if srFeats.Name == srRast.Name:
      printMsg('Coordinate systems for features and raster are the same. Copying...')
      arcpy.CopyFeatures_management (in_Polys, out_Polys)
   else:
      printMsg('Reprojecting features to match raster...')
      # Check if geographic transformation is needed, and handle accordingly.
      if srFeats.GCS.Name == srRast.GCS.Name:
         geoTrans = ""
         printMsg('No geographic transformation needed...')
      else:
         transList = arcpy.ListTransformations(srFeats,srRast)
         geoTrans = transList[0]
      arcpy.Project_management (in_Polys, out_Polys, srRast, geoTrans)

   # Add and calculate a field needed for raster conversion
   arcpy.AddField_management (out_Polys, 'rasterVal', 'SHORT')
   arcpy.CalculateField_management (out_Polys, 'rasterVal', '1', 'PYTHON_9.3')
      
   # Count features and report
   numFeats = countFeatures(out_Polys)
   printMsg('There are %s features to process.' % numFeats)
   
   # Variables used in loop
   trashList = [] # Empty list for trash collection
   tmpFeat = out_Scratch + os.sep + 'tmpFeat'
   srcRast = out_Scratch + os.sep + 'srcRast'
   procBuff = out_Scratch + os.sep + 'procBuff'
   clp_FlowDir = out_Scratch + os.sep + 'clp_FlowDir'
   clp_Watershed = out_Scratch + os.sep + 'clp_Watershed'
   snk_FlowDir = out_Scratch + os.sep + 'snk_FlowDir'
   FlowDist = out_Scratch + os.sep + 'FlowDist'
   clipBuff = out_Scratch + os.sep + 'clipBuff'
   clp_FlowDist = out_Scratch + os.sep + 'clp_FlowDist'
   binRast = out_Scratch + os.sep + 'binRast'
   cleanRast = out_Scratch + os.sep + 'cleanRast'
   prePoly = out_Scratch + os.sep + 'prePoly'
   finPoly = out_Scratch + os.sep + 'finPoly'
   coalescedPoly = out_Scratch + os.sep + 'finPoly'
   multiPoly = out_Scratch + os.sep + 'multiPoly'
   
   # Create an empty list to store IDs of features that fail to get processed
   myFailList = []

   # Set up processing cursor and loop
   flags = [] # Initialize empty list to keep track of suspects
   cursor = arcpy.da.UpdateCursor(out_Polys, [fld_ID, "SHAPE@"])
   counter = 1
   for row in cursor:
      try:
         # Extract the unique ID and geometry object
         myID = row[0]
         myShape = row[1]

         printMsg('Working on feature %s with ID %s' % (counter, str(myID)))

         # Process:  Select (Analysis)
         # Create a temporary feature class including only the current feature
         selQry = "%s = %s" % (fld_ID, str(myID))
         arcpy.Select_analysis (out_Polys, tmpFeat, selQry)

         # Clip flow direction raster to processing buffer
         printMsg('Buffering feature to set maximum processing distance')
         arcpy.Buffer_analysis (tmpFeat, procBuff, procDist, "", "", "ALL", "")
         myExtent = str(arcpy.Describe(procBuff).extent).replace(" NaN", "")
         #printMsg('Extent: %s' %myExtent)
         printMsg('Clipping flow direction raster to processing buffer')
         arcpy.Clip_management (in_FlowDir, myExtent, clp_FlowDir, procBuff, "", "ClippingGeometry")
         arcpy.env.extent = procBuff
         arcpy.env.mask = procBuff
         
         # Convert feature to raster
         arcpy.PolygonToRaster_conversion (tmpFeat, 'rasterVal', srcRast, "MAXIMUM_COMBINED_AREA", 'rasterVal', cellSize)

         # Get the watershed for the SCU feature (truncated by processing buffer)
         printMsg('Creating truncated watershed from feature...')
         tmpRast = Watershed (clp_FlowDir, srcRast)
         tmpRast2 = CellStatistics([tmpRast, srcRast], "MAXIMUM", "DATA")
         # Above step needed in situations with missing flow direction data (coastal)
         tmpRast2.save(clp_Watershed)
         arcpy.env.mask = clp_Watershed # Processing now restricted to Watershed
         
         # Burn SCU feature into flow direction raster as sink
         printMsg('Creating sink from feature...')
         tmpRast = Con(IsNull(srcRast),clp_FlowDir)
         tmpRast.save(snk_FlowDir)
         
         # Calculate flow distance down to sink
         printMsg('Within watershed, calculating flow distance to sink...')
         tmpRast = FlowLength (snk_FlowDir, "DOWNSTREAM")
         tmpRast.save(FlowDist)
         
         # Clip flow distance raster to the maximum distance buffer
         arcpy.Buffer_analysis (tmpFeat, clipBuff, maxDist, "", "", "ALL", "")
         myExtent = str(arcpy.Describe(clipBuff).extent).replace(" NaN", "")
         #printMsg('Extent: %s' %myExtent)
         printMsg('Clipping flow distance raster to maximum distance buffer')
         arcpy.Clip_management (FlowDist, myExtent, clp_FlowDist, clipBuff, "", "ClippingGeometry")
         arcpy.env.extent = clp_FlowDist
         
         # Make a binary raster based on flow distance
         printMsg('Creating binary raster from flow distance...')
         tmpRast = Con((IsNull(clp_FlowDist) == 1),
                  (Con((IsNull(srcRast)== 0),1,0)),
                  (Con((Raster(clp_FlowDist) <= num),1,0)))
         tmpRast.save(binRast)
         # printMsg('Boundary cleaning...')
         # tmpRast = BoundaryClean (binRast, 'NO_SORT', 'TWO_WAY')
         # tmpRast.save(cleanRast)
         printMsg('Setting zeros to nulls...')
         tmpRast = SetNull (binRast, 1, 'Value = 0')
         tmpRast.save(prePoly)

         # Convert raster to polygon
         printMsg('Converting flow distance raster to polygon...')
         arcpy.RasterToPolygon_conversion (prePoly, finPoly, "NO_SIMPLIFY")
     
         # Check the number of features at this point. 
         # It should be just one. If more, need to remove orphan fragments.
         arcpy.MakeFeatureLayer_management (finPoly, "finPoly")
         count = countFeatures("finPoly")
         if count > 1:
            printMsg('Removing orphan fragments...')
            arcpy.SelectLayerByLocation_management("finPoly", "CONTAINS", tmpFeat, "", "NEW_SELECTION")
         
         # Use the flow distance buffer geometry as the final shape
         myFinalShape = arcpy.SearchCursor("finPoly").next().Shape

         # Update the feature with its final shape
         row[1] = myFinalShape
         cursor.updateRow(row)
         del row 

         printMsg('Finished processing feature %s' %str(myID))

      except:
         # Add failure message and append failed feature ID to list
         printMsg("\nFailed to fully process feature " + str(myID))
         myFailList.append(myID)

         # Error handling code swiped from "A Python Primer for ArcGIS"
         tb = sys.exc_info()[2]
         tbinfo = traceback.format_tb(tb)[0]
         pymsg = "PYTHON ERRORS:\nTraceback Info:\n" + tbinfo + "\nError Info:\n " + str(sys.exc_info()[1])
         msgs = "ARCPY ERRORS:\n" + arcpy.GetMessages(2) + "\n"

         printWrng(msgs)
         printWrng(pymsg)
         printMsg(arcpy.GetMessages(1))

         # Add status message
         printMsg("\nMoving on to the next feature.  Note that the output will be incomplete.")
         
      finally:
         # Reset extent, because Arc is stupid.
         arcpy.env.extent = "MAXOF"
         
         # Update counter
         counter += 1
         
         # Grasping at straws here to avoid failure processing large datasets.
         if counter%25 == 0:
            printMsg('Compacting scratch geodatabase...')
            arcpy.Compact_management (out_Scratch)
   
   if len(flags) > 0:
      printWrng('These features may be incorrect: %s' % str(flags))
   if len(myFailList) > 0:
      printWrng('These features failed to process: %s' % str(myFailList))
   

   
   arcpy.CheckInExtension("Spatial")
   
   # timestamp
   t1 = datetime.now()
   ds = GetElapsedTime (t0, t1)
   printMsg('Completed function. Time elapsed: %s' % ds)
   
   return out_Polys
   
# Use the main function below to run functions directly from Python IDE or command line with hard-coded variables
def main():
   in_hydroNet = r'C:\Users\xch43889\Documents\Working\SCU\VA_HydroNet.gdb\HydroNet\HydroNet_ND'
   in_blueways = r'C:\Users\xch43889\Documents\Working\ConsVision\RecMod\Watertrails2019\waterTrails_work.gdb\Watertrails_prj'
   out_points = r'C:\Users\xch43889\Documents\Working\ConsVision\RecMod\Watertrails2019\waterTrails_work.gdb\Watertrails_points'
   out_cleanBlueways = r'C:\Users\xch43889\Documents\Working\ConsVision\RecMod\Watertrails2019\waterTrails_work.gdb\Watertrails_clean'
   # End of user input

   # Function(s) to run
   #MakeRouteLayer_bw(in_hydroNet)
   MakeRoutePts_bw(in_hydroNet, out_cleanBlueways, out_points)

   
if __name__ == '__main__':
   main()
