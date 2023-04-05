"""
process_basemap_data.py

2022-06-30 Tested with Server 10.9.1, ArcGIS Pro 2.9.3

Run this standalone (that is, NOT inside ArcGIS Pro) to download and build feature classes for basemaps
Runs fast in VS Code or run from Python Idle or some other IDE, 

DON'T run it in Arc Pro in a Jupyter notebook, because first it will throw errors over and over
and then when you finally get it to run it will tear out the original layer from the map
and throw away the symbology you spent 3 days working on. You will shed tears.
"""
import sys, os
import arcpy
from config import Config

class ProcessBasemapData(object):

    def __init__(self) -> None:
        self.label = "Process Basemap Data"
        self.description = """Prepare data for webmaps."""
        self.canRunInBackground = False
        self.category = "CCPublish"
        #self.stylesheet = "" # I don't know how to use this yet.
        return

    def getParameterInfo(self) -> list:
        """
        I suppose I could let the user specify  something here, with good defaults.
        Just to give more info on what will happen?
        """
        map = arcpy.Parameter(
            name="map",
            displayName="Map",
            datatype=["GPString","GPMap"],
            parameterType="Required", # Required|Optional|Derived
            direction="Input", # Input|Output
        )
        map.value = Config.DATASOURCE_MAP

        # I suppose defining the layers here could be useful?
        # Roads
        # Trails
        # Water_Lines
        # Water polygons
        # Parks
        # County Boundary

        # params[1] = FGDB workspace
        workspace = arcpy.Parameter(
            name="workspace",
            displayName="Destination for reprojected data",
            datatype="DEWorkspace",
            parameterType="Required", # Required|Optional|Derived
            direction="Input", # Input|Output
        )
        workspace.value = "Basemap.gdb"

        return [map, workspace]

    def isLicensed(self) -> bool:
        return True

    def updateParameters(self, parameters) -> None:
        return

    def updateMessages(self, parameters) -> None:
        return

    def execute(self, params, messages) -> None:
        map = params[0].value
        try:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
        except Exception as e:
            arcpy.AddMessage(f"Could not use CURRENT. {e}")
            aprx = arcpy.mp.ArcGISProject(Config.BASEMAP_APRX)       
        try:
            m = aprx.listMaps(map)[0]
        except Exception as e:
            arcpy.AddError(f"Could not use map. {e}")

        workspace = params[1].valueAsText

        arcpy.AddMessage(f'"{m.name}" is {type(m)} and {workspace} is {type(workspace)}')

    
        layers = find_my_layers(m, workspace)

        # I tried to set the version I wanted to read here and failed
        # Show what version is selected on each layer.
        for (ds, layer) in layers.items():
            arcpy.AddMessage(f'Source "{ds}": {layer["layer"].connectionProperties["dataset"]}')
            arcpy.AddMessage(f'version: {layer["layer"].connectionProperties["connection_info"]["version"]}')

        arcpy.env.workspace = "in_memory"

        # Roads that are unsplit are better for query operations.
        (roads, roads_unsplit) = unsplit_road_lines(layers['roads']['layer'])
        layers["roads_unsplit"] = {"layer": roads_unsplit, "dest": basemap_workspace} # this is used for polylines and queries
        layers['roads'] = {"layer": roads, "dest": basemap_workspace} # this is used for labels
        layers['water_lines'] = {"layer":unsplit_water_lines(layers['water_lines']['layer']), "dest": basemap_workspace}

        errors = 0
        for (dst,layer) in layers.items():
            try:
                dstpath = os.path.join(layer['dest'], dst)
                src = layer['layer']    
                arcpy.AddMessage(f"Reprojecting {src} to {dstpath}")
                arcpy.management.Project(in_dataset=src, out_dataset=dstpath, 
                    out_coor_system = Config.WM_SRS, transform_method = Config.TRANSFORMS,
                    in_coor_system = Config.LOCAL_SRS,
                    preserve_shape="NO_PRESERVE_SHAPE", max_deviation="", vertical="NO_VERTICAL")
            except Exception as e:
                arcpy.AddMessage(f"Failed! {e}")
                errors += 1

        if errors:
            arcpy.AddError("There were errors (%d anyway), this is bad." % errors)

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
    ll = m.listLayers()

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
    class Messenger(object):
        def addMessage(self, message: str) -> None:
            print(message)
            return
 
    arcpy.env.overwriteOutput = True

    assert(arcpy.Exists(Config.BASEMAP_APRX))
    basemap_aprx = arcpy.mp.ArcGISProject(Config.BASEMAP_APRX)
    basemap_workspace = basemap_aprx.defaultGeodatabase
    m = basemap_aprx.listMaps(Config.DATASOURCE_MAP)[0]
    print(f"Project: {Config.BASEMAP_APRX} Map: \"{m.name}\"")

    pbd = ProcessBasemapData()
    params = pbd.getParameterInfo()
    arcpy.SetParameter(0, m)
    pbd.execute(params, Messenger)

    print("All done!!")

# That's all!