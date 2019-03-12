# wf_FishingAnalysis.py
# Version:  ArcGIS 10.3.1 / Python 2.7.8
# Creation Date: 2019-03-06
# Last Edit: 2019-03-08
# Creator:  Kirsten R. Hazler
#
# Summary:
# Workflow: sets up function runs to get fishing access attributes
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
 
   multiplier = 1000000 # to avoid failure due to tiny numbers in zonal statistics
   unitUpdate = 10000 # to get fishing access points per 10,000 people
   BenchVal = 0.0001 # 1 fishing access point per 10,000 people

   recPP = r'F:\Working\RecMod\FinalDataToUse\raw_summary_scores.gdb\popAdj_sum_a_afsh_serviceAreas'
   recPP_upd = r'F:\Working\RecMod\Outputs\VA_RecMod_Archive.gdb\rFsh_RecPP'
   recAcc = r'F:\Working\RecMod\FinalDataToUse\raw_summary_scores.gdb\servArea_sum_a_afsh_serviceAreas'
   driveTime = r'F:\Working\RecMod\FinalDataToUse\regional_access_all_60min_ServiceAreas.gdb\grp_afsh_servArea'
   ttBin_drive = r'F:\Working\RecMod\Outputs\VA_RecMod_Archive.gdb\rFsh_tt30'
   walkTime = r'F:\Working\RecMod\FinalDataToUse\local_access_walk30min.gdb\walk30min_access_a_afsh_20190221'
   ttBin_walk = r'F:\Working\RecMod\Outputs\VA_RecMod_Archive.gdb\lFsh_tt10'
   
   # Functions to run
   # AssessRecNeed(inHex, hexFld, BenchVal, inPop, recPP_upd, inMask, outGDB, "rFsh", 5, remNulls_n, multiplier)
   zonalMean(inHex, hexFld, "rFsh_Acc", recAcc, remNulls_y, 0)
   zonalMean(inHex, hexFld, "rFsh_p10K", recPP_upd, remNulls_n, 0, inPop, 0, multiplier, unitUpdate)
   
   # travelBinary(driveTime, 30, inPop, ttBin_drive)
   zonalMean(inHex, hexFld, "rFsh_tt30", ttBin_drive, remNulls_n, 0, inPop)
   zonalMean(inHex, hexFld, "rFsh_ttAvg", driveTime, remNulls_n, 0, inPop)
   updateNulls(inHex, "rFsh_ttAvg", 61, "PopSum")
   
   # travelBinary(walkTime, 10, inPop, ttBin_walk)
   zonalMean(inHex, hexFld, "lFsh_tt10", ttBin_walk, remNulls_n, 0, inPop)
   zonalMean(inHex, hexFld, "lFsh_ttAvg", walkTime, remNulls_n, 0, inPop)
   updateNulls(inHex, "lFsh_ttAvg", 31, "PopSum")
   
   
if __name__ == '__main__':
   main()
