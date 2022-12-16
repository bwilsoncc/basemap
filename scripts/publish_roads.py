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
from config import Config
from scripts.portal import PortalContent, show
sys.path.insert(0,'')
from utils import getServiceItem

def find_map(aprx, mapname):
    maps = aprx.listMaps(mapname)
    if len(maps) != 1:
        return None
    return maps[0]


def create_service_definition(map: object, item: dict, folder: str, sd_file: str):
    """
    Create an sd file named "sd_file".
    """
    # https://pro.arcgis.com/en/pro-app/2.9/arcpy/mapping/map-class.htm
    # (It's possible to pass a layerlist here to limit what gets published)
    sddraft = map.getWebLayerSharingDraft(
        server_type="FEDERATED_SERVER",
        service_type="MAP_IMAGE",
        service_name=item["pkgname"],
    )

    sddraft.federatedServerUrl = Config.SERVER_URL
    sddraft.description = item["description"]
    sddraft.credits = Config.CREDITS
    sddraft.useLimitations = Config.DISCLAIMER_TEXT
    sddraft.tags = ",".join(Config.STAGING_TAG_LIST)
    sddraft.portalFolder = item["folder"]
    # sddraft.summary = "say something here"
    # sddraft.serverFolder
    sddraft.overwriteExistingService = True # WELL THIS FAILS SPECTACULARLY

    # The draft file is an XML file.
    sddraft_file = os.path.join(Config.SCRATCH_WORKSPACE, pkgname + ".sddraft")

    sddraft.exportToSDDraft(sddraft_file)

    if os.path.exists(sd_file):
        #return sd_file # Uncomment this line for faster debugging.
        os.unlink(sd_file)

    print("Creating", sd_file)
    # "Stage" is the Esri verb for "archive with 7Z".
    # The 7z file contains a FGDB and various settings.
    arcpy.server.StageService(sddraft_file, sd_file)

    return


def delete_item(item) -> bool:
    item.protect(enable=False)
    try:
        return item.delete()
    except Exception as e:
        print("Delete failed, ", e)
        # Mysterious huh? See the Wiki, search for ArcGIS Enterprise.
    return False


# ==========================================================================

if __name__ == "__main__":

    (scriptpath, scriptname) = os.path.split(__file__)

    arcpy.env.workspace = Config.SCRATCH_WORKSPACE

    initials = os.environ.get("USERNAME")[0:2].upper()
    textmark = (
        datetime.datetime.now().strftime("%m/%d/%y %H:%M") + " " + initials
    )  # more readable

    portal = GIS(Config.PORTAL_URL, Config.PORTAL_USER, Config.PORTAL_PASSWORD)
    print("%s Logged in as %s" % (textmark, str(portal.properties.user.username)))
    pc = PortalContent(portal)

    try:
        aprx = arcpy.mp.ArcGISProject(Config.BASEMAP_APRX)
    except Exception as e:
        print("Can't open APRX file,", e)
        exit(-1)

    layer_desc = """<p>Feature layers: Roads, Roads by Jurisdiction, Trails /></p>
    <p>It is in WEB MERCATOR projection.</p>"""
    project_desc = '<p>Project file: "%s"' % aprx.filePath

    # The APRX file has to have maps with these mapnames defined.
    mapnames = [
        {
            "mapname": Config.ROAD_MAP,
            "description": """<p>This map is used for queries.</p>"""
            + layer_desc
            + project_desc
            + "<br />" + Config.AUTOGRAPH,
            #"folder": "TESTING_Brian", "pkgname": "DELETEME_" + Config.ROAD_MAP.replace(" ", "_"), # TEST RUN
            "folder": "Public Works", "pkgname": Config.ROAD_MAP.replace(" ", "_"), # SHOWTIME!!!!
        }
    ]

    # Validate the group list
    staging_groups = pc.get_groups(Config.STAGING_GROUP_LIST)

    total = len(mapnames)

    n = 0
    for item in mapnames:
        mapname = item["mapname"]
        pkgname = item["pkgname"]
        n += 1
        progress = "%d/%d" % (n, total)

        map = find_map(aprx, mapname)
        if not map:
            print('ERROR! Map not found in APRX. Skipping "%s".' % mapname)
            continue

        # https://pro.arcgis.com/en/pro-app/2.9/help/sharing/overview/automate-sharing-web-layers.htm

        sd_file = os.path.join(Config.SCRATCH_WORKSPACE, pkgname + ".sd")
        if arcpy.Exists(sd_file):
            print(f"Using existing file \"{sd_file}\".")
        else:
            print(progress, 'Building "%s".' % item["pkgname"])
            
            # 1. Create a service definition draft
            # 2. Stage the service (zip)
            create_service_definition(map, item, item["folder"], sd_file)

        # 3. Upload the service definition
        # THIS WILL DESTROY AN EXISTING SERVICE
        #  * First I should try to update an existing definition.
        #  * If that fails then I create a new one...

        print('Uploading definition using "%s" to "%s" folder.' % (pkgname, item["folder"]))

        # Upload the service definition to SERVER
        # In theory everything needed to publish the service is already in the SD file.
        # https://pro.arcgis.com/en/pro-app/latest/tool-reference/server/upload-service-definition.htm
        # You can override permissions, ownership, groups here too.
        try:
            # in_startupType HAS TO BE "STARTED" else no service is started on the SERVER.
            rval = arcpy.SignInToPortal(Config.PORTAL_URL, Config.PORTAL_USER, Config.PORTAL_PASSWORD)
            rval = arcpy.server.UploadServiceDefinition(sd_file, Config.SERVER_URL, in_startupType="STARTED")

        except Exception as e:
            print("Could not generate service.", e)
            if e.args[0].startswith("ERROR 001117"):
                print(
                    'ERROR. Open the APRX file in ArcGIS Pro and put a description in "%s".'
                    % mapname
                )
                print('Skipping "%s".' % mapname)
            continue

        # Add a comment to the service

        gis = GIS(Config.PORTAL_URL, username=Config.PORTAL_USER, password=Config.PORTAL_PASSWORD)            
        target_item = getServiceItem(gis, PortalContent(gis), pkgname)
        target_item.add_comment("Updated %s" % textmark)
        show(target_item)

    print("All done!!!")
