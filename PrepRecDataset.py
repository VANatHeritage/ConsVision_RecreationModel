"""
PrepRecDataset
Created by: David Bucklin
Created on: 2020-10
Version:  ArcGIS Pro / Python 3.x

Standardizes all recreation datasets for inclusion in the recreation model, outputs a new feature class. The following
procedures are run:
   - subsets features to region defined by study_area
   - projects to the spatial reference system of study_area
   - repairs geometries
   - adds standard fields [src_table, src_fid, src_name, a_wct, a_fsh, a_swm, a_gen, t_trl, t_lnd, use, use_why]
   - for [polygon / line] feature classes, adds a join_score field indicating [area (acres) / length (miles)]
   - populates access type fields, according to values given to [access_types]
   - updates src_table to dataset name, src_fid to original FID value, use = 1,
      and src_name to `feature_names` (if provided)

This is the initial step prior to any other processing. After this, access and use fields should be further edited, to
indicate the type of recreation access available, and whether to exclude certain features (`use` field).

This script is set up for import into ArcGIS Pro as a script tool.
"""

import arcpy
import os
import time
import re
arcpy.env.transferDomains = True
arcpy.env.maintainAttachments = False


def PrepRecDataset(data, study_area, out_gdb, access_types, feature_names=None):

   date = time.strftime('%Y%m%d')
   data_nm = os.path.basename(data).replace('.shp', '')
   out_fc = out_gdb + os.sep + 'prep_' + re.sub(' |-', '', data_nm) + '_' + str(date)
   if arcpy.Exists(out_fc):
      arcpy.Delete_management(out_fc)

   data_flds = [a for a in arcpy.ListFields(data)]
   src_fid = [a.name for a in data_flds if a.type == 'OID'][0]

   # Select/Project/Repair
   lyr = arcpy.MakeFeatureLayer_management(data)
   arcpy.SelectLayerByLocation_management(lyr, "INTERSECT", study_area)
   arcpy.CalculateField_management(lyr, "tmpfid", "!" + src_fid + "!", field_type="LONG")
   arcpy.FeatureClassToFeatureClass_conversion(lyr, out_gdb, 'tmpft')
   print('Projecting features...')
   arcpy.Project_management(out_gdb + os.sep + 'tmpft', out_fc, study_area)
   arcpy.RepairGeometry_management(out_fc)

   # add fields
   flds = [["src_table", "TEXT", "Source dataset"],
           ["src_fid", "LONG", "Source OID"],
           ["src_name", "TEXT", "Source feature name"],
           ["a_wct", "SHORT", "Watercraft access", None, 0],
           ["a_fsh", "SHORT", "Fishing access", None, 0],
           ["a_swm", "SHORT", "Swimming access", None, 0],
           ["a_gen", "SHORT", "Unspecified aquatic access", None, 0],
           ["t_trl", "SHORT", "Trail access", None, 0],
           ["t_lnd", "SHORT", "Public land access", None, 0],
           ["use", "SHORT", "Model use flag"],
           ["use_why", "TEXT", "Model use comment"]]
   arcpy.AddFields_management(out_fc, flds)
   # calculate fields
   # fc_name = os.path.basename(data)
   add = ['tmpfid']
   if feature_names in [a.name for a in data_flds]:
      add.append(feature_names)
   with arcpy.da.UpdateCursor(out_fc, [f[0] for f in flds] + add) as uc:
      for r in uc:
         r[0] = data_nm
         r[1] = r[11]
         if feature_names:
            r[2] = r[12]
         if "Boat access" in access_types:
            r[3] = 1
         if "Fishing access" in access_types:
            r[4] = 1
         if "Swim access" in access_types:
            r[5] = 1
         if "Unspecified water access" in access_types:
            r[6] = 1
         if "Trail access (non-water)" in access_types:
            r[7] = 1
         if "Land access" in access_types:
            r[8] = 1
         r[9] = 1
         uc.updateRow(r)

   # Add join score for recreation feature (area for polygons, length for lines)
   d = arcpy.Describe(out_fc)
   if d.shapeType == "Polygon":
      arcpy.CalculateField_management(out_fc, "join_score", '!shape.area@ACRES!', field_type="DOUBLE")
   elif d.shapeType == "Polyline":
      arcpy.CalculateField_management(out_fc, "join_score", '!shape.length@MILES!', field_type="DOUBLE")
   else:
      # Points get join score of 1. Can manually update if needed
      arcpy.CalculateField_management(out_fc, "join_score", '1', field_type="DOUBLE")

   del lyr
   print('Cleaning up...')
   arcpy.DeleteField_management(out_fc, 'tmpfid')
   arcpy.DeleteField_management(data, 'tmpfid')
   arcpy.Delete_management(out_gdb + os.sep + 'tmpft')

   return out_fc


def main():
   data = arcpy.GetParameterAsText(0)
   study_area = arcpy.GetParameterAsText(1)
   out_gdb = arcpy.GetParameterAsText(2)
   access_types = [a.strip('\'') for a in arcpy.GetParameterAsText(3).split(";")]
   feature_names = arcpy.GetParameterAsText(4)

   arcpy.AddMessage("Access types: (" + ", ".join(access_types) + ")")
   out = PrepRecDataset(data, study_area, out_gdb, access_types, feature_names)
   # Setting parameter will add to the Map
   arcpy.SetParameter(5, out)

if __name__ == '__main__':
   main()

#############################

### IDE runtime  below

# access_all = ["Boat access", "Fishing access", "Swim access", "Unspecified water access", "Trail access (non-water)", "Land access"]
#
# arcpy.env.overwriteOutput = True
# study_area = r'L:\David\projects\RCL_processing\RCL_processing.gdb\VA_Buff50mi_wgs84'
#
# out_gdb = r'E:\projects\rec_model\rec_datasets\rec_datasets_prep_clean\test_rec_datasets_202010.gdb'
# if not os.path.exists(out_gdb):
#    arcpy.CreateFileGDB_management(os.path.dirname(out_gdb), os.path.basename(out_gdb))
#

# List [rec dataset, feature names field] here
# fcs = [
#    [r'E:\projects\rec_model\rec_datasets\VOP_mapper\new_20181004\VA_PUBLIC_ACCESS_LANDS.shp', 'MANAME'],
#    [r'L:\David\GIS_data\PAD\PAD_US2_1_GDB\PAD_US2_1.gdb\PADUS2_1Combined_Fee_Designation', "Unit_Nm"]
# ]
#
# # Loop over datasets
# for i in fcs:
#    print(i[0])
#    data = i[0]
#    feature_names = i[1]
#    PrepRecDataset(data, study_area, out_gdb, feature_names)