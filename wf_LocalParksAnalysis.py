# wf_LocalParksAnalysis.py
# Version:  ArcGIS 10.3.1 / Python 2.7.8
# Creation Date: 2019-03-06
# Last Edit: 2019-03-14
# Creator:  Kirsten R. Hazler
#
# Summary:
# Workflow: sets up function runs to get local parks attributes
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
 
   multiplier = 10000 # to avoid failure due to tiny numbers in zonal statistics
   unitUpdate = 1000 # to get acres per 1000 people
   BenchVal = 0.003 # 3 acres per 1000 people
   multFactor = 0.222395 # to convert pixel area (900 square meters) to acres
   inRadius = 2414.02 # 1.5 miles = 2414.02 meters to define local neighborhood
   
   inParks = r'F:\Working\RecMod\FinalDataToUse\rec_source_datasets.gdb\pub_lands_final_20190221'
   parksRaster = r'F:\Working\RecMod\Outputs\Products.gdb\allParks_raster'
   locPopSum = r'F:\Working\RecMod\Outputs\VA_RecMod_Archive.gdb\locPopSum' 
   recAcc = r'F:\Working\RecMod\Outputs\VA_RecMod_Archive.gdb\lPrk_Sum'
   recPP = r'F:\Working\RecMod\Outputs\VA_RecMod_Archive.gdb\lPrk_PP'
   travTime = r'F:\Working\RecMod\FinalDataToUse\local_access_walkNearest.gdb\walkNearest_access_pub_lands_final_20190221'
   ttBin = r'F:\Working\RecMod\Outputs\VA_RecMod_Archive.gdb\lPrk_tt10'
   
   codeblock = '''def Status(bNeed, PP):
   if bNeed == None:
      return None
   elif bNeed == 0: 
      return 0
   else: 
      if PP > 3:
         return 1
      elif bNeed <= 5:
         return 2
      elif bNeed <= 10:
         return 3
      elif bNeed <=15:
         return 4
      else:
         return 5'''
   
   expression = 'Status(!lPrk_bNeed!, !lPrk_p1K!)'
   
   # Functions to run
   # FeatToRaster(inParks, inPop, inMask, parksRaster)
   # LocalParksPP(parksRaster, multFactor, inRadius, locPopSum, recAcc, recPP, inMask, "SUM")
   # AssessRecNeed(inHex, hexFld, BenchVal, inPop, recPP, inMask, outGDB, "lPrk", 5, remNulls_n, multiplier)
   zonalMean(inHex, hexFld, "lPrk_Acc", recAcc, remNulls_y, 0)
   # zonalMean(inHex, hexFld, "lPrk_p1K", recPP, remNulls_n, 0, inPop, 0, multiplier, unitUpdate)
   
   travelBinary(travTime, 10, inPop, ttBin)
   zonalMean(inHex, hexFld, "lPrk_tt10", ttBin, remNulls_n, 0, inPop)
   zonalMean(inHex, hexFld, "lPrk_ttAvg", travTime, remNulls_n, 0, inPop)
   
   arcpy.AddField_management (inHex, "lPrk_bStat", "SHORT")
   arcpy.CalculateField_management (inHex, "lPrk_bStat", expression, "PYTHON", codeblock)
   
if __name__ == '__main__':
   main()
