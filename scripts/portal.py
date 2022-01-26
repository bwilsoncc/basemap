"""
This file contains a class "PortalContent" that supplements the ArcGIS GIS ContentManager class.

Currently it's a different version of the 'search' method that does exact
instead of fuzzy searches by using the REST 'filter' option.

find_* comments
    Weirdness #1: This only searchs PORTAL and if for any reason a "delete" fails
    to delete the SERVICE on the SERVER, then when you try to publish, this 
    function will not find any service but the publishing will FAIL saying the
    service already exists and currently that means going to server manager
    and finding and deleting the service manually!!

    Weirdness #2: if you search for a name with an extension on it, eg "tilepack.vtpk",
    and there is a file by that name, it will strip off the extension and the search
    will fail. You need to search by name="tilepack" and type="Vector Tile Package",
    or I need to modify this function to strip the extension and add the type!
    See the unit tests for examples.

"""
import os
from arcgis.gis import GIS

class PortalContent(object):

    VectorTileService = 'Vector Tile Service'
    VectorTilePackage = 'Vector Tile Package'

    def __init__(self, gis) -> None:
        self.gis = gis
        return

    def find_items(self, title=None, name=None, type=None) -> list:
        """ 
        Search the Portal using any combination of name, title, and type.
        Return the list of items if there were any matches else None.
        """
        connection = self.gis._con

        # https://developers.arcgis.com/rest/users-groups-and-items/search-reference.htm
        url = connection.baseurl + 'search'
        q = ''
        if name:
            q += 'name:"%s"' % name
        if title:
            if q: q += ' AND '
            q += 'title:"%s"' % title
        if type:
            if q: q += ' AND '
            q += 'type:"%s"' % type
        params = {
            'q': '',     # This is required. This is the fuzzy match operation.
            'filter': q  # This is the exact match operation.
        }
        res = connection.post(url, params)
        if res['total'] > 0:
            return res['results']
        return None

    def find_item(self, title=None, name=None, type=None):
        """ 
        Search the Portal using any combination of name, title, and type.
        Return the item if exactly one match is found, else None.
        """
        items = self.find_items(title, name, type)
        if not items or len(items)!=1:
            return None
        return self.gis.content.get(items[0]['id'])

    def find_id(self, title=None, name=None, type=None):
        """ 
        Search the Portal using any combination of name, title, and type.
        Return the id if exactly one match is found, else None.
        """
        item = self.find_item(title, name, type)
        if not item: 
            return None
        return item.id

    def get_groups(self, groups):
        """
            Search the groups on the portal using a string or list of strings.
            Return a list of IDs that can be used to set groups on items.
        """
        # Validate the list of groups by looking them up.
        group_ids = []
        if isinstance(groups,str):
            groups = [groups]
        for g in groups: 
            try:
                group_ids.append(
                    self.gis.groups.search('title:\"%s\"' % g, outside_org=False)[0]
                )
            except Exception as e:
                print("Group '%s' not found." % g, e)
        return group_ids

"""
    NOT WORKING
    def rename(self, oldname=None, newname=None, type=None) -> bool:
        connection = self.gis._con

        # https://developers.arcgis.com/rest/users-groups-and-items/search-reference.htm
        url = 'https://delta.co.clatsop.or.us/server/renameService'
        params = {
            'serviceName': oldname,
            'serviceNewName': newname,
            'serviceType': type,
            'f': 'json'
        }
        res = connection.post(url, params)
        return res['status'] == 'success'
"""

# -----

def show(items) -> None:
    """ Show brief information about an item or each item in a list. """
    if items:
#       print(json.dumps(items, indent=4)) # This is the verbose version
        if not isinstance(items, list): items = [items]
        for item in items:
            print(item["id"], item["name"], '||', item["title"], '||', item["type"])
    return

if __name__ == '__main__':

    from config import Config
    import json
    portal = GIS(Config.PORTAL_URL, Config.PORTAL_USER, Config.PORTAL_PASSWORD)
    print("Logged in as " + str(portal.properties.user.username))
    pc = PortalContent(portal)

    item = pc.find_item(title='Clatsop_County', type=pc.VectorTileService)
    show(item)

    groups = pc.get_groups(Config.STAGING_GROUP_LIST)
    print(groups)

    groups = pc.get_groups('GIS Team')
    print(groups)
    groups = pc.get_groups(['GIS Team', 'Emergency Management', 'NO SUCH GROUP'])
    print(groups)

    item = pc.find_item(name='Vector_Tiles', title='Vector Tiles', type=pc.VectorTileService)
    show(item)

    show(pc.find_items(name='Unlabeled_Vector_Tiles'))
    show(pc.find_items(name='Unlabeled_Vector_Tiles',
        title='Unlabeled_Vector_Tile_Layer'))

    show(pc.find_items(type=pc.VectorTileService))

    # SADLY it's still not an exact match! See comments at the top of the file
    print(pc.find_id(name='Unlabeled_Vector_Tiles.vtpk')) # This fails even if the file exists

    print(pc.find_id(name='Unlabeled_Vector_Tiles', type=pc.VectorTilePackage))

    print(pc.find_id(title='Unlabeled_Vector_Tiles'))
    print(pc.find_id(title='Unlabeled_Vector_Tiles', type=pc.VectorTileService))

    print(pc.find_id(name='Unlabeled_Vector_Tiles',
        title='Unlabeled_Vector_Tile_Layer',
        type=pc.VectorTileService))

    exit(0)
    
