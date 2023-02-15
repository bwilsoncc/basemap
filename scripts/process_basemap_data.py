"""
process_basemap_data.py

2022-06-30 Tested with Server 10.9.1, ArcGIS Pro 2.9.3

Run this standalone (that is, NOT inside ArcGIS Pro) to download and build feature classes for basemaps
Runs fast in VS Code or run from Python Idle or some other IDE, 

DON'T run it in Arc Pro in a Jupyter notebook, because first it will throw errors over and over
and then when you finally get it to run it will tear out the original layer from the map
and throw away the symbology you spent 3 days working on. You will shed tears.
"""
import os
import arcpy
from utils import listLayers, unsplit_lines
from config import Config


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


def find_my_layers(m : arcpy._mp.Map, workspace: str) -> dict:
    """
    Return a dict of the layers from the map that we need.
    """
    layers = dict()

    # Point at all the required layers.
    try:
        # Basemaps data
        layers['roads'] = {"layer": m.listLayers('Roads')[0], "dest": workspace}
        layers['trail'] = {"layer": m.listLayers('Trails')[0], "dest": workspace}
        layers['water_lines'] = {"layer": m.listLayers('Water lines')[0], "dest": workspace}
        layers['water_polygons'] = {"layer": m.listLayers('Water polygons')[0], "dest": workspace}
        layers['parks'] = {"layer": m.listLayers('Parks')[0], "dest": workspace}
        layers['county_boundary'] = {"layer": m.listLayers('County Boundary')[0], "dest": workspace}

    except Exception as e:
        print("Could not read all required layers.", e)
        raise e

    return layers


# ===============================
if __name__ == "__main__":

    cwd = os.getcwd()
    arcpy.env.overwriteOutput = True

    basemap_aprx = arcpy.mp.ArcGISProject(Config.BASEMAP_APRX)
    basemap_workspace = basemap_aprx.defaultGeodatabase
    maps = basemap_aprx.listMaps()
    m = basemap_aprx.listMaps(Config.DATASOURCE_MAP)[0]
    print(f"Project: {Config.BASEMAP_APRX} Map: \"{m.name}\"")
  
        # List the layer names in this map.
    #listLayers(m)

    layers = find_my_layers(m, basemap_workspace)

    # I tried to set the version I wanted to read here and failed
    # every way possible. 
    # I tried reading the APRX file and failed there too.
    # It worked for a few months. Perhaps after upgrading ArcPro???  
    # No -- it's arcpy installed the wrong way somehow.
    #conn = "k:\\webmaps\\basemap\\cc-gis.sde"
    #arcpy.env.workspace = conn
    #roads = 'Clatsop.DBO.roads'
    #roads_layer = arcpy.management.MakeFeatureLayer('roads', 'roads_layer')
        
    # Show what version is selected on each layer.
    for (ds, layer) in layers.items():
        
        print(f'Source "{ds}":', 
            layer['layer'].connectionProperties['dataset'],
            '  version:', layer['layer'].connectionProperties['connection_info']['version'])

    arcpy.env.workspace = "in_memory"

    # Roads that are unsplit are better for query operations.
    (roads, roads_unsplit) = unsplit_road_lines(layers['roads']['layer'])
    layers["roads_unsplit"] = {"layer": roads_unsplit, "dest": basemap_workspace} # this is used for polylines and queries
    layers['roads'] = {"layer": roads, "dest": basemap_workspace} # this is used for labels
    layers['water_lines'] = {"layer":unsplit_water_lines(layers['water_lines']['layer']), "dest": basemap_workspace}

    # Keep only features with names. No sense in having a popup when it's empty.
    # This is an idea but gives kind of bad feedback when you click and 
    # nothing happens. Better to tell as much as we know.
    #roads_layer = roads_unsplit + '_layer'
    #arcpy.management.MakeFeatureLayer(roads_unsplit, roads_layer, 
    #    where_clause='"StreetName" IS NOT NULL" AND StreetName"!=""'")
    #print("road layer =", arcpy.management.GetCount(roads_layer))
    
    errors = 0
    for (dst,layer) in layers.items():
        try:
            dstpath = os.path.join(layer['dest'], dst)
            src = layer['layer']    
            print("Reprojecting %s to %s" % (src, dstpath))
            arcpy.management.Project(in_dataset=src, out_dataset=dstpath, 
                out_coor_system = Config.WM_SRS, transform_method = Config.TRANSFORMS,
                in_coor_system = Config.LOCAL_SRS,
                preserve_shape="NO_PRESERVE_SHAPE", max_deviation="", vertical="NO_VERTICAL")
        except Exception as e:
            print("Failed!", e)
            errors += 1

    if errors:
        print("There were errors (%d anyway), this is bad." % errors)
        exit(-1)

    print("All done!!")

# That's all!