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
from config import Config
from scripts.portal import PortalContent

sys.path.insert(0,'')

# ==========================================================================
if __name__ == "__main__":

    (scriptpath, scriptname) = os.path.split(__file__)

    initials = os.environ.get("USERNAME")[0:2].upper()
    textmark = datetime.datetime.now().strftime("%m/%d/%y %H:%M") + " " + initials
    arcpy.env.workspace = Config.SCRATCH_WORKSPACE

    gis = GIS(Config.PORTAL_URL, Config.PORTAL_USER, Config.PORTAL_PASSWORD)
    portal = PortalContent(gis)
    print("%s Logged in as %s" % (textmark, str(portal.gis.properties.user.username)))

    try:
        aprx = arcpy.mp.ArcGISProject(Config.BASEMAP_APRX)
    except Exception as e:
        print("Can't open APRX file,", e)
        exit(-1)

    layer_desc = """<p>Feature layers: Roads, Roads by Jurisdiction, Trails /></p>
    <p>It is in WEB MERCATOR projection.</p>"""
    project_desc = '<p>Project file: "%s"' % aprx.filePath
    mapd = {
        "mapname": "Roads",
        "description": layer_desc + project_desc + "<br />" + Config.DOC_LINK,
        "folder": "Public Works", 
        "pkgname": "Roads",
        'makeFeatures': False, # only make the MIL
    }

    try:
        publishMIL(gis, mapd)

    except Exception as e:
        print("Could not generate service.", e)
        if e.args[0].startswith("ERROR 001117"):
            print(f'ERROR: Open the APRX file in ArcGIS Pro and put a description in properties.')
            
    print("All done!!!")
