# wf_RegionalParksAnalysis.py
# Version:  ArcGIS 10.3.1 / Python 2.7.8
# Creation Date: 2019-03-06
# Last Edit: 2019-03-14
# Creator:  Kirsten R. Hazler
#
# Summary:
# Workflow: Sets up parameters and function runs to get regional parks attributes
#
#--------------------------------------------------------------------------------------
import AssessRecOpps
from AssessRecOpps import *

def main():
   # Parameters
   inHex = r'F:\Working\RecMod\Outputs\VA_RecMod.gdb\RecreationAccess'
   hexFld = 'Unique_ID'
   inPop = r'F:\Working\RecMod\FinalDataToUse\RoadsPopProducts.gdb\distribPop_kdens'
   inMask = r'F:\Working\VA_Buff50mi\VA_Buff50mi.shp'
   outGDB = r'F:\Working\RecMod\Outputs\VA_RecMod_Archive.gdb'
   remNulls_y = 1 # Replace nulls in value field with replacement value
   remNulls_n = 0 # Leave nulls in value field
 
   multiplier = 10000 # to avoid failure in zonal statistics
   unitUpdate = 1000 # to get acres per 1000 people
   BenchVal = 0.01 # 10 acres per 1000 people

   recPP = r'F:\Working\RecMod\FinalDataToUse\raw_summary_scores.gdb\popAdj_sum_t_tlnd_serviceAreas'
   recPP_upd = r'F:\Working\RecMod\Outputs\VA_RecMod_Archive.gdb\rPrk_RecPP'
   recAcc = r'F:\Working\RecMod\FinalDataToUse\raw_summary_scores.gdb\servArea_sum_t_tlnd_serviceAreas'
   recAcc_upd = r'F:\Working\RecMod\Outputs\VA_RecMod_Archive.gdb\rPrk_RecSum'
   travTime = r'F:\Working\RecMod\FinalDataToUse\regional_access_all_driveNearest.gdb\grp_tlnd_servArea'
   ttBin = r'F:\Working\RecMod\Outputs\VA_RecMod_Archive.gdb\rPrk_tt30'
   
   codeblock = '''def Status(bNeed, PP):
      if bNeed == None:
         return None
      elif bNeed == 0: 
         return 0
      else: 
         if PP > 10:
            return 1
         elif bNeed <= 5:
            return 2
         elif bNeed <= 10:
            return 3
         elif bNeed <=15:
            return 4
         else:
            return 5'''
         
   expression = 'Status(!rPrk_bNeed!, !rPrk_p1K!)'
   
   # Functions to run
   # AssessRecNeed(inHex, hexFld, BenchVal, inPop, recPP_upd, inMask, outGDB, "rPrk", 5, remNulls_n, multiplier)
   recSum = Con(IsNull(recAcc), 0, recAcc)
   recSum.save(recAcc_upd)
   zonalMean(inHex, hexFld, "rPrk_Acc", recAcc_upd)
   zonalMean(inHex, hexFld, "rPrk_p1K", recPP_upd, remNulls_n, 0, inPop, 0, multiplier, unitUpdate)
   
   travelBinary(travTime, 30, inPop, ttBin)
   zonalMean(inHex, hexFld, "rPrk_tt30", ttBin, remNulls_n, 0, inPop)
   zonalMean(inHex, hexFld, "rPrk_ttAvg", travTime, remNulls_n, 0, inPop)  
   
   arcpy.AddField_management (inHex, "rPrk_bStat", "SHORT")
   arcpy.CalculateField_management (inHex, "rPrk_bStat", expression, "PYTHON", codeblock)
   
if __name__ == '__main__':
   main()
