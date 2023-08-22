"""
stage_basemap_services.py

2023-08-22 Tested with Server 10.9.1, ArcGIS Pro 3.1.2
2022-09-15 Tested with Server 10.9.1, ArcGIS Pro 2.9.4

Builds the "basemap" vector tiles and stages them to the server.
Once you have done QC, use the release_services script
to publish them under the publicly accessible names.

All the try/except blocks and if statements are part of a design
philosophy that the script should always complete, even if it can't
do everything like set a custom thumbnail. It's better to issue a 
warning and press on than to crash and leave things in an 
indeterminate state.
"""
import os, sys
from posixpath import splitext
import arcpy
from arcgis.gis import GIS
from datetime import datetime
from config import Config
from portal import PortalContent
from watermark import mark

#TEST = True # Generate a test service only.
TEST = False # Generate real services.

PACKAGE_THUMBNAIL = "W:/ALL/GIS/Projects/Images/Services_thumbnails/package.png"
COUNTY_THUMBNAIL = "W:/ALL/GIS/Projects/Images/Services_thumbnails/clatsopcounty_plus_logo.png"
assert(os.path.exists(PACKAGE_THUMBNAIL))
assert(os.path.exists(COUNTY_THUMBNAIL))

class StageBasemapServices(object):

    def __init__(self) -> None:
        self.label = "Stage Basemap Services"
        self.description = """Stage Basemap Services."""
        self.canRunInBackground = False
        self.category = "CCPublish"
        #self.stylesheet = "" # I don't know how to use this yet.
        return

    def getParameterInfo(self) -> list:
        return []

    def isLicensed(self) -> bool:
        return True

    def updateParameters(self, parameters) -> None:
        return

    def updateMessages(self, parameters) -> None:
        return

    def execute(self, parameters, messages) -> None:
        return

def find_map(aprx, mapname):
    maps = aprx.listMaps(mapname)
    if len(maps) != 1: return None
    return maps[0]


def build_tile_package(map, pkgname, min_zoom = Config.MIN_COUNTY_ZOOM, overwrite=False):
    """ Build a tile package. Does not overwrite by default.

    'map' is a map from an aprx
    'pkgname' is the name of the package (will be the filename too)
    'min_zoom' defaults to county level, you might choose tax level
    'overwrite' is (well you know) True or False, defaults to False

    Returns absolute pathname of package if a package was built or None
    (We need the path to be absolute when we do the "add" in staging.)
    """
    pkgfile = os.path.join(arcpy.env.workspace, pkgname + '.vtpk')
    if arcpy.Exists(pkgfile): # BTW, this uses the workspace env
        if overwrite:
            os.unlink(pkgfile)
        else:
            print("Reusing existing file, %s" % pkgfile)
            return pkgfile

    # I tried to add a description to the map object here but it did not work.
    # If there is no description, the Esri tool fails. Sorry.

    # Note, we'll update metadata later .
    # BTW, that 99999 error you're getting could be a definition query problem.
    # RTM https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/create-vector-tile-package.htm

    arcpy.management.CreateVectorTilePackage(map, pkgfile, 
        service_type="ONLINE", tiling_scheme=None, 
        tile_structure="FLAT", # or INDEXED
        min_cached_scale=min_zoom, max_cached_scale=Config.MAX_ZOOM
    )

    return pkgfile


def delete_item(item) -> bool:
    item.protect(enable=False)
    try:
        return item.delete()
    except Exception as e:
        print("Delete failed, ", e)
        # Mysterioous huh? See the Wiki, search for ArcGIS Enterprise.
    return False
    

def upload_tile_package(portal, pkgname, pkgfile, description, overwrite=True):
    """ 
    Upload a tile package.
    Return package item or None
    """
    global signature
    pc = PortalContent(portal)
    pkg_item = None

    # Snippet (aka "summary") can't contain markup.
    snippet = ("%s (%s)" % (pkgname, signature)).replace('_', ' ')

    # 2021-10-15 I've had this fail, I worked around it by deleting manually. 
    existing_item = pc.findItem(name=pkgname, type=pc.VectorTilePackage)
    if existing_item:
        if overwrite:
            delete_item(existing_item)
        else:
            print("WARNING: Target exists and overwrite=False, skipping upload.")
            return existing_item

    try:
        # Basically ANY or ALL the metadata can be written with the add() method.
        pkg_item = portal.content.add({
                'title': pkgname.replace('_', ' '),
            },
            data=pkgfile, # Absolute path or URL
            folder="Basemaps"
        )
    except Exception as e:
        print("Upload did not work for %s!" % pkgname, e)
        return None

    thumbnail = PACKAGE_THUMBNAIL
    outname = os.path.join(Config.SCRATCH_WORKSPACE, 'package_thumbnail.png')
    pkg_thumbnail = mark(thumbnail, outname, caption="Basemap", textmark="Package File")

    pkg_item.update(
        item_properties = {
            "title": snippet,
            "snippet": snippet,
            "tags": Config.STAGING_TAG_LIST, # This can be a list or a string
            "accessInformation": Config.CREDITS,
            "licenseInfo": Config.DISCLAIMER_TEXT, 
            "description": description,
        },
        thumbnail = pkg_thumbnail
    )
    os.unlink(pkg_thumbnail)

    # Remember, markup won't work here, neither will newlines
    comment = "Uploaded %s" % signature
    try:
        pkg_item.add_comment(comment)
    except Exception as e:
        print("Could not add package comment \"%s\". -- %s" % (comment, e))

    return pkg_item


def stage_tile_service(portal, pkg_item, pkgname, description, overwrite=True):
    """ 
    Publish a tile package as a service.

    Returns layer service item or None
    """
    global datestamp, signature

    pc = PortalContent(portal)
    lyr_item = None
    
    # Snippet (aka "summary") can't contain markup.
    snippet = ("%s (%s)" % (pkgname, signature)).replace('_', ' ')

    # Publish the (uploaded) tile package as a hosted service
    # "overwrite = True" always seems to break here no matter what.
    
    lyr_title = (pkgname + ' STAGED').replace('_',' ')
    existing_item = pc.findItem(title=lyr_title, type=pc.VectorTileService) 
    if existing_item:
        if overwrite:
            if existing_item.content_status == 'org_authoritative':
                print("Won't overwrite authoritative layer \"%s\"." % existing_item.title)
            else: 
                delete_item(existing_item)
        else:
            return None

#    lyr_name = pkgname # "Vector_Tiles" was failing failing failing!
    lyr_name = (pkgname + '_' + datestamp).replace(' ', '_')
    lyr_items = pc.findItems(name=lyr_name, type=pc.VectorTileService)
    if lyr_items:
        # dearie me there is at least one service with this name so pick another
        print("This is not a unique layername so I am trying to use \"%s\"." % lyr_name)

    try:
        lyr_item = pkg_item.publish(
            output_type = "VectorTiles",
#            overwrite = overwrite, # This just seems to hurt things.
            publish_parameters={
                "title": lyr_title, # Appears to do nothing, but has to be here
                "name": lyr_name, # This can't have spaces in it.
                "tags": "STAGED", # "Tags" is required!!
            })
        # I really want this set NOW!
        lyr_item.update(item_properties={"title": lyr_title})
        #print("service item", lyr_item)

    except Exception as e:
        print("Staging failed!", e)
        # "Service name 'Vector_Tiles' already exists for '0123456789'"
        items = pc.findItems(name=lyr_name) 
        PortalContent.show(items)
        items = pc.findItems(title=lyr_title) 
        PortalContent.show(items)
        return None

    thumbnail = COUNTY_THUMBNAIL
    outname = os.path.join(Config.SCRATCH_WORKSPACE, 'layer_thumbnail.png')
    lyr_thumbnail = mark(thumbnail, outname, caption="Basemap", textmark="Vector Tiles")
    lyr_item.update(
        item_properties = {
            #"title": snippet, Title was already set in publish step.
            "snippet": snippet,
            "tags": Config.STAGING_TAG_LIST, # This can be a list or a string
            "accessInformation": Config.CREDITS,
            "licenseInfo": Config.DISCLAIMER_TEXT, 
            "description": description,
        }, 
        thumbnail = lyr_thumbnail
    )
    os.unlink(lyr_thumbnail)

    # Remember, markup won't work here, neither will newlines
    comment = "Staged %s" % signature
    try:
        lyr_item.add_comment(comment)
    except Exception as e:
        print("Could not add the layer comment! Darn.", e)

    return lyr_item

# ==========================================================================

if __name__ == "__main__":

    (scriptpath, scriptname) = os.path.split(__file__)

    print(os.getcwd())

    arcpy.env.workspace = Config.SCRATCH_WORKSPACE # Normally C:\\Temp but your choice.

    initials  = os.environ.get('USERNAME')[0:2].upper()
    datestamp = datetime.now().strftime("%Y%m%d %H%M") # good for filenames
    signature = datetime.now().strftime("%m/%d/%y %H:%M") + ' ' + initials # Good for humans to read

    try:
        aprx = arcpy.mp.ArcGISProject(Config.BASEMAP_APRX)
    except Exception as e:
        print("Can't open APRX file,", e)
        exit(-1)

    layer_desc = """<p>Feature layers: Roads, Trails, Parks, Water (lines), Water (polygons), County Boundary <br /></p>
    <p>NOTE, it is in <b>WEB MERCATOR</b></p>"""
    project_desc = "<p>Project file: \"%s\"" % aprx.filePath

    # The APRX file has to have maps with these mapnames defined.
    if TEST:
        mapnames = [
            {
                "mapname": "TEST Vector Tiles", 
                "description": """<p>This is just a test and should be deleted.</p>""" + Config.AUTOGRAPH,
                "min_zoom": Config.MIN_COUNTY_ZOOM
            },
        ]
    else:
        mapnames = [
            {
                "mapname": Config.COMBINED_MAP, 
                "description": """<p>This layer is optimized for use in Collector and Field Maps; use it as a basemap for offline field work.
        It includes both the labels and the features in one vector tile layer.</p>"""
                + layer_desc + project_desc,
                "min_zoom": Config.MIN_COUNTY_ZOOM,
                "ignore": False, # Set to True to skip rebuilding this map.
            },
            {
                "mapname": Config.LABEL_MAP, 
                "description": """<p>This layer contains only labels and the county boundary. Use it as a reference layer.</p>""" 
                + layer_desc + project_desc,
                "min_zoom": Config.MIN_COUNTY_ZOOM,
                "ignore": False, # Set to True to skip rebuilding this map.
            },
            {
                "mapname": Config.FEATURE_MAP, 
                "description": """<p>This layer is contains the shapes only, no labels. Use it above a basemap.</p>""" 
                + layer_desc + project_desc,
                "min_zoom": Config.MIN_COUNTY_ZOOM,
                "ignore": False, # Set to True to skip rebuilding this map.
            },

        ]

    gis = GIS(Config.PORTAL_URL, Config.PORTAL_USER, Config.PORTAL_PASSWORD)
    print(f"Logged in to {Config.PORTAL_URL} as {str(gis.properties.user.username)}.")
    pc = PortalContent(gis)

    # Validate the group list
    staging_groups = pc.getGroups(Config.STAGING_GROUP_LIST)

    progress = 0
    total = len(mapnames)
    for item in mapnames:
        mapname = item["mapname"]
        progress += 1

        item["pkgname"] = mapname.replace(' ', '_')
        pkgname = item["pkgname"]

        if item['ignore'] : 
            print(f"{progress}/{total} Skipping \"{mapname}\". \"ignore\" option is set.")
            continue
        print(f"{progress}/{total} \"{mapname}\" => \"{pkgname}\".")
         
        map = find_map(aprx, mapname)
        if not map:
            print("    ERROR! Map not found in APRX. Skipping \"%s\"." % mapname)
            continue

        print("    Building package.")
        try:
            # When debugging the publish step you can change overwrite to False
            # so you don't have to wait each iteration for the package build step.
            # Don't forget to change it back!!!
            item["pkgfile"] = build_tile_package(map, pkgname, 
                                                 min_zoom=item["min_zoom"], 
                                                 overwrite=True)
        except Exception as e:
            print("   Could not generate tiles.", e)
            if e.args[0].startswith("ERROR 001117"):
                print("   ERROR. You need to open the APRX file in ArcGIS Pro and put a description in \"%s\"." % mapname)
            item['pkgfile'] = ''
            print("   Skipping \"%s\"." % mapname)
            continue

        print("    Uploading tile package to server.")
        pkg_item = upload_tile_package(gis, pkgname, item['pkgfile'], item["description"], overwrite=True)
        if not pkg_item: continue
        # NB if you don't set "allow_members_to_edit" True then groups=groups will fail.
        res = pkg_item.share(everyone=False, org=False, groups=staging_groups, allow_members_to_edit=True)

        print("    Staging service.")
        lyr_item = stage_tile_service(gis, pkg_item, pkgname, item["description"], overwrite=True)
        if not lyr_item: 
            print("   Service could not be staged.")
            continue

        # NB if you don't set "allow_members_to_edit" True then groups=groups will fail.
        res = lyr_item.share(everyone=False, org=False, groups=staging_groups, allow_members_to_edit=True)
        url = Config.PORTAL_URL + f"/home/item.html?id={lyr_item.id}"
        print(f"Published at {lyr_item.homepage}")
        print("")

    print("All done.")
