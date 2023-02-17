"""
publish_roads.py

Publish the roads feature class from the Roads map in basemap.aprx.
It will be a Map Image Layer and the "Roads" layer therein will
be queryable (but invisible), so that we can generate meaningful popups.
There is also a layer "Roads by Jurisdiction", it is symbolized by jurisdiction.
"""
import os, sys
import datetime
import arcpy
from arcgis.gis import GIS
from scripts.publish_MIL import publishMIL
from scripts.portal import PortalContent
from config import Config

sys.path.insert(0,'')

# ==========================================================================
if __name__ == "__main__":

    (scriptpath, scriptname) = os.path.split(__file__)
    arcpy.env.workspace = Config.SCRATCH_WORKSPACE

    gis = GIS(Config.PORTAL_URL, Config.PORTAL_USER, Config.PORTAL_PASSWORD)
    portal = PortalContent(gis)
    print("Logged in as", str(portal.gis.properties.user.username))

    try:
        aprx = arcpy.mp.ArcGISProject(Config.BASEMAP_APRX)
    except Exception as e:
        print("Can't open APRX file,", e)
        exit(-1)

    initials = os.environ.get("USERNAME")[0:2].upper()
    textmark = datetime.datetime.now().strftime("%m/%d/%y %H:%M") + " " + initials

    mapd = {
        "name": "Taxlot Queries",
        "description": f"""<p>Project file: "{aprx.filePath}" Script: {scriptname}<br />
        <Updated <b>{textmark}</b> {Config.DOC_LINK}</p>""",
        "folder": "Taxmaps", 
        "pkgname": "Taxlot_Queries",
        "copyData": False,
        "makeFeatures": True, # Also make a feature layer collection
    }
    try:
        publishMIL(gis, aprx, mapd)

    except Exception as e:
        print("Could not generate service.", e)
        if e.args[0].startswith("ERROR 001117"):
            print(f'ERROR: Open the APRX file in ArcGIS Pro and put a description in properties.')
            
    print("All done!!!")
