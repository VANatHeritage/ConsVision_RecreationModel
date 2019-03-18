# fldOps.py
# Version:  ArcGIS 10.3.1 / Python 2.7.8
# Creation Date: 2019-03-13
# Last Edit: 2019-03-18
# Creator:  Kirsten R. Hazler
#
# Summary:
# Functions for working with fields specific to the Recreation Access Model.
#
#--------------------------------------------------------------------------------------

import Helper
from Helper import *
import collections

def updateAliases(inTab, fldDict):
   '''Updates aliases for fields as specified in a field dictionary.'''
   
   for field in fldDict:
      alias = fldDict[field]
      try:
         arcpy.AlterField_management(inTab, field, "", alias)
         printMsg('Alias for field %s has been set.' %field)
      except:
         printWrng('Unable to update alias for field %s' %field)
         
   return()
   
def addFields(inTab, fldDict):
   for field in fldDict:
      alias = fldDict[field][0]
      type = fldDict[field][1]
      
      try:
         arcpy.AddField_management (inTab, field, type, "", "", "", alias)
         printMsg('Field %s added.' %field)
      except:
         printWrng('Unable to add field %s.' %field)
         printWrng
   
def recModFields():
   '''Sets up data dictionary needed for the updateAliases and addFields functions. Amend code as needed for desired fields and aliases.'''
   d = collections.OrderedDict() # Empty ordered data dictionary to store field names and aliases
   
   # General fields
   d['PopSum'] = ['Population', 'DOUBLE']
   
   # Regional Parks fields
   d['rPrk_bNeed'] = ['Reg. Parks Base Need, Acres', 'DOUBLE']
   d['rPrk_mNeed'] =  ['Reg. Parks Max Need, Acres', 'DOUBLE']
   d['rPrk_Acc'] =  ['Reg. Park Acres in Range', 'DOUBLE']
   d['rPrk_p1K'] =  ['Reg. Park Acres per 1000', 'DOUBLE']
   d['rPrk_tt30'] =  ['Prop. w/in 30 Min. of Reg. Park', 'DOUBLE']
   d['rPrk_ttAvg'] =  ['Avg. Drive Time to Reg. Park' , 'DOUBLE']
   d['rPrk_bStat'] = ['Reg. Parks Baseline Benchmark Status', 'SHORT']
   d['rPrk_mStat'] = ['Reg. Parks Max Benchmark Status', 'SHORT']
   
   # Local Parks fields
   d['lPrk_bNeed'] =  ['Loc. Parks Base Need, Acres', 'DOUBLE']
   d['lPrk_mNeed'] =  ['Loc. Parks Max Need, Acres', 'DOUBLE']
   d['lPrk_Acc'] =  ['Loc. Park Acres in Range' , 'DOUBLE']
   d['lPrk_p1K'] =  ['Loc. Park Acres per 1000', 'DOUBLE']
   d['lPrk_tt10'] =  ['Prop. w/in 10 Min. of Loc. Park', 'DOUBLE']
   d['lPrk_ttAvg'] =  ['Avg. Walk Time to Loc. Park' , 'DOUBLE']
   d['lPrk_bStat'] = ['Loc. Parks Baseline Benchmark Status', 'SHORT']
   d['lPrk_mStat'] = ['Loc. Parks Max Benchmark Status', 'SHORT']
   
   # Regional Trails fields
   d['rTrl_bNeed'] =  ['Reg. Trails Base Need, Miles', 'DOUBLE']
   d['rTrl_mNeed'] =  ['Reg. Trails Max Need, Miles', 'DOUBLE']
   d['rTrl_Acc'] =  ['Reg. Trail Miles in Range', 'DOUBLE']
   d['rTrl_p75C'] =  ['Reg. Trail Miles per 7500', 'DOUBLE']
   d['rTrl_tt30'] =  ['Prop. w/in 30 Min. of Reg. Trail', 'DOUBLE']
   d['rTrl_ttAvg'] =  ['Avg. Drive Time to Reg. Trail', 'DOUBLE']
   d['rTrl_bStat'] = ['Reg. Trails Baseline Benchmark Status', 'SHORT']
   d['rTrl_mStat'] = ['Reg. Trails Max Benchmark Status', 'SHORT']
   
   # Local Trails fields
   d['lTrl_bNeed'] =  ['Loc. Trails Base Need, Miles', 'DOUBLE']
   d['lTrl_mNeed'] =  ['Loc. Trails Max Need, Miles', 'DOUBLE']
   d['lTrl_Acc'] =  ['Loc. Trail Miles in Range', 'DOUBLE']
   d['lTrl_p75C'] =  ['Loc. Trail Miles per 7500', 'DOUBLE']
   d['lTrl_tt10'] =  ['Prop. w/in 10 Min. of Loc. Trail', 'DOUBLE']
   d['lTrl_ttAvg'] =  ['Avg. Walk Time to Loc. Trail', 'DOUBLE']
   d['lTrl_bStat'] = ['Loc. Trails Baseline Benchmark Status', 'SHORT']
   d['lTrl_mStat'] = ['Loc. Trails Max Benchmark Status', 'SHORT']
   
   # Boating fields
   d['rBtl_bNeed'] =  ['Boating Base Need, Access Pts.', 'DOUBLE']
   d['rBtl_mNeed'] =  ['Boating Max Need, Access Pts.', 'DOUBLE']
   d['rBtl_Acc'] =  ['Boating Access Pts. in Range', 'DOUBLE']
   d['rBtl_p10K'] =  ['Boating Access Pts. per 10,000', 'DOUBLE']
   d['rBtl_tt30'] =  ['Prop. w/in 30 Min. of Boating', 'DOUBLE']
   d['rBtl_ttAvg'] =  ['Avg. Drive Time to Boating', 'DOUBLE']
   d['rBtl_bStat'] = ['Boating Baseline Benchmark Status', 'SHORT']
   d['rBtl_mStat'] = ['Boating Max Benchmark Status', 'SHORT']
   
   # Fishing fields
   d['rFsh_bNeed'] =  ['Fishing Base Need, Access Pts.', 'DOUBLE']
   d['rFsh_mNeed'] =  ['Fishing Max Need, Access Pts.', 'DOUBLE']
   d['rFsh_Acc'] =  ['Fishing Access Pts. in Range', 'DOUBLE']
   d['rFsh_p10K'] =  ['Fishing Access Pts. per 10,000', 'DOUBLE']
   d['rFsh_tt30'] =  ['Prop. w/in 30 Min. of Fishing', 'DOUBLE']
   d['rFsh_ttAvg'] =  ['Avg. Drive Time to Fishing', 'DOUBLE']
   d['lFsh_tt10'] =  ['Prop. w/in 10 Min. of Fishing', 'DOUBLE']
   d['lFsh_ttAvg'] =  ['Avg. Walk Time to Fishing', 'DOUBLE']
   d['rFsh_bStat'] = ['Fishing Baseline Benchmark Status', 'SHORT']
   d['rFsh_mStat'] = ['Fishing Max Benchmark Status', 'SHORT']
   
   # Swimming fields
   d['rSwm_bNeed'] =  ['Swimming Base Need, Access Pts.', 'DOUBLE']
   d['rSwm_mNeed'] =  ['Swimming Max Need, Access Pts.', 'DOUBLE']
   d['rSwm_Acc'] =  ['Swimming Access Pts. in Range', 'DOUBLE']
   d['rSwm_p10K'] =  ['Swimming Access Pts. per 10,000', 'DOUBLE']
   d['rSwm_tt30'] =  ['Prop. w/in 30 Min. of Swimming', 'DOUBLE']
   d['rSwm_ttAvg'] =  ['Avg. Drive Time to Swimming', 'DOUBLE']
   d['lSwm_tt10'] =  ['Prop. w/in 10 Min. of Swimming', 'DOUBLE']
   d['lSwm_ttAvg'] =  ['Avg. Walk Time to Swimming', 'DOUBLE']
   d['rSwm_bStat'] = ['Swimming Baseline Benchmark Status', 'SHORT']
   d['rSwm_mStat'] = ['Swimming Max Benchmark Status', 'SHORT']
   
   # Summary fields
   d['terrScore'] = ['Terrestrial Recreation Score', 'SHORT']
   d['aquaScore'] = ['Aquatic Recreation Score', 'SHORT']

   return d
   
def recModDomains():
   '''Sets up code-value pairs for coded domains.'''
   
   prk = collections.OrderedDict()
   prk[0] = 'Benchmark Completely Met'
   prk[1] = 'Benchmark Partially Met'
   prk[2] = '≤ 5 Acres Needed to Meet Benchmark'
   prk[3] = '5 - 10 Acres Needed to Meet Benchmark'
   prk[4] = '10 - 15 Acres Needed to Meet Benchmark'
   prk[5] = '> 15 Acres Needed to Meet Benchmark'
   
   prk2 = collections.OrderedDict()
   prk2[0] = 'Benchmark Completely Met'
   prk2[1] = 'Benchmark Partially Met'
   prk2[2] = '≤ 5 Acres Needed to Meet Benchmark'
   prk2[3] = '5 - 25 Acres Needed to Meet Benchmark'
   prk2[4] = '25 - 50 Acres Needed to Meet Benchmark'
   prk2[5] = '> 50 Acres Needed to Meet Benchmark'
   
   trl = collections.OrderedDict()
   trl[0] = 'Benchmark Completely Met'
   trl[1] = 'Benchmark Partially Met'
   trl[2] = '≤ 1 Mile Needed to Meet Benchmark'
   trl[3] = '1 - 2 Miles Needed to Meet Benchmark'
   trl[4] = '2 - 3 Miles Needed to Meet Benchmark'
   trl[5] = '> 3 Miles Needed to Meet Benchmark'
   
   trl2 = collections.OrderedDict()
   trl2[0] = 'Benchmark Completely Met'
   trl2[1] = 'Benchmark Partially Met'
   trl2[2] = '≤ 1 Mile Needed to Meet Benchmark'
   trl2[3] = '1 - 5 Miles Needed to Meet Benchmark'
   trl2[4] = '5 - 10 Miles Needed to Meet Benchmark'
   trl2[5] = '> 10 Miles Needed to Meet Benchmark'
   
   aqua = collections.OrderedDict()
   aqua[0] = 'Benchmark Completely Met'
   aqua[1] = 'Benchmark Partially Met'
   aqua[2] = '≤ 1 Access Pt. Needed to Meet Benchmark'
   aqua[3] = '1 - 2 Access Pts. Needed to Meet Benchmark'
   aqua[4] = '2 - 3 Access Pts. Needed to Meet Benchmark'
   aqua[5] = '> 3 Access Pts. Needed to Meet Benchmark'
   
   aqua2 = collections.OrderedDict()
   aqua2[0] = 'Benchmark Completely Met'
   aqua2[1] = 'Benchmark Partially Met'
   aqua2[2] = '≤ 1 Access Pt. Needed to Meet Benchmark'
   aqua2[3] = '1 - 5 Access Pts. Needed to Meet Benchmark'
   aqua2[4] = '5 - 10 Access Pts. Needed to Meet Benchmark'
   aqua2[5] = '> 10 Access Pts. Needed to Meet Benchmark'
   
   summary = collections.OrderedDict()
   summary[0] = '0: Very High Need'
   summary[1] = '1: High Need'
   summary[2] = '2: Moderate Need'
   summary[3] = '3: Low Need'
   summary[4] = '4: Very Low Need'
   summary[5] = '5: All Benchmarks Met'
   
   return (prk, prk2, trl, trl2, aqua, aqua2, summary)
   
def attachCodedDomain(inGDB, inTab, inFld, domainName, domainDesc, codeDict):
   arcpy.CreateDomain_management(inGDB, domainName, domainDesc, "SHORT", "CODED")
   for code, desc in codeDict.items():
      arcpy.AddCodedValueToDomain_management(inGDB, domainName, code, desc)
   arcpy.AssignDomainToField_management(inTab, inFld, domainName)
   
def calcScores(inTab):
   '''Calculates summary scores. Note that scores are rounded down when integerized.'''
   # Terrestrial Score
   codeblock = '''def calcTerrScore(PopSum, f1, f2, f3, f4):
      sum = 0
      for f in [f1, f2, f3, f4]:
         val = 5 - f
         sum += val
      score = sum/4
      if PopSum == 0:
         return None
      else:
         return int(score)
      '''
   expression = "calcTerrScore(!PopSum!, !rPrk_bStat!, !lPrk_bStat!, !rTrl_bStat!, !lTrl_bStat!)"
   arcpy.CalculateField_management (inTab, "terrScore", expression, "PYTHON", codeblock)
   
   # Aquatic Score
   codeblock = '''def calcAquaScore(PopSum, f1, f2, f3):
      sum = 0
      for f in [f1, f2, f3]:
         val = 5 - f
         sum += val
      score = sum/3
      if PopSum == 0:
         return None
      else:
         return int(score)
      '''
   expression = "calcAquaScore(!PopSum!, !rBtl_bStat!, !rFsh_bStat!, !rSwm_bStat!)"
   arcpy.CalculateField_management (inTab, "aquaScore", expression, "PYTHON", codeblock)
   
   return
   
def main():
   inTab = r'F:\Working\RecMod\Outputs\VA_RecMod_CONUS\VA_RecMod.gdb\RecreationAccess'
   targetTab = r'F:\Working\RecMod\Outputs\VA_RecMod_CONUS\VA_RecMod.gdb\RecreationAccess_Final'
   inGDB = r'F:\Working\RecMod\Outputs\VA_RecMod_CONUS\VA_RecMod.gdb'
   
   printMsg('Calculating scores...')
   calcScores(inTab)
   
   fldDict = recModFields()
   printMsg('Field data dictionary created. Adding fields...')
   addFields(targetTab, fldDict)
      
   printMsg('Setting up coded domain values...')
   prk, prk2, trl, trl2, aqua, aqua2, summary = recModDomains()
   
   printMsg('Attaching domains to fields...')
   attachCodedDomain(inGDB, targetTab, 'rPrk_bStat', 'rPrk_bDomain', 'Regional Park Benchmark Status, Baseline', prk)
   attachCodedDomain(inGDB, targetTab, 'lPrk_bStat', 'lPrk_bDomain', 'Local Park Benchmark Status, Baseline', prk)
   attachCodedDomain(inGDB, targetTab, 'rTrl_bStat', 'rTrl_bDomain', 'Regional Trail Benchmark Status, Baseline', trl)
   attachCodedDomain(inGDB, targetTab, 'lTrl_bStat', 'lTrl_bDomain', 'Local Trail Benchmark Status, Baseline', trl)
   attachCodedDomain(inGDB, targetTab, 'rBtl_bStat', 'rBtl_bDomain', 'Boating Benchmark Status, Baseline', aqua)
   attachCodedDomain(inGDB, targetTab, 'rFsh_bStat', 'rFsh_bDomain', 'Fishing Benchmark Status, Baseline', aqua)
   attachCodedDomain(inGDB, targetTab, 'rSwm_bStat', 'rSwm_bDomain', 'Swimming Benchmark Status, Baseline', aqua)
   
   attachCodedDomain(inGDB, targetTab, 'rPrk_mStat', 'rPrk_mDomain', 'Regional Park Benchmark Status, Max', prk2)
   attachCodedDomain(inGDB, targetTab, 'lPrk_mStat', 'lPrk_mDomain', 'Local Park Benchmark Status, Max', prk2)
   attachCodedDomain(inGDB, targetTab, 'rTrl_mStat', 'rTrl_mDomain', 'Regional Trail Benchmark Status, Max', trl2)
   attachCodedDomain(inGDB, targetTab, 'lTrl_mStat', 'lTrl_mDomain', 'Local Trail Benchmark Status, Max', trl2)
   attachCodedDomain(inGDB, targetTab, 'rBtl_mStat', 'rBtl_mDomain', 'Boating Benchmark Status, Max', aqua2)
   attachCodedDomain(inGDB, targetTab, 'rFsh_mStat', 'rFsh_mDomain', 'Fishing Benchmark Status, Max', aqua2)
   attachCodedDomain(inGDB, targetTab, 'rSwm_mStat', 'rSwm_mDomain', 'Swimming Benchmark Status, Max', aqua2)
   
   attachCodedDomain(inGDB, targetTab, 'terrScore', 'terrScore_Domain', 'Terrestrial Benchmark Status', summary)
   attachCodedDomain(inGDB, targetTab, 'aquaScore', 'aquaScore_Domain', 'Aquatic Benchmark Status', summary)
   
   printMsg('Appending records...')
   arcpy.Append_management (inTab, targetTab, 'NO_TEST')

   printMsg('Done')
   
if __name__ == '__main__':
   main()
