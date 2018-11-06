Shp2GT
------

To convert an ESRI Shapefile to the graph-tool (https://graph-tool.skewed.de)
native format, the binary GT format, load a source .shp file, verify it's
integrity, and then save as a binary .gt file.

    >>> import shp2gt
    >>> converter = Shp2GT()
    >>> converter.load('~/data/roads.shp')
    >>> converter.verify()
    >>> converter.save('~/data/roads.gt')

