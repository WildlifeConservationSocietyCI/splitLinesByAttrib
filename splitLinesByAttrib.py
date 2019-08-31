# ---------------------------------------------------------------------------
# splitLinesByAttrib.py
# Script to iterate through polyline feature class and create output point feature class with points at equal intervals along line features, number determined by attribute value
# Assumes projected/linear units. Projection of output points set to that of input lines.
# Ignores features with numSegments attrib = 0
# Todo: make work with geodatabases; determine reliability with non-projected coordinate system; add ability to carry over polyline attributes
# 0.1 KF 04.04.10 Basic script
# 0.2 KF 04.08.10 Changed first param to input directory over which the feature classes are iterated
#                 Fixed output overwrite, added some error-checking, did some refactoring
#                 Added optional prohibition of duplicate points
# ---------------------------------------------------------------------------

# Setup
import arcgisscripting, os, utilities as util
gp = arcgisscripting.create(9.3)
gp.overWriteOutput = 1

# Inputs
inLinesDir = gp.GetParameterAsText(0)
numSegmentsAttrib = gp.GetParameterAsText(1)
outPointsDir = gp.GetParameterAsText(2)
allowDuplicatePoints = gp.GetParameter(3)

# Set workspace to input polyline FC dir and loop over the FCs therein
gp.Workspace = inLinesDir
inLinesFCs = gp.ListFeatureClasses()
for inLines in inLinesFCs:

  # Input polyline FC basic properties
  desc = gp.Describe(inLines)
  
  # Only proceed if the FC has polylines and has an attribute named that specified by numSegmentsAttrib
  if (desc.ShapeType == "Polyline" and util.fieldInFieldList(numSegmentsAttrib, gp.ListFields(inLines))):
    
    # Create output FC to hold points and create insert cursor for it
    outPoints = outPointsDir + os.sep + os.path.basename(inLines).replace('.shp', 'Points.shp') # if input is shapefile
    if outPoints[-4:] != '.shp': outPoints += 'Points.shp' # if input is not a shapefile
    if gp.Exists(outPoints): gp.Delete(outPoints)
    gp.CreateFeatureClass(outPointsDir, os.path.basename(outPoints), "Point", "", "", "", desc.SpatialReference)
    gp.AddMessage("Creating points in " + os.path.basename(outPoints) + " from lines in " + inLines)
    cur = gp.InsertCursor(outPoints)
    
    # Initialization
    pid = 0
    point = gp.CreateObject("Point")
    if (not allowDuplicatePoints): pointList = []
    
    # Iterate over polyline FC
    rows = gp.SearchCursor(inLines)
    row = rows.Next()
    while row:
      #gp.AddMessage("Feature " + str(row.getvalue(desc.OIDFieldName)) + ":")
      numSegments = row.GetValue(numSegmentsAttrib)
      #gp.AddMessage("Number of segments: " + str(numSegments))
      if numSegments > 0:
        # Create the polyline geometry object
        feat = row.GetValue(desc.ShapeFieldName)
        
        # Enter while loop for each part in the feature (if a singlepart feature this will occur only once)
        partnum = 0
        while partnum < feat.PartCount:
          #gp.AddMessage("Part " + str(partnum) + ":")
          part = feat.GetPart(partnum)
          
          # Deal with first point of segment
          pnt = part.Next()
          lastpnt = pnt
          
          # Set new point feature's properties
          point.id = pid
          point.x = pnt.x
          point.y = pnt.y
            
          # Only add a point if we don't care about duplicate points, or we do care but the point's coordinates don't exist in the list yet
          if (allowDuplicatePoints or (not allowDuplicatePoints and not util.pointInList([pnt.x, pnt.y], pointList))):
            # Create and insert new point feature
            newPt = cur.NewRow()
            newPt.shape = point
            cur.InsertRow(newPt)
            
            pid += 1
            if (not allowDuplicatePoints): pointList.append([pnt.x, pnt.y])
      
          # Enter while loop for each vertex
          while pnt:
            #gp.AddMessage('pnt: ' + str(pnt.x) + ',' + str(pnt.y))
            if pnt != lastpnt: 
              #gp.AddMessage('lastpnt: ' + str(lastpnt.x) + ',' + str(lastpnt.y))
              # Figure individual x and y distance components by dividing distance between lastpnt and pnt by # of segments
              distX = (pnt.x - lastpnt.x) / numSegments
              distY = (pnt.y - lastpnt.y) / numSegments
              
              # Loop over # of segments and create new point for each with x and y set to last one plus div distance
              seg = 1
              while seg <= numSegments:
                # Set new point feature's properties
                point.id = pid
                point.x = lastpnt.x + (distX * seg)
                point.y = lastpnt.y + (distY * seg)
                
                # Only add a point if we don't care about duplicate points, or we do care but the point's coordinates don't exist in the list yet
                if (allowDuplicatePoints or (not allowDuplicatePoints and not util.pointInList([point.x, point.y], pointList))):
                  # Create and insert new point feature
                  newPt = cur.NewRow()
                  newPt.shape = point
                  cur.InsertRow(newPt)
                  
                  pid += 1
                  if (not allowDuplicatePoints): pointList.append([point.x, point.y])
                
                seg += 1
      
              lastpnt = pnt
              
            pnt = part.Next()
            # If pnt is null, part is finished
            if not pnt: pnt = part.Next()
      
          partnum += 1
      
      row = rows.Next()
      #gp.AddMessage(str(pointList))
    del cur
