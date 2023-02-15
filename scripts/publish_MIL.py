"""
    publish_MIL.py

    Publish a map from an APRX project file as
    a map image layer and as a feature layer collection.
"""
import os, sys
import datetime
import arcpy
from arcgis.gis import GIS
from scripts.portal import PortalContent
from scripts.popups import makePopup
import xml.dom.minidom as DOM
from xml_utils import EnableFeatureLayers, ConfigureFeatureserverCapabilities
import json
sys.path.insert(0,'')
from config import Config

import subprocess
BROWSER = "C:/Program Files/Mozilla Firefox/firefox.exe"
SHOWPOPUP = False


def find_map(aprx, mapname):
    maps = aprx.listMaps(mapname)
    if len(maps) != 1:
        return None
    return maps[0]



def enableFeatureService(sddraft: str, sddraft_new: str) -> None:
    """
`   Write an sdddraft (XML) file to enable Feature Services on the MIL.
    (This is the equivalent of clicking the "Features" checkbox in Pro.)

    You can have it overwrite the original file (sdraft == sdraft_new)

    The code there is an example of why XML is dying out.
    https://pro.arcgis.com/en/pro-app/latest/arcpy/sharing/mapimagesharingdraft-class.htm#GUID-98B8320E-3561-4E46-AECF-70B0553AE4FF

    """
    # Read the .sddraft file
    doc = DOM.parse(sddraft)
    doc = EnableFeatureLayers(doc)

    # Modify the .sddraft file to change feature layer properties
    # Defaults are Query,Create,Update,Delete,Uploads,Editing
    # Comment out the line below if you don't want to modify feature layer properties
    doc = ConfigureFeatureserverCapabilities(doc, "Create,Query")

    # Write the replacement .sddraft file
    with open(sddraft_new, "w") as fp:
        doc.writexml(fp)
    
    return

def create_service_definition(map: arcpy._mp.Map, item: dict, sd_file: str) -> None:
    """
    Create an sd file named "sd_file".
    """

    # https://pro.arcgis.com/en/pro-app/2.9/arcpy/mapping/map-class.htm
    # (It's possible to pass a layerlist here to limit what gets published)
    
    sddraft = map.getWebLayerSharingDraft(
        server_type="FEDERATED_SERVER",
        service_type="MAP_IMAGE", # The name is "Map Service" in Portal and "MAP_IMAGE" here, sigh...
        service_name=item["name"],
    )
    # When type is MAP_IMAGE,
    # sddraft will be a MapIUmageSharingDraft object, refer to
    # https://pro.arcgis.com/en/pro-app/2.9/arcpy/sharing/mapimagesharingdraft-class.htm

    sddraft.federatedServerUrl = Config.SERVER_AGS # Using an URL here fails.
    sddraft.copyDataToServer = item['copyData'] # This only matters if the data source in the map is registered. Other data is always copied.
    sddraft.overwriteExistingService = True # THIS FAILS IF THE SD FILE EXISTS

    # I think this is the thing where it gives an error message in Analysis stage if you don't 
    # have "Allow assignment of unique numeric IDs for sharing web layers"
    # https://pro.arcgis.com/en/pro-app/2.9/help/sharing/overview/assign-layer-ids.htm
    # also read https://community.esri.com/t5/arcgis-enterprise-documents/utilising-unique-numeric-ids-in-published-services/ta-p/915453
    #sddraft.checkUniqueIDAssignment = True

    # You should always define these in the map metadata, okay?
    # I still want to append information on, to identify APRX and map used.

    sddraft.summary = map.metadata.summary
    sddraft.description = map.metadata.description + item["description"]
    sddraft.credits = map.metadata.credits
    sddraft.useLimitations = map.metadata.accessConstraints
    sddraft.tags = map.metadata.tags

    sddraft.portalFolder = item["folder"] # This is not working today. All goes in root. Bah!
    # sddraft.serverFolder

    #sddraft.offline = True # Set this if you don't have access to Portal but still want to create the draft. 
    # The draft file is an XML file. Writing 2 XML files makes debugging a lot easier.
    sddraft_file = os.path.join(Config.SCRATCH_WORKSPACE, item["pkgname"] + ".sddraft")
    sddraft_with_features = os.path.join(Config.SCRATCH_WORKSPACE, item["pkgname"] + "_features_enabled" + ".sddraft")

    if os.path.exists(sddraft_file): os.unlink(sddraft_file)
    sddraft.exportToSDDraft(sddraft_file)

    if os.path.exists(sddraft_with_features): os.unlink(sddraft_with_features)
    enableFeatureService(sddraft_file, sddraft_with_features)
        
    print("    Creating", sd_file)
    try:
        # "Stage" is the Esri verb for "archive with 7Z".
        # The 7z file contains a FGDB and various settings. If you asked for hosted data, a copy of the data will be in the FGDB.
        if os.path.exists(sd_file): os.unlink(sd_file)
        arcpy.server.StageService(sddraft_with_features, sd_file)
    except Exception as e:
        print("ERROR:", e)
        raise e

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

    overwrite = True
    username = os.environ.get("USERNAME")
    textmark = datetime.datetime.now().strftime("%m/%d/%y %H:%M") + " " + username[0:2].upper()
    arcpy.env.workspace = Config.SCRATCH_WORKSPACE

    gis = GIS(Config.PORTAL_URL, Config.PORTAL_USER, Config.PORTAL_PASSWORD)
    portal = PortalContent(gis)
    print(f'User {username} logged in to Portal as "{str(gis.properties.user.username)}".')
    # Validate the group list
    release_groups = portal.getGroups(Config.RELEASE_GROUP_LIST)

    try:
        aprx = arcpy.mp.ArcGISProject(Config.TAXMAP_APRX)
    except Exception as e:
        print("Can't open APRX file,", e)
        exit(-1)

    project_desc = f'<p>Project file: "{aprx.filePath}" <br /><Updated <b>{textmark}</b> {Config.DOC_LINK}</p>' 

    # The APRX file has to have maps with these mapnames defined.
    maps = [
        {
            "name": "Taxlot Queries",
            "description": project_desc,
            "folder": "Taxmaps", 
            "pkgname": "Taxlot Queries".replace(" ", "_"),
            "copyData": False
        }
    ]

    total = len(maps)
    n = 0
    for item in maps:
        name = item["name"]
        n += 1
        progress = "%d/%d" % (n, total)

        map = find_map(aprx, name)
        if not map:
            print(f'ERROR! Map "{name}" not found in APRX.')
            continue
        map.clearSelection()

        # There's a bug that causes the ArcPy code to fail to write the popup settings,
        # so I coded around it. This generates the JSON. It will get written later.
        #cimMap = map.getDefinition(cim_version='V2')

        popupDict = makePopup(map.listLayers())
        # For debugging, dump to a file as JSON
        json_file = os.path.join(Config.SCRATCH_WORKSPACE, item["pkgname"] + ".json")
        with open(json_file, 'w') as fp:
            json.dump(popupDict, fp, indent=2)

        # https://pro.arcgis.com/en/pro-app/2.9/help/sharing/overview/automate-sharing-web-layers.htm

        sd_file = os.path.join(Config.SCRATCH_WORKSPACE, item["pkgname"] + ".sd")
        if arcpy.Exists(sd_file) and not overwrite:
            print(f"Using existing file \"{sd_file}\".")
        else:
            print(progress, f'Building "{item["name"]}" sd file in {Config.SCRATCH_WORKSPACE}.')
            
            # 1. Create a service definition draft
            # 2. Stage the service (zip)
            create_service_definition(map, item, sd_file)

        # 3. Upload the service definition
        # This will overwrite an existing service
        # or publish a new one.

        print(f'    Uploading "{sd_file}" to "{item["folder"]}" folder.')

        # Upload the service definition to SERVER
        # In theory everything needed to publish the service is already in the SD file.
        # https://pro.arcgis.com/en/pro-app/latest/tool-reference/server/upload-service-definition.htm
        # You can override permissions, ownership, groups here too.
        try:
            # in_startupType HAS TO BE "STARTED" else no service is started on the SERVER.
            rval = arcpy.SignInToPortal(Config.PORTAL_URL, Config.PORTAL_USER, Config.PORTAL_PASSWORD)
            rval = arcpy.server.UploadServiceDefinition(sd_file, Config.SERVER_AGS, in_startupType="STARTED")

        except Exception as e:
            print("Could not generate service.", e)
            if e.args[0].startswith("ERROR 001117"):
                print(f'ERROR: Open the APRX file in ArcGIS Pro and put a description in properties for "{name}".')
                print(f'Skipping "{name}".')
            continue

        # Update sharing.
        # Skipping this step bit me, (2023-02-09) because suddenly everyone had to log in. (The service was not accessible by Everyone.)

        # This script creates a MIL and a feature service with the same name.

        mil_item = portal.getServiceItem(title=item["name"], type=portal.MapImageLayer)
        mil_item.update(item_properties = { 'text' : popupDict })

        mil_item.content_status = 'authoritative'
        mil_item.protect(enable=True)
        mil_item.share(everyone=True, org=True,
            groups=release_groups, allow_members_to_edit=True)

        # Add a comment to the service
        # Comments will log whoever ran the script and when. They can't use HTML
        mil_item.add_comment(f"Updated as {username} by {scriptname}.")

        fl_item = portal.getServiceItem(title=item["name"], type=portal.FeatureService)
        if fl_item:
            fl_item.update(item_properties = { 'text' : popupDict })
            fl_item.content_status = 'authoritative'
            fl_item.protect(enable=True)
            fl_item.share(everyone=True, org=True,
                groups=release_groups, allow_members_to_edit=True)

            fl_item.add_comment(f"Updated as {username} by {scriptname}.")


    print("All done!!!")

