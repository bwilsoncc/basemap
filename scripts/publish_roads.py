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
        return [initials, textmark]

    def isLicensed(self) -> bool:
        return True

    def updateParameters(self, parameters) -> None:
        return

    def updateMessages(self, parameters) -> None:
        return

    def execute(self, params, messages) -> None:

        # UGH, this is wrong, fix
        arcpy.env.workspace = Config.SCRATCH_WORKSPACE
        gis = GIS(Config.PORTAL_URL, Config.PORTAL_USER, Config.PORTAL_PASSWORD)
        portal = PortalContent(gis)
        print("Logged in as %s" % str(portal.gis.properties.user.username))
        try:
            aprx = arcpy.mp.ArcGISProject(Config.BASEMAP_APRX)
        except Exception as e:
            print("Can't open APRX file,", e)
            return

        initials = params[0].value
        textmark = params[1].value
        
        script_url = f'{Config.GIT_BASE}blob/main/scripts/{self.scriptname}'
        description = f"""<p>Project file: <a href="file:///{aprx.filePath}">{aprx.filePath}</a><br />
                {Config.DOC_LINK} Script: <a href="{script_url}{self.scriptname}">{self.scriptname}</a><br />
                <em>Updated {textmark}</p></em>"""
        maps = [
            {
                "name": "Roads",
                "servicename": "Roads_Test",
                "description": description,
                "folder": "Public Works", 
                "pkgname": "Roads",
                "copyData": False,
                "makeFeatures": False, # also make feature service | only make the MIL
            },
            {
                "name": "Roads",
                "servicename": "Roads_Test",
                "description": description,
                "folder": "Public Works", 
                "pkgname": "Roads_registered",
                "copyData": False,
                "makeFeatures": False, # also make feature service | only make the MIL
            },
            {
                "name": "Roads",
                "servicename": "Roads_Test",
                "description": description,
                "folder": "Public Works", 
                "pkgname": "Roads_registered_features",
                "copyData": False,
                "makeFeatures": True, # also make feature service | only make the MIL
            },
            {
                "name": "Roads",
                "servicename": "Roads_Test",
                "description": description,
                "folder": "Public Works", 
                "pkgname": "Roads_copied",
                "copyData": True,
                "makeFeatures": False, # also make feature service | only make the MIL
            },
            {
                "name": "Roads",
                "servicename": "Roads_Test",
                "description": description,
                "folder": "Public Works", 
                "pkgname": "Roads_copied_features",
                "copyData": True,
                "makeFeatures": True, # also make feature service | only make the MIL
            },
        ]

        for mapd in maps:
            map = aprx.listMaps(mapd['name'])[0]
            try:
                sd_file = BuildSD(map, mapd)
            except Exception as e:
                print(e)
                # Perhaps analysis failed?
                continue
            #PublishFromSD(gis, map, mapd, sd_file)

            return
    
# ==========================================================================
if __name__ == "__main__":
    class Messenger(object):
        def addMessage(self, message: str) -> None:
            print(message)
            return
 
    print(os.getcwd())

    pubroads = PublishRoads()
    params = pubroads.getParameterInfo()
    pubroads.execute(params, Messenger)

    print("All done!!!")
