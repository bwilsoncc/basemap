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
from scripts.portal import PortalContent
sys.path.insert(0,'')

cwd = os.getcwd()
arcpy.env.overwriteOutput = True


def listLayers(m):
    # List the layer names in the map.
    for layer in m.listLayers():
        print("layer:", layer.name)
        cim = layer.getDefinition('V2')
        pup = cim.popupInfo
        if pup:
            print("popup title: ", pup.title)
#            print(pup.showPopups)
            for ex in pup.expressionInfos:
                print(f'expression/{ex.name} = """{ex.expression}"""')

    return


def import_taxlots(src : str, dst: str) -> None:
    errors = 0

    # Ancient of Days takes so LONG to delete one field at a time
    # even when working from a local FGDB in SSD. Oh well. Normally I don't sit and watch.
    # I tried deleting a list of fields but that failed.
    # I tried using a field map in the Project step but that failed too.

    try:
        print("Reprojecting %s to %s" % (src, dst)) # dst cannot be in memory!!
        arcpy.management.Project(in_dataset=src, out_dataset=dst, 
            out_coor_system = Config.WM_SRS, transform_method = Config.TRANSFORMS,
            in_coor_system = Config.LOCAL_SRS,
            preserve_shape="NO_PRESERVE_SHAPE", max_deviation="", vertical="NO_VERTICAL")
    except Exception as e:
        print("Failed!", e)
        errors += 1

    keepers = [
        'OBJECTID',

        'ACCOUNT_ID',
        'Taxlot',
        'X_COORD', 'Y_COORD', ## Needed for street view
        'TAXMAPNUM',
        'TAXLOTKEY',

        # Mailing address
        'OWNER_LINE',
        'OWNER_LL_1',
        'OWNER_LL_2',
        'STREET_ADD',
        'CITY', 
        'STATE', 
        'ZIP_CODE',
        
        # Situs address
        'SITUS_ADDR',
        'SITUS_CITY',
        
        'TAXCODE', # Probably never used

        # These are used in Sales Search in A&T
        # "MA", "NH",

        'PROPERTY_C', ## Needed for 'unimproved' layer

        'Shape_Length', 'Shape_Area'
    ]
    actual_fields = arcpy.ListFields(dst, '*')
    deletethese = []
    for f in actual_fields:
        if not f.name in keepers and f.type != 'Geometry':
            deletethese.append(f.name)
    try:
        for field in deletethese:
            print("Deleting", field)
            arcpy.management.DeleteField(dst, field)
    except Exception as e:
        print(f"WARNING, field delete failed for {field}.", e)

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
    sddraft.federatedServerUrl = Config.SERVER_AGS
    sddraft.description = item["description"]
    sddraft.credits = Config.CREDITS
    sddraft.useLimitations = Config.DISCLAIMER_TEXT
    sddraft.tags = ",".join(Config.STAGING_TAG_LIST) + ',taxlots,parcels'
    sddraft.portalFolder = item["portalFolder"]
    # sddraft.summary = "say something here"
    # sddraft.serverFolder = item["serverFolder"]
    sddraft.overwriteExistingService = True # WELL THIS FAILS SPECTACULARLY

    # The generated draft file is an XML file.
    sddraft_file = os.path.join(Config.SCRATCH_WORKSPACE, item["pkgname"] + ".sddraft")
    sddraft.exportToSDDraft(sddraft_file)

    if os.path.exists(sd_file):
        #return sd_file # Uncomment this line for faster debugging.
        os.unlink(sd_file)

    print("Creating", sd_file)
    try:
        # "Stage" is the Esri verb meaning "archive with 7Z".
        # The 7z file contains a FGDB and various settings.
        arcpy.server.StageService(sddraft_file, sd_file)
    except Exception as e:
        print("Staging failed.", e)
        sd_file = None

    return sd_file


# ===============================
if __name__ == "__main__":

    sdefile = "cc-thesql_SDE.sde"
    taxlots_fc = "Clatsop.DBO.taxlot_accounts"

    # Esri does not provide a method for creating an APRX
    # I left one here called empty.aprx if you need a starting point.
    # then you could load taxlots.mapx into it.
    # An APRX is a ZIP with lots of gunk and JSON "CIM" files in it.
    project = arcpy.mp.ArcGISProject(Config.TAXMAP_APRX)
    mapname = Config.TAXLOTS_MAP
    m = project.listMaps(mapname)[0]
    print(f"Project: {Config.TAXMAP_APRX}\nMap: {m.name}")

    # This locks the taxlots fc in the geodatabase, go figure out THAT.
#    listLayers(m)

    taxlots_workspace = project.defaultGeodatabase # Could dig this out of APRX.

    src = os.path.join(sdefile, taxlots_fc)
#    assert(arcpy.Exists(src))
#    assert(arcpy.Exists(taxlots_workspace))

    initials = os.environ.get("USERNAME")[0:2].upper()
    textmark = (
        datetime.datetime.now().strftime("%m/%d/%y %H:%M") + " " + initials
    )  # more readable

    dst_name = 'Taxlots_WM'
    dst = os.path.join(taxlots_workspace, dst_name)
    #rval = import_taxlots(src, dst)
    #if rval>0: exit(-1)

    item = {
        "portalFolder": "TESTING_Brian",
        "description": "Taxlots map image layer",
        "pkgname": "taxlots_testing"
    }
    sd_file = os.path.join(Config.SCRATCH_WORKSPACE, item['pkgname']+".sd")
    create_service_definition(m, item, sd_file)

    # 3. Upload the service definition (OVERWRITE EXISTING SERVICE)
    print('Uploading definition using "%s" to the "%s" portal folder.' % (item["pkgname"], item["portalFolder"]))

    # Upload the service definition to SERVER
    # In theory everything needed to publish the service is already in the SD file.
    # https://pro.arcgis.com/en/pro-app/latest/tool-reference/server/upload-service-definition.htm
    # You can override permissions, ownership, groups here too.
    try:
        # in_startupType HAS TO BE "STARTED" else no service is started on the SERVER.
        rval = arcpy.SignInToPortal(Config.PORTAL_URL, Config.PORTAL_USER, Config.PORTAL_PASSWORD)
        rval = arcpy.server.UploadServiceDefinition(sd_file, Config.SERVER_AGS, in_startupType="STARTED")

    except Exception as e:
        print("FAIL! Could not generate service.", e)
        if e.args[0].startswith("ERROR 001117"):
            print(f'Open the APRX file in ArcGIS Pro and put a description in the map "{mapname}".')
        exit(1)

    # Add a comment to the service, so we know who did what
    portal = GIS(Config.PORTAL_URL, username=Config.PORTAL_USER, password=Config.PORTAL_PASSWORD)            
    print("%s Logged in as %s" % (textmark, str(portal.properties.user.username)))
    pcm = PortalContent(portal)
    target_item = pcm.getServiceItem(item["pkgname"])
    target_item.add_comment("Updated %s" % textmark)
    PortalContent.show(target_item)

    print("All done!")

#TAXLOTKEY IS NOT NULL And (STREET_ADD IS NOT NULL Or PO_BOX IS NOT NULL Or CITY IS NOT NULL)