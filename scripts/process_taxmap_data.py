"""
process_taxmap_data.py

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

def find_my_layers(m : arcpy._mp.Map, workspace: str) -> dict:
    """
    Return a dict of the layers from the map that we need.
    """
    layers = dict()

    # Point at all the required layers. This is a WORK IN PROGRESS, clearly.
    try:
        # Taxmaps data
        layers['taxlots'] = {"layer": m.listLayers('Taxlots')[0], "dest": taxmap_workspace}

    except Exception as e:
        print("Could not read all required layers.", e)
        raise e

    return layers


# ===============================
if __name__ == "__main__":

    cwd = os.getcwd()
    arcpy.env.overwriteOutput = True
    arcpy.env.workspace = "in_memory"

    taxmap_aprx = arcpy.mp.ArcGISProject(Config.TAXMAP_APRX)
    taxmap_workspace = taxmap_aprx.defaultGeodatabase
    maps = taxmap_aprx.listMaps()
    m = taxmap_aprx.listMaps(Config.DATASOURCE_MAP)[0]
    print(f"Project: {Config.TAXMAP_APRX} Workspace:\"{taxmap_workspace}\"\n")
  
    # List the layer names in this map. Helps debug.
    n = 0
    for item in m.listLayers():
        if item.name:
            print(n, item.name)
        n += 1
    
    layers = find_my_layers(m, taxmap_workspace)

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
        print(f"ERRORS: There were errors ({errors} anyway), this is bad.")
        exit(-1)

    print("All done!!")

# That's all!