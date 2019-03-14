# wf_LocalTrailsAnalysis.py
# Version:  ArcGIS 10.3.1 / Python 2.7.8
# Creation Date: 2019-03-06
# Last Edit: 2019-03-14
# Creator:  Kirsten R. Hazler
#
# Summary:
# Workflow: sets up function runs to get local trails attributes
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
   unitUpdate = 7500 # to get miles per 7500 people
   BenchVal = 0.000133 # 1 mile per 7500 people
   multFactor = 0.000621371 # to get trail length in miles, converting from meters
   inRadius = 2414.02 # 1.5 miles = 2414.02 meters to define local neighborhood

   inTrails = r'F:\Working\RecMod\FinalDataToUse\rec_source_datasets.gdb\trails_include_20190221'
   locPopSum = r'F:\Working\RecMod\Outputs\VA_RecMod_Archive.gdb\locPopSum' 
   recAcc = r'F:\Working\RecMod\Outputs\VA_RecMod_Archive.gdb\lTrl_Sum'
   recPP = r'F:\Working\RecMod\Outputs\VA_RecMod_Archive.gdb\lTrl_PP'
   travTime = r'F:\Working\RecMod\FinalDataToUse\local_access_walkNearest.gdb\walkNearest_access_trails_include_20190221'
   ttBin = r'F:\Working\RecMod\Outputs\VA_RecMod_Archive.gdb\lTrl_tt10'
   
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
         
   expression = 'Status(!lTrl_bNeed!, !lTrl_p75C!)'
   
   # Functions to run
   # LocalTrailsPP(inTrails, multFactor, inRadius, locPopSum, inPop, inMask, recAcc, recPP)
   # AssessRecNeed(inHex, hexFld, BenchVal, inPop, recPP, inMask, outGDB, "lTrl", 5, remNulls_n, multiplier)
   zonalMean(inHex, hexFld, "lTrl_Acc", recAcc)
   zonalMean(inHex, hexFld, "lTrl_p75C", recPP, remNulls_n, 0, inPop, 0, multiplier, unitUpdate)
   
   travelBinary(travTime, 10, inPop, ttBin)
   zonalMean(inHex, hexFld, "lTrl_tt10", ttBin, remNulls_n, 0, inPop)
   zonalMean(inHex, hexFld, "lTrl_ttAvg", travTime, remNulls_n, 0, inPop)

   arcpy.AddField_management (inHex, "lTrl_bStat", "SHORT")
   arcpy.CalculateField_management (inHex, "lTrl_bStat", expression, "PYTHON", codeblock)
   
if __name__ == '__main__':
   main()
