"""
    Update the taxlots map image layer,

    1. Reproject latest taxlot data into a local FGDB
    2. Overwrite to Portal
"""
import os, sys
from datetime import datetime
import arcpy
from arcgis.gis import GIS
from config import Config
from scripts.portal import PortalContent, show
sys.path.insert(0,'')
from utils import listLayers, getServiceItem

cwd = os.getcwd()
arcpy.env.overwriteOutput = True

def rebuild_taxlots(src : str, dst_path: str, dst_name : str) -> None:
    errors = 0

    # Ancient of Days takes so LONG to delete one field at a time
    # even when working from a local FGDB in SSD. Oh well. Normally I don't sit and watch.
    # I tried deleting a list of fields but that failed.
    # I tried using a field map but that failed.

    scratch_db = os.path.join(Config.SCRATCH_WORKSPACE, 'scratch.gdb')
    if not arcpy.Exists(scratch_db):
        arcpy.management.CreateFileGDB(Config.SCRATCH_WORKSPACE, "scratch")
    scratch_dst = os.path.join(scratch_db, dst_name)

    try:
        print("Reprojecting %s to %s" % (src, scratch_dst)) # dst cannot be in memory!!
        arcpy.management.Project(in_dataset=src, out_dataset=scratch_dst, 
            out_coor_system = Config.WM_SRS, transform_method = Config.TRANSFORMS,
            in_coor_system = Config.LOCAL_SRS,
            preserve_shape="NO_PRESERVE_SHAPE", max_deviation="", vertical="NO_VERTICAL")
    except Exception as e:
        print("Failed!", e)
        errors += 1

    keepers = [
        'OBJECTID',
        'Taxlot',
        'X_COORD', 'Y_COORD',
        'TAXMAPNUM',
        'TAXLOTKEY',
        'PROPERTY_C',
        'OWNER_LINE',
        'OWNER_LL_1',
        'OWNER_LL_2',
        'STREET_ADD',
        'CITY', 
        'STATE', 
        'ZIP_CODE',
        'SITUS_ADDR',
        'SITUS_CITY',
        'TAXCODE',
        'ACCOUNT_ID',
        'Shape_Length', 'Shape_Area'
    ]
    actual_fields = arcpy.ListFields(scratch_dst, '*')
    deletethese = []
    for f in actual_fields:
        if not f.name in keepers and f.type != 'Geometry':
            deletethese.append(f.name)
    try:
        for field in deletethese:
            print("Deleting", field)
            arcpy.management.DeleteField(scratch_dst, field)
    except Exception as e:
        print(f"WARNING, field delete failed for {field}.", e)

    arcpy.conversion.FeatureClassToFeatureClass(scratch_dst, dst_path, dst_name)
    return errors

def create_service_definition(map: object, item: dict, sd_file: str):
    """
    Create an sd file named "sd_file".
    """
    # https://pro.arcgis.com/en/pro-app/2.9/arcpy/mapping/map-class.htm
    # (It's possible to pass a layerlist here to limit what gets published)
    sddraft = map.getWebLayerSharingDraft(
        server_type="FEDERATED_SERVER",
        service_type="MAP_IMAGE",
        service_name=item["pkgname"],
        # layers_and_tables # I could use this to allow extra layers in the map to be ignored, for example a basemap.
    )

    sddraft.federatedServerUrl = Config.SERVER_URL
    sddraft.description = item["description"]
    sddraft.credits = Config.CREDITS
    sddraft.useLimitations = Config.DISCLAIMER_TEXT
    sddraft.tags = ",".join(Config.STAGING_TAG_LIST) + ',taxlots,parcels'
    sddraft.portalFolder = item["portalFolder"]
    # sddraft.summary = "say something here"
    # sddraft.serverFolder = item["serverFolder"]
    sddraft.overwriteExistingService = True # WELL THIS FAILS SPECTACULARLY

    # The draft file is an XML file.
    sddraft_file = os.path.join(Config.SCRATCH_WORKSPACE, item["pkgname"] + ".sddraft")
    sddraft.exportToSDDraft(sddraft_file)

    if os.path.exists(sd_file):
        return sd_file # Uncomment this line for faster debugging.
        os.unlink(sd_file)

    print("Creating", sd_file)
    # "Stage" is the Esri verb for "archive with 7Z".
    # The 7z file contains a FGDB and various settings.
    arcpy.server.StageService(sddraft_file, sd_file)

    return sd_file


# ===============================
if __name__ == "__main__":

    sdefile = "cc-thesql_SDE.sde"
    taxlots_fc = "Clatsop.DBO.taxlot_accounts"

    taxmap_aprx = arcpy.mp.ArcGISProject(Config.TAXMAP_APRX)
    taxmap_workspace = taxmap_aprx.defaultGeodatabase
    mapname = Config.TAXLOTS_MAP
    m = taxmap_aprx.listMaps(mapname)[0]
    print(f"Project: {Config.TAXMAP_APRX}\nMap: {m.name}")

    # List the layer names in the destination map.
    listLayers(m)

    src = os.path.join(sdefile, taxlots_fc)
    assert(arcpy.Exists(src))
    assert(arcpy.Exists(taxmap_workspace))

    initials = os.environ.get("USERNAME")[0:2].upper()
    textmark = (
        datetime.datetime.now().strftime("%m/%d/%y %H:%M") + " " + initials
    )  # more readable

    dst_name = 'Taxlots_WM'
    #rval = rebuild_taxlots(src, taxmap_workspace, dst_name)
    #if rval>0: exit(-1)

    item = {
        "portalFolder": "TESTING_Brian",
        "description": "Taxlots map image layer",
        "pkgname": "taxlots_testing"
    }
    sd_file = os.path.join(Config.SCRATCH_WORKSPACE, item['pkgname']+".sd")
    create_service_definition(m, item, sd_file)
    assert(os.path.exists(sd_file))

    # 3. Upload the service definition
    # THIS WILL DESTROY AN EXISTING SERVICE
    #  * First I should try to update an existing definition.
    #  * If that fails then I create a new one...

    print('Uploading definition using "%s" to the "%s" portal folder.' % (item["pkgname"], item["portalFolder"]))

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
            print(f'Open the APRX file in ArcGIS Pro and put a description in the map "{mapname}".')
        exit(1)

    # Add a comment to the service

    portal = GIS(Config.PORTAL_URL, username=Config.PORTAL_USER, password=Config.PORTAL_PASSWORD)            
    print("%s Logged in as %s" % (textmark, str(portal.properties.user.username)))
    pc = PortalContent(portal)

    target_item = getServiceItem(portal, PortalContent(portal), item["pkgname"])
    target_item.add_comment("Updated %s" % textmark)
    show(target_item)

    print("All done!")
