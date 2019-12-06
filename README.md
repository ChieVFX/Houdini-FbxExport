# Houdini-FbxExport
Allows you to export the contents of a single SOP as an FBX hierarchy.

Just add the contents of the fbx_export_rc1.py to your shelf as a new tool.

Then the proccess is like this:
0) Make sure prims inside your SOP node have "path" attribute set (example: "left_arm\ring_finger")
1) Select the SOP node
2) Press on the tool (it might ask you where to put the exported file)

The following things then will occur:
1) At the "obj" you'll get a new "EXPORT" subnetwork node, containing your fbx insides
2) An exported FBX file will be created in $HIP folder

Currently there is no way to set the pivots of parts, so they're set to centroids.