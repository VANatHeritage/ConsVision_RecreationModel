# wf_RegionalParksAnalysis.py
# Version:  ArcGIS 10.3.1 / Python 2.7.8
# Creation Date: 2019-03-06
# Last Edit: 2019-03-08
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
   travTime = r'F:\Working\RecMod\FinalDataToUse\regional_access_all_60min_ServiceAreas.gdb\grp_tlnd_servArea'
   ttBin = r'F:\Working\RecMod\Outputs\VA_RecMod_Archive.gdb\rPrk_tt30'
   
   # Functions to run
   AssessRecNeed(inHex, hexFld, BenchVal, inPop, recPP_upd, inMask, outGDB, "rPrk", 5, remNulls_n, multiplier)
   zonalMean(inHex, hexFld, "rPrk_Acc", recAcc, remNulls_y, 0)
   zonalMean(inHex, hexFld, "rPrk_p1K", recPP_upd, remNulls_n, 0, inPop, 0, multiplier, unitUpdate)
   
   travelBinary(travTime, 30, inPop, ttBin)
   zonalMean(inHex, hexFld, "rPrk_tt30", ttBin, remNulls_n, 0, inPop)
   zonalMean(inHex, hexFld, "rPrk_ttAvg", travTime, remNulls_n, 0, inPop)
   updateNulls(inHex, "rPrk_ttAvg", 61, "PopSum")
   
   
if __name__ == '__main__':
   main()
