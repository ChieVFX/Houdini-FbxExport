# houdini tool
# Setups everything neccessary to export required geometry from one SOP with the existing hierarchy
# create new tool on the tool shelf inside houdini. Choose "Edit tool" and copypaste this code

import hou, os

def displayMessage(msg):
    # hou.ui.displayMessage(msg)
    raise Exception(msg)

def pathToGroup(path):
    return path.replace('/', '_')

def getCreateNode(node, relativePath, nodeType = None, rewrite = False):
    absolutePath = node.path()+"/"+relativePath
    return getCreateNodeAbs(absolutePath, nodeType, rewrite)

#>>>
def getCreateNodeAbs(absolutePath, nodeType = None, rewrite = False):
    def checkForNode(path):
        if hou.node(path) is None:
            raise Exception("No node found via path: " + path)
    node = hou.node(absolutePath)
    if node is not None:
        if not rewrite:
            return node
    if not nodeType:
        return None
    splitPath = absolutePath.split('/') # type: str
    splitPath = filter(bool, splitPath)
    if len(splitPath) == 0:
        raise Exception("Trying to create a node within root! This is prohibited!")
    currentPath = splitPath[0]
    maxIndex = len(splitPath)-1
    node = hou.node("/"+splitPath[0])
    for i, nodeName in enumerate(splitPath):
        if (i==0):
            continue
        if i == maxIndex:
            if rewrite:
                existingNode = node.node(nodeName)
                if existingNode is not None:
                    existingNode.destroy()
            try:
                return node.createNode(nodeType, nodeName)
            except:
                raise Exception("Invalid params: {type:" + nodeType + ", name:" + nodeName+"}")
        currentPath += "/"+nodeName
        node = node.node(nodeName)
        if node is None:
            raise Exception("No node at intermediate path: " + currentPath)
    return None
#<<<-----------------------

#>>>
def setPivotsToCentroids(node, affectThisNode):
    if not isinstance(node, hou.ObjNode):
        raise Exception("'getcenter' functionality is supported only for OBJ nodes at the moment!")

    localToWorldMatrix = node.worldTransform()
    worldToLocalMatrix = localToWorldMatrix.inverted()
    worldToParentLocalMatrix = node.localTransform()

    outputs = node.outputs()

    #center = node.origin()
    geo = None
    isNull = node.userData("IsNull") is not None
    if not isNull:
        try:
            sopNode = node if isinstance(node, hou.SopNode) else node.displayNode()
            geo = sopNode.geometry()
        except:
            geo = None
            isNull = True

    newCenter = hou.Vector3()
    pointOldWorldPositions = {}
    outputsAmount = 0
    if not isNull:
        points = geo.points()
        for point in points:
            pointPos = point.position()
            pointWorldPosition = pointPos * localToWorldMatrix
            newCenter += pointWorldPosition
            pointOldWorldPositions[point] = pointWorldPosition
        outputsAmount += len(points)

    for output in outputs:
        outputCenter = setPivotsToCentroids(output, True)
        newCenter += outputCenter
        # print(output.name() + ": " + outputCenter.__str__())
    outputsAmount = max(1, len(outputs)+outputsAmount)

    if not affectThisNode:
        return node.origin()

    newCenter = newCenter/outputsAmount
    translateMatrix = hou.hmath.buildTranslate(newCenter)
    #translateMatrix *= worldToParentLocalMatrix
    #rotationMatrix = worldToLocalMatrix.extractRotates()
    # scaleMatrix = worldToLocalMatrix.extractScales()
    newWorldToLocalMatrix = translateMatrix#*rotationMatrix#*scaleMatrix
    #node.setParmPivotTransform(newWorldToLocalMatrix)
    #node.setParmTransform(newWorldToLocalMatrix)

    node.setWorldTransform(translateMatrix)
    # if isNull:
    #     node.setWorldTransform(translateMatrix)
    # else:
    #     node.setParmPivotTransform(newWorldToLocalMatrix)

    translateMatrixInvert = translateMatrix.inverted()
    for output in outputs:
        isOutputNull = output.userData("IsNull") is not None
        output.setParmTransform(output.parmTransform()*translateMatrixInvert)
    # geo.transform(newWorldToLocalMatrix)

    # if (geo is not None) and (geo.prims()):
    #     points = geo.points()
    #     for point in points:
    #         point.setPosition(pointOldWorldPositions[point]*newWorldToLocalMatrix)

    return newCenter
#<<<------------------------

root_node_name = "TEMP_FBX"#"temp_export_"

path_to_source_geometry = ""

sop_nodes = []

for n in hou.session.hou.selectedNodes():
    if isinstance(n, hou.SopNode):
        sop_nodes.append(n)

nodeForExport = None
sopNode = None
selection = hou.selectedNodes(True)
if selection is None:
    displayMessage("Selection is null!")
for node in selection:
    if (isinstance(node, hou.ObjNode)):
        nodeForExport = node
        displayNode = node.displayNode()
        if (isinstance(displayNode, hou.SopNode)):
            sopNode = node.displayNode()
            break
    if (isinstance(node, hou.SopNode)):
        nodeForExport = node
        sopNode = node
if sopNode is None:
    displayMessage("No SOP node in selection!")
path_to_source_geometry = sopNode.path()

if not path_to_source_geometry:
    displayMessage("There's no any SOP nodes selected. Please select one.")

#root_node_name += nodeForExport.name()

#!form unique pathes
geo = hou.node(path_to_source_geometry).geometry()
pathAttribute = geo.findPrimAttrib("path")
if (pathAttribute is None):
    displayMessage("No path attribute on prims!")
paths = geo.primStringAttribValues("path")
uniquePaths = [] # type: Array
for path in paths:
    if not path:
        displayMessage("At least one path on prim is empty!")
    if path in uniquePaths:
        continue
    uniquePaths.append(path)

#!sort unique pathes
uniquePaths.sort(key=lambda p:p.count('/'))
if (len(uniquePaths) == 0):
    raise Exception("No unique paths!")

# create root subnet node
objRoot = hou.node("/obj")
#THIS IS TEMPORARY
exportNode = getCreateNode(objRoot, "EXPORT", "subnet")
fbxRoot = getCreateNode(exportNode, root_node_name, "subnet", True)
str_parm = hou.StringParmTemplate("source_path", "Source Path", 1)
if not exportNode.parm('source_path'):
    exportNode.addSpareParmTuple(str_parm, in_folder=("Groups Source",), create_missing_folders=True)
exportNode.parm("source_path").set(path_to_source_geometry)

#! create special node where pipeline the geometry
sourceNode = getCreateNode(exportNode, "source_geometry", "geo")
sourceNode.setDisplayFlag(False)
importNode = getCreateNode(sourceNode, "import", "object_merge")
importNode.parm("objpath1").set(path_to_source_geometry)

#!setup import and groups
amountOfGroups = len(uniquePaths) # type: int
groupExpression = getCreateNode(sourceNode, "group_creation", "groupexpression")
groupExpression.parm("expressions").set(amountOfGroups)
i = 1
for path in uniquePaths:
    groupExpression.parm("groupname"+format(i)).set(pathToGroup(path))
    groupExpression.parm("snippet"+format(i)).set("s@path == \""+path+"\"")
    i = i+1
groupExpression.setFirstInput(importNode)
groupExpression.setDisplayFlag(True)
groupExpression.setRenderFlag(True)
sourceNode.layoutChildren()
sourceGeometry = groupExpression.geometry()

#!create structure
nodes = [] # type: Array
nodeParentRoot = fbxRoot.createNode("null", nodeForExport.name())
for path in uniquePaths: # type: str
    splitPath = path.split('/')
    splitPath = filter(bool, splitPath)
    maxIndex = len(splitPath)-1;
    if (len(splitPath) == 0):
        displayMessage("path does not contain any dirs! " + path)

    # createdNodes = {}

    name = "e" # type: str
    currentPath = ""
    for i, dir in enumerate(splitPath):
        # nodeParent = createdNodes.get(name) fbxRoot.node(name)
        nodeParent = fbxRoot.node(name)
        name += "_"+dir
        currentPath += (dir if (not currentPath) else ("/"+dir))
        node = fbxRoot.node(name)
        if node is None:
            groupName = pathToGroup(currentPath)
            if sourceGeometry.findPrimGroup(groupName):
                node = fbxRoot.createNode("geo", node_name=name)
                geoNode = node.createNode("object_merge", "geometry")
                geoNode.parm("objpath1").set(sourceNode.path())
                geoNode.parm("group1").set(pathToGroup(path))
                geoNode.parm("xformtype").set(1)
            else:
                node = fbxRoot.createNode("null", node_name=name)
                node.setUserData("IsNull", "True")
            nodes.append(node)
            # createdNodes[name] = node
        if nodeParent is not None:
            node.setFirstInput(nodeParent)
        else:
            node.setFirstInput(nodeParentRoot)

    if node is None:
        continue
    # geoNode = node.createNode("object_merge", "imported_geometry")
    # geoNode.parm("objpath1").set(importNode.path())
    # print(path + " : " + pathToGroup(path))
    # geoNode.parm("group1").set(pathToGroup(path))
fbxRoot.layoutChildren()

#!centroids
setPivotsToCentroids(nodeParentRoot, False)

# #! create node contents
# for node in nodes:
#     # create node that we want to create inside
#     sopObjMerge = node.createNode("object_merge", node_name=node.name())
#
#     # change parameter to change
#     sopObjMerge.parm("objpath1").set( path_to_source_geometry )
#     sopObjMerge.parm("group1").set( "group" )

#!fill geometry

#!setup ropnet
ropNet = getCreateNode(exportNode, "ropnet_fbx", "ropnet")
ropFbx = getCreateNode(ropNet, "rop_fbx", "filmboxfbx")
ropFbx.parm("startnode").set(fbxRoot.path())
ropFbx.parm("createsubnetroot").set(False)
defaultOutputPath = "$HIP/out.fbx"
outputPath = None
try:
    outputPath = nodeForExport.parm("export").evalAsString()
except:
    if (hou.ui.displayMessage("Would you like to add 'ExportPath' param?", buttons=("Yes", "No")) == 0):
        exportFileParamName = "export"
        fileTemplate = hou.StringParmTemplate(exportFileParamName, "Fbx Export", 1, default_value=defaultOutputPath,
                                              string_type=hou.stringParmType.FileReference)
        fileExportParm = nodeForExport.addSpareParmTuple(fileTemplate)
        outputPath = hou.ui.selectFile(file_type=hou.fileType.Geometry)
        nodeForExport.parm(exportFileParamName).set(outputPath)
    else:
        print("No 'ExportPath' param found on the object or set. Setting the default output path\n")
if (not outputPath) or (not os.path.isdir(os.path.dirname(outputPath))):
    outputPath = defaultOutputPath
ropFbx.parm("sopoutput").set(outputPath)
ropFbx.parm("execute").pressButton()

exportNode.layoutChildren()