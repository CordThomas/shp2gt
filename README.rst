Shp2GT
------

To convert an ESRI Shapefile to the graph-tool (https://graph-tool.skewed.de)
native format, the binary GT format, load a source .shp file, verify it's
integrity, and then save as a binary .gt file.

    >>> from shp2gt import *
    >>> converter = Shp2Gt()
    >>> converter.load('~/data/roads.shp')
    >>> converter.verify()
    >>> converter.save('~/data/roads.gt')

