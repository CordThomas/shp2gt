Shp2GT
------

## Summary

To convert an ESRI Shapefile to the graph-tool (https://graph-tool.skewed.de)
native format, the binary GT format, load a source .shp file, verify it's
integrity, and then save as a binary .gt file.

## Installation

The code is provided as a package.  To install the package into your
python3 environment, execute:

    >>> python3 setup.py install

## The Process Overview

There are basically two steps to the process:

* Load a shapefile.
  * Provide the relative or full path to the file and the key identifying field in the shapefile
  * The load method converts the shape file to a memory-based GT network
* Save the GT binary record
  * Provide the relative or full path to the output file

## Usage

    >>> from shp2gt import *
    >>> converter = Shp2Gt()
    >>> converter.load('~/data/roads.shp', 'osmid')
    >>> converter.verify()
    >>> converter.save('~/data/roads.gt')

