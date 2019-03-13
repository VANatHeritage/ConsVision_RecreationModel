import Helper
from Helper import *

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
   
def recModAliases():
   '''Sets up data dictionary needed for the updateAliases function. Amend code as needed for desired aliases.'''
   
   d = {} # Empty data dictionary to store field names and aliases
   
   # Regional Parks fields
   d['rPrk_bNeed'] = 'Reg. Parks Base Need, Acres'
   d['rPrk_mNeed'] =  'Reg. Parks Max Need, Acres'
   d['rPrk_Acc'] =  'Reg. Park Acres in Range'
   d['rPrk_p1K'] =  'Reg. Park Acres per 1000'
   d['rPrk_tt30'] =  'Prop. w/in 30 Min. of Reg. Park'
   d['rPrk_ttAvg'] =  'Avg. Drive Time to Reg. Park' 
   
   # Local Parks fields
   d['lPrk_bNeed'] =  'Loc. Parks Base Need, Acres'
   d['lPrk_mNeed'] =  'Loc. Parks Max Need, Acres'
   d['lPrk_Acc'] =  'Loc. Park Acres in Range' 
   d['lPrk_p1K'] =  'Loc. Park Acres per 1000'
   d['lPrk_tt10'] =  'Prop. w/in 10 Min. of Loc. Park'
   d['lPrk_ttAvg'] =  'Avg. Walk Time to Loc. Park' 
   
   # Regional Trails fields
   d['rTrl_bNeed'] =  'Reg. Trails Base Need, Miles'
   d['rTrl_mNeed'] =  'Reg. Trails Max Need, Miles'
   d['rTrl_Acc'] =  'Reg. Trail Miles in Range'
   d['rTrl_p75C'] =  'Reg. Trail Miles per 7500'
   d['rTrl_tt30'] =  'Prop. w/in 30 Min. of Reg. Trail'
   d['rTrl_ttAvg'] =  'Avg. Drive Time to Reg. Trail'
   
   # Local Trails fields
   d['lTrl_bNeed'] =  'Loc. Trails Base Need, Miles'
   d['lTrl_mNeed'] =  'Loc. Trails Max Need, Miles'
   d['lTrl_Acc'] =  'Loc. Trail Miles in Range'
   d['lTrl_p75C'] =  'Loc. Trail Miles per 7500'
   d['lTrl_tt10'] =  'Prop. w/in 10 Min. of Loc. Trail'
   d['lTrl_ttAvg'] =  'Avg. Walk Time to Loc. Trail' 
   
   # Boating fields
   d['rBtl_bNeed'] =  'Boating Base Need, Access Pts.'
   d['rBtl_mNeed'] =  'Boating Max Need, Access Pts.'
   d['rBtl_Acc'] =  'Boating Access Pts. in Range'
   d['rBtl_p10K'] =  'Boating Access Pts. per 10,000'
   d['rBtl_tt30'] =  'Prop. w/in 30 Min. of Boating'
   d['rBtl_ttAvg'] =  'Avg. Drive Time to Boating'
   
   # Swimming fields
   d['rSwm_bNeed'] =  'Swimming Base Need, Access Pts.'
   d['rSwm_mNeed'] =  'Swimming Max Need, Access Pts.'
   d['rSwm_Acc'] =  'Swimming Access Pts. in Range'
   d['rSwm_p10K'] =  'Swimming Access Pts. per 10,000'
   d['rSwm_tt30'] =  'Prop. w/in 30 Min. of Swimming'
   d['rSwm_ttAvg'] =  'Avg. Drive Time to Swimming'
   d['lSwm_tt10'] =  'Prop. w/in 10 Min. of Swimming'
   d['lSwm_ttAvg'] =  'Avg. Walk Time to Swimming'
   
   # Fishing fields
   d['rFsh_bNeed'] =  'Fishing Base Need, Access Pts.'
   d['rFsh_mNeed'] =  'Fishing Max Need, Access Pts.'
   d['rFsh_Acc'] =  'Fishing Access Pts. in Range'
   d['rFsh_p10K'] =  'Fishing Access Pts. per 10,000'
   d['rFsh_tt30'] =  'Prop. w/in 30 Min. of Fishing'
   d['rFsh_ttAvg'] =  'Avg. Drive Time to Fishing'
   d['lFsh_tt10'] =  'Prop. w/in 10 Min. of Fishing'
   d['lFsh_ttAvg'] =  'Avg. Walk Time to Fishing'
   
   return d
   
def main():
   fldDict = recModAliases()
   inTab = r'F:\Working\RecMod\Outputs\VA_RecMod_WGS\VA_RecMod.gdb\RecreationAccess'
   updateAliases(inTab, fldDict)
   
if __name__ == '__main__':
   main()