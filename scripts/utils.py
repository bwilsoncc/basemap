from arcgis.gis import GIS
from portal import PortalContent, show
from config import Config

def getServiceItem(gis:object, pc:object, title:str, type=None) -> object:
    """
    Given the service tuple, 
    make sure it matches only 1 existing service,
    return it.
    """
    item = None
    ids = pc.find_ids(title=title, type=type)
    if len(ids) != 1:
        # If there are multiple services with the same name, you need to delete the extra(s) yourself!
        print("ERROR: %d matches for \"%s\" found." % (len(ids), title))
        if len(ids):
            print("Service IDs:", ids)
    else:
        # Load the metadata from the existing layer.
        item = gis.content.get(ids[0])
    return item

if __name__ == "__main__":
    # unit test

    gis = GIS(Config.PORTAL_URL, Config.PORTAL_USER, Config.PORTAL_PASSWORD)
    print("Logged in as " + str(gis.properties.user.username))
    pc = PortalContent(gis)

    svc = getServiceItem(gis, pc, "DELETEME_Roads", type=pc.MapImageLayer)
    show(svc)

    svc = getServiceItem(gis, pc, "DELETEME_Roads")
    show(svc)

    print("All done!")

