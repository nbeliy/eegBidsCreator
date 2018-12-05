import xml.etree.ElementTree as ElementTree
from datetime import datetime

def addDict(parent):
    d = dict()
    for child in parent:
        data = child.get('{urn:schemas-microsoft-com:datatypes}dt', None)
        if data != None :
            del child.attrib['{urn:schemas-microsoft-com:datatypes}dt']
            try:
                if child.text = None:
                    d[child.tag] = None
                else:
                    if data == 'string':
                        d[child.tag] = child.text
                    elif data == 'datetime':
                        d[child.tag] = datetime.strptime(child.text+"000", "%Y-%m-%dT%H:%M:%S.%f")
                    elif data == 'r8':
                        d[child.tag] = float(child.text)
                    elif data == 'i2' or data == 'i4':
                        d[child.tag] = int(child.text)
                    else :
                        raise Exception("Unown type {}".format(data))
            except Exception as e:
                print(e)
                d[child.tag] = child.text
            d.update(parent.attrib)
        else : 
            d[child.tag] = addDict(child)
    d.update(parent.attrib)
    return d
    



def ParceRecording(xml):
    root = ElementTree.fromstring(xml)
    return addDict(root)
    
    

