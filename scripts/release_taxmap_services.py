"""
This script will finalize the release of the taxmap services.

2022-06-30 Tested with Server 10.9.1, ArcGIS Pro 2.9.3
2022-06-22 This version does not preserve comments.

When you use "Update" from the web interface
   * the staging version will go away,
   * it will create an archive of the previous service, 
   * all the metadata and comment(s) carefully crafted get tossed. (It keeps the obsolete metadata.)
so instead I'm doing it all correctly here. Like this.

1. If a published service is missing, create it.
2. Else replace it with the staged layer.
3. Fix up the metadata.
4. Creates backups of the existing services. Marks the backup as deprecated.
"""
import os, sys
from arcgis.gis import GIS
from datetime import datetime
from portal import PortalContent
from config import Config
sys.path.insert(0,'')

TEST = True # If set true, use a bogus service so that it does not break all our the live maps.
TEST = False # Okay, here we go!
CONTOURS = False

def replace_service(staged_item, target_item, archive_name) -> None:
    """
        Replace the released service with the staged service,
    """

    # Copy the properties we want to preserve.
    copied = {
        'description': staged_item.description,
        'snippet': staged_item.snippet,
        'accessInformation': staged_item.accessInformation,
        'licenseInfo': staged_item.licenseInfo,

        #'content_status': ???
        #'can_delete': False,
        #'protected': False,

        # other interesting properties
        #'banner':
        #'access: 'public',
        #'categories':
        #'dependencies':,
        #'listed':
        #'properties':,
        #'shared_with':,
        #'tables':
        #'tags':
    }


    # replace_metadata=True should copy through the thumbnail, tag, description, and summary fields

    gis.content.replace_service(replace_item=target_item, new_item=staged_item,
        replaced_service_name=archive_name, replace_metadata=True
    )

    try:
        # Override the rest of the metadata with what we want
        # I could put an updated thumbnail here but it makes this script so complex...
        target_item.update(item_properties=copied)
    except Exception as e:
        print("Could not update metadata.", e)

    return

def update_sharing(gis: object, pc: PortalContent, service_title: str, release_groups: object) -> None:
    service_item = pc.getServiceItem(service_title)
    if not service_item:
        return

    # We've really hit the big time now,
    service_item.content_status = "authoritative"
    service_item.protect(enable=True)  # Turn on delete protection
    # NB Setting groups does not work without allow_members_to_edit=True
    try:
        service_item.share(everyone=True, org=True,
                        groups=release_groups, allow_members_to_edit=True)
    except Exception as e:
        print("Sharing permissions update failed. %s" % e)

    return


if __name__ == "__main__":
    gis = GIS(Config.PORTAL_URL, Config.PORTAL_USER, Config.PORTAL_PASSWORD)
    print("Logged in as " + str(gis.properties.user.username))
    pc = PortalContent(gis)

    # Validate the group list.
    release_groups = pc.getGroups(Config.RELEASE_GROUP_LIST)

    if TEST:
        delete_me = pc.getServiceItem("TEST Vector Tiles")
        if delete_me:
            print("WARNING, for a complete test, service should not already exist. Up to you what you are testing...")

        services = [
            {  # Test case when there is no layer
                "staged_title": "TEST NONEXISTENT STAGED",
                "target_title": "TEST Vector Tiles",
                "offline": True,  # Allow use in an offline map
            },
            {  # Test case when the target layer does not exist -- publishing
                "staged_title": "TEST Vector Tiles STAGED",
                "target_title": "TEST Vector Tiles",
                "offline": True,  # Allow use in an offline map
            },
        ]
        

    elif CONTOURS:

        # After the 10.9.1 the tile package was still on the server
        # but the service was broken so I republished.

        services = [
            {
                "staged_title": "Contour 40",
                "target_title": "Contour 40",
                "offline": True,  # Allow use in an offline map
            },
        ]


    else:
        services = [
            {
                "staged_title": "Taxlot Labels STAGED",
                "target_title": "Taxlot Labels",
                "offline": True,  # Allow use in an offline map
            },
            {
                "staged_title": "Taxlot Address Labels STAGED",
                "target_title": "Taxlot Address Labels",
                "offline": True,  # Allow use in an offline map
            }
        ]

    initials  = os.environ.get('USERNAME')[0:2].upper()
    datestamp = datetime.now().strftime("%Y%m%d %H%M") # good for filenames
    textmark  = datetime.now().strftime("%m/%d/%y %H:%M") + ' ' + initials # more readable

    for service in services:
        print(service)

        staged_title = service['staged_title']
        staged_item = pc.getServiceItem(staged_title)
        if not staged_item:
            continue

        target_title = service['target_title']
        target_item = pc.getServiceItem(target_title)
        if not target_item:
            # We're doing 'publish the first time', just rename. (This is fast.)
            publishAs = target_title
            staged_item.update(item_properties={"title": target_title})
            staged_item.add_comment("Released into the wild! %s" % textmark)
        elif target_item.type == 'Vector Tile Package':
            # Well this code fails certainly 
            
            # We're publishing a PACKAGE (Contours!) to turn it into a service.
            #analyzed = gis.content.analyze(item=target_item)
            #pp = analyzed['publishParameters']
            #pp['name'] = target_item['Contour_40']
            #pp['locationType'] = None
            try:
                target_item.publish(
                    #publish_parameters=pp, # optional when publishing a tile package
                    file_type='vectortilepackage',
                    output_type='Tiles',
#                    item_id="46370d4ddea4440184a44736974897b5" # reuse!!
                )
            except Exception as e:
                print("Oh boy, ", e)
                
        else:
            # We're doing a replacement. This takes a bit of time.
            archive_name = 'ARCHIVED_' + target_item.name + '_' + datestamp.replace(' ','_')
            replace_service(staged_item, target_item, archive_name)
            try:
                target_item.add_comment("Released into the wild! %s" % textmark)
                pc.deprecateService(archive_name)
            except Exception as e:
                print("WARNING", e)
                pass
        pc.UpdateSharing(target_title, release_groups)

print("That's all!")
