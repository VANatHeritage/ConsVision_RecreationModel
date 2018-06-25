# ----------------------------------------------------------------------------------------
# WaterAccess.py
# Version:  ArcGIS 10.3.1 / Python 2.7.8
# Creation Date: 2018-06-07
# Last Edit: 2018-06-13
# Creator:  Kirsten R. Hazler

# Summary:
# Functions for creating water access areas for Recreation Model. 
# Requirements:
# - A geodatabase containing a fully functional hydrologic network and associated NHD features (VA_HydroNet.gdb). References to objects within this geodatabase are hard-coded.
# - A set of points representing water access. These may have been combined from multiple sources, and must already have been filtered to include only points with true water access (i.e., within 50-m of water features).

# TO DO:
# - Add processing time benchmarks
# - Fix various oddities, esp. coastal area
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
   '''

   # Make service area layer 
   nwDataset = in_GDB + os.sep + "HydroNet" + os.sep + "HydroNet_ND"
   
   outNALayer = arcpy.MakeServiceAreaLayer_na(in_network_dataset=nwDataset,
         out_network_analysis_layer="FlowlineTrace_5k", 
         impedance_attribute="Length", 
         travel_from_to="TRAVEL_FROM", 
         default_break_values="4999 5000", 
         polygon_type="NO_POLYS", 
         merge="NO_MERGE", 
         nesting_type="RINGS", 
         line_type="TRUE_LINES_WITH_MEASURES", 
         overlap="NON_OVERLAP", 
         split="SPLIT", 
         excluded_source_name="", 
         accumulate_attribute_name="Length", 
         UTurn_policy="ALLOW_UTURNS", 
         restriction_attribute_name="NoCanalDitches;NoConnectors;NoPipelines;NoUndergroundConduits", 
         polygon_trim="TRIM_POLYS", 
         poly_trim_value="100 Meters", 
         lines_source_fields="NO_LINES_SOURCE_FIELDS", 
         hierarchy="NO_HIERARCHY", 
         time_of_day="")

   # Save layer file
   arcpy.SaveToLayerFile_management(in_layer="FlowlineTrace_5k", out_layer=out_LyrFile, is_relative_path="RELATIVE", version="CURRENT")   
         
   # Get the layer object from the result object. The service area layer can now be referenced using the layer object.
   outNALayer = outNALayer.getOutput(0)

   return outNALayer

# Load barriers into the service area layer
def LoadBarriers_aqua(in_ServiceLayer, in_GDB):
   '''Creates line barriers in the service area layer, using dams and weirs. This results in truncation and separation of service areas in some places.
   Parameters:
   - in_ServiceLayer = The service layer output from the MakeServiceLayer_aqua function
   - in_GDB = The geodatabase containing the network and associated features
   '''
   
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
   
# Load water access points into the service area layer
def LoadAccessPts_aqua(in_ServiceLayer, in_Points):
   '''Creates facilities in the service area layer, from water access points input by user. Assumes water access input is a shapefile, as this function uses the FID for the facilities names. May want to recode to use some other unique identifier.
   
   NOTE: A large search distance is used because for wide features, the access point at the edge of the water body can be quite far from the linear network FlowLines. The input access points should be filtered to ensure that they are in fact within 50-m of NHD features, prior to loading into the service area layer.
   
   Parameters:
   - in_ServiceLayer = The service layer output from the MakeServiceLayer_aqua function
   - in_Points = The shapefile representing water access points.
   '''
   
   access = arcpy.AddLocations_na(in_network_analysis_layer=in_ServiceLayer, 
         sub_layer="Facilities", 
         in_table=in_Points, 
         field_mappings="Name FID #", 
         search_tolerance="5000 Meters", 
         sort_field="", 
         search_criteria="NHDFlowline SHAPE;HydroNet_ND_Junctions NONE", 
         match_type="MATCH_TO_CLOSEST", 
         append="CLEAR", 
         snap_to_position_along_network="NO_SNAP", 
         snap_offset="5 Meters", 
         exclude_restricted_elements="EXCLUDE", 
         search_query="NHDFlowline #;HydroNet_ND_Junctions #")
 
# Solve the service area layer and generate polygons from lines
def GetServiceAreas_aqua(in_ServiceLayer, in_GDB, in_BeachLines, out_GDB):
   '''Gets the output from solving the service layer and performs additional steps to get final output.
   Parameters:
   - in_ServiceLayer = The service layer output from the MakeServiceLayer_aqua function
   - in_GDB = The input geodatabase containing the network and associated features
   - in_BeachLines = Line feature class representing public beaches
   - out_GDB = Geodatabase for storing outputs.
   '''
   
   # Solve the service area
   printMsg('Solving service area...')
   arcpy.Solve_na(in_network_analysis_layer=in_ServiceLayer, 
      ignore_invalids="SKIP", 
      terminate_on_solve_error="TERMINATE", 
      simplification_tolerance="")

   # Save out the service area points NOT located on network. We need these to capture off-network features.
   printMsg('Saving out non-network points...')
   in_Points = arcpy.mapping.ListLayers(in_ServiceLayer, "Facilities")[0]
   where_clause = '"Status" <> 0' 
   arcpy.MakeFeatureLayer_management (in_Points, "lyr_offPts", where_clause)
   out_Points = out_GDB + os.sep + "offPts"
   arcpy.CopyFeatures_management("lyr_offPts", out_Points)
      
   # Save out the service area lines
   printMsg('Saving out lines...')
   in_Lines = arcpy.mapping.ListLayers(in_ServiceLayer, "Lines")[0]
   out_Lines = out_GDB + os.sep + "saLines"
   arcpy.CopyFeatures_management(in_Lines, out_Lines)
   
   # Attach the FType to lines
   nhdFlowLine = in_GDB + os.sep + "HydroNet" + os.sep + "NHDFlowline"
   arcpy.JoinField_management(in_data=out_Lines, in_field="SourceOID", join_table=nhdFlowLine, join_field="OBJECTID", fields="FType")
   
   # Add relevant geometry info to lines
   printMsg('Adding geometric attributes to service area lines...')
   arcpy.AddGeometryAttributes_management(Input_Features=out_Lines, Geometry_Properties="LINE_START_MID_END;LINE_BEARING")

   # Create and calculate field for right-perpendicular bearing
   arcpy.AddField_management(in_table=outLines, field_name="BearingRight", field_type="DOUBLE", field_precision="", field_scale="", field_length="", field_alias="", field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED", field_domain="")
   
   expression = "perp(!BEARING!)"
   code_block='''def perp(bearing):
      perp = bearing + 90
      if perp > 360:
         perp = perp - 360
      return perp'''
   arcpy.CalculateField_management(outLines, "BearingRight", expression, "PYTHON_9.3", code_block)
   
   # Create and calculate field for left-perpendicular bearing
   arcpy.AddField_management(in_table=outLines, field_name="BearingLeft", field_type="DOUBLE", field_precision="", field_scale="", field_length="", field_alias="", field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED", field_domain="")
   
   expression = "perp(!BEARING!)"
   code_block='''def perp(bearing):
      perp = bearing - 90
      if perp < 0:
         perp = perp + 360
      return perp'''
   arcpy.CalculateField_management(outLines, "BearingLeft", expression, "PYTHON_9.3", code_block)
   
   # Make subsets of service area lines depending on type
   where_clause = "FType in (558,460)" # includes StreamRiver and ArtificialPath types
   lyrStreamline = arcpy.MakeFeatureLayer_management (out_Lines, "lyr_Streamline", where_clause)
   
   where_clause = "FType in (558,460) and ToCumul_Length = 5000" 
   # Includes the farthest ends of the StreamRiver and ArtificialPath types. 
   # These will be used to create perpendicular transects to chop up StreamRiver polygons.
   lyrStreamEnds = arcpy.MakeFeatureLayer_management (out_Lines, "lyr_StreamEnds", where_clause)
   
   where_clause = "FType = 566" # includes Coastline type only
   lyrCoastline = arcpy.MakeFeatureLayer_management (out_Lines, "lyr_Coastline", where_clause)
   
   # Buffer the lines
   printMsg('Buffering lines...')
   streamBuff = out_GDB + os.sep + "streamBuff"
   #riverBuff = out_GDB + os.sep + "riverBuff"
   coastBuff = out_GDB + os.sep + "coastBuff"
   beachBuff = out_GDB + os.sep + "beachBuff"
   arcpy.Buffer_analysis (lyrStreamline, streamBuff, "5 METERS", "", "FLAT", "ALL")
   #arcpy.Buffer_analysis (out_Lines, riverBuff, "2500 METERS", "", "FLAT", "ALL")
   arcpy.Buffer_analysis (lyrCoastline, coastBuff, "1000 METERS", "", "FLAT", "ALL")
   arcpy.Buffer_analysis (in_BeachLines, beachBuff, "1000 METERS", "", "FLAT", "ALL")
   
   # Process the relevant NHDArea polygons
   printMsg('Processing NHDArea polygons...')
   nhdArea = in_GDB + os.sep + "HydroNet" + os.sep + "NHDArea"
   
   where_clause = "FType = 460" # StreamRiver polygons only
   arcpy.MakeFeatureLayer_management (nhdArea, "lyr_StreamRiver", where_clause)
   arcpy.SelectLayerByLocation_management ("lyr_StreamRiver", "CONTAINS", out_Lines, "", "NEW_SELECTION")
   clp = "in_memory" + os.sep + "clp"
   arcpy.Clip_analysis ("lyr_StreamRiver", riverBuff, clp)
   expl = "in_memory" + os.sep + "expl"
   arcpy.MultipartToSinglepart_management (clp, expl)
   arcpy.MakeFeatureLayer_management (expl, "lyr_StreamRiver")
   arcpy.SelectLayerByLocation_management ("lyr_StreamRiver", "CONTAINS", out_Lines, "", "NEW_SELECTION")
   StreamRiver = out_GDB + os.sep + "StreamRiver"
   arcpy.CopyFeatures_management("lyr_StreamRiver", StreamRiver)
   
   where_clause = "FType = 445" # SeaOcean polygons only
   arcpy.MakeFeatureLayer_management (nhdArea, "lyr_SeaOcean", where_clause)
   arcpy.SelectLayerByLocation_management ("lyr_SeaOcean", "CONTAINS", out_Lines, "", "NEW_SELECTION")
   clp = "in_memory" + os.sep + "clp"
   arcpy.Clip_analysis ("lyr_SeaOcean", coastBuff, clp)
   expl = "in_memory" + os.sep + "expl"
   arcpy.MultipartToSinglepart_management (clp, expl)
   arcpy.MakeFeatureLayer_management (expl, "lyr_SeaOcean")
   SeaOcean = out_GDB + os.sep + "SeaOcean"
   arcpy.CopyFeatures_management("lyr_SeaOcean", SeaOcean)
   
   arcpy.MakeFeatureLayer_management (nhdArea, "lyr_SeaOcean", where_clause)
   arcpy.SelectLayerByLocation_management ("lyr_SeaOcean", "WITHIN_A_DISTANCE", in_BeachLines, "50 METERS", "NEW_SELECTION")
   arcpy.Clip_analysis ("lyr_SeaOcean", beachBuff, clp)
   expl = "in_memory" + os.sep + "expl"
   arcpy.MultipartToSinglepart_management (clp, expl)
   arcpy.Append_management (expl, SeaOcean, "NO_TEST")
   
   # Process the relevant NHDWaterbody polygons
   printMsg('Processing NHDWaterbody polygons...')
   nhdWaterbody = in_GDB + os.sep + "HydroNet" + os.sep + "NHDWaterbody"
   
   where_clause = "FType in (390, 436)" # LakePond and Reservoir polygons only
   arcpy.MakeFeatureLayer_management (nhdWaterbody, "lyr_LakePond", where_clause)
   arcpy.SelectLayerByLocation_management ("lyr_LakePond", "CONTAINS", out_Lines, "", "NEW_SELECTION")
   arcpy.SelectLayerByLocation_management ("lyr_LakePond", "WITHIN_A_DISTANCE", out_Points, "50 METERS", "ADD_TO_SELECTION") # This picks up polygons without network flowlines
   LakePond = out_GDB + os.sep + "LakePond"
   arcpy.CopyFeatures_management("lyr_LakePond", LakePond)
   
   where_clause = "FType = 493" # Estuary polygons only
   arcpy.MakeFeatureLayer_management (nhdWaterbody, "lyr_Estuary", where_clause)
   arcpy.SelectLayerByLocation_management ("lyr_Estuary", "CONTAINS", out_Lines, "", "NEW_SELECTION")
   clp = "in_memory" + os.sep + "clp"
   arcpy.Clip_analysis ("lyr_Estuary", coastBuff, clp)
   expl = "in_memory" + os.sep + "expl"
   arcpy.MultipartToSinglepart_management (clp, expl)
   arcpy.MakeFeatureLayer_management (expl, "lyr_Estuary")
   arcpy.SelectLayerByLocation_management ("lyr_Estuary", "CONTAINS", out_Lines, "", "NEW_SELECTION")
   Estuary = out_GDB + os.sep + "Estuary"
   arcpy.CopyFeatures_management("lyr_Estuary", Estuary)
   
   arcpy.MakeFeatureLayer_management (nhdWaterbody, "lyr_Estuary", where_clause)
   arcpy.SelectLayerByLocation_management ("lyr_Estuary", "WITHIN_A_DISTANCE", in_BeachLines, "50 METERS", "NEW_SELECTION")
   arcpy.Clip_analysis ("lyr_Estuary", beachBuff, clp)
   expl = "in_memory" + os.sep + "expl"
   arcpy.MultipartToSinglepart_management (clp, expl)
   arcpy.Append_management (expl, Estuary, "NO_TEST")

   # Combine all the polygons
   printMsg('Combining polygons...')
   tmpPolys = "in_memory" + os.sep + "tmpPolys"
   aquaPolys = out_GDB + os.sep + "aquaPolys"
   arcpy.Merge_management ([streamBuff, StreamRiver, SeaOcean, LakePond, Estuary], tmpPolys)
   arcpy.Dissolve_management (tmpPolys, aquaPolys, "", "", "SINGLE_PART")
   
   return aquaPolys
   
 
################################################################################################
# Use the main function below to run functions directly from Python IDE or command line with hard-coded variables

def main():
   # Set up variables
   in_GDB = r'C:\Users\xch43889\Documents\Working\ConsVision\HydroNet_testing\VA_HydroNet.gdb'
   in_Points = r'C:\Users\xch43889\Documents\Working\ConsVision\HydroNet_testing\VOPdata\vopBoatAccess_valam.shp'
   in_BeachLines = r'C:\Users\xch43889\Downloads\PublicBeaches\PublicBeachesExtents.shp'
   out_GDB = r'C:\Users\xch43889\Documents\Working\ConsVision\HydroNet_testing\testing.gdb'
   
   
   # Specify function(s) to run
   printMsg('Making service layer...')
   outNALayer = MakeServiceLayer_aqua(in_GDB)
   
   printMsg('Loading barriers...')
   LoadBarriers_aqua(outNALayer, in_GDB)
   
   printMsg('Loading access points...')
   LoadAccessPts_aqua(outNALayer, in_Points)
   
   printMsg('Creating service area output...')
   GetServiceAreas_aqua(outNALayer, in_GDB, in_BeachLines, out_GDB)
   
   printMsg('Processing complete.')
   
   return outNALayer
   
if __name__ == '__main__':
   main()
