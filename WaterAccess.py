# ----------------------------------------------------------------------------------------
# WaterAccess.py
# Version:  ArcGIS 10.3.1 / Python 2.7.8
# Creation Date: 2018-06-07
# Last Edit: 2018-06-07
# Creator:  Kirsten R. Hazler

# Summary:
# Functions for creating water access areas for Recreation Model. 
# Requirements:
# - A geodatabase containing a fully functional hydrologic network and associated NHD features (VA_HydroNet.gdb)
# - A set of points representing water access. These may have been combined from multiple sources, and must already have been filtered to include only points with true water access.
# ----------------------------------------------------------------------------------------


# Import Helper module and functions
import Helper
from Helper import *
from arcpy import env

# Check out the Network Analyst extension license
arcpy.CheckOutExtension("Network")

# Create the service area layer
def MakeServiceLayer_aqua(in_GDB):
   '''Creates a service area layer based on 5-km travel distance up and down the hydro network.
   Parameters:
   - in_GDB = The geodatabase containing the network and associated features
   '''

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
         restriction_attribute_name="", 
         polygon_trim="TRIM_POLYS", 
         poly_trim_value="100 Meters", 
         lines_source_fields="NO_LINES_SOURCE_FIELDS", 
         hierarchy="NO_HIERARCHY", 
         time_of_day="")

   #Get the layer object from the result object. The service area layer can now be referenced using the layer object.
   outNALayer = outNALayer.getOutput(0)

   return outNALayer

# Load barriers into the service area layer
def LoadBarriers_aqua(in_ServiceLayer, in_GDB):
   '''Creates line barriers in the service area layer, using dams and weirs. This truncates and separates service areas in some places.
   Parameters:
   - in_ServiceLayer = The service layer output from the MakeServiceLayer_aqua function
   - in_GDB = The geodatabase containing the network and associated features
   '''
   
   in_Lines = in_GDB + os.sep + "HydroNet" + os.sep + "NHDLine_DamWeir"

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
   '''Creates facilities in the service area layer, from water access points input by user. Assumes water access input is a shapefile, as function uses the FID for the facilities names. May want to recode to use some other unique identifier.
   
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
         search_criteria="NHDFlowline SHAPE_MIDDLE_END;HydroNet_ND_Junctions NONE", 
         match_type="MATCH_TO_CLOSEST", 
         append="CLEAR", 
         snap_to_position_along_network="SNAP", 
         snap_offset="5 Meters", 
         exclude_restricted_elements="INCLUDE", 
         search_query="NHDFlowline #;HydroNet_ND_Junctions #")
 
# Solve the service area layer and generate polygons from lines
def GetServiceAreas_aqua(in_ServiceLayer, in_GDB, in_BeachLines, out_GDB):
   '''Gets the output from solving the service layer and performs additional steps to get final output.
   Parameters:
   - in_ServiceLayer = The service layer output from the MakeServiceLayer_aqua function
   - in_GDB = The geodatabase containing the network and associated features
   - in_BeachLines = Line feature class representing public beaches
   - out_GDB = Geodatabase for storing outputs.
   '''
   printMsg('Solving service area...')
   arcpy.Solve_na(in_network_analysis_layer=in_ServiceLayer, 
      ignore_invalids="SKIP", 
      terminate_on_solve_error="TERMINATE", 
      simplification_tolerance="")

   # Save out the lines and points
   # subLayerNames = arcpy.na.GetNAClassNames(in_ServiceLayer)
   # facilitiesLayerName = subLayerNames["Facilities"]
   # linesLayerName = subLayerNames["SALines"]
   printMsg('Saving out lines...')
   in_Lines = arcpy.mapping.ListLayers(in_ServiceLayer, "Lines")[0]
   out_Lines = out_GDB + os.sep + "FlowTrace"
   arcpy.CopyFeatures_management(in_Lines, out_Lines)
   
   printMsg('Saving out non-network points...')
   in_Points = arcpy.mapping.ListLayers(in_ServiceLayer, "Facilities")[0]
   where_clause = '"Status" <> 0' # Only grab points not located on network
   arcpy.MakeFeatureLayer_management (in_Points, "lyr_offPts", where_clause)
   out_Points = out_GDB + os.sep + "offPts"
   arcpy.CopyFeatures_management("lyr_offPts", out_Points)
   
   # Buffer the lines
   printMsg('Buffering lines...')
   streamBuff = out_GDB + os.sep + "streamBuff"
   riverBuff = out_GDB + os.sep + "riverBuff"
   oceanBuff = out_GDB + os.sep + "oceanBuff"
   beachBuff = out_GDB + os.sep + "beachBuff"
   arcpy.Buffer_analysis (out_Lines, streamBuff, "15 METERS", "", "FLAT", "ALL")
   arcpy.Buffer_analysis (out_Lines, riverBuff, "2500 METERS", "", "FLAT", "ALL")
   arcpy.Buffer_analysis (out_Lines, oceanBuff, "5000 METERS", "", "FLAT", "ALL")
   arcpy.Buffer_analysis (in_BeachLines, beachBuff, "5000 METERS", "", "FLAT", "ALL")
   
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
   arcpy.Clip_analysis ("lyr_SeaOcean", oceanBuff, clp)
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
   arcpy.Clip_analysis ("lyr_Estuary", oceanBuff, clp)
   expl = "in_memory" + os.sep + "expl"
   arcpy.MultipartToSinglepart_management (clp, expl)
   arcpy.MakeFeatureLayer_management (expl, "lyr_Estuary")
   arcpy.SelectLayerByLocation_management ("lyr_Estuary", "CONTAINS", out_Lines, "", "NEW_SELECTION")
   Estuary = out_GDB + os.sep + "Estuary"
   arcpy.CopyFeatures_management("lyr_Estuary", Estuary)
   
   #### TODO: Add estuary beaches

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
   in_Points = r'C:\Users\xch43889\Documents\Working\ConsVision\HydroNet_testing\testing.gdb\test_waterAccess'
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
   
   return outNALayer
   
if __name__ == '__main__':
   main()
