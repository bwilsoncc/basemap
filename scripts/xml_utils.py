import os
import xml.dom.minidom as DOM


def EnableFeatureLayers(doc):

    # Find all elements named TypeName
    # This is where the extensions are defined
    typeNames = doc.getElementsByTagName("TypeName")
    for typeName in typeNames:
        # Get the TypeName to enable
        if typeName.firstChild.data == "FeatureServer":
            extension = typeName.parentNode
            for extElement in extension.childNodes:
                if extElement.tagName == "Enabled":
                    extElement.firstChild.data = "true"

    return doc

def ConfigureFeatureserverCapabilities(doc, capabilities):

    # "TypeName" is where the additional layers and capabilities are defined
    typeNames = doc.getElementsByTagName("TypeName")
    for typeName in typeNames:
        # Get the TypeName to enable
        if typeName.firstChild.data == "FeatureServer":
            extension = typeName.parentNode
            for extElement in extension.childNodes:
                if extElement.tagName == "Info":
                    for propSet in extElement.childNodes:
                        for prop in propSet.childNodes:
                            for prop1 in prop.childNodes:
                                if prop1.tagName == "Key":
                                    if prop1.firstChild.data == "WebCapabilities":
                                        if prop1.nextSibling.hasChildNodes():
                                            prop1.nextSibling.firstChild.data = (
                                                capabilities
                                            )
                                        else:
                                            txt = doc.createTextNode(capabilities)
                                            prop1.nextSibling.appendChild(txt)
    return doc

if __name__ == "__main__":

    # Consider this a unit test

    outdir = r"C:\Temp"
    service_name = "Taxlot_Queries"
    sddraft_filename = service_name + ".sddraft"
    sddraft_output_filename = os.path.join(outdir, sddraft_filename)

    # Read the .sddraft file
    doc = DOM.parse(sddraft_output_filename)

    # Modify the DOM to enable feature layers for each map layer.
    doc = EnableFeatureLayers(doc)

    # Modify the DOM to change feature layer properties
    # Defaults are Query,Create,Update,Delete,Uploads,Editing
    # Comment out the line below if you don't want to modify feature layer properties
    doc = ConfigureFeatureserverCapabilities(doc, "Create,Sync,Query")

    # OVERWRITE the original .sddraft file
    with open(sddraft_output_filename, "w") as fp:
        doc.writexml(fp)

    print("Unit tests passed.")
