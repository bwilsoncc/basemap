"""
Basemap Toolbox

@author: Brian Wilson <brian@wildsong.biz>
"""
import arcpy
import importlib

import process_basemap_data as pbd
importlib.reload(pbd)
from process_basemap_data import ProcessBasemapData

import stage_basemap_services as sbs
importlib.reload(sbs)
from stage_basemap_services import StageBasemapServices

import release_basemap_services as rbs
importlib.reload(rbs)
from release_basemap_services import ReleaseBasemapServices

import publish_roads as pr
importlib.reload(pr)
from publish_roads import PublishRoads

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of this .pyt file)."""
        self.description = """Sample toolbox containing sample tools."""

        self.label = "Basemap Toolbox"
        self.alias = "BasemapToolbox"  # no special characters including spaces!
        self.description = """Python tools for publishing basemap data."""

        # List of tool classes associated with this toolbox
        self.tools = [
            ProcessBasemapData,
            StageBasemapServices,
            ReleaseBasemapServices,
            PublishRoads
            #Sample_Tool_2
        ]
        return

def list_tools():
    toolbox = Toolbox()
    print("toolbox:", toolbox.label)
    print("description:", toolbox.description)
    print("tools:")
    for t in toolbox.tools:
        tool = t()
        print('  ', tool.label)
        print('   description:', tool.description)
        for param in tool.getParameterInfo():
            print('    ',param.name,':',param.displayName)
        print()


if __name__ == "__main__":
    # Running this as a standalone script lists information about the toolbox and each tool.
    list_tools()
    #exit(0) # This causes the toolbox not to load in ArcGIS Pro. Whatever.

# That's all!
