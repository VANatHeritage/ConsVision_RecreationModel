# ----------------------------------------------------------------------------------------
# WaterAccess.py
# Version:  ArcGIS 10.3.1 / Python 2.7.8
# Creation Date: 2018-06-07
# Last Edit: 2018-06-19
# Creator:  Kirsten R. Hazler

# Summary:
# Functions for creating water access areas for Recreation Model. 
# Requirements:
# - A geodatabase containing a fully functional hydrologic network and associated NHD features (VA_HydroNet.gdb). References to objects within this geodatabase are hard-coded.
# - A set of points representing water access. These may have been combined from multiple sources, and must already have been filtered to include only points with true water access (i.e., within 50-m of water features).
# - A set of lines representing public beaches

# NOTE: In a few rare cases, an access point may end up with two different areas associated with it. This should be accounted for somehow in subsequent processing.
# ----------------------------------------------------------------------------------------


# Import Helper module and functions
import Helper
from Helper import *
from arcpy import env

# Check out the Network Analyst extension license
arcpy.CheckOutExtension("Network")

# Create the service area layer
def MakeServiceLayer_aqua(in_GDB, out_LyrFile):
   '''Creates a service area layer based on 5-km travel distance up and down the hydro network.
   Parameters:
   - in_GDB = The geodatabase containing the network and associated features
   - out_LyrFile = The output layer file 
   NOTE: Removed restriction on CanalDitches, because it was excluding some features that should have been kept.
   '''
   t1 = datetime.now()
   
   # Make service area layer 
   nwDataset = in_GDB + os.sep + "HydroNet" + os.sep + "HydroNet_ND"
   
   outNALayer = arcpy.MakeServiceAreaLayer_na(in_network_dataset=nwDataset,
         out_network_analysis_layer="FlowlineTrace_5k", 
         impedance_attribute="Length", 
         travel_from_to="TRAVEL_FROM", 
         default_break_values="5000", 
         polygon_type="NO_POLYS", 
         merge="NO_MERGE", 
         nesting_type="RINGS", 
         line_type="TRUE_LINES_WITH_MEASURES", 
         overlap="NON_OVERLAP", 
         split="SPLIT", 
         excluded_source_name="", 
         accumulate_attribute_name="Length", 
         UTurn_policy="ALLOW_UTURNS", 
         restriction_attribute_name="NoConnectors;NoPipelines;NoUndergroundConduits", 
         polygon_trim="TRIM_POLYS", 
         poly_trim_value="100 Meters", 
         lines_source_fields="LINES_SOURCE_FIELDS", 
         hierarchy="NO_HIERARCHY", 
         time_of_day="")

   # Save layer file
   arcpy.SaveToLayerFile_management(in_layer="FlowlineTrace_5k", out_layer=out_LyrFile, is_relative_path="RELATIVE", version="CURRENT")   
         
   # Get the layer object from the result object. The service area layer can now be referenced using the layer object.
   outNALayer = outNALayer.getOutput(0)

   t2 = datetime.now()
   deltaString = GetElapsedTime (t1, t2)
   printMsg('Time elapsed to create service area layer: %s' % deltaString)
   
   return outNALayer

# Load barriers into the service area layer
def LoadBarriers_aqua(in_ServiceLayer, in_GDB):
   '''Creates line barriers in the service area layer, using dams and weirs. This results in truncation and separation of service areas in some places.
   Parameters:
   - in_ServiceLayer = The service layer output from the MakeServiceLayer_aqua function
   - in_GDB = The geodatabase containing the network and associated features
   '''
   
   t1 = datetime.now()
   
   in_Lines = in_GDB + os.sep + "HydroNet" + os.sep + "NHDLine"
   where_clause = "FType = 343" # DamWeir only
   arcpy.MakeFeatureLayer_management (in_Lines, "lyr_DamWeir", where_clause)
   in_Lines = "lyr_DamWeir"

   barriers = arcpy.AddLocations_na(in_network_analysis_layer=in_ServiceLayer, 
         sub_layer="Line Barriers", 
         in_table=in_Lines, 
         field_mappings="Name Permanent_Identifier #", 
         search_tolerance="100 Meters", 
         sort_field="", 
         search_criteria="NHDFlowline SHAPE_MIDDLE_END;HydroNet_ND_Junctions NONE", 
         match_type="MATCH_TO_CLOSEST", 
         append="CLEAR", 
         snap_to_position_along_network="SNAP", 
         snap_offset="5 Meters", 
         exclude_restricted_elements="INCLUDE", 
         search_query="NHDFlowline #;HydroNet_ND_Junctions #")

   t2 = datetime.now()
   deltaString = GetElapsedTime (t1, t2)
   printMsg('Time elapsed to load barriers: %s' % deltaString)
   
   return in_ServiceLayer
   
# Load water access points into the service area layer
def LoadAccessPts_aqua(in_ServiceLayer, in_Points):
   '''Creates facilities in the service area layer, from water access points input by user. Assumes water access input is a shapefile, as this function uses the FID for the facilities names. May want to recode to use some other unique identifier.
   
   NOTE: Since the search tolerance to assign points to networks is generous, input access points not specifically water-based should be filtered to ensure that they are in fact within 50-m of NHD features, prior to loading into the service area layer.
   
   Parameters:
   - in_ServiceLayer = The service layer output from the MakeServiceLayer_aqua function
   - in_Points = The shapefile representing water access points.
   '''
   
   t1 = datetime.now()
   
   access = arcpy.AddLocations_na(in_network_analysis_layer=in_ServiceLayer, 
         sub_layer="Facilities", 
         in_table=in_Points, 
         field_mappings="Name FID #", 
         search_tolerance="500 Meters", 
         sort_field="", 
         search_criteria="NHDFlowline SHAPE;HydroNet_ND_Junctions NONE", 
         match_type="MATCH_TO_CLOSEST", 
         append="CLEAR", 
         snap_to_position_along_network="NO_SNAP", 
         snap_offset="5 Meters", 
         exclude_restricted_elements="EXCLUDE", 
         search_query="NHDFlowline #;HydroNet_ND_Junctions #")
   
   in_ServiceLayer.save
   
   t2 = datetime.now()
   deltaString = GetElapsedTime (t1, t2)
   printMsg('Time elapsed to load access points: %s' % deltaString)
   
   return in_ServiceLayer
   
# Solve the service area layer and generate polygons from lines
def GetServiceAreas_aqua(in_ServiceLayer, in_GDB, in_BeachLines, out_GDB, scratchGDB = "in_memory"):
   '''Gets the output from solving the service layer and performs additional steps to get final output.
   Parameters:
   - in_ServiceLayer = The service layer output from the MakeServiceLayer_aqua function
   - in_GDB = The input geodatabase containing the network and associated features
   - in_BeachLines = Line feature class representing public beaches
   - out_GDB = Geodatabase for storing outputs.
   '''
   
   t1 = datetime.now()
   
   # Solve the service area
   printMsg('Solving service area...')
   arcpy.Solve_na(in_network_analysis_layer=in_ServiceLayer, 
      ignore_invalids="SKIP", 
      terminate_on_solve_error="TERMINATE", 
      simplification_tolerance="")
      
   # # Save out the service area points NOT located on network. We need these to capture off-network features.
   # printMsg('Saving out non-network points...')
   # in_Points = arcpy.mapping.ListLayers(in_ServiceLayer, "Facilities")[0]
   # where_clause = '"Status" <> 0' 
   # arcpy.MakeFeatureLayer_management (in_Points, "lyr_offPts", where_clause)
   # out_Points = out_GDB + os.sep + "offPts"
   # arcpy.CopyFeatures_management("lyr_offPts", out_Points)
      
   # Save out the service area lines
   printMsg('Saving out lines...')
   in_Lines = arcpy.mapping.ListLayers(in_ServiceLayer, "Lines")[0]
   out_Lines = out_GDB + os.sep + "saLines"
   arcpy.CopyFeatures_management(in_Lines, out_Lines)
   
   # Set up some variables for NHD features
   nhdFlowLine = in_GDB + os.sep + "HydroNet" + os.sep + "NHDFlowline"
   nhdArea = in_GDB + os.sep + "HydroNet" + os.sep + "NHDArea"
   nhdWaterbody = in_GDB + os.sep + "HydroNet" + os.sep + "NHDWaterbody"
   
   # Attach the FType to lines
   printMsg('Attaching FType attributes...')
   arcpy.JoinField_management(out_Lines, "SourceOID", nhdFlowLine, "OBJECTID", "FType")
   
   # Make subsets from NHD features, if they don't already exist
   nhdStreamRiver = in_GDB + os.sep + "nhdStreamRiverCanalDitch"
   if not arcpy.Exists (nhdStreamRiver):
      printMsg('Creating StreamRiverCanalDitch subset from NHD...')
      where_clause = "FType in (460,336)" # StreamRiver and CanalDitch polygons only
      arcpy.Select_analysis(nhdArea, nhdStreamRiver, where_clause)
   
   nhdLakePond = in_GDB + os.sep + "nhdLakePondReservoir"
   if not arcpy.Exists(nhdLakePond):
      printMsg('Creating LakePondReservoir subset from NHD...')
      where_clause = "FType in (390, 436)" # LakePond and Reservoir polygons only
      arcpy.Select_analysis(nhdWaterbody, nhdLakePond, where_clause)

   nhdSeaOcean = in_GDB + os.sep + "nhdSeaOcean"
   if not arcpy.Exists(nhdSeaOcean):
      printMsg('Creating SeaOcean subset from NHD...')
      where_clause = "FType = 445" # SeaOcean polygons only
      arcpy.Select_analysis(nhdArea, nhdSeaOcean, where_clause)
   
   nhdEstuary = in_GDB + os.sep + "nhdEstuary"
   if not arcpy.Exists(nhdEstuary):
      printMsg('Creating Estuary subset from NHD...')
      where_clause = "FType = 493" # Estuary polygons only
      arcpy.Select_analysis(nhdWaterbody, nhdEstuary, where_clause)
   
   nhdChesBay = in_GDB + os.sep + "nhdChesBay"
   if not arcpy.Exists(nhdChesBay):
      printMsg('Creating Chesapeake Bay polygon from NHD...')
      where_clause = "GNIS_Name = 'Chesapeake Bay'" # Get the Chesapeak Bay polygon
      arcpy.Select_analysis(nhdWaterbody, nhdChesBay, where_clause)
      
   # Make layers from service area lines
   where_clause = "FType in (558,460,336)" # Artificial Paths, StreamRiver, and CanalDitch lines
   lyrStreamline = arcpy.MakeFeatureLayer_management (out_Lines, "lyr_Streamline", where_clause)
   arcpy.AddField_management (lyrStreamline, "inBay", "SHORT")
   arcpy.SelectLayerByLocation_management (lyrStreamline, "WITHIN", nhdChesBay)
   arcpy.CalculateField_management (lyrStreamline, "inBay", 1, "PYTHON")
   where_clause = "FType in (558,460,336) AND  inBay IS NULL" # Artificial Paths, StreamRiver, and CanalDitch lines not in Bay
   lyrStreamline = arcpy.MakeFeatureLayer_management (out_Lines, "lyr_Streamline", where_clause)
   
   where_clause = "FType = 566" # Coastline type only
   lyrCoastline = arcpy.MakeFeatureLayer_management (out_Lines, "lyr_Coastline", where_clause)

   ### Process the streamlines
   printMsg('Processing streamlines...')

   # Create narrow stream buffers
   # Opted for round buffers to avoid artifactual disconnects at coastline junctions
   printMsg('Applying 5-m buffers to streams...')
   aquaBuff= out_GDB + os.sep + "aquaBuff"
   arcpy.Buffer_analysis (lyrStreamline, aquaBuff, "5 METERS", "", "ROUND", "ALL")
   
   # Declare some variables
   dissLines = scratchGDB + os.sep + "dissLines"
   dissStreamlines = out_GDB + os.sep + "dissStreamlines"
   dissCoastlines = out_GDB + os.sep + "dissCoastlines"
   minBnd = scratchGDB + os.sep + "minBnd"
   
   # Group and delineate boundaries for streamlines
   # Limit to streamlines contained within StreamRiver and LakePond polygons
   printMsg('Selecting streamlines within StreamRiver polygons...')
   arcpy.SelectLayerByLocation_management (lyrStreamline, "INTERSECT", nhdStreamRiver)
   printMsg('Adding streamlines within LakePond polygons...')
   arcpy.SelectLayerByLocation_management (lyrStreamline, "INTERSECT", nhdLakePond, "", "ADD_TO_SELECTION")

   printMsg('First streamline dissolve...')
   arcpy.Dissolve_management(lyrStreamline, dissLines,"FacilityID", "", "MULTI_PART", "DISSOLVE_LINES")
   printMsg('Second streamline dissolve...')
   arcpy.Dissolve_management(dissLines, dissStreamlines, "", "", "MULTI_PART", "UNSPLIT_LINES")
   arcpy.Delete_management(dissLines)
   
   c = countFeatures(dissStreamlines)
   printMsg('Starting streamline loop. %s features to process.' %str(c))
   i = 1
   with arcpy.da.SearchCursor(dissStreamlines, ["SHAPE@"]) as myLines:
      for line in myLines:
         printMsg('Working on streamline feature %s...' % str(i))
         lnShp = line[0]
         
         # Create bounding polygon
         printMsg('Creating minimum bounding polygon...')
         arcpy.MinimumBoundingGeometry_management(lnShp, minBnd, "CIRCLE", "NONE")
   
         # Clip StreamRiver polygons to streamline boundaries and append to aquaBuff
         clpStreamRiver = scratchGDB + os.sep + "clpStreamRiver"
         printMsg('Clipping StreamRiver polygons to minimum bounding polygon...')
         CleanClip(nhdStreamRiver, minBnd, clpStreamRiver)
         lyrCleanClip = arcpy.MakeFeatureLayer_management (clpStreamRiver, "lyr_CleanClip")
         printMsg('Selecting clips that intersect streamline feature...')
         arcpy.SelectLayerByLocation_management (lyrCleanClip, "INTERSECT", lnShp)
         printMsg('Appending...')
         arcpy.Append_management (lyrCleanClip, aquaBuff, "NO_TEST")
         
         # Clip on-network LakePond and Reservoir polygons to streamline boundaries and append to aquaBuff
         clpLakePond = scratchGDB + os.sep + "clpLakePond"
         printMsg('Clipping LakePond polygons to minimum bounding polygon...')
         CleanClip(nhdLakePond, minBnd, clpLakePond)
         lyrCleanClip = arcpy.MakeFeatureLayer_management (clpLakePond, "lyr_CleanClip")
         printMsg('Selecting clips that intersect streamline feature...')
         arcpy.SelectLayerByLocation_management (lyrCleanClip, "INTERSECT", lnShp)
         printMsg('Appending...')
         arcpy.Append_management (lyrCleanClip, aquaBuff, "NO_TEST")
         
         i += 1
   
   ### Process the coastlines
   printMsg('Processing coastlines...')

   # Group and delineate boundaries for coastlines
   printMsg('First coastline dissolve...')
   arcpy.Dissolve_management(lyrCoastline, dissLines,"FacilityID", "", "MULTI_PART", "DISSOLVE_LINES")
   printMsg('Second coastline dissolve...')
   arcpy.Dissolve_management(dissLines, dissCoastlines, "", "", "MULTI_PART", "UNSPLIT_LINES")
   arcpy.Delete_management(dissLines)
   
   # Declare in-loop variables
   coastBuff = scratchGDB + os.sep + "coastBuff"
   coastBnd = scratchGDB + os.sep + "coastBnd"
   clpCoastal = scratchGDB + os.sep + "clpCoastal"
   
   c = countFeatures(dissCoastlines)
   printMsg('Starting coastline loop. %s features to process.' %str(c))
   i = 1
   with arcpy.da.SearchCursor(dissCoastlines, ["SHAPE@"]) as myLines:
      for line in myLines:
         printMsg('Working on coastline feature %s...' % str(i))
         lnShp = line[0]
      
         # Create bounding polygon
         arcpy.MinimumBoundingGeometry_management(lnShp, minBnd, "CIRCLE", "NONE")
         arcpy.Buffer_analysis (lnShp, coastBuff, "5000 METERS", "", "ROUND", "ALL")
         arcpy.Intersect_analysis ([coastBuff, minBnd], coastBnd, "ONLY_FID")
         
         # Clip SeaOcean polygons to coastline boundaries and append to aquaBuff
         CleanClip (nhdSeaOcean, coastBnd, clpCoastal)
         lyrCleanClip = arcpy.MakeFeatureLayer_management (clpCoastal, "lyr_CleanClip")
         arcpy.SelectLayerByLocation_management (lyrCleanClip, "INTERSECT", lnShp)
         arcpy.Append_management (lyrCleanClip, aquaBuff, "NO_TEST")
         
         # Clip Estuary polygons to coastline boundaries and append to aquaBuff
         CleanClip (nhdEstuary, coastBnd, clpCoastal)
         lyrCleanClip = arcpy.MakeFeatureLayer_management (clpCoastal, "lyr_CleanClip")
         arcpy.SelectLayerByLocation_management (lyrCleanClip, "INTERSECT", lnShp)
         arcpy.Append_management (lyrCleanClip, aquaBuff, "NO_TEST")
         
         i += 1
   
   ###Process beaches. These can be on ocean, bay, or large river.
   # Proximity of 32 meters was chosen based on Near analysis and to minimize chance of grabbing incorrect areas.
   printMsg('Processing beachlines...')
   beachBuff = scratchGDB + os.sep + "beachBuff"
   arcpy.Buffer_analysis (in_BeachLines, beachBuff, "1000 METERS", "", "FLAT", "ALL")
   
   # Clip SeaOcean to beach buffer and append to aquaBuff
   CleanClip (nhdSeaOcean, beachBuff, clpCoastal)
   lyrCleanClip = arcpy.MakeFeatureLayer_management (clpCoastal, "lyr_CleanClip")
   arcpy.SelectLayerByLocation_management (lyrCleanClip, "WITHIN_A_DISTANCE", in_BeachLines, "32 METERS")
   arcpy.Append_management (lyrCleanClip, aquaBuff, "NO_TEST")
   
   # Clip Estuary polygons to beach buffer and append to aquaBuff
   CleanClip (nhdEstuary, beachBuff, clpCoastal)
   lyrCleanClip = arcpy.MakeFeatureLayer_management (clpCoastal, "lyr_CleanClip")
   arcpy.SelectLayerByLocation_management (lyrCleanClip, "WITHIN_A_DISTANCE", in_BeachLines, "32 METERS")
   arcpy.Append_management (lyrCleanClip, aquaBuff, "NO_TEST")
   
   # Clip StreamRiver polygons to beach buffer and append to aquaBuff
   CleanClip (nhdStreamRiver, beachBuff, clpCoastal)
   lyrCleanClip = arcpy.MakeFeatureLayer_management (clpCoastal, "lyr_CleanClip")
   arcpy.SelectLayerByLocation_management (lyrCleanClip, "WITHIN_A_DISTANCE", in_BeachLines, "32 METERS")
   arcpy.Append_management (lyrCleanClip, aquaBuff, "NO_TEST")


   ### Process all points to get minimum areas
   printMsg('Processing points...')
   # Merge polygon layers into one
   mergePolys = "in_memory" + os.sep + "mergePolys"
   arcpy.Merge_management ([nhdEstuary, nhdSeaOcean, nhdLakePond, nhdStreamRiver], mergePolys)

   # Declare in-loop variables
   tmpBuff = "in_memory" + os.sep + "tmpBuff"
   tmpCleanClip = "in_memory" + os.sep + "tmpCleanClip"
   tmpDissolve = "in_memory" + os.sep + "tmpDissolve"
   
   # Process points and polygons within loop
   in_Points = arcpy.mapping.ListLayers(in_ServiceLayer, "Facilities")[0]
   printMsg('Looping through all points to establish minimum areas covered within associated polygons...')
   with arcpy.da.SearchCursor(in_Points, ["SHAPE@"]) as myPoints:
      for point in myPoints:
         ptShape = point[0]
         
         arcpy.Buffer_analysis (ptShape, tmpBuff, "2500 METERS")
         CleanClip (mergePolys, tmpBuff, tmpCleanClip)
         
         # Not sure why I put in this Dissolve step. Delete?
         arcpy.Dissolve_management (tmpCleanClip, tmpDissolve, "", "", "SINGLE_PART")
         lyrDissolve = arcpy.MakeFeatureLayer_management (tmpDissolve, "lyr_Dissolve")
         
         arcpy.SelectLayerByLocation_management (lyrDissolve, "WITHIN_A_DISTANCE", ptShape, "100 METERS")
         arcpy.Append_management (lyrDissolve, aquaBuff, "NO_TEST")

   ### Dissolve all the polygons
   printMsg('Dissolving polygons...')
   aquaPolys = out_GDB + os.sep + "aquaPolys"
   arcpy.Dissolve_management (aquaBuff, aquaPolys, "", "", "SINGLE_PART")
   
   t2 = datetime.now()
   deltaString = GetElapsedTime (t1, t2)
   printMsg('Time elapsed to create service area polygons: %s' % deltaString)
   
   return aquaPolys
   
 
################################################################################################
# Use the main function below to run functions directly from Python IDE or command line with hard-coded variables

def main():
   # Set up variables
   in_GDB = r'C:\Users\xch43889\Documents\Working\ConsVision\HydroNet_testing\VA_HydroNet.gdb'
   out_LyrFile = r'C:\Users\xch43889\Documents\Working\ConsVision\HydroNet_testing\saAquaLyr.lyr'
   in_Points = r'C:\Users\xch43889\Documents\Working\ConsVision\HydroNet_testing\VOPdata\vopBoatAccess_valam.shp'
   in_BeachLines = r'C:\Users\xch43889\Documents\Working\ConsVision\HydroNet_testing\PublicBeachExtents_valam.shp'
   out_GDB = r'C:\Users\xch43889\Documents\Working\ConsVision\HydroNet_testing\RecMod_aquaPolys5.gdb'
   #scratchGDB = r'C:\Users\xch43889\Documents\Working\ConsVision\HydroNet_testing\testing4.gdb'
   
   
   # Specify function(s) to run
   printMsg('Creating output geodatabase...')
   outpath = r'C:\Users\xch43889\Documents\Working\ConsVision\HydroNet_testing'
   outname = r'RecMod_aquaPolys5.gdb'
   arcpy.CreateFileGDB_management (outpath, outname)
   
   printMsg('Making service layer...')
   outNALayer = MakeServiceLayer_aqua(in_GDB, out_LyrFile)
   
   printMsg('Loading barriers...')
   LoadBarriers_aqua(outNALayer, in_GDB)
   outNALayer.save # This achieves nothing; need a way to save updated layer containing facilities, etc.
   
   printMsg('Loading access points...')
   LoadAccessPts_aqua(outNALayer, in_Points)
   outNALayer.save # This achieves nothing
   
   printMsg('Creating service area output...')
   GetServiceAreas_aqua(outNALayer, in_GDB, in_BeachLines, out_GDB)
   
   printMsg('Processing complete.')
   
   return outNALayer
   
if __name__ == '__main__':
   main()
