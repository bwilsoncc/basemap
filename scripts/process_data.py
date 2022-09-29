"""
process_data.py

2022-06-30 Tested with Server 10.9.1, ArcGIS Pro 2.9.3

Run this standalone (that is, NOT inside ArcGIS Pro) to download and build feature classes for basemaps
Runs fast in VS Code or run from Python Idle or some other IDE, 

DON'T run it in Arc Pro in a Jupyter notebook, because first it will throw errors over and over
and then when you finally get it to run it will tear out the original layer from the map
and throw away the symbology you spent 3 days working on. You will shed tears.
"""
import os
import arcpy
from config import Config

cwd = os.getcwd()
arcpy.env.overwriteOutput = True

def unsplit_lines(src_layer, dissolve_attribute_list=None, attributes=None):
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


def unsplit_road_lines(road_lines_layer):
    # Typically I screw up here by selecting a road and saving the project
    # so, clear selection before copying. Unfortunately a bug prevents it from working.
    road_lines_layer.setSelectionSet() # "select nothing" = clear, supposedly
    set = road_lines_layer.getSelectionSet() 
    if set and len(set):
        # clear fails so we exit
        print("There is a selection set in roads, this will mess us up.")
        exit(-1)

    # We unsplit on the Owner attribute so that the "Roads by Jurisdiction" feature will work.
    road_attributes = [
                #["Street", "FIRST"],    # 8TH ST      best for vector maps
                #["Name", "FIRST"],      # 8th
                #["Type", "FIRST"],      # St
                ["Alias", "FIRST"],      # HWY 101 -- used for creating highway shields; sometimes a street has a name like Roosevelt Dr and an alias like HWY 101 
                ["Surface", "FIRST"], 
    ]
    (roads, roads_unsplit) = unsplit_lines(road_lines_layer,
        dissolve_attribute_list= ["StreetName", "FunClassM", "FunClassD", "Owner"], # dissolve on these -- attributes will be preserved but renamed first_*
        attributes = road_attributes # list other attributes that you want to preserve here
    )
    roads_count= arcpy.management.GetCount(roads)
    print("There are %s roads." % roads_count)

    arcpy.management.CalculateField(roads_unsplit, \
        "Miles", "Round(Length($feature, \"miles\"),2)", "ARCADE", field_type="DOUBLE")

    return roads, roads_unsplit


def unsplit_water_lines(water_lines_layer):
    # Unsplitting water lines have 0 useful names,
    # but doing this does remove unwanted attributes.
    (water_lines, water_unsplit) = unsplit_lines(water_lines_layer,
        dissolve_attribute_list= [#"WaterName",
            "LineType", "MapScale"], # dissolve on these -- the attributes will be preserved
        attributes = [] # list other attributes that you want to preserve here
    )
    water_layer_name = water_unsplit + '_layer'
    # Keep only River, Creek, Canal
    water_layer = arcpy.management.MakeFeatureLayer(water_unsplit,
        water_layer_name, 
        where_clause='"LineType"=24 OR "LineType"=26 OR "LineType"=28')
    result = arcpy.management.GetCount(water_layer)
    print("There are %s water line features." % result)
#    if water_count < 1000:
#        print("I'm thinking that you have a selection set in the APRX. Fix that.")
    #    exit(-1)
    return water_layer


# ===============================
if __name__ == "__main__":
    # Find the map we are using.
    # Normally version here is set to STAGING
    # so that I don't have to wait for compression.
    # (But if I did any edits I need to do a reconcile/post before running this!)
    aprx = arcpy.mp.ArcGISProject(Config.APRX_FILE)
    m = aprx.listMaps(Config.MAPNAME)[0]
    print(f"project: {Config.APRX_FILE} map: {m.name}")

    # Find the file geodatabase to use as the destination.
    fgdb = aprx.defaultGeodatabase
    print("gdb:", fgdb)

    # List the layer names, just a sanity check.
    all_layers = m.listLayers()
    n = 0
    for item in all_layers:
        if item.isFeatureLayer and item.name:
            print(n, item.name)
        n += 1

    # Point at all the required layers.
    try:
        road_lines_layer = m.listLayers('Roads')[0]
        water_lines_layer = m.listLayers('Water lines')[0]
        water_polygons_layer = m.listLayers('Water polygons')[0]
        parks_layer = m.listLayers('Parks')[0]
        county_boundary_layer = m.listLayers('County Boundary')[0]
    except Exception as e:
        print("Could not read all required layers.", e)
        exit(-1)

    # I tried to set the version I wanted to read here and failed
    # every way possible. 

    # I tried reading the APRX file and failed there too.
    # It worked for a few months. Perhaps after upgrading ArcPro???  
    # No -- it's arcpy installed the wrong way somehow.
    #conn = "k:\\webmaps\\basemap\\cc-gis.sde"
    #arcpy.env.workspace = conn
    #roads = 'Clatsop.DBO.roads'
    #roads_layer = arcpy.management.MakeFeatureLayer('roads', 'roads_layer')
        
    # Sanity check -- show what version is selected.
    print("Roads dataset:", road_lines_layer.connectionProperties['dataset'])
    print("version:", road_lines_layer.connectionProperties['connection_info']['version'])

    print("Water dataset:", water_lines_layer.connectionProperties['dataset'])
    print("version:", water_lines_layer.connectionProperties['connection_info']['version'])

    arcpy.env.workspace = "in_memory"

    # Roads that are unsplit are better for query operations.
    (roads, roads_unsplit) = unsplit_road_lines(road_lines_layer)
    water_layer = unsplit_water_lines(water_lines_layer)

    # Keep only features with names. No sense in having a popup when it's empty.
    # This is an idea but gives kind of bad feedback when you click and 
    # nothing happens. Better to tell as much as we know.
    #roads_layer = roads_unsplit + '_layer'
    #arcpy.management.MakeFeatureLayer(roads_unsplit, roads_layer, 
    #    where_clause='"StreetName" IS NOT NULL" AND StreetName"!=""'")
    #print("road layer =", arcpy.management.GetCount(roads_layer))

    layers = [
        (roads_unsplit, "roads_unsplit"), # this is used for polylines and queries
        (roads, "roads"), # this is used for labels

        (water_layer, "water_lines"),
        (water_polygons_layer, "water_polygons"),

        (parks_layer, "parks"),

        (county_boundary_layer, "county_boundary")
    ]
    errors = 0
    for (src,dst) in layers:
        try:
            dst = os.path.join(fgdb, dst)
            print("Reprojecting %s to %s" % (src, dst))
            arcpy.management.Project(in_dataset=src, out_dataset=dst, 
                out_coor_system = Config.WM_SRS, transform_method = Config.TRANSFORMS,
                in_coor_system = Config.LOCAL_SRS,
                preserve_shape="NO_PRESERVE_SHAPE", max_deviation="", vertical="NO_VERTICAL")
        except Exception as e:
            print("Failed!", e)
            errors += 1

    if errors:
        print("There were errors (%d anyway), this is bad." % errors)
        exit(-1)

    # Some random debug code that I could delete, 
    # just shows the fields in "roads_unsplit".
    dissolved = os.path.join(fgdb, 'roads_unsplit')
    desc =  arcpy.Describe(dissolved)
    fields = [(f.name, f.aliasName, f.baseName) for f in desc.fields]
    print(fields)

    print("All done!!")

# That's all!