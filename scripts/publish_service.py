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


def enable_feature_service(sddraft: str, sddraft_new: str) -> None:
    """
`   Write an sdddraft (XML) file to enable Feature Services on the MIL.
    (This is the equivalent of clicking the "Features" checkbox in Pro.)

    You can have it overwrite the original file (sdraft == sdraft_new)

    The code there is an example of why XML is dying out.
    https://pro.arcgis.com/en/pro-app/latest/arcpy/sharing/mapimagesharingdraft-class.htm#GUID-98B8320E-3561-4E46-AECF-70B0553AE4FF

    """
    # Read the .sddraft file
    doc = DOM.parse(sddraft)

    """
        Rewrite the XML file so that
        it's in a standardized format vs "Esri standard"
        so that compare actually works.
    """
    # Write the replacement .sddraft file
    with open(sddraft, "w") as fp:
        doc.writexml(fp, newl="\n")
    print("Rewrote", sddraft)

    doc = EnableFeatureLayers(doc)

    # Modify the .sddraft file to change feature layer properties
    # Defaults are Query,Create,Update,Delete,Uploads,Editing
    # Comment out this line if you don't want to modify feature layer properties
    doc = ConfigureFeatureserverCapabilities(doc, "Query")

    # Write the replacement .sddraft file
    with open(sddraft_new, "w") as fp:
        doc.writexml(fp, newl="\n")

    return



def delete_item(item) -> bool:
    item.protect(enable=False)
    try:
        return item.delete()
    except Exception as e:
        print("Delete failed, ", e)
        # Mysterious huh? See the Wiki, search for ArcGIS Enterprise.
    return False


def show(id: str) -> None:
    details = Config.PORTAL_URL + '/home/item.html?id=' + id
    viewer = Config.PORTAL_URL + '/home/webmap/viewer.html?useExisting=1&layers=' + id
    print(f"Details {details}")
    print(f"Viewer {viewer}")
    return


def BuildSD(map: object, mapd: dict) -> None:
    """
    Build an SD file.
    If features=True, creates a Feature Service (aka "Feature Layer Collection") with same name.
    """
    sd_file = os.path.join(Config.SCRATCH_WORKSPACE, mapd["pkgname"] + ".sd")
    print(f'Building \"{sd_file}\".')    

    map.clearSelection() # I wonder if this works?

    # https://pro.arcgis.com/en/pro-app/2.9/help/sharing/overview/automate-sharing-web-layers.htm

    # 1. Create a service definition draft
    # 2. Stage the service (zip)

    # https://pro.arcgis.com/en/pro-app/2.9/arcpy/mapping/map-class.htm
    # (It's possible to pass a layerlist here to limit what gets published)
    
    sddraft = map.getWebLayerSharingDraft(
        server_type="FEDERATED_SERVER",
        service_type="MAP_IMAGE", # The name is "Map Service" in Portal and "MAP_IMAGE" here, sigh...
        service_name=mapd['name'] # we might overwride this in the upload
    )
    # When type is MAP_IMAGE,
    # sddraft will be a MapIUmageSharingDraft object, refer to
    # https://pro.arcgis.com/en/pro-app/2.9/arcpy/sharing/mapimagesharingdraft-class.htm

    # in theory this is redundant since it's also defined in the upload step.
    # fails if not defined
    sddraft.federatedServerUrl = Config.SERVER_AGS # Using an URL here fails.

    sddraft.copyDataToServer = mapd['copyData'] # This only matters if the data source in the map is registered. Other data is always copied.
    sddraft.overwriteExistingService = True # THIS FAILS IF THE SD FILE EXISTS

    # I think this is the thing where it gives an error message in Analysis stage if you don't 
    # have "Allow assignment of unique numeric IDs for sharing web layers"
    # https://pro.arcgis.com/en/pro-app/2.9/help/sharing/overview/assign-layer-ids.htm
    # also read https://community.esri.com/t5/arcgis-enterprise-documents/utilising-unique-numeric-ids-in-published-services/ta-p/915453
    #sddraft.checkUniqueIDAssignment = True

    # You should always define these in the map metadata, okay?
    # I still want to append information on, to identify APRX and map used.

    # It's possible to set up sharing here too.

    sddraft.summary = map.metadata.summary
    sddraft.description = map.metadata.description + mapd["description"]
    sddraft.credits = map.metadata.credits
    sddraft.useLimitations = map.metadata.accessConstraints
    sddraft.tags = map.metadata.tags

    sddraft.portalFolder = mapd["folder"] # This is not working. All goes in root. Bah!
    # sddraft.serverFolder

    #sddraft.offline = True # Set this if you don't have access to Portal but still want to create the draft. 
    # The draft file is an XML file. Writing 2 XML files makes debugging a lot easier.
    sddraft_file = os.path.join(Config.SCRATCH_WORKSPACE, mapd["pkgname"] + ".sddraft")
    sddraft_with_features = os.path.join(Config.SCRATCH_WORKSPACE, mapd["pkgname"] + "_features_enabled" + ".sddraft")

    # Create the sddraft file
    if os.path.exists(sddraft_file): os.unlink(sddraft_file)
    sddraft.exportToSDDraft(sddraft_file)
    if mapd['makeFeatures']: 
        # Modify the sddraft file.    
        if os.path.exists(sddraft_with_features): os.unlink(sddraft_with_features)
        enable_feature_service(sddraft_file, sddraft_with_features)
        print("wrote", sddraft_with_features)
        sddraft_file = sddraft_with_features
        
    print("Staging = analyse definition then build", sd_file)
    try:
        # "Stage" is the Esri verb for "archive with 7Z".
        # The 7z file contains a FGDB and various settings. If you asked for hosted data, a copy of the data will be in the FGDB.
        if os.path.exists(sd_file): os.unlink(sd_file)
        arcpy.server.StageService(sddraft_file, sd_file)
    except Exception as e:
        print("ERROR:", e)
        """ERROR: ERROR 001272: Analyzer errors were encountered 
        ([
            {"code":"00231","message":"Layer's data source must be registered with the server","object":"Roads (popups)"},
            {"code":"00231","message":"Layer's data source must be registered with the server","object":"Trails (popups)"},
            {"code":"00231","message":"Layer's data source must be registered with the server","object":"Roads by Jurisdiction"}]).
        Failed to execute (StageService)."""
        raise e

    return sd_file


def PublishFromSD(gis: GIS, map: object, mapd: dict, sd_file: str) -> None:
    """
    Upload the service definition to the SERVER
    This will overwrite an existing service
    or publish a new one.
    """
    servicename = mapd['name'].replace(' ', '_')
    if 'servicename' in mapd:
        servicename = mapd['servicename']

    print(f'Uploading sd file to "{mapd["folder"]}" folder (which does not work BTW).')

    portal = PortalContent(gis)
    username = os.environ.get("USERNAME")

    # Validate the group list
    release_groups = portal.getGroups(Config.RELEASE_GROUP_LIST)

    # In theory everything needed to publish the service is now in the SD file.
    # https://pro.arcgis.com/en/pro-app/latest/tool-reference/server/upload-service-definition.htm
    # You can override permissions, ownership, groups here too.
    # in_startupType HAS TO BE "STARTED" else no service is started on the SERVER.
    rval = arcpy.SignInToPortal(Config.PORTAL_URL, Config.PORTAL_USER, Config.PORTAL_PASSWORD)

    # It's possible to set up sharing here too.
    rval = arcpy.server.UploadServiceDefinition(in_sd_file=sd_file, in_server=Config.SERVER_AGS, in_service_name=servicename, in_startupType="STARTED")

    # Update sharing.
    # Skipping this step bit me, (2023-02-09) because suddenly everyone had to log in. (The service was not accessible by Everyone.)

    mil_item = portal.getServiceItem(title=mapd["name"], type=portal.MapImageLayer)

    # Fix the extent of the service(s), not sure if this is needed.
    # Once you have loaded the layer in Map Viewer, use "Zoom to".
    cimMap = map.getDefinition('V2')
    j = arcpy.cim.GetJSONForCIMObject(cimMap.defaultExtent, 'V2')
    defaultMapExtent = json.loads(j)
    extentProperty = [
        [defaultMapExtent['xmin'], defaultMapExtent['ymin']],
        [defaultMapExtent['xmax'], defaultMapExtent['ymax']]
    ]
    print("Default map extent is", extentProperty)

    # There's an Esri bug, it fails to write the popup settings,
    # so I coded around it. This generates the JSON. It will get written later.
    popupDict = makePopup(map.listLayers())
    # For debugging, dump to a file as JSON
#    json_file = os.path.join(Config.SCRATCH_WORKSPACE, mapd["pkgname"] + ".json")
#    with open(json_file, 'w') as fp:
#        json.dump(popupDict, fp, indent=2)

    print("Current extent", mil_item.extent) 
    mil_item.update(item_properties = { 'text' : popupDict, 'extent': extentProperty })

    print("Setting status to authoritative")
    mil_item.content_status = 'authoritative'
    print("Marking as 'do not delete'.")
    mil_item.protect(enable=True)
    print("Setting sharing.")
    mil_item.share(everyone=True, org=True, groups=release_groups, allow_members_to_edit=True)

    # Add a comment to the service
    # Comments will log whoever ran the script and when. They can't use HTML
    print("Adding comment.")
    mil_item.add_comment(f"Updated as {username}.")
    show(mil_item.id)

    print("features")
    if mapd['makeFeatures']:
        fl_item = portal.getServiceItem(title=mapd["name"], type=portal.FeatureService)
        if fl_item:
            fl_item.update(item_properties = { 'text' : popupDict, 'extent': extentProperty })
            fl_item.content_status = 'authoritative'
            fl_item.protect(enable=True)
            fl_item.share(everyone=True, org=True,
                groups=release_groups, allow_members_to_edit=True)

            fl_item.add_comment(f"Updated as {username}.")
            show(fl_item.id)

    return

# ==========================================================================
if __name__ == "__main__":
    print("No unit tests here yet.")
    