""" 
Most of the code that used to be here was really portal related so it moved to portal.py today.
"""
import arcpy
from arcgis.gis import GIS
from config import Config


def listLayers(m: arcpy._mp.Map) -> None:
    all_layers = m.listLayers()
    n = 0
    for item in all_layers:
        if item.isFeatureLayer and item.name:
            print(n, item.name)
        n += 1
    return


def unsplit_lines(src_layer, dissolve_attribute_list=None, attributes=None) -> tuple:
    """
    Copy then unsplit (like 'dissolve' but for line features)

    Doing copy because this feature class won't go through otherwise due to errors about participating in a topology maybe

    Unsplitting has the side effect of getting rid of attributes;
    list the ones you want to preserve in 'attributes'
    """
    assert(src_layer.isFeatureLayer)
    scratch = (src_layer.name + "_2913").replace(' ', '_')
    try:
        arcpy.management.CopyFeatures(src_layer, scratch)
        print("\"%s\" feature count = %s" % (scratch, arcpy.management.GetCount(scratch)))
    except Exception as e:
        print("Download of \"%s\" failed." % src_layer.name, e)
    assert(arcpy.Exists(scratch))

    print("Unsplitting %s." % scratch)
    dissolved = scratch + "_unsplit"
    arcpy.management.UnsplitLine(scratch, dissolved, 
        dissolve_attribute_list, # dissolve on these -- the attributes will be preserved
        attributes # list other attributes that you want to preserve here
    )
    print("Unsplit feature count =", arcpy.management.GetCount(dissolved))

    # Unsplit changed all the attributes, now change them back!
    for old_name, stat_field in attributes:
        new_name = stat_field + "_" + old_name
        results = arcpy.management.AlterField(in_table= dissolved, field= new_name, new_field_name= old_name.lower(), new_field_alias= old_name)

    return (scratch, dissolved)


##################################################################################
if __name__ == "__main__":
    # unit test

    aprx = arcpy.mp.ArcGISProject(Config.BASEMAP_APRX)
    m = aprx.listMaps(Config.DATASOURCE_MAP)[0]
    listLayers(m)

    gis = GIS(Config.PORTAL_URL, Config.PORTAL_USER, Config.PORTAL_PASSWORD)
    print("Logged in as " + str(gis.properties.user.username))

    print("MORE TESTS NEEDED HERE.")
    unsplit_lines()

    print("Unit tests done.")
