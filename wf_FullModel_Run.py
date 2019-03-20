# FullModel_Run.py
# Version:  ArcGIS 10.3.1 / Python 2.7.8
# Creation Date: 2019-03-11
# Last Edit: 2019-03-11
# Creator:  Kirsten R. Hazler
#
# Summary:
# Runs each of the workflows for different Recreation Model components.
#
#--------------------------------------------------------------------------------------
from Helper import * 

# Regional Parks
print 'Running regional parks analysis...'
try:
   import wf_RegionalParksAnalysis
   wf_RegionalParksAnalysis.main()
   print 'Regional parks analysis complete.'
except:
   print 'Something went wrong with regional parks analysis.'
   tbackInLoop()

# Local Parks
print 'Running local parks analysis...'
try:
   import wf_LocalParksAnalysis
   wf_LocalParksAnalysis.main()
   print 'Local parks analysis complete.'
except:
   print 'Something went wrong with local parks analysis.'
   tbackInLoop()

# Regional Trails
print 'Running regional trails analysis...'
try:
   import wf_RegionalTrailsAnalysis
   wf_RegionalTrailsAnalysis.main()
   print 'Regional trails analysis complete.'
except:
   print 'Something went wrong with regional trails analysis.'
   tbackInLoop()

# Local Trails
print 'Running local trails analysis...'
try:
   import wf_LocalTrailsAnalysis
   wf_LocalTrailsAnalysis.main()
   print 'Local trails analysis complete.'
except:
   print 'Something went wrong with local trails analysis.'
   tbackInLoop()

# Boating
print 'Running boating analysis...'
try:
   import wf_BoatingAnalysis
   wf_BoatingAnalysis.main()
   print 'Boating analysis complete.'
except:
   print 'Something went wrong with boating analysis.'
   tbackInLoop()

# Fishing
print 'Running fishing analysis...'
try:
   import wf_FishingAnalysis
   wf_FishingAnalysis.main()
   print 'Fishing analysis complete.'
except:
   print 'Something went wrong with fishing analysis.'
   tbackInLoop()

# Swimming
print 'Running swimming analysis...'
try:
   import wf_SwimmingAnalysis
   wf_SwimmingAnalysis.main()
   print 'Swimming analysis complete.'
except:
   print 'Something went wrong with swimming analysis.'
   tbackInLoop()