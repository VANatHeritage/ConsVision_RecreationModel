# fldOps.py
# Version:  ArcGIS 10.3.1 / Python 2.7.8
# Creation Date: 2019-03-13
# Last Edit: 2020-05-18
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
   # Domain for rPrk_bStat and rPrk_mStat fields
   prk = collections.OrderedDict()
   prk[0] = 'Benchmark Met'
   prk[1] = '≤ 1 Acre Needed per 1000 Hexagons'
   prk[2] = '1 - 10 Acres Needed per 1000 Hexagons'
   prk[3] = '10 - 100 Acres Needed per 1000 Hexagons'
   prk[4] = '100 - 1000 Acres Needed per 1000 Hexagons'
   prk[5] = '> 1000 Acres Needed per 1000 Hexagons'
   
   # Domain for lPrk_bStat and lPrk_mStat fields
   prk2 = collections.OrderedDict()
   prk2[0] = 'Benchmark Met'
   prk2[1] = '≤ 5 Acres Needed'
   prk2[2] = '5 - 10 Acres Needed'
   prk2[3] = '10 - 15 Acres Needed'
   prk2[4] = '15 - 20 Acres Needed'
   prk2[5] = '> 20 Acres Needed'
   
   # Domain for rTrl_bStat and rTrl_mStat fields
   trl = collections.OrderedDict()
   trl[0] = 'Benchmark Met'
   trl[1] = '≤ 1 Mile Needed per 1000 Hexagons'
   trl[2] = '1 - 10 Miles Needed per 1000 Hexagons'
   trl[3] = '10 - 100 Miles Needed per 1000 Hexagons'
   trl[4] = '100 - 1000 Miles Needed per 1000 Hexagons'
   trl[5] = '> 1000 Miles Needed per 1000 Hexagons'
   
   # Domain for lTrl_bStat and lTrl_mStat fields
   trl2 = collections.OrderedDict()
   trl2[0] = 'Benchmark Met'
   trl2[1] = '≤ 1 Mile Needed'
   trl2[2] = '1 - 2 Miles Needed'
   trl2[3] = '2 - 3 Miles Needed'
   trl2[4] = '3 - 4 Miles Needed'
   trl2[5] = '> 4 Miles Needed'
   
   # Domain for aquatic *_bStat and *_mStat fields
   aqua = collections.OrderedDict()
   aqua[0] = 'Benchmark Met'
   aqua[1] = '≤ 1 Access Point Needed per 1000 Hexagons'
   aqua[2] = '1 - 10 Access Points Needed per 1000 Hexagons'
   aqua[3] = '10 - 100 Access Points Needed per 1000 Hexagons'
   aqua[4] = '100 - 1000 Access Points Needed per 1000 Hexagons'
   aqua[5] = '> 1000 Access Points Needed per 1000 Hexagons'
   
   # Domain for aquaScore and terrScore fields
   summary = collections.OrderedDict()
   summary[0] = '0: Very High Need'
   summary[1] = '1: High Need'
   summary[2] = '2: Moderate Need'
   summary[3] = '3: Low Need'
   summary[4] = '4: Very Low Need'
   summary[5] = '5: All Benchmarks Met'
   
   return (prk, prk2, trl, trl2, aqua, summary)
   
def attachCodedDomain(inGDB, inTab, inFld, domainName, domainDesc, codeDict):
   arcpy.CreateDomain_management(inGDB, domainName, domainDesc, "SHORT", "CODED")
   for code, desc in codeDict.items():
      arcpy.AddCodedValueToDomain_management(inGDB, domainName, code, desc)
   arcpy.AssignDomainToField_management(inTab, inFld, domainName)
   
def calcScores(inTab):
   '''Calculates summary scores. Note that scores are rounded down when integerized. Assumes very specific data structure with specific field names; will fail if not correct.'''
   
   # Terrestrial Score
   codeblock = '''def calcTerrScore(PopSum, rb1, rb2, lb1, lb2, d1, d2, w1, w2):
      sum = 0
      for b in [rb1, rb2]:
         val = 5 - b
         sum += val
      rbscore = sum/2
      
      sum = 0
      for b in [lb1, lb2]:
         val = 5 - b
         sum += val
      lbscore = sum/2
      
      sum = 0
      for d in [d1, d2]:
         if d <= 30:
            val = 5
         elif d <= 45:
            val = 4
         elif d <= 60:
            val = 3
         elif d <= 75:
            val = 2
         elif d <= 90:
            val = 1
         else:
            val = 0
         sum += val
      dscore = sum/2
      
      sum = 0
      for w in [w1, w2]:
         if w <= 10:
            val = 5
         elif w <= 15:
            val = 4
         elif w <= 20:
            val = 3
         elif w <= 25:
            val = 2
         elif w <= 30:
            val = 1
         else:
            val = 0
         sum += val
      wscore = sum/2
      
      regscore = (rbscore + dscore)/2
      locscore = (lbscore + wscore)/2
      comboscore = (regscore + locscore)/2
      
      if PopSum == 0:
         return None
      elif PopSum < 500:
         return int(regscore)
      else:
         return int(comboscore)
      '''
   expression = "calcTerrScore(!PopSum!, !rPrk_bStat!, !rTrl_bStat!, !lPrk_bStat!, !lTrl_bStat!, !rPrk_ttAvg!, !rTrl_ttAvg!, !lPrk_ttAvg!, !lTrl_ttAvg!)"
   arcpy.CalculateField_management (inTab, "terrScore", expression, "PYTHON", codeblock)
   
   # Aquatic Score
   codeblock = '''def calcAquaScore(PopSum, b1, b2, b3, t1, t2, t3):
      sum = 0
      for b in [b1, b2, b3]:
         val = 5 - b
         sum += val
      bscore = sum/3
      
      sum = 0
      for t in [t1, t2, t3]:
         if t <= 30:
            val = 5
         elif t <= 45:
            val = 4
         elif t <= 60:
            val = 3
         elif t <= 75:
            val = 2
         elif t <= 90:
            val = 1
         else:
            val = 0
         sum += val
      tscore = sum/3
      
      score = (bscore + tscore)/2
      
      if PopSum == 0:
         return None
      else:
         return int(score)
      '''
   expression = "calcAquaScore(!PopSum!, !rBtl_bStat!, !rFsh_bStat!, !rSwm_bStat!, !rBtl_ttAvg!, !rFsh_ttAvg!, !rSwm_ttAvg!)"
   arcpy.CalculateField_management (inTab, "aquaScore", expression, "PYTHON", codeblock)
   
   return

def terrScore_bt(inTab):
   '''alculates summary terrestrial score, version BT. Note that scores are rounded down when integerized. Assumes very specific data structure with specific field names; will fail if not correct.'''
   
   # Version BT = same as original score version, but applying heavier weight to travel time scores
   codeblock = '''def calcTerrScore(PopSum, rb1, rb2, lb1, lb2, d1, d2, w1, w2):
      sum = 0
      for b in [rb1, rb2]:
         val = 5 - b
         sum += val
      rbscore = sum/2
      
      sum = 0
      for b in [lb1, lb2]:
         val = 5 - b
         sum += val
      lbscore = sum/2
      
      sum = 0
      for d in [d1, d2]:
         if d <= 30:
            val = 5
         elif d <= 45:
            val = 4
         elif d <= 60:
            val = 3
         elif d <= 75:
            val = 2
         elif d <= 90:
            val = 1
         else:
            val = 0
         sum += val
      dscore = sum/2
      
      sum = 0
      for w in [w1, w2]:
         if w <= 10:
            val = 5
         elif w <= 15:
            val = 4
         elif w <= 20:
            val = 3
         elif w <= 25:
            val = 2
         elif w <= 30:
            val = 1
         else:
            val = 0
         sum += val
      wscore = sum/2
      
      regscore = (rbscore + 2*dscore)/3
      locscore = (lbscore + 2*wscore)/3
      comboscore = (regscore + locscore)/2
      
      if PopSum == 0:
         return None
      elif PopSum < 500:
         return int(regscore)
      else:
         return int(comboscore)
      '''
   expression = "calcTerrScore(!PopSum!, !rPrk_bStat!, !rTrl_bStat!, !lPrk_bStat!, !lTrl_bStat!, !rPrk_ttAvg!, !rTrl_ttAvg!, !lPrk_ttAvg!, !lTrl_ttAvg!)"
   arcpy.CalculateField_management (inTab, "terrScore_bt", expression, "PYTHON", codeblock)
   
def terrScore_me(inTab):
   '''Calculates summary terrestrial score, version ME. Note that scores are rounded down when integerized. Assumes very specific data structure with specific field names; will fail if not correct.'''
   
   # Version ME = same as original score version, but using maximum instead of baseline benchmarks
   codeblock = '''def calcTerrScore(PopSum, rb1, rb2, lb1, lb2, d1, d2, w1, w2):
      sum = 0
      for b in [rb1, rb2]:
         val = 5 - b
         sum += val
      rbscore = sum/2
      
      sum = 0
      for b in [lb1, lb2]:
         val = 5 - b
         sum += val
      lbscore = sum/2
      
      sum = 0
      for d in [d1, d2]:
         if d <= 30:
            val = 5
         elif d <= 45:
            val = 4
         elif d <= 60:
            val = 3
         elif d <= 75:
            val = 2
         elif d <= 90:
            val = 1
         else:
            val = 0
         sum += val
      dscore = sum/2
      
      sum = 0
      for w in [w1, w2]:
         if w <= 10:
            val = 5
         elif w <= 15:
            val = 4
         elif w <= 20:
            val = 3
         elif w <= 25:
            val = 2
         elif w <= 30:
            val = 1
         else:
            val = 0
         sum += val
      wscore = sum/2
      
      regscore = (rbscore + dscore)/2
      locscore = (lbscore + wscore)/2
      comboscore = (regscore + locscore)/2
      
      if PopSum == 0:
         return None
      elif PopSum < 500:
         return int(regscore)
      else:
         return int(comboscore)
      '''
   expression = "calcTerrScore(!PopSum!, !rPrk_mStat!, !rTrl_mStat!, !lPrk_mStat!, !lTrl_mStat!, !rPrk_ttAvg!, !rTrl_ttAvg!, !lPrk_ttAvg!, !lTrl_ttAvg!)"
   arcpy.CalculateField_management (inTab, "terrScore_me", expression, "PYTHON", codeblock)

def terrScore_mt(inTab):
   '''Calculates summary terrestrial score, version MT. Note that scores are rounded down when integerized. Assumes very specific data structure with specific field names; will fail if not correct.'''
   
   # Version MT = same as version BT, but using maximum instead of baseline benchmarks
   codeblock = '''def calcTerrScore(PopSum, rb1, rb2, lb1, lb2, d1, d2, w1, w2):
      sum = 0
      for b in [rb1, rb2]:
         val = 5 - b
         sum += val
      rbscore = sum/2
      
      sum = 0
      for b in [lb1, lb2]:
         val = 5 - b
         sum += val
      lbscore = sum/2
      
      sum = 0
      for d in [d1, d2]:
         if d <= 30:
            val = 5
         elif d <= 45:
            val = 4
         elif d <= 60:
            val = 3
         elif d <= 75:
            val = 2
         elif d <= 90:
            val = 1
         else:
            val = 0
         sum += val
      dscore = sum/2
      
      sum = 0
      for w in [w1, w2]:
         if w <= 10:
            val = 5
         elif w <= 15:
            val = 4
         elif w <= 20:
            val = 3
         elif w <= 25:
            val = 2
         elif w <= 30:
            val = 1
         else:
            val = 0
         sum += val
      wscore = sum/2
      
      regscore = (rbscore + 2*dscore)/3
      locscore = (lbscore + 2*wscore)/3
      comboscore = (regscore + locscore)/2
      
      if PopSum == 0:
         return None
      elif PopSum < 500:
         return int(regscore)
      else:
         return int(comboscore)
      '''
   expression = "calcTerrScore(!PopSum!, !rPrk_mStat!, !rTrl_mStat!, !lPrk_mStat!, !lTrl_mStat!, !rPrk_ttAvg!, !rTrl_ttAvg!, !lPrk_ttAvg!, !lTrl_ttAvg!)"
   arcpy.CalculateField_management (inTab, "terrScore_mt", expression, "PYTHON", codeblock)

def terrScore_bme(inTab):
   '''Calculates summary terrestrial score, version BME. Note that scores are rounded down when integerized. Assumes very specific data structure with specific field names; will fail if not correct.'''
   
   # Version BME = same as original score version, but using combination of maximum and baseline benchmarks
   codeblock = '''def calcTerrScore(PopSum, rb1, rm1, rb2, rm2, lb1, lm1, lb2, lm2, d1, d2, w1, w2):
      sum = 0
      for b in [rb1, rm1, rb2, rm2]:
         val = 5 - b
         sum += val
      rbscore = sum/4
      
      sum = 0
      for b in [lb1, lm1, lb2, lm2]:
         val = 5 - b
         sum += val
      lbscore = sum/4
      
      sum = 0
      for d in [d1, d2]:
         if d <= 30:
            val = 5
         elif d <= 45:
            val = 4
         elif d <= 60:
            val = 3
         elif d <= 75:
            val = 2
         elif d <= 90:
            val = 1
         else:
            val = 0
         sum += val
      dscore = sum/2
      
      sum = 0
      for w in [w1, w2]:
         if w <= 10:
            val = 5
         elif w <= 15:
            val = 4
         elif w <= 20:
            val = 3
         elif w <= 25:
            val = 2
         elif w <= 30:
            val = 1
         else:
            val = 0
         sum += val
      wscore = sum/2
      
      regscore = (rbscore + dscore)/2
      locscore = (lbscore + wscore)/2
      comboscore = (regscore + locscore)/2
      
      if PopSum == 0:
         return None
      elif PopSum < 500:
         return int(regscore)
      else:
         return int(comboscore)
      '''
   expression = "calcTerrScore(!PopSum!, !rPrk_bStat!, !rPrk_mStat!, !rTrl_bStat!, !rTrl_mStat!, !lPrk_bStat!, !lPrk_mStat!, !lTrl_bStat!, !lTrl_mStat!, !rPrk_ttAvg!, !rTrl_ttAvg!, !lPrk_ttAvg!, !lTrl_ttAvg!)"
   arcpy.CalculateField_management (inTab, "terrScore_bme", expression, "PYTHON", codeblock)

def terrScore_bmt(inTab):
   '''Calculates summary terrestrial score, version BME. Note that scores are rounded down when integerized. Assumes very specific data structure with specific field names; will fail if not correct.'''
   
   # Version BMT = same as version BME, but applying heavier weight to travel time scores
   codeblock = '''def calcTerrScore(PopSum, rb1, rm1, rb2, rm2, lb1, lm1, lb2, lm2, d1, d2, w1, w2):
      sum = 0
      for b in [rb1, rm1, rb2, rm2]:
         val = 5 - b
         sum += val
      rbscore = sum/4
      
      sum = 0
      for b in [lb1, lm1, lb2, lm2]:
         val = 5 - b
         sum += val
      lbscore = sum/4
      
      sum = 0
      for d in [d1, d2]:
         if d <= 30:
            val = 5
         elif d <= 45:
            val = 4
         elif d <= 60:
            val = 3
         elif d <= 75:
            val = 2
         elif d <= 90:
            val = 1
         else:
            val = 0
         sum += val
      dscore = sum/2
      
      sum = 0
      for w in [w1, w2]:
         if w <= 10:
            val = 5
         elif w <= 15:
            val = 4
         elif w <= 20:
            val = 3
         elif w <= 25:
            val = 2
         elif w <= 30:
            val = 1
         else:
            val = 0
         sum += val
      wscore = sum/2
      
      regscore = (rbscore + 2*dscore)/3
      locscore = (lbscore + 2*wscore)/3
      comboscore = (regscore + locscore)/2
      
      if PopSum == 0:
         return None
      elif PopSum < 500:
         return int(regscore)
      else:
         return int(comboscore)
      '''
   expression = "calcTerrScore(!PopSum!, !rPrk_bStat!, !rPrk_mStat!, !rTrl_bStat!, !rTrl_mStat!, !lPrk_bStat!, !lPrk_mStat!, !lTrl_bStat!, !lTrl_mStat!, !rPrk_ttAvg!, !rTrl_ttAvg!, !lPrk_ttAvg!, !lTrl_ttAvg!)"
   arcpy.CalculateField_management (inTab, "terrScore_bmt", expression, "PYTHON", codeblock)

def terrScore_bmin(inTab):
   '''Calculates summary terrestrial score, version BMIN. Note that scores are rounded down when integerized. Assumes very specific data structure with specific field names; will fail if not correct.'''
   
   # Version BMIN = same as original score version, but using minimum instead of average of sub-scores
   codeblock = '''def calcTerrScore(PopSum, rb1, rb2, lb1, lb2, d1, d2, w1, w2):
      m = 5
      for b in [rb1, rb2]:
         val = 5 - b
         m = min(m, val)
      rbscore = m
      
      m = 5
      for b in [lb1, lb2]:
         val = 5 - b
         m = min(m, val)
      lbscore = m
      
      m = 5
      for d in [d1, d2]:
         if d <= 30:
            val = 5
         elif d <= 45:
            val = 4
         elif d <= 60:
            val = 3
         elif d <= 75:
            val = 2
         elif d <= 90:
            val = 1
         else:
            val = 0
         m = min(m, val)
      dscore = m
      
      m = 5
      for w in [w1, w2]:
         if w <= 10:
            val = 5
         elif w <= 15:
            val = 4
         elif w <= 20:
            val = 3
         elif w <= 25:
            val = 2
         elif w <= 30:
            val = 1
         else:
            val = 0
         m = min(m, val)
      wscore = m
      
      regscore = min(rbscore, dscore)
      locscore = min(lbscore, wscore)
      comboscore = min(regscore, locscore)
      
      if PopSum == 0:
         return None
      elif PopSum < 500:
         return int(regscore)
      else:
         return int(comboscore)
      '''
   expression = "calcTerrScore(!PopSum!, !rPrk_bStat!, !rTrl_bStat!, !lPrk_bStat!, !lTrl_bStat!, !rPrk_ttAvg!, !rTrl_ttAvg!, !lPrk_ttAvg!, !lTrl_ttAvg!)"
   arcpy.CalculateField_management (inTab, "terrScore_bmin", expression, "PYTHON", codeblock)

def terrScore_mmin(inTab):
   '''Calculates summary terrestrial score, version MMIN. Note that scores are rounded down when integerized. Assumes very specific data structure with specific field names; will fail if not correct.'''
   
   # Version MMIN = same as original score version, but using minimum instead of average of sub-scores, and maximum instead of baseline benchmarks
   codeblock = '''def calcTerrScore(PopSum, rb1, rb2, lb1, lb2, d1, d2, w1, w2):
      m = 5
      for b in [rb1, rb2]:
         val = 5 - b
         m = min(m, val)
      rbscore = m
      
      m = 5
      for b in [lb1, lb2]:
         val = 5 - b
         m = min(m, val)
      lbscore = m
      
      m = 5
      for d in [d1, d2]:
         if d <= 30:
            val = 5
         elif d <= 45:
            val = 4
         elif d <= 60:
            val = 3
         elif d <= 75:
            val = 2
         elif d <= 90:
            val = 1
         else:
            val = 0
         m = min(m, val)
      dscore = m
      
      m = 5
      for w in [w1, w2]:
         if w <= 10:
            val = 5
         elif w <= 15:
            val = 4
         elif w <= 20:
            val = 3
         elif w <= 25:
            val = 2
         elif w <= 30:
            val = 1
         else:
            val = 0
         m = min(m, val)
      wscore = m
      
      regscore = min(rbscore, dscore)
      locscore = min(lbscore, wscore)
      comboscore = min(regscore, locscore)
      
      if PopSum == 0:
         return None
      elif PopSum < 500:
         return int(regscore)
      else:
         return int(comboscore)
      '''
   expression = "calcTerrScore(!PopSum!, !rPrk_mStat!, !rTrl_mStat!, !lPrk_mStat!, !lTrl_mStat!, !rPrk_ttAvg!, !rTrl_ttAvg!, !lPrk_ttAvg!, !lTrl_ttAvg!)"
   arcpy.CalculateField_management (inTab, "terrScore_mmin", expression, "PYTHON", codeblock)


def main():
   inTab = r'F:\Working\RecMod\Outputs\VA_RecMod_CONUS\VA_RecMod.gdb\RecreationAccess'
   targetTab = r'F:\Working\RecMod\Outputs\VA_RecMod_CONUS\VA_RecMod.gdb\RecreationAccess_Final'
   inGDB = r'F:\Working\RecMod\Outputs\VA_RecMod_CONUS\VA_RecMod.gdb'
   
   fldDict = recModFields()
   printMsg('Field data dictionary created. Adding fields...')
   addFields(targetTab, fldDict)
      
   printMsg('Setting up coded domain values...')
   prk, prk2, trl, trl2, aqua, summary = recModDomains()
   
   printMsg('Attaching domains to fields...')
   attachCodedDomain(inGDB, targetTab, 'rPrk_bStat', 'rPrk_bDomain', 'Regional Park Benchmark Status, Baseline', prk)
   attachCodedDomain(inGDB, targetTab, 'lPrk_bStat', 'lPrk_bDomain', 'Local Park Benchmark Status, Baseline', prk2)
   attachCodedDomain(inGDB, targetTab, 'rTrl_bStat', 'rTrl_bDomain', 'Regional Trail Benchmark Status, Baseline', trl)
   attachCodedDomain(inGDB, targetTab, 'lTrl_bStat', 'lTrl_bDomain', 'Local Trail Benchmark Status, Baseline', trl2)
   attachCodedDomain(inGDB, targetTab, 'rBtl_bStat', 'rBtl_bDomain', 'Boating Benchmark Status, Baseline', aqua)
   attachCodedDomain(inGDB, targetTab, 'rFsh_bStat', 'rFsh_bDomain', 'Fishing Benchmark Status, Baseline', aqua)
   attachCodedDomain(inGDB, targetTab, 'rSwm_bStat', 'rSwm_bDomain', 'Swimming Benchmark Status, Baseline', aqua)
   
   attachCodedDomain(inGDB, targetTab, 'rPrk_mStat', 'rPrk_mDomain', 'Regional Park Benchmark Status, Max', prk)
   attachCodedDomain(inGDB, targetTab, 'lPrk_mStat', 'lPrk_mDomain', 'Local Park Benchmark Status, Max', prk2)
   attachCodedDomain(inGDB, targetTab, 'rTrl_mStat', 'rTrl_mDomain', 'Regional Trail Benchmark Status, Max', trl)
   attachCodedDomain(inGDB, targetTab, 'lTrl_mStat', 'lTrl_mDomain', 'Local Trail Benchmark Status, Max', trl2)
   attachCodedDomain(inGDB, targetTab, 'rBtl_mStat', 'rBtl_mDomain', 'Boating Benchmark Status, Max', aqua)
   attachCodedDomain(inGDB, targetTab, 'rFsh_mStat', 'rFsh_mDomain', 'Fishing Benchmark Status, Max', aqua)
   attachCodedDomain(inGDB, targetTab, 'rSwm_mStat', 'rSwm_mDomain', 'Swimming Benchmark Status, Max', aqua)
   
   attachCodedDomain(inGDB, targetTab, 'terrScore', 'terrScore_Domain', 'Terrestrial Benchmark Status', summary)
   attachCodedDomain(inGDB, targetTab, 'aquaScore', 'aquaScore_Domain', 'Aquatic Benchmark Status', summary)
   
   printMsg('Appending records...')
   arcpy.Append_management (inTab, targetTab, 'NO_TEST')
   
   printMsg('Calculating scores...')
   calcScores(targetTab)

   printMsg('Done')
   
if __name__ == '__main__':
   main()
