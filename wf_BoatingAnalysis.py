# wf_BoatingAnalysis.py
# Version:  ArcGIS 10.3.1 / Python 2.7.8
# Creation Date: 2019-03-06
# Last Edit: 2019-03-18
# Creator:  Kirsten R. Hazler
#
# Summary:
# Workflow: sets up function runs to get boating access attributes
#
#--------------------------------------------------------------------------------------
import AssessRecOpps
from AssessRecOpps import *

def main():
   # Parameters
   inHex = r'F:\Working\RecMod\Outputs\VA_RecMod_CONUS\VA_RecMod.gdb\RecreationAccess'
   hexFld = 'Unique_ID'
   inPop = r'F:\Working\RecMod\FinalDataToUse\RoadsPopProducts.gdb\distribPop_kdens'
   inMask = r'F:\Working\VA_Buff50mi\VA_Buff50mi.shp'
   outGDB = r'F:\Working\RecMod\Outputs\VA_RecMod_CONUS\VA_RecMod_Archive.gdb'
   remNulls_y = 1 # Replace nulls in value field with replacement value
   remNulls_n = 0 # Leave nulls in value field
 
   multiplier = 1000000 # to avoid failure in zonal statistics
   unitUpdate = 10000 # to get boat launches per 10,000 people
   BenchVal = 0.0001 # 1 boat launch per 10,000 people

   recPP = r'F:\Working\RecMod\FinalDataToUse\raw_summary_scores.gdb\popAdj_sum_a_awct_serviceAreas'
   recPP_upd = outGDB + os.sep + 'rBtl_RecPP'
   recAcc = r'F:\Working\RecMod\FinalDataToUse\raw_summary_scores.gdb\servArea_sum_a_awct_serviceAreas'
   recAcc_upd = outGDB + os.sep + 'rBtl_RecSum'
   driveTime = r'F:\Working\RecMod\FinalDataToUse\regional_access_all_driveNearest.gdb\grp_awct_servArea'
   ttBin_drive = outGDB + os.sep + 'rBtl_tt30'
   
   codeblock = '''def Status(bNeed, PP):
      if bNeed == None:
         return None
      elif bNeed == 0: 
         return 0
      else: 
         if PP > 1:
            return 1
         elif bNeed <= 1:
            return 2
         elif bNeed <= 2:
            return 3
         elif bNeed <= 3:
            return 4
         else:
            return 5'''
         
   expression = 'Status(!rBtl_bNeed!, !rBtl_p10K!)'
   
   codeblock2 = '''def Status(mNeed, PP):
      if mNeed == None:
         return None
      elif mNeed == 0: 
         return 0
      else: 
         if PP > 5:
            return 1
         elif mNeed <= 1:
            return 2
         elif mNeed <= 5:
            return 3
         elif mNeed <= 10:
            return 4
         else:
            return 5'''
         
   expression2 = 'Status(!rBtl_mNeed!, !rBtl_p10K!)'
   
   # Functions to run
   # AssessRecNeed(inHex, hexFld, BenchVal, inPop, recPP_upd, inMask, outGDB, "rBtl", 5, remNulls_n, multiplier)
   # recSum = Con(IsNull(recAcc), 0, recAcc)
   # recSum.save(recAcc_upd)
   # zonalMean(inHex, hexFld, "rBtl_Acc", recAcc_upd)
   # zonalMean(inHex, hexFld, "rBtl_p10K", recPP_upd, remNulls_n, 0, inPop, 0, multiplier, unitUpdate)
   
   # travelBinary(driveTime, 30, inPop, ttBin_drive)
   # zonalMean(inHex, hexFld, "rBtl_tt30", ttBin_drive, remNulls_n, 0, inPop)
   # zonalMean(inHex, hexFld, "rBtl_ttAvg", driveTime, remNulls_n, 0, inPop)

   # arcpy.AddField_management (inHex, "rBtl_bStat", "SHORT")
   # arcpy.CalculateField_management (inHex, "rBtl_bStat", expression, "PYTHON", codeblock)
   
   arcpy.AddField_management (inHex, "rBtl_mStat", "SHORT")
   arcpy.CalculateField_management (inHex, "rBtl_mStat", expression2, "PYTHON", codeblock2)
   
if __name__ == '__main__':
   main()
