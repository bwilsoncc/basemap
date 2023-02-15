"""
    Read from an arcpy map and
    build JSON for a layer list that can be used to define popups.
"""
import os
import arcpy
import json
import subprocess
from config import Config


def makeLayer(layer: arcpy._mp.Layer) -> dict:
    """ 
    Make a popup layer from an arcpy layer.
    Returns a dict or None. 
    """
        
    cimLayer = layer.getDefinition('V2')
    if cimLayer.layerType != 'Operational':
        return None

    showPopups = cimLayer.showPopups
    id = cimLayer.serviceLayerID
    name = cimLayer.name
    popfile = os.path.join(Config.SCRATCH_WORKSPACE, name + '.html')

    print(f'layer name: "{name}" id:{id}, showPopups={showPopups}')
    
    fieldInfoList = list()

    # There won't be any fieldDescriptions for a layer
    # unless you alter the data view in Pro.
    # If there are no FD's then I guess you have to
    # read the field list in the feature class directly.
    # I don't feel like doing that today.
    if not len(cimLayer.featureTable.fieldDescriptions):
        connection = cimLayer.featureTable.dataConnection.workspaceConnectionString
        print(f"There are no fields described for {id} in your map.")
        return None
    
    for field in cimLayer.featureTable.fieldDescriptions:
        if not field.visible: continue
        d = {
            "fieldName": field.fieldName,
            "label": field.fieldName,
        }
        if field.numberFormat:
            d["format"] = {
                "places": field.numberFormat.roundingValue,
                "digitSeparator": field.numberFormat.useSeparator
            }
        else:
            d["stringFieldOption"] = "textbox"
        
        fieldInfoList.append(d)

    popup_info = cimLayer.popupInfo

    expressionList = list()
    for e in popup_info.expressionInfos:
        expressionList.append({
            'expression': e.expression,
            'title': e.title,
            'name': e.name,
            'returnType': e.returnType
        })

    mediaInfoList = list()
    for minfo in popup_info.mediaInfos:
        html = minfo.text
        # Test the HTML by opening it in a browser.
#        with open(popfile, "w") as fp:
#            fp.write(html)
#        if SHOWPOPUP:
#            print("Opening {popfile} in browser")
#            subprocess.check_call([BROWSER, "file:///"+popfile])

    return {
        "id": id,
        "name": name,
        "popupInfo": {
            "fieldInfos": fieldInfoList,
            "expressionInfos": expressionList,
            'mediaInfos': mediaInfoList,
            'description': html
        }
    }


def makePopup(layers: arcpy._mp.Layer) -> dict:
    """
    Using an arcpy layer list as input,
    a list of layers to define a popup, in a dict.
    """
    popupLayers = list()
    for layer in layers:
        # If the layer is not operational (eg a basemap)
        # or no fields are defined in it, None will be returned.
        #
        # Generally since the way we use this is to update
        # a service in Enterprise, empty layers probably 
        # won't hurt us, they will just disappoint us.
        popupDict = makeLayer(layer)
        if popupDict:
            popupLayers.append(popupDict)
    return {"layers": popupLayers}


# ===============================
if __name__ == "__main__":
    # Unit tests

    mapname = "Taxlot Queries"
    aprx = arcpy.mp.ArcGISProject(Config.TAXMAP_APRX)
    map = aprx.listMaps(mapname)[0]
    popupDict = makePopup(map.listLayers())

    print(json.dumps(popupDict,indent=2))

    # For debugging, dump to a file
    json_file = os.path.join(Config.SCRATCH_WORKSPACE, mapname + ".json")
    with open(json_file, 'w') as fp:
        json.dump(popupDict, fp, indent=2)
 
    print("Tests completed.")
