        print("Delete unwanted fields.")
# Republish raster tiles for a basemap

import sys, os
import arcpy

map_image_layer = "https://delta.co.clatsop.or.us/server/rest/services/Hosted/Astoria_Base_Map/MapServer"
area_of_interest = None

def do_work(input_service, area_of_interest) :
    scales = [11, 12, 13, 14, 15, 16]

    # You should provide one of these
    aoi_featureset = None
    update_extent = None

    # Does the service already exist?
    # if blah blah
    
    # I could make up a tiling scheme here and save it in an XML file
    # and then send the XML file into the Create*

    try:
        arcpy.CreateMapServerCache_server(input_service, service_cache_directory,
                "NEW",  
                scales_type, 
                6, 96, tile_size="256x256",
                tile_origin=
                scales=[9028,18056,36112,72224,144448,288895])
    except Exception as e:
        print("Create failed; ", e)
    
    try:
        out_job_url = arcpy.ManageMapServerCacheTiles_server(input_service, scales, "RECREATE_ALL_TILES", -1, aoi_featureset, update_extent, True)
        print("Look at this URL for status:", out_job_url)

    except Exception as e:
        print("A serious error occurred; ", e)
        return False
    return True

if __name__ == '__main__':
    print("here we are")
    do_work(map_image_layer, area_of_interest)

