# wf_RegionalTrailsAnalysis.py
# Version:  ArcGIS 10.3.1 / Python 2.7.8
# Creation Date: 2019-03-06
# Last Edit: 2019-03-08
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
   inHex = r'F:\Working\RecMod\Outputs\VA_RecMod.gdb\RecreationAccess'
   hexFld = 'Unique_ID'
   inPop = r'F:\Working\RecMod\FinalDataToUse\RoadsPopProducts.gdb\distribPop_kdens'
   inMask = r'F:\Working\VA_Buff50mi\VA_Buff50mi.shp'
   outGDB = r'F:\Working\RecMod\Outputs\VA_RecMod_Archive.gdb'
   remNulls_y = 1 # Replace nulls in value field with replacement value
   remNulls_n = 0 # Leave nulls in value field
 
   multiplier = 1000000 # to avoid failure in zonal statistics
   unitUpdate = 7500 # to get miles per 7500 people
   BenchVal = 0.0004 # 1 mile per 2500 people

   recPP = r'F:\Working\RecMod\FinalDataToUse\raw_summary_scores.gdb\popAdj_sum_t_ttrl_serviceAreas'
   recPP_upd = r'F:\Working\RecMod\Outputs\VA_RecMod_Archive.gdb\rTrl_RecPP'
   recAcc = r'F:\Working\RecMod\FinalDataToUse\raw_summary_scores.gdb\servArea_sum_t_ttrl_serviceAreas'
   travTime = r'F:\Working\RecMod\FinalDataToUse\regional_access_all_60min_ServiceAreas.gdb\grp_ttrl_servArea'
   ttBin = r'F:\Working\RecMod\Outputs\VA_RecMod_Archive.gdb\rTrl_tt30'
   
   # Functions to run
   AssessRecNeed(inHex, hexFld, BenchVal, inPop, recPP_upd, inMask, outGDB, "rTrl", 5, remNulls_n, multiplier)
   zonalMean(inHex, hexFld, "rTrl_Acc", recAcc, remNulls_y, 0)
   zonalMean(inHex, hexFld, "rTrl_p75C", recPP_upd, remNulls_n, 0, inPop, 0, multiplier, unitUpdate)
   
   travelBinary(travTime, 30, inPop, ttBin)
   zonalMean(inHex, hexFld, "rTrl_tt30", ttBin, remNulls_n, 0, inPop)
   zonalMean(inHex, hexFld, "rTrl_ttAvg", travTime, remNulls_n, 0, inPop)
   updateNulls(inHex, "rTrl_ttAvg", 61, "PopSum")
   
   
if __name__ == '__main__':
   main()
