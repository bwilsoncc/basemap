import os
from xml.sax.handler import feature_namespace_prefixes

# In PRODUCTION conda sets up the environment,
# so look in ~/.conda/envs/covid/etc/conda/activate.d/env_vars.sh
# to see how it is set up.


class Config(object):
    """ Read environment here to create configuration data. """

    # Use absolute path for APRX, because it will be published in Server properties for the service.
    BASEMAP_APRX = os.environ.get("BASEMAP_APRX") or "basemap.aprx"
    TAXMAP_APRX = os.environ.get("TAXMAP_APRX") or "Taxmaps\\TaxMaps.aprx"
#    TAXMAP_APRX = os.environ.get("TAXMAP_APRX") or os.path.abspath("Taxmaps\\TaxMaps.aprx")

    TAXLOTS_LYRX = os.environ.get("TAXLOT_LYRX") or "Taxmaps\\Taxlots.lyrx"
    PORTAL_URL = os.environ.get('PORTAL_URL') or "https://delta.co.clatsop.or.us/portal"

    CHAT_USER="bwilson"
    CHAT_PASSWORD = os.environ.get("PORTAL_PASSWORD")
    CHAT_SERVER = "https://chat.clatsopcounty.gov" 

    # This is a server connection file set up with enough permission to write to the ArcGIS Server.
    SERVER_AGS = os.environ.get('SERVER_AGS') or "server_on_delta.ags"
    
    # The layers in this BASEMAP map will define our datasources in EGDB
    DATASOURCE_MAP = '2913 sources for services'

    # This will be used to overwrite the existing MIL.
    TAXLOTS_MAP = 'Taxlots'
    
    LABEL_MAP = "Vector Tile Labels"
    FEATURE_MAP = "Unlabeled Vector Tiles"
    COMBINED_MAP = "Vector Tiles"

    ROAD_MAP = "Roads"

    WM_SRS = "PROJCS[\"WGS_1984_Web_Mercator_Auxiliary_Sphere\",GEOGCS[\"GCS_WGS_1984\",DATUM[\"D_WGS_1984\",SPHEROID[\"WGS_1984\",6378137.0,298.257223563]],PRIMEM[\"Greenwich\",0.0],UNIT[\"Degree\",0.0174532925199433]],PROJECTION[\"Mercator_Auxiliary_Sphere\"],PARAMETER[\"False_Easting\",0.0],PARAMETER[\"False_Northing\",0.0],PARAMETER[\"Central_Meridian\",0.0],PARAMETER[\"Standard_Parallel_1\",0.0],PARAMETER[\"Auxiliary_Sphere_Type\",0.0],UNIT[\"Meter\",1.0]]"
    LOCAL_SRS = "PROJCS[\"NAD_1983_HARN_StatePlane_Oregon_North_FIPS_3601_Feet_Intl\",GEOGCS[\"GCS_North_American_1983_HARN\",DATUM[\"D_North_American_1983_HARN\",SPHEROID[\"GRS_1980\",6378137.0,298.257222101]],PRIMEM[\"Greenwich\",0.0],UNIT[\"Degree\",0.0174532925199433]],PROJECTION[\"Lambert_Conformal_Conic\"],PARAMETER[\"False_Easting\",8202099.737532808],PARAMETER[\"False_Northing\",0.0],PARAMETER[\"Central_Meridian\",-120.5],PARAMETER[\"Standard_Parallel_1\",44.33333333333334],PARAMETER[\"Standard_Parallel_2\",46.0],PARAMETER[\"Latitude_Of_Origin\",43.66666666666666],UNIT[\"Foot\",0.3048]]"
    TRANSFORMS = ["NAD_1983_HARN_To_WGS_1984_2"]

    GIT_BASE = 'https://github.com/bwilsoncc/basemap/'

    # This gets tagged onto the service description so we can figure out how to do it again in 3 months.
    DOC_LINK = f"<a target=\"_github\" href=\"{GIT_BASE}#readme\">README for this project</a></p>"

    SCRATCH_WORKSPACE = "C:\TEMP"
    if not os.path.exists(SCRATCH_WORKSPACE):
        SCRATCH_WORKSPACE = os.environ["TEMP"]

    PORTAL_USER = os.environ.get('PORTAL_USER')
    PORTAL_PASSWORD = os.environ.get('PORTAL_PASSWORD')

    STAGING_GROUP_LIST = ['GIS Team']
    RELEASE_GROUP_LIST = ['GIS Team']
    STAGING_TAG_LIST = ['"Clatsop County"']
    CREDITS = 'Clatsop County GIS Services'

    DISCLAIMER_TEXT = """Disclaimer: This data was produced using Clatsop County GIS data. 
The data is maintained by Clatsop County to support its governmental activities. 
Clatsop County is not responsible for any map errors, possible misuse, or misinterpretation."""

    # Scales https://www.esri.com/arcgis-blog/products/product/mapping/web-map-zoom-levels-updated/
    MIN_COUNTY_ZOOM = 1155581.108577  # LOD  9
    MIN_TAXLOT_ZOOM =  144447.638572  # LOD 12
    MAX_ZOOM        =      70.5310735 # LOD 23

    pass


if __name__ == "__main__":

    assert Config.PORTAL_URL
    assert Config.PORTAL_USER
    assert Config.PORTAL_PASSWORD

    assert os.path.exists(Config.SERVER_AGS)
    assert Config.SCRATCH_WORKSPACE
    
    assert Config.STAGING_GROUP_LIST
    assert Config.STAGING_TAG_LIST

    assert os.path.exists(Config.BASEMAP_APRX)
    assert os.path.exists(Config.TAXMAP_APRX)
    assert os.path.exists(Config.TAXLOTS_LYRX)

    print("All tests passed.")

# That's all!
