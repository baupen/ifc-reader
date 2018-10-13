import sys
import numpy as np
import json
import re
import os

ifc_path = sys.argv[1]

def parse_file(text):
    """
    text is the string of the whole file. It will be split at every ";" and then all "\n" will be removed
    """
    tmp = list(map(lambda x: x.replace('\n', ''), text.split(';')))
    output = {}
    for item in tmp:
        if not '=' in item:
            continue
        firstequal = item.find('=')
        identifier = item[:firstequal].strip()
        obj        = item[firstequal+1:].strip()
        output[identifier] = obj
    return output

def get_attributes(string, obj):
    if string in ['IFCCARTESIANPOINT', 'IFCDIRECTION']:
        return [obj[len(string)+1:-1]]
    elif string == 'IFCPOLYLINE':
        return obj[len(string)+2:-2].split(',')
    tmp =  obj[len(string)+1:-1].split(',')
    return tmp


def process_ifccartesianpoint(ifccartesianpoint):
    assert ifccartesianpoint.startswith('IFCCARTESIANPOINT')
    attributes = get_attributes('IFCCARTESIANPOINT', ifccartesianpoint)
    return np.array(eval(attributes[0]))

def process_ifcdirection(ifcdirection):
    assert ifcdirection.startswith('IFCDIRECTION')
    attributes = get_attributes('IFCDIRECTION', ifcdirection)
    return np.array(eval(attributes[0]))

def process_ifcaxis2placement3d(ifcaxis2placement3d):
    assert ifcaxis2placement3d.startswith('IFCAXIS2PLACEMENT3D')
    attributes = get_attributes('IFCAXIS2PLACEMENT3D', ifcaxis2placement3d)

    location = attributes[0]
    axis = attributes[1]
    refDirection = attributes[2]

    location = process_ifccartesianpoint(ifcobjects[location])
    if '$' in axis:
        axis = np.array([0.,0.,1.])
    else:
        axis = process_ifcdirection(ifcobjects[axis])
    if '$' in refDirection:
        refDirection = np.array([1.,0.,0.])
    else:
        refDirection = process_ifcdirection(ifcobjects[refDirection])
    return location

def process_ifcaxis2placement2d(ifcaxis2placement2d):
    assert ifcaxis2placement2d.startswith('IFCAXIS2PLACEMENT2D')
    attributes = get_attributes('IFCAXIS2PLACEMENT2D', ifcaxis2placement2d)

    location = attributes[0]
    refDirection = attributes[1]

    location = process_ifccartesianpoint(ifcobjects[location])
    if '$' in refDirection:
        return location
    else:
        refDirection = process_ifcdirection(ifcobjects[refDirection])

    # it is assumed that the y axis is 90 degrees counter-clock-wise to refDirection
    refDirection = refDirection / np.linalg.norm(refDirection)
    angle = np.arccos(refDirection[0])
    rotationAngle = angle if refDirection[1] < 0 else -1 * angle
    R = np.zeros((2,2))
    cos = np.cos(rotationAngle)
    sin = np.sin(rotationAngle)
    R[0,0] = cos
    R[1,1] = cos
    R[0,1] = -sin
    R[1,0] = sin
    return location, R


def process_ifcaxis2placement(ifcaxis2placement):
    if ifcaxis2placement.startswith('IFCAXIS2PLACEMENT2D'):
        return process_ifcaxis2placement2d(ifcaxis2placement)
    elif ifcaxis2placement.startswith('IFCAXIS2PLACEMENT3D'):
        return process_ifcaxis2placement3d(ifcaxis2placement)
    else:
        assert 0, 'something went horribly wrong with ' + ifcaxis2placement

def process_ifclocalplacement(ifclocalplacement):
    assert ifclocalplacement.startswith('IFCLOCALPLACEMENT'), 'relative origin only works with IFCLOCALPLACEMENT'
    attributes = get_attributes('IFCLOCALPLACEMENT', ifclocalplacement)

    placementRelTo = attributes[0]
    relativePlacemnet = attributes[1]

    if '$' in placementRelTo:
        placementRelTo = np.zeros(3)
    else:
        placementRelTo = process_ifclocalplacement(ifcobjects[placementRelTo])
    
    relativePlacemnet = process_ifcaxis2placement(ifcobjects[relativePlacemnet])

    return placementRelTo + relativePlacemnet


def process_ifcpolyline(ifcpolyline):
    assert ifcpolyline.startswith('IFCPOLYLINE'), ifcpolyline
    attributes = get_attributes('IFCPOLYLINE', ifcpolyline)
    ifccartesianpoints = map(lambda point: ifcobjects[point], attributes)
    points = list(map(lambda ifccartesianpoint: process_ifccartesianpoint(ifccartesianpoint), ifccartesianpoints))
    return points


def process_ifcarbitraryclosedprofiledef(ifcarbitraryclosedprofiledef):
    assert ifcarbitraryclosedprofiledef.startswith('IFCARBITRARYCLOSEDPROFILEDEF'), ifcarbitraryclosedprofiledef
    attributes = get_attributes('IFCARBITRARYCLOSEDPROFILEDEF', ifcarbitraryclosedprofiledef)

    assert attributes[0] == '.AREA.', "at the moment only polygons are supported"
    outercurve = attributes[2]
    return process_ifcpolyline(ifcobjects[outercurve])


def process_ifcrectangleprofiledef(ifcrectangleprofiledef):
    assert ifcrectangleprofiledef.startswith('IFCRECTANGLEPROFILEDEF'), ifcrectangleprofiledef
    attributes = get_attributes('IFCRECTANGLEPROFILEDEF', ifcrectangleprofiledef)
    profileType = attributes[0]
    position = attributes[2]
    xDim = attributes[3]
    yDim = attributes[4]

    assert profileType == '.AREA.', "so far only areas are supported and not " + profileType
    position, rotationMatrix = process_ifcaxis2placement(ifcobjects[position])
    xDim = float(xDim)
    yDim = float(yDim)

    localPoints = [np.array([xDim/2, yDim/2]), np.array([-xDim/2, yDim/2]), np.array([-xDim/2, -yDim/2]), np.array([xDim/2, -yDim/2])]
    
    totalPoints = list(map(lambda x: np.matmul(rotationMatrix,x)+position, localPoints))
    return totalPoints



def process_ifcarbitraryprofiledefwithvoids(ifcarbitraryprofiledefwithvoids):
    assert ifcarbitraryprofiledefwithvoids.startswith('IFCARBITRARYPROFILEDEFWITHVOIDS'), ifcarbitraryprofiledefwithvoids
    attributes = get_attributes('IFCARBITRARYPROFILEDEFWITHVOIDS', ifcarbitraryprofiledefwithvoids)

    profileType = attributes[0]
    profileName = attributes[1]
    outerCurve = attributes[2]
    innerCurves = attributes[3]

    assert profileType == '.AREA.'
    outerCurve = process_ifcpolyline(ifcobjects[outerCurve])
    # for the moment being we don't care about inner curves
    return outerCurve


def process_ifcprofiledef(ifcprofiledef):
    if ifcprofiledef.startswith('IFCARBITRARYCLOSEDPROFILEDEF'):
        return process_ifcarbitraryclosedprofiledef(ifcprofiledef)
    elif ifcprofiledef.startswith('IFCRECTANGLEPROFILEDEF'):
        return process_ifcrectangleprofiledef(ifcprofiledef)
    elif ifcprofiledef.startswith('IFCARBITRARYPROFILEDEFWITHVOIDS'):
        return process_ifcarbitraryprofiledefwithvoids(ifcprofiledef)
    else:
        assert 0, str(ifcprofiledef) + " can't be parsed yet"


def process_ifcextrudedareasolid(ifcextrudedareasolid):
    assert ifcextrudedareasolid.startswith('IFCEXTRUDEDAREASOLID'), ifcextrudedareasolid
    attributes = get_attributes('IFCEXTRUDEDAREASOLID', ifcextrudedareasolid)
    sweptArea = attributes[0]
    position = attributes[1]
    extrudedDirection = attributes[2]
    depth = attributes[3]

    sweptArea = process_ifcprofiledef(ifcobjects[sweptArea])
    position = process_ifcaxis2placement3d(ifcobjects[position])
    assert np.array_equal(position, np.array([0.,0.,0.]))
    extrudedDirection = process_ifcdirection(ifcobjects[extrudedDirection])
    assert np.array_equal(extrudedDirection, np.array([0.,0.,1.]))
    return sweptArea


def process_ifcshaperepresentation(ifcshaperepresentation):
    assert ifcshaperepresentation.startswith('IFCSHAPEREPRESENTATION'), ifcshaperepresentation
    attributes = get_attributes('IFCSHAPEREPRESENTATION', ifcshaperepresentation)
    # in the file we initially got, each shaperepresentation only has one item
    items = attributes[-1]
    return process_ifcextrudedareasolid(ifcobjects[items[1:-1]])


def process_ifcproductrepresentationshape(ifcproductrepresentationshape):
    assert ifcproductrepresentationshape.startswith('IFCPRODUCTDEFINITIONSHAPE'), ifcproductrepresentationshape
    attributes = get_attributes('IFCPRODUCTDEFINITIONSHAPE', ifcproductrepresentationshape)
    
    # In the provided file, each list only has one element
    representations = attributes[2][1:-1]
    return process_ifcshaperepresentation(ifcobjects[representations])
    


def process_ifcproductrepresentation(ifcproductrepresentation):
    if ifcproductrepresentation.startswith('IFCPRODUCTDEFINITIONSHAPE'):
        return process_ifcproductrepresentationshape(ifcproductrepresentation)
    elif ifcproductrepresentation.startswith('IFCMATERIALDEFINITIONREPRESENTATION'):
        assert 0, 'IFCMATERIALDEFINITIONREPRESENTATION not implemented yet'
    else:
        assert 0, 'something went horribly wrong'


def process_ifcspace(ifcspace):
    assert ifcspace.startswith('IFCSPACE'), ifcspace
    attributes = get_attributes('IFCSPACE', ifcspace)

    name = attributes[2]
    objectPlacement = attributes[5]
    representation = attributes[6]
    longName = parse_name(attributes[7])

    objectPlacement = process_ifclocalplacement(ifcobjects[objectPlacement])
    representation = process_ifcproductrepresentation(ifcobjects[representation])

    listofpoints = list(map(lambda x: np.append(x, [0.]) + objectPlacement, representation))
    # remove double points
    if listofpoints[0][0] == listofpoints[len(listofpoints) - 1][0] and listofpoints[0][1] == listofpoints[len(listofpoints) - 1][1]:
        print("found")
        listofpoints = listofpoints[:-1]
    return listofpoints, longName, name


# attempts to remove any invalid chars
def parse_name(name):
    # matches \X2\00FF\X0\
    prog = re.compile(r"\\X2\\"+ "([0-9A-F]{4})" + r"\\X0\\")
    while True:
        result = prog.search(name)
        if not result:
            break
        else:
            # unicode found; replace with correct character
            uni = result.group(1)
            char = chr(int(uni, 16))
            name = name.replace("\\X2\\"+ uni + "\\X0\\", char)
        
    return name

def extractMinMax(spaces):
    minimum = np.ones(3) * np.Inf
    maximum = np.ones(3) * -np.Inf
    for space in spaces:
        for point in space:
            minimum = np.minimum(minimum, point)
            maximum = np.maximum(maximum, point)
    return minimum, maximum


with open(ifc_path, 'r', encoding='utf-8') as ifc:
    global ifcobjects 
    ifcobjects = parse_file(ifc.read())
    
    allspaces = []
    allnames = []
    allidentifiers = []
    for key in ifcobjects:
        if 'IFCSPACE' in ifcobjects[key]:
            listofpoints, name, identifier = process_ifcspace(ifcobjects[key])
            allspaces.append(listofpoints)
            allnames.append(name)
            allidentifiers.append(identifier)
    
    minimum, maximum = extractMinMax(allspaces)
    for i in range(len(allspaces)):
        for j in range(len(allspaces[i])):
            allspaces[i][j] -= minimum
            allspaces[i][j] = np.divide(allspaces[i][j][:2], (maximum-minimum)[:2])

    allobjects = []
    for i in range(len(allspaces)):
        points = list(map(lambda point: {"x":point[0], "y":point[1]}, allspaces[i]))
        allobjects.append({"identifier":allidentifiers[i], "name":allnames[i], "points":points})
    
    with open(ifc_path + ".json", 'w', encoding="utf8") as outfile:
        json.dump(allobjects, outfile, ensure_ascii=False, indent=4)




    # ifcobjects = parse_file(ifc.read())
    # print(ifcobjects['#5'])
    # spaces = []
    # spacesPoints = []
    # names = []    
    # for key in ifcobjects:
    #     if 'IFCSPACE' in ifcobjects[key]: 
    #         spaces.append(key)
    #         tmp1, longName = process_ifcspace(ifcobjects[key])
    #         spacesPoints.append(tmp1)
    #         names.append(longName)
    #         print('\n\n')
    
    # minimum, maximum = extractMinMax(spacesPoints)
    # for i in range(len(spacesPoints)):
    #     for j in range(len(spacesPoints[i])):
    #         spacesPoints[i][j] -= minimum
    #         spacesPoints[i][j] = np.divide(spacesPoints[i][j], maximum-minimum) * 100

    # laufVariable = 0
    # for space in spacesPoints:
    #     print(names[laufVariable])
    #     kleinst = np.ones(2) * 1000
    #     grösst = np.ones(2) * -1
    #     for point in space:
    #         kleinst = np.minimum(kleinst, point[:2])
    #         grösst = np.maximum(grösst, point[:2])
    #     print(kleinst)
    #     print(grösst)
    #     print('\n\n')
    #     laufVariable += 1

    
    #process_ifcspace(ifcobjects[spaces[-1]])
    