"""
Builds the "basemap" vector tiles and stages them to the server.
Once you have done QC use the release_services script.

Watermarks are disabled right now, something broke there.

TODO: Rewrite as a python tool

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
from scripts.portal import PortalContent, show

#from watermark import mark

# Scales https://www.esri.com/arcgis-blog/products/product/mapping/web-map-zoom-levels-updated/
MIN_ZOOM = 1155581.108577  # LOD  9
MAX_ZOOM = 70.5310735      # LOD 23

def find_map(aprx, mapname):
    maps = aprx.listMaps(mapname)
    if len(maps) != 1: return None
    return maps[0]


def build_tile_package(map, pkgname, overwrite=False):
    """ Build a tile package. Does not overwrite by default.

    'map' is a map from an aprx
    'pkgname' is the name of the package (will be the filename too)

    Returns absolute pathname of package if a package was built or None
    (We need the path to be absolute when we do the "add" in staging.)
    """
    pkgfile = os.path.join(arcpy.env.workspace, pkgname + '.vtpk')
    if arcpy.Exists(pkgfile): # BTW, this uses the workspace env
        if overwrite:
            os.unlink(pkgfile)
        else:
            return pkgfile

    # I tried to add a description to the map object here but it did not work.
    # If there is no description, the Esri tool fails. Sorry.

    # Note, we'll update metadata later .
    # BTW, that 99999 error you're getting could be a definition query problem.
    arcpy.management.CreateVectorTilePackage(map, pkgfile, 
        "ONLINE", None, "INDEXED", 
        MIN_ZOOM, MAX_ZOOM
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
    

def upload_tile_package(portal, pkgname, pkgfile, original_thumbnail, textmark, description, overwrite=True):
    """ 
    Upload a tile package.

    Return package item or None
    """
    pc = PortalContent(portal)
    pkg_item = None

    # Snippet (aka "summary") can't contain markup.
    snippet = ("%s (%s)" % (pkgname, textmark)).replace('_', ' ')

    # 2021-10-15 I've had this fail, I worked around it by deleting manually. 
    existing_item = pc.find_item(name=pkgname, type=pc.VectorTilePackage)
    if existing_item:
        if overwrite:
            delete_item(existing_item)
        else:
            print("WARNING: Target exists and overwrite=False, skipping upload.")
            return existing_item

    try:
        # Basically ANY or ALL the metadata can be written with the add() method.
        # Thumbnail will come from the package if you don't specify one here.
        pkg_item = portal.content.add({
                'title': pkgname.replace('_', ' '),
            },
            data=pkgfile, # Absolute path or URL
            folder="Basemaps"
        )
    except Exception as e:
        print("Upload did not work for %s!" % pkgname, e)
        return None

    outname = os.path.join(Config.SCRATCH_WORKSPACE, 'package_thumbnail.png')
    #pkg_thumbnail = mark(original_thumbnail, outname, caption='Vector Tile Package', textmark=textmark)
    
    pkg_item.update(
        item_properties = {
            "title": snippet,
            "snippet": snippet,
            "tags": Config.STAGING_TAG_LIST, # This can be a list or a string
            "accessInformation": Config.CREDITS,
            "licenseInfo": Config.DISCLAIMER_TEXT, 
            "description": description,
        },
        #thumbnail = pkg_thumbnail
    )
    #os.unlink(pkg_thumbnail)

    # Remember, markup won't work here, neither will newlines
    comment = "Uploaded %s" % textmark
    try:
        pkg_item.add_comment(comment)
    except Exception as e:
        print("Could not add package comment \"%s\". -- %s" % (comment, e))

    return pkg_item


def stage_tile_service(portal, pkg_item, pkgname, original_thumbnail, snippet, description, overwrite=True):
    """ 
    Publish a tile package as a service.

    Returns layer service item or None
    """
    pc = PortalContent(portal)
    lyr_item = None
    
    # Snippet (aka "summary") can't contain markup.
    snippet = ("%s (%s)" % (pkgname, textmark)).replace('_', ' ')

    # Publish the (uploaded) tile package as a hosted service
    # "overwrite = True" always seems to break here no matter what.
    
    lyr_title = (pkgname + ' STAGED').replace('_',' ')
    existing_item = pc.find_item(title=lyr_title, type=pc.VectorTileService) 
    if existing_item:
        if overwrite:
            if existing_item.content_status == 'org_authoritative':
                print("Won't overwrite authoritative layer \"%s\"." % existing_item.title)
            else: 
                delete_item(existing_item)
        else:
            return None

    print("Staging tile service...")

#    lyr_name = pkgname # "Vector_Tiles" was failing failing failing!
    lyr_name = (pkgname + '_' + datestamp).replace(' ', '_')
    lyr_items = pc.find_items(name=lyr_name, type=pc.VectorTileService)
    if lyr_items:
        # dearie me there is at least one service with this name so pick another
        print("I see this is not a unique layername so I am trying to use \"%s\"." % lyr_name)

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
        print("service item", lyr_item)

    except Exception as e:
        print("Publishing failed!", e)
        # "Service name 'Vector_Tiles' already exists for '0123456789'"
        items = pc.find_items(name=lyr_name) 
        show(items)
        items = pc.find_items(title=lyr_title) 
        show(items)
        return None

    outname = os.path.join(Config.SCRATCH_WORKSPACE, 'layer_thumbnail.png')
#    lyr_thumbnail = mark(original_thumbnail, outname, caption='Vector Tile Service', textmark=textmark)

    lyr_item.update(
        item_properties = {
            #"title": snippet, Title was already set in publish step.
            "snippet": snippet,
            "tags": Config.STAGING_TAG_LIST, # This can be a list or a string
            "accessInformation": Config.CREDITS,
            "licenseInfo": Config.DISCLAIMER_TEXT, 
            "description": description,
        }, 
#        thumbnail = lyr_thumbnail
    )
    #os.unlink(lyr_thumbnail)

    # Remember, markup won't work here, neither will newlines
    comment = "Staged %s" % textmark
    try:
        lyr_item.add_comment(comment)
    except Exception as e:
        print("Could not add the layer comment! Darn.", e)

    return lyr_item

# ==========================================================================

if __name__ == "__main__":

    (scriptpath, scriptname) = os.path.split(__file__)

    arcpy.env.workspace = Config.SCRATCH_WORKSPACE 

    initials  = os.environ.get('USERNAME')[0:2].upper()
    datestamp = datetime.now().strftime("%Y%m%d %H%M") # good for filenames
    textmark  = datetime.now().strftime("%m/%d/%y %H:%M") + ' ' + initials # more readable

    portal = GIS(Config.PORTAL_URL, Config.PORTAL_USER, Config.PORTAL_PASSWORD)
    print("%s Logged in as %s" % (textmark, str(portal.properties.user.username)))
    pc = PortalContent(portal)

    try:
        aprx = arcpy.mp.ArcGISProject(Config.APRX_FILE)
    except Exception as e:
        print("Can't open APRX file,", e)
        exit(-1)

    layer_desc = """<p>Feature layers: Roads, Parks, Water (lines), Water (polygons), County Boundary <br /></p>
    <p>NOTE, it is in <b>WEB MERCATOR</b></p>"""
    project_desc = "<p>Project file: \"%s\"" % aprx.filePath

    mapnames = [
        {
            "mapname": "Vector Tiles", 
            "description": """<p>This layer is optimized for use in Collector and Field Maps; use it as a basemap for offline field work.
It includes both the labels and the features in one vector tile layer.</p>""" + layer_desc + project_desc + Config.ATTRIBUTION,
        },
        {
            "mapname": "Vector Tile Labels", 
            "description": """<p>This layer contains only labels and the county boundary. Use it as a reference layer.</p>""" 
                + layer_desc + project_desc + Config.ATTRIBUTION,
        },
        {
            "mapname": "Unlabeled Vector Tiles", 
            "description": """<p>This layer is contains the shapes only, no labels. Use it above a basemap.</p>""" 
            + layer_desc + project_desc + Config.ATTRIBUTION,
        }
    ]

    # Validate the group list
    staging_groups = pc.get_groups(Config.STAGING_GROUP_LIST)

    total = len(mapnames)

    print("Building tile packages.")
    n = 0
    for item in mapnames:
        mapname = item["mapname"]
        item["pkgname"] = mapname.replace(' ', '_')
        n += 1
        progress = "%d/%d" % (n, total)
        
        map = find_map(aprx, mapname)
        if not map:
            print("ERROR! Map not found in APRX. Skipping \"%s\"." % mapname)
            continue

        try:
            print(progress, "Building \"%s\"." % item["pkgname"])
            # When debugging the publish step you can change overwrite to False
            # so you don't have to wait each iteration for the package build step.
            # Don't forget to change it back!!!
            item["pkgfile"] = build_tile_package(map, item["pkgname"], overwrite=False)
        except Exception as e:
            print("Could not generate tiles.", e)
            if e.args[0].startswith("ERROR 001117"):
                print("ERROR. You need to open the APRX file in ArcGIS Pro and put a description in \"%s\"." % mapname)
                print("Skipping \"%s\"." % mapname)
            continue
    print("Build completed.")

    n = 0
    for item in mapnames:
        pkgname = item["pkgname"]
        pkgfile = item["pkgfile"]
        n += 1
        progress = "%d/%d" % (n, total)

        # Get the thumbnail from the map.
        original_thumbnail = map.metadata.thumbnailUri
        ok = os.path.exists(original_thumbnail)

        print("%s Uploading tile package. %s" % (progress, pkgname))
        pkg_item = upload_tile_package(portal, pkgname, pkgfile, original_thumbnail, textmark, item["description"], overwrite=True)
        if not pkg_item: continue
        # NB if you don't set "allow_members_to_edit" True then groups=groups will fail.
        res = pkg_item.share(everyone=False, org=False, groups=staging_groups, allow_members_to_edit=True)

        print("%s Staging service. %s" % (progress, pkgname))
        lyr_item = stage_tile_service(portal, pkg_item, pkgname, original_thumbnail, textmark, item["description"], overwrite=True)
        if not lyr_item: continue
        # NB if you don't set "allow_members_to_edit" True then groups=groups will fail.
        res = lyr_item.share(everyone=False, org=False, groups=staging_groups, allow_members_to_edit=True)

    print("All done!!!")
# That's all!
