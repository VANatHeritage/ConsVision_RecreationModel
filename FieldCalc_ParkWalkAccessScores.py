# ---------------------------------------------------------------------------
# FieldCalc_ParkWalkAccessScores.py
# Version:  Version: ArcPro / Python 3+
# Creation Date: 2020-09-17
# Last Edit: 2020-09-25
# Creator:  Kirsten R. Hazler

# Summary:
# Set of field calculator code blocks for different scoring options. Copy/paste the desired scoring definition into the field calculator code block box, then add the appropriate expression to run it. This is a temporary file. Once we have finalized the scoring option, we can incorporate it into a formal script/workflow, and delete this file.

# Each scoring definition takes the following parameters:
# - pop: The population NOT served (e.g., the population not within a 10-minute walk)
# - time: The average travel time to the nearest resource (e.g., time in minutes to walk to nearest park)
# - minority: The percent of the population classified as a racial minority
# - poverty: The percent of households below the poverty line
# ---------------------------------------------------------------------------

def ParkWalkScore1a(pop, time, minority, poverty):
   # equity adjustment factor
   e = 1 + (minority + poverty)/200

   # adjusted population
   apop = e*pop

   # population score
   if apop <= 5:
      ps = 1
   elif apop <= 50:
      ps = 2
   elif apop <= 250:
      ps = 3
   elif apop <= 500:
      ps = 4
   else: 
      ps = 5
    
   # time score for walking
   if time <= 5:
      ts = 1
   elif time <= 10:
      ts = 2
   elif time <= 15:
      ts = 3
   elif time <= 20:
      ts = 4
   else:
      ts = 5
     
   s = int(0.5 + math.sqrt(ts * ps))

   return s
   
def ParkWalkScore1b(pop, time, minority, poverty):
   # equity adjustment factor
   e = 1 + (minority+poverty)/200

   # adjusted population
   apop = e*pop

   # population score
   if apop <= 10:
      ps = 1
   elif apop <= 100:
      ps = 2
   elif apop <= 500:
      ps = 3
   elif apop <= 1000:
      ps = 4
   else: 
      ps = 5
    
   # time score for walking
   if time <= 5:
      ts = 1
   elif time <= 10:
      ts = 2
   elif time <= 15:
      ts = 3
   elif time <= 20:
      ts = 4
   else:
      ts = 5
     
   s = int(0.5 + math.sqrt(ts * ps))

   return s
   
def ParkWalkScore2a(pop, time, minority, poverty):
   # equity adjustment factor
   e = (minority + poverty)/200
   
   # time adjustment factor
   if time == 0:
      t = -0.5
   else:
      t = -(math.log(10/time))/2 # for walk time
   if t > 0.5:
      t = 0.5
   elif t < -0.5:
      t = -0.5
   else:
      pass

   # adjusted population
   apop = (1 + e + t)*pop
   if apop < 0:
      apop = 0

   # access need score
   if apop <= 5:
      s = 1
   elif apop <= 50:
      s = 2
   elif apop <= 250:
      s = 3
   elif apop <= 500:
      s = 4
   else: 
      s = 5
    
   return s
   
def ParkWalkScore2b(pop, time, minority, poverty):
   # equity adjustment factor
   e = (minority + poverty)/200
   
   # time adjustment factor
   if time == 0:
      t = -0.5
   else:
      t = -(math.log(10/time))/2 # for walk time
   if t > 0.5:
      t = 0.5
   elif t < -0.5:
      t = -0.5
   else:
      pass

   # adjusted population
   apop = (1 + e + t)*pop
   if apop < 0:
      apop = 0

   # access need score
   if apop <= 10:
      s = 1
   elif apop <= 100:
      s = 2
   elif apop <= 500:
      s = 3
   elif apop <= 1000:
      s = 4
   else: 
      s = 5
    
   return s
   
def ParkWalkScore2c(pop, time, minority, poverty):
   # equity adjustment factor
   e = (minority + poverty)/200
   
   # time adjustment factor
   if time == 0:
      t = -0.5
   else:
      t = -(math.log(10/time))/2 # for walk time
   if t > 0.5:
      t = 0.5
   elif t < -0.5:
      t = -0.5
   else:
      pass

   # adjusted population
   apop = (1 + e + t)*pop
   if apop < 0:
      apop = 0

   # access need score
   if apop <= 50:
      s = 1
   elif apop <= 250:
      s = 2
   elif apop <= 1250:
      s = 3
   elif apop <= 6250:
      s = 4
   else: 
      s = 5
    
   return s
   
def ParkWalkScore2d(pop, time, minority, poverty):
   # equity adjustment factor
   e = (minority + poverty)/200
   
   # time adjustment factor
   if time == 0:
      t = -0.5
   else:
      t = -(math.log(10/time))/2 # for walk time
   if t > 0.5:
      t = 0.5
   elif t < -0.5:
      t = -0.5
   else:
      pass

   # adjusted population
   apop = (1 + e + t)*pop
   if apop < 0:
      apop = 0

   # access need score
   if apop <= 50:
      s = 1
   elif apop <= 250:
      s = 2
   elif apop <= 1000:
      s = 3
   elif apop <= 3000:
      s = 4
   else: 
      s = 5
    
   return s

def ParkWalkScore3c(pop, time, minority, poverty):
   # equity adjustment factor
   e = (minority + poverty)/200
   
   # time adjustment factor
   if time < 5:
      time = 5
   elif time > 30:
      time = 30
   else:
      pass
   
   t = -(math.log(5/time))/2 

   # adjusted population
   apop = (1 + e + t)*pop
   if apop < 0:
      apop = 0

   # access need score
   if apop <= 50:
      s = 1
   elif apop <= 250:
      s = 2
   elif apop <= 1250:
      s = 3
   elif apop <= 6250:
      s = 4
   else: 
      s = 5
    
   return s