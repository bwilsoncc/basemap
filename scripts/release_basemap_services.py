"""
release_basemap_services.py

This script will finalize the release of the basemap vector tile services.

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
import arcpy
from arcgis.gis import GIS
from datetime import datetime
from portal import PortalContent
from config import Config

def replace_service(gis: object, staged_item: str, target_item: str, archive_name: str) -> None:
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

class ReleaseBasemapServices(object):

    def __init__(self) -> None:
        self.label = "Release Basemap Services"
        self.description = """You've QC'ed the STAGED services and now you are ready to release them."""
        self.canRunInBackground = False
        self.category = "CCPublish"
        #self.stylesheet = "" # I don't know how to use this yet.
        return

    def getParameterInfo(self) -> list:

        initials  = arcpy.Parameter(
            name = 'initials',
            displayName = 'Your initials',
            datatype = 'GPString',
            parameterType='Required',
            direction = 'Input'
        )
        initials.value = os.environ.get('USERNAME')[0:2].upper()

        datestamp = arcpy.Parameter(
            name = 'datestamp',
            displayName = 'Date stamp string used in filenames.',
            datatype = 'GPString',
            parameterType='Required',
            direction = 'Input'
        )
        datestamp.value = datetime.now().strftime("%Y%m%d %H%M") # good for filenames
        
        textmark = arcpy.Parameter(
            name = 'datestamp',
            displayName = 'Date stamp string used in comments.',
            datatype = 'GPString',
            parameterType='Required',
            direction = 'Input'
        )
        textmark.value = datetime.now().strftime("%m/%d/%y %H:%M") + ' ' + initials.value
        return [initials, datestamp, textmark]

    def isLicensed(self) -> bool:
        return True

    def updateParameters(self, parameters) -> None:
        return

    def updateMessages(self, parameters) -> None:
        return

    def execute(self, params, messages) -> None:
        initials = params[0].value
        datestamp = params[1].value
        textmark = params[2].value

        services = [
            {  # This is the layer with labels used for Collector and Field Maps apps.
                "staged_title": "Vector Tiles STAGED",
                "target_title": "Vector Tiles",
                "offline": True,  # Allow use in an offline map
            },
            {  # This is the layer with only the labels
                "staged_title": "Vector Tile Labels STAGED",
                "target_title": "Vector Tile Labels",
                "offline": True,  # Allow use in an offline map
            },
            {  # This is the layer with only the shapes
                "staged_title": "Unlabeled Vector Tiles STAGED",
                "target_title": "Unlabeled Vector Tiles",
                "offline": True,  # Allow use in an offline map
            }
        ]

        # This code does not belong here. Fix.
        gis = GIS(Config.PORTAL_URL, Config.PORTAL_USER, Config.PORTAL_PASSWORD)
        portal = PortalContent(gis)
        print("Logged in as " + str(portal.gis.properties.user.username))
        # Validate the group list.
        release_groups = portal.getGroups(Config.RELEASE_GROUP_LIST)

        for service in services:
            print(service)

            staged_title = service['staged_title']
            staged_item = portal.getServiceItem(staged_title)
            if not staged_item:
                continue

            target_title = service['target_title']
            target_item = portal.getServiceItem(target_title)
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
                # We're doing a replacement.
                
                target_item.protect(enable = False)

                archive_name = 'ARCHIVED_' + target_item.name + '_' + datestamp.replace(' ','_')
                replace_service(gis, staged_item, target_item, archive_name)
                try:
                    target_item.add_comment("Released! %s" % textmark)
                    portal.deprecateService(archive_name)
                except Exception as e:
                    print("WARNING", e)
                    pass

            try:
                target_item.share(everyone=True, groups=release_groups)
                target_item.protect(enable = True)
                
            except Exception as e:
                print("ERROR:", e)

            return


if __name__ == "__main__":
    class Messenger(object):
        def addMessage(self, message: str) -> None:
            print(message)
            return
 
    rbs = ReleaseBasemapServices()
    params = rbs.getParameterInfo()
    rbs.execute(params, Messenger)

print("That's all!")
