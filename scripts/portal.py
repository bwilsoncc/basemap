"""
This file contains a class "PortalContent" that supplements the ArcGIS GIS ContentManager class.

Esri's 'search' method that does fuzzy matches only (which generally sucks IMO)
whereas here I do exact searches by using the REST 'filter' option.

find* method comments
    Weirdness #1: This only searches PORTAL and if for any reason a "delete" fails
    to delete the SERVICE on the SERVER, then when you try to publish, this 
    function will not find any service but the publishing will FAIL saying the
    service already exists and currently that means going to Server Manager
    and finding and deleting the service manually. Sometimes that fails too
    and you have to actually delete files from server.

    Weirdness #2: if you search for a name with an extension on it, eg "tilepack.vtpk",
    and there is a file by that name, it will strip off the extension and the search
    will fail. You need to search by name="tilepack" and type="Vector Tile Package",
    or I need to modify this function to strip the extension and add the type!
    See the unit tests for examples. 
    I think that it's a bug that it let me publish with the extension 
    and now the poor thing is stranded in there.

"""
import os
from arcgis.gis import GIS

class PortalContent(object):

    VectorTileService = 'Vector Tile Service'
    VectorTilePackage = 'Vector Tile Package'
    MapImageLayer = 'Map Service'
    FeatureService = 'Feature Service'

    def __init__(self, gis) -> None:
        self.gis = gis
        return

    def getItemUrl(self, item: str) -> None:
        """ Show the ID of an item formatted as a Portal URL """
        return f"{self.gis.url}/home/item.html?id={item['id']}"


    def findItems(self, title=None, name=None, type=None) -> list:
        """ 
        Search the Portal using any combination of name, title, and type.
        Return the list of items, which might be empty.
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
        return res['results']


    def findItem(self, title=None, name=None, type=None) -> object:
        """ 
        Search the Portal using any combination of name, title, and type.
        Return the "item" object if EXACTLY ONE MATCH is found, else None.
        """
        items = self.findItems(title, name, type)
        if not items or len(items)!=1:
            return None
        return self.gis.content.get(items[0]['id'])


    def findIds(self, title=None, name=None, type=None) -> list:
        """ 
        Search the Portal using any combination of name, title, and type.
        Return a list of ids, which might be empty.
        """
        items = self.findItems(title, name, type)
        ids = [item['id'] for item in items]
        return ids


    def getServiceItem(self, title:str, type=None) -> object:
        """
        Given the service title and type, 
        make sure it matches only 1 existing service,
        Return the "item" object.

        Services can have identical names, so use a type setting (eg portalcontentmanager.MapImageLayer) to specify one.
        """
        item = None
        items = self.findItems(title=title, type=type)
        if len(items) != 1:
            # If there are multiple services with the same name, you need to delete the extra(s) yourself!
            print(f"ERROR: {len(items)} matches for \"{title}\" found.")
            if len(items):
                # I print all the service names as URLs so you can 
                # use Ctl-Click to open them in a browser.
                print("Service IDs:")
                for item in items:
                    print(self.getItemUrl(item))
        else:
            # Load the metadata from the existing layer.
            d = items[0] # This is a dictionary
            item = self.gis.content.get(d['id']) # this is an "item".

        return item


    def getGroups(self, groups) -> list:
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

    def deprecateService(self, service_name: str) -> bool:
        """
        Change the status on a service to "deprecated".
        """    
        rval = False
        ids = self.findIds(name=service_name, type=self.VectorTileService)
        if len(ids) == 1:
            item = self.gis.content.get(ids[0])
            item.content_status = "deprecated"
            item.protect(enable = False)
            rval = True
        else:
            print("WARNING: I can't find a service named \"%s\"." % service_name)
            items = self.findItems(name=service_name, type=self.VectorTileService)
            PortalContent.show(items)
        return rval


    @staticmethod
    def show(items: list) -> None:
        """ Show brief information about an item or each item in a list. """
        if items:
    #       print(json.dumps(items, indent=4)) # This is the verbose version
            if not isinstance(items, list): items = [items]
            for item in items:
                print(item)
        return
    

##################################################################################
if __name__ == '__main__':

    # TODO make all tests assertions.

    from config import Config
    import json
    gis = GIS(Config.PORTAL_URL, Config.PORTAL_USER, Config.PORTAL_PASSWORD)
    assert gis
    # FIXME SOMEDAY
    #gis = GIS(url=Config.PORTAL_URL, profile=Config.PORTAL_PROFILE)
    assert gis
    print("Logged in as " + str(gis.properties.user.username))
    pcm = PortalContent(gis)

    item = pcm.findItem(title='Vector Tiles', type=pcm.VectorTileService)
    assert item
    PortalContent.show(item)

    item = pcm.getServiceItem(title='Roads')
    assert item

    items = pcm.findItems(title='Roads')
    PortalContent.show(items)

    items = pcm.findItems(title='Roads_hosted')
    PortalContent.show(items)

    items = pcm.findItems(name='Roads_hosted')
    PortalContent.show(items)

    items = pcm.findItems(title='Taxlot_Queries')
    PortalContent.show(items)

    items = pcm.findItems(type=pcm.MapImageLayer)
    PortalContent.show(items)

    items = pcm.findItems(title='Vector Tiles', type=pcm.VectorTileService)
    PortalContent.show(items)

    ids = pcm.findIds(title='Vector Tiles', type=pcm.VectorTileService)
    assert(len(ids)==1) 
    PortalContent.show(ids)

    svc = pcm.getServiceItem("DELETEME_Roads", type=pcm.MapImageLayer)
    assert(not svc)
    PortalContent.show(svc)

    svc = pcm.getServiceItem("DELETEME_Roads")
    assert(not svc)
    PortalContent.show(svc)

    groups = pcm.getGroups(Config.STAGING_GROUP_LIST)
    assert groups
    print(groups)

    groups = pcm.getGroups(Config.RELEASE_GROUP_LIST)
    print(groups)

    groups = pcm.getGroups(['GIS Team', 'Emergency Management', 'NO SUCH GROUP'])
    print(groups)

    item = pcm.findItem(name='Vector_Tiles', title='Vector Tiles', type=pcm.VectorTileService)
    PortalContent.show(item)

    PortalContent.show(pcm.findItems(name='Unlabeled_Vector_Tiles'))
    PortalContent.show(pcm.findItems(name='Unlabeled_Vector_Tiles',
        title='Unlabeled_Vector_Tile_Layer'))

    #all = pc.find_items(type=pc.VectorTileService)
    #print(all)

    # SADLY it's still not an exact match! See comments at the top of the file
    print(pcm.findIds(name='Unlabeled_Vector_Tiles.vtpk')) # This fails even if the file exists

    print(pcm.findIds(name='Unlabeled_Vector_Tiles', type=pcm.VectorTilePackage)) # FIND THE PACKAGE

    # These should all give the same result.
    print(pcm.findIds(title='Unlabeled Vector Tiles'))
    print(pcm.findIds(title='Unlabeled Vector Tiles', type=pcm.VectorTileService))
    print(pcm.findIds(name='Unlabeled_Vector_Tiles',
        title='Unlabeled Vector Tiles',
        type=pcm.VectorTileService))

    exit(0)
    
