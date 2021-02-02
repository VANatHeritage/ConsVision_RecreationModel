# wf_RegionalTrailsAnalysis.py
# Version:  ArcGIS 10.3.1 / Python 2.7.8
# Creation Date: 2019-03-26
# Last Edit: 2019-03-18
# Creator:  Kirsten R. Hazler
#
# Summary:
# Workflow: Sets up parameters and function runs to get regional trails attributes
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
   unitUpdate = 7500 # to get miles per 7500 people
   BenchVal = 0.0004 # 1 mile per 2500 people = 3 miles per 7500 people

   recPP = r'F:\Working\RecMod\FinalDataToUse\raw_summary_scores.gdb\popAdj_sum_t_ttrl_serviceAreas'
   recPP_upd = outGDB + os.sep + 'rTrl_RecPP'
   recAcc = r'F:\Working\RecMod\FinalDataToUse\raw_summary_scores.gdb\servArea_sum_t_ttrl_serviceAreas'
   recAcc_upd = outGDB + os.sep + 'rTrl_RecSum'
   travTime = r'F:\Working\RecMod\FinalDataToUse\regional_access_all_driveNearest.gdb\grp_ttrl_servArea'
   ttBin = outGDB + os.sep + 'rTrl_tt30'
   
   codeblock = '''def Status(bNeed):
      if bNeed == None:
         return None
      elif bNeed == 0: 
         return 0
      elif bNeed <= 0.001:  
         return 1
      elif bNeed <= 0.01:
         return 2
      elif bNeed <= 0.1:
         return 3
      elif bNeed <= 1:
         return 4
      else:
         return 5'''
         
   expression = 'Status(!rTrl_bNeed!)'
   expression2 = 'Status(!rTrl_mNeed!)'
   
   # Functions to run
   AssessRecNeed(inHex, hexFld, BenchVal, inPop, recPP_upd, inMask, outGDB, "rTrl", 5, remNulls_n, multiplier)
   recSum = Con(IsNull(recAcc), 0, recAcc)
   recSum.save(recAcc_upd)
   zonalMean(inHex, hexFld, "rTrl_Acc", recAcc_upd)
   zonalMean(inHex, hexFld, "rTrl_p75C", recPP_upd, remNulls_n, 0, inPop, 0, multiplier, unitUpdate)
   
   travelBinary(travTime, 30, inPop, ttBin)
   zonalMean(inHex, hexFld, "rTrl_tt30", ttBin, remNulls_n, 0, inPop)
   zonalMean(inHex, hexFld, "rTrl_ttAvg", travTime, remNulls_n, 0, inPop)
   
   arcpy.AddField_management (inHex, "rTrl_bStat", "SHORT")
   arcpy.CalculateField_management (inHex, "rTrl_bStat", expression, "PYTHON", codeblock)
   
   arcpy.AddField_management (inHex, "rTrl_mStat", "SHORT")
   arcpy.CalculateField_management (inHex, "rTrl_mStat", expression2, "PYTHON", codeblock)
   
if __name__ == '__main__':
   main()
