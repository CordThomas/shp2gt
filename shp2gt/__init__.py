from osgeo import ogr, osr
import configparser, os
from graph_tool import util as gutil
from graph_tool import topology as gtopo
from graph_tool.all import *

# http://epydoc.sourceforge.net/manual-fields.html
# https://graph-tool.skewed.de/performance
"""Convert a line shapefile from a source file to a graph-tool GT file.

   Given a street network in the ESRI Shapefile format, convert the 
   file to the native GT format supported by the graph-tool for
   us in various network analyses.  The script assumes you are
   working with census street lines, that the geoid is the 
   unique identifier for starting nodes of a network, that the
   graph is undirected.   
   
   The script uses the line end point nodes or vertices coordinates (lat/lon) as
   unique identifiers in building the network.  It supports both
   linestring and multilinestring 
"""

__author__ = "Cord Thomas"
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Cord Thomas"
__email__ = "cord.thomas@gmail.com"
__status__ = "Prototype"


class Shp2Gt (object):

  # Convert a multilinestring to a linestring
  def _convert_multilinestring_to_linestring(self, multilinestring):

    if (multilinestring.GetGeometryType() == ogr.wkbLineString):
      return multilinestring
    else:
      ls = ogr.Geometry(ogr.wkbLineString)
      for linestr in multilinestring:
        # print ('Processing MLS with line {}'.format(linestr))
        for pnt in linestr.GetPoints():
          # print ('Processing MLS with point {}'.format(pnt))
          ls.AddPoint(pnt[0], pnt[1])

      return ls

  def _set_graph_properties(self):
    """Initiate the graph object with attributes from the shapefile.

       Adds some key fields to the vertices needed for network analysis
       and copy the fields from the shapefile.  Adds a weight_distance field
       that will be populated with the calculated length of each linestring.
       Could also add a weight_traffic or weight_terrain as other measures
       of network performance."""
    v_prop = self.graph.new_vertex_property("string")
    self.graph.vertex_properties["geoid"] = v_prop
    v_prop = self.graph.new_vertex_property("string")
    self.graph.vertex_properties["latlon"] = v_prop

    for i in range(self.shape_layer_defn.GetFieldCount()):
      e_prop = self.graph.new_edge_property(self.shape_layer_defn.GetFieldDefn(i).GetTypeName().lower())
      self.graph.edge_properties[self.shape_layer_defn.GetFieldDefn(i).GetName()] = e_prop

    e_prop = self.graph.new_edge_property("double")
    self.graph.edge_properties["weight_dist"] = e_prop

    print(self.graph.list_properties())

  def _add_graph_vertices(self, feature):
    """Add the graph verices as the end points of the street geometry.
       This method first checks whether each vertex has already been
       added to the network and if not adds it.  The method
       uses the vertex's XY coordiantes as unique identifiers.  It's
       technically possible that a Shapefile street network might have multiple
       nodes at a single location, there's no reason to duplicate those
       in a transportation analysis network.

       The key to a vertex is its latlon value which is a colon-separated
       lat/lon value from the street graph's start and end nodes.
       e.g.,
           "11914024.0:3024277.1", "11915337.4:3023873.7"
           "11914067.9:3024195.7", "11914264.2:3024196.6"
       """
    v1, v2 = None, None
    line_geometry = self._convert_multilinestring_to_linestring(feature.GetGeometryRef())
    start_vertex_lon, start_vertex_lat, start_vertex_z = line_geometry.GetPoint(0)
    end_vertex_lon, end_vertex_lat, end_vertex_z = line_geometry.GetPoint(line_geometry.GetPointCount() - 1)
    start_lat_lon = str(start_vertex_lat)  + ":" + str(start_vertex_lon)
    end_lat_lon = str(end_vertex_lat)  + ":" + str(end_vertex_lon)

    geoid = ""

    if feature.GetFieldIndex("geoid") > -1:
      geoid = feature.GetField("geoid")

    vertex_index = self.graph.vertex_properties["latlon"]
    vertex_geoid = self.graph.vertex_properties["geoid"]

    """Possibly add the first node of the street segment and set the 
       geoid if it's available"""
    vertices = gutil.find_vertex(self.graph, vertex_index, start_lat_lon)
    if (len(vertices) == 0):
      v1 = self.graph.add_vertex()
      vertex_index[self.graph.vertex(v1)] = start_lat_lon
      vertex_geoid[self.graph.vertex(v1)] = geoid
    else:
      v1 = vertices[0]

    """Possibly add the second node of the street segment. Here we don't
       care about the GeoID because it only belongs on the starting node."""
    vertices = gutil.find_vertex(self.graph, vertex_index, end_lat_lon)
    if (len(vertices) == 0):
      v2 = self.graph.add_vertex()
      vertex_index[self.graph.vertex(v1)] = start_lat_lon
    else:
      v2 = vertices[0]

    return v1, v2

  def _add_graph_edge(self, feature, start_vertex, end_vertex, weight):
    """Add a graph edge between the vertices provided, using the
       feature attributes.
       """

    edge = self.graph.add_edge(start_vertex, end_vertex)
    for i in range(feature.GetFieldCount()):
      fielddef = feature.GetFieldDefnRef(i)
      field_value = feature.GetField(fielddef.GetName())
      edge_field = self.graph.edge_properties[fielddef.GetName()]
      edge_field[edge] = field_value

    weight_field = self.graph.edge_properties["weight_dist"]
    weight_field[edge] = weight

  def __init__(self):
    self.driver = ogr.GetDriverByName('ESRI Shapefile')

  def get_shortest_path(self, start_geoid, end_geoid):
    """Returns the length of and the vertices involved in the shortest path in the network"""
    start_vertex, end_vertex = None, None
    vertex_geoid = self.graph.vertex_properties["geoid"]
    vertices = gutil.find_vertex(self.graph, vertex_geoid, start_geoid)
    if (len(vertices) > 0):
      start_vertex = vertices[0]
    vertices = gutil.find_vertex(self.graph, vertex_geoid, end_geoid)
    if (len(vertices) > 0):
      end_vertex = vertices[0]

    if (start_vertex is not None) and (end_vertex is not None):
      shortest_vertices = gtopo.shortest_path(self.graph, start_vertex,
                          end_vertex, self.graph.edge_properties["weight_dist"])

      shortest_distance = gtopo.shortest_distance(self.graph, start_vertex,
                          end_vertex, self.graph.edge_properties["weight_dist"])

      return shortest_distance, shortest_vertices
    else:
      return -1, "Could not find start or end vertex"

  def load(self, src):
    """Load a shapefile and initiate processing"""
    self.shape_layer_src = src
    self.shape_datasource = self.driver.Open(self.shape_layer_src, 0)
    self.shape_layer = self.shape_datasource.GetLayer(0)
    self.shape_layer_defn = self.shape_layer.GetLayerDefn()

    self.graph = Graph()
    self._set_graph_properties()

    for feature in self.shape_layer:
      geom = feature.GetGeometryRef()
      length = geom.Length()

      start_vertex, end_vertex = self._add_graph_vertices(feature)
      self._add_graph_edge (feature, start_vertex, end_vertex, length)

  def save(self, outfile):
    self.graph.save(outfile)