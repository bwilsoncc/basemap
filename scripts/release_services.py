"""
This script will finalize the release of the vector tile services.

When you use "Update" from the web interface
   * the staging version will go away,
   * it will create an archive of the previous service, 
   * all the metadata and comment(s) carefully crafted get tossed. (It keeps the obsolete metadata.)
so instead I'm doing it all correctly here. Like this.

1. If a published service is missing, create it.
2. Else replace it with the staged layer.
3. Fix up the metadata. This includes comments and thumbnails.
4. Creates backups of the existing services. Mark the backup as deprecated.

"""
import os, sys
from arcgis.gis import GIS
from datetime import datetime
from portal import PortalContent, show
from config import Config

# These source titles rely on you deleting the old layers, which will have the same title.
# If you don't there will be an error and this script will stop.

services = [
    { # This is the layer with labels used for Collector and Field Maps apps.
        "source_title": "Vector Tiles STAGED",
        "target_title": "Vector Tiles",
        "offline" : True, # Allow use in an offline map
    },
    { # This is the layer with only the labels
        "source_title": "Vector Tile Labels STAGED", 
        "target_title": "Vector Tile Labels",
        "offline" : True, # Allow use in an offline map
    },
    { # This is the layer with only the shapes
        "source_title": "Unlabeled Vector Tiles STAGED",
        "target_title": "Unlabeled Vector Tiles",
        "offline" : True, # Allow use in an offline map
    }
]

initials  = os.environ.get('USERNAME')[0:2].upper()
datestamp = datetime.now().strftime("%Y%m%d %H%M") # good for filenames
textmark  = datetime.now().strftime("%m/%d/%y %H:%M") + ' ' + initials # more readable


def get_thumb(item, save_as) -> bool:
    """
    Download a thumbnail from the portal.
    Return True or False.
    """
    with open(save_as, "wb") as fp:
        bits = item.get_thumbnail()
        fp.write(bits)
    #print("Downloaded thumbnail \"%s\"." % save_as)
    return True


if __name__ == "__main__":
    portal = GIS(Config.PORTAL_URL, Config.PORTAL_USER, Config.PORTAL_PASSWORD)
    print("Logged in as " + str(portal.properties.user.username))
    pc = PortalContent(portal)
    
    # Validate the group list.
    release_groups = pc.get_groups(Config.RELEASE_GROUP_LIST)

    for service in services:
        print("============")
        print(service)

        source_title = service['source_title']
        source_id = pc.find_id(title=source_title, type=pc.VectorTileService)
        if not source_id: 
            print("No service \"%s\" found." % source_title)
            continue

        # Load the metadata from the staged layer.
        source_item = portal.content.get(source_id)
        print("SOURCE ")
        show(source_item)

        target_title = service['target_title']
        target_id = pc.find_id(title=target_title, type=pc.VectorTileService)
        if not target_id: 
            publishAs = target_title
        else:
            target_item = portal.content.get(target_id)
            print("TARGET")
            show(target_item)

            source_thumb = os.path.join(Config.SCRATCH_WORKSPACE, "new.png")
            get_thumb(source_item, source_thumb)

            old_thumb = os.path.join(Config.SCRATCH_WORKSPACE, "old.png")
            get_thumb(target_item, old_thumb)

        #assert(target_id == service['target_id'])

        if target_id:
            # We're doing a "replace"

            # Fix up the metadata, it's still the old stuff.

            # Copy the properties we want to preserve.
            copied = {
                'description': source_item.description,
                'snippet': source_item.snippet,
                'accessInformation': source_item.accessInformation,
                'licenseInfo': source_item.licenseInfo,

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

            # Grab the comment list
            comment_list = source_item.comments

            # Figure out the name for the archive.
            archive_name = 'ARCHIVED_' + target_item.name + '_' + datestamp.replace(' ','_')

            portal.content.replace_service(replace_item=target_id, new_item=source_id,
                replaced_service_name=archive_name, replace_metadata=False
            )

            try:
                updated = target_item.update(item_properties=copied, thumbnail=source_thumb)
                if updated:
                    os.unlink(source_thumb)
                else:
                    print("\"update\" returned 'false' :-(")
            except Exception as e:
                print("Could not update thumbnail.", e)

            # Remove the exalted status from the archive.
            archive_id = pc.find_id(name=archive_name, type=pc.VectorTileService)
            if archive_id:
                archive_item = portal.content.get(archive_id)
                archive_item.content_status = "deprecated"
                archive_item.protect(enable = False)
                try:
                    # Replace the thumbnail on the archive with the old thumbnail.
                    archive_item.update(thumbnail=old_thumb)
                    os.unlink(old_thumb)   
                except Exception as e:
                    print("Could not replace thumbnail on archive.", e)
            else:
                print("WARNING I can't find the archive named \"%s\"." % archive_name)
                archive_items = pc.find_items(name=archive_name, type=pc.VectorTileService)
                show(archive_items)
            
            try:
                target_item.share(everyone=True, org=True, 
                    groups=release_groups, allow_members_to_edit=True)
            except Exception as e:
                print("Sharing permissions update failed. %s" % e)
            # Copy the comments
            for comment_item in comment_list:
                # I might want to try to preserve the other properties of comment_item
                # like the owner and timestamp? Or to indicate it was copied?
                target_item.add_comment(comment_item.comment)          

        else:
            # We're doing a 'publish the first time'

            # I think all I need to do is rename the VTS and I'm done.
            # Everything else is already done.

            source_item.update(item_properties={
                "title": target_title,
            })

            # We've really hit the big time now,
            source_item.content_status = "authoritative"
            source_item.protect(enable = True) # Turn on delete protection

            # NB Setting groups does not work without allow_members_to_edit=True
            source_item.share(everyone=True, org=True,
                groups=release_groups, allow_members_to_edit=True)

            source_item.add_comment("Released into the wild! %s" % textmark)

# That's all!
