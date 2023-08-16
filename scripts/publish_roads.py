"""
    publish_roads.py

    Publish the roads feature class from the Roads map in basemap.aprx.
    It will be a Map Image Layer and the "Roads" layer therein will
    be queryable (but invisible), so that we can generate meaningful popups.
    There is also a layer "Roads by Jurisdiction", it is symbolized by jurisdiction.
"""
import os, sys
import arcpy
from arcgis.gis import GIS
from datetime import datetime
from publish_service import BuildSD, PublishFromSD
from portal import PortalContent
from config import Config

mapobj = None # hacky stupid hacky hack hack
class PublishRoads(object):

    def __init__(self) -> None:
        self.label = "Publish Roads"
        self.description = """Roads data has been updated and you need to publish it."""
        self.canRunInBackground = False
        self.category = "CCPublish"

        self.scriptname = 'publish_roads.py'
        #self.stylesheet = "" # I don't know how to use this yet.
        return

    def getParameterInfo(self) -> list:
        map  = arcpy.Parameter(
            name = 'map',
            displayName = 'Map (drag from Catalog)',
            datatype = 'GPMap',
            parameterType='Required',
            direction = 'Input'
        )
 #       map.value = mapobj

        initials  = arcpy.Parameter(
            name = 'initials',
            displayName = 'Your initials',
            datatype = 'GPString',
            parameterType='Required',
            direction = 'Input'
        )
        initials.value = os.environ.get('USERNAME')[0:2].upper()
        
        textmark = arcpy.Parameter(
            name = 'datestamp',
            displayName = 'Date stamp string used in comments.',
            datatype = 'GPString',
            parameterType='Required',
            direction = 'Input'
        )
        textmark.value = datetime.now().strftime("%m/%d/%y %H:%M") + ' ' + initials.value
        return [map, initials, textmark]

    def isLicensed(self) -> bool:
        return True

    def updateParameters(self, parameters) -> None:
        return

    def updateMessages(self, parameters) -> None:
        return

    def execute(self, params, messages) -> None:

        global gis

        map = params[0].value

        # THIS ONLY WORKS IN THE COMNMAND LINE,
        # the parameter setting Esri provides is not a map object so it fails here.

        global mapobj
        if mapobj:
            map = mapobj
        initials = params[1].value
        textmark = params[2].value
        
        script_url = f'{Config.GIT_BASE}blob/main/scripts/{self.scriptname}'
        aprx_link = '' # 'Project file: <a href="file:///{aprx.filePath}">{aprx.filePath}</a><br />'
        description = f"""<p>{aprx_link}
                {Config.DOC_LINK} Script: <a href="{script_url}{self.scriptname}">{self.scriptname}</a><br />
                <em>Updated {textmark}</p></em>"""
        
        title = "Roads_hosted_test" # Set this to a different name when testing.
        #title = "Roads" # The official name

        mapd = {
                "name": "Roads",
                "title": title,
                "pkgname": title,
                "description": description,
                "folder": "Public Works", # server folder
                "copyData": True, # This is "hosted" data
                "makeFeatures": False, # also make feature service | only make the MIL
        }
        
        # Don't need this until actually publishing to the server
        gis = None # Testing build stage without publishing
        gis = GIS(url=Config.PORTAL_URL, profile=Config.PORTAL_PROFILE)
        
        workspace = arcpy.env.workspace

        arcpy.AddMessage(mapd["title"])
        arcpy.AddMessage(f"Our map: {type(map)}")
        try:
            sd_file = os.path.join(workspace, mapd["pkgname"] + ".sd")
            if not os.path.exists(sd_file): # for testing, recycle existing file
                BuildSD(map, mapd, sd_file)
        except Exception as e:
            arcpy.AddMessage(e)
            # Perhaps analysis failed?

        if gis: # for testing don't publish if None
            PublishFromSD(gis, map, mapd, sd_file, textmark)
        
        return
    
# ==========================================================================
if __name__ == "__main__":
    class Messenger(object):
        def addMessage(self, message: str) -> None:
            print(message)
            return

    arcpy.env.workspace = Config.SCRATCH_WORKSPACE

    pubroads = PublishRoads()
    params = pubroads.getParameterInfo()
 
    aprx = arcpy.mp.ArcGISProject(Config.BASEMAP_APRX)
    mapobj = aprx.listMaps('Roads')[0]
    params[0].value = mapobj # This, quite simply, fails.

    pubroads.execute(params, Messenger)

    print("All done!!!")
