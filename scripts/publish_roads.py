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
    print("Logged in as %s" % str(portal.gis.properties.user.username))

    try:
        aprx = arcpy.mp.ArcGISProject(Config.BASEMAP_APRX)
    except Exception as e:
        print("Can't open APRX file,", e)
        exit(-1)

    initials = os.environ.get("USERNAME")[0:2].upper()
    textmark = datetime.datetime.now().strftime("%m/%d/%y %H:%M") + " " + initials

    mapd = {
        "name": "Roads Test",
        "description": f"""<p>Project file: <a href="file:///>{aprx.filePath}</a><br />
        {Config.DOC_LINK} Script: <a href="https://github.com/bwilsoncc/basemap/blob/main/scripts/{scriptname}">{scriptname}</a><br />
        <em>Updated {textmark}</p></em>""",
        "folder": "Public Works", 
        "pkgname": "Roads",
        "copyData": True,
        "makeFeatures": False, # only make the MIL
    }

    publishMIL(gis, aprx, mapd)

    print("All done!!!")
