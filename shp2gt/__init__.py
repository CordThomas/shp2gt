import sys, time
from osgeo import ogr, osr
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

  _graph = None

  def update_progress(self, w_str):
    w_str = str(w_str)
    sys.stdout.write("\b" * len(w_str))
    sys.stdout.write(" " * len(w_str))
    sys.stdout.write("\b" * len(w_str))
    sys.stdout.write(w_str)
    sys.stdout.flush()

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
    v_prop = self._graph.new_vertex_property("string")
    self._graph.vertex_properties["geoid"] = v_prop
    v_prop = self._graph.new_vertex_property("string")
    self._graph.vertex_properties["latlon"] = v_prop

    for i in range(self._shape_layer_defn.GetFieldCount()):
      e_prop = self._graph.new_edge_property(self._shape_layer_defn.GetFieldDefn(i).GetTypeName().lower())
      self._graph.edge_properties[self._shape_layer_defn.GetFieldDefn(i).GetName()] = e_prop

    e_prop = self._graph.new_edge_property("double")
    self._graph.edge_properties["weight_dist"] = e_prop

    print(self._graph.list_properties())

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

       :param feature: The ogr feature from which the start and end vertices will be extracted
       :return v1, v2:  The start and end verticies
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

    vertex_index = self._graph.vertex_properties["latlon"]
    vertex_geoid = self._graph.vertex_properties["geoid"]

    """Possibly add the first node of the street segment and set the 
       geoid if it's available"""
    vertices = gutil.find_vertex(self._graph, vertex_index, start_lat_lon)
    if (len(vertices) == 0):
      v1 = self._graph.add_vertex()
      vertex_index[self._graph.vertex(v1)] = start_lat_lon
      vertex_geoid[self._graph.vertex(v1)] = geoid
    else:
      v1 = vertices[0]

    """Possibly add the second node of the street segment. Here we don't
       care about the GeoID because it only belongs on the starting node."""
    vertices = gutil.find_vertex(self._graph, vertex_index, end_lat_lon)
    if (len(vertices) == 0):
      v2 = self._graph.add_vertex()
      vertex_index[self._graph.vertex(v1)] = start_lat_lon
    else:
      v2 = vertices[0]

    return v1, v2

  def _add_graph_edge(self, feature, start_vertex, end_vertex, weight):
    """Add a graph edge between the vertices provided, using the
       feature attributes.
       """

    edge = self._graph.add_edge(start_vertex, end_vertex)
    for i in range(feature.GetFieldCount()):
      fielddef = feature.GetFieldDefnRef(i)
      field_value = feature.GetField(fielddef.GetName())
      edge_field = self._graph.edge_properties[fielddef.GetName()]
      edge_field[edge] = field_value

    weight_field = self._graph.edge_properties["weight_dist"]
    weight_field[edge] = weight

  def __init__(self):
    self.driver = ogr.GetDriverByName('ESRI Shapefile')

  def get_shortest_path(self, start_geoid, end_geoid):
    """Returns the length of and the vertices involved in the shortest path in the network
    :param start_geoid:  The string value of the starting GeoID for the shortest path analysis
    :param end_geoid:  The string value of the ending GeoID for the shortest path analysis
    :return shortest_distance, vertex_list, edge_list:  The length of the shortest path from the field
    weight_distance and the list of vertices and edges in the shortest path network
    """
    start_vertex, end_vertex = None, None
    vertex_geoid = self._graph.vertex_properties["geoid"]
    vertices = gutil.find_vertex(self._graph, vertex_geoid, start_geoid)
    if (len(vertices) > 0):
      start_vertex = vertices[0]
    vertices = gutil.find_vertex(self._graph, vertex_geoid, end_geoid)
    if (len(vertices) > 0):
      end_vertex = vertices[0]

    if (start_vertex is not None) and (end_vertex is not None):
      vertex_list, edge_list = gtopo.shortest_path(self._graph, start_vertex,
                          end_vertex, self._graph.edge_properties["weight_dist"])

      shortest_distance = gtopo.shortest_distance(self._graph, start_vertex,
                          end_vertex, self._graph.edge_properties["weight_dist"])

      return shortest_distance, vertex_list, edge_list
    else:
      return -1, "Could not find start or end vertex"

  def verify(self):

    print("GRAPH PROPERTIES")
    print (self._graph.list_properties())
    print("================")

    print("GRAPH ENTITY COUNT")
    print ("Vertices: {}".format(str(self._graph.num_vertices())))
    print ("Edges: {}".format(str(self._graph.num_edges())))
    print("================")

  def load(self, src, with_progress=False):
    """Load a shapefile and convert it into a GT network
    :param src:  The absolute path to the Shapefile to convert
    :param with_progress:  Show progress as the number of edges
    processed in the Shapefile conversion to GT network; default
    is false.
    :return:  None
    """
    self._shape_layer_src = src
    self._shape_datasource = self.driver.Open(self._shape_layer_src, 0)
    self._shape_layer = self._shape_datasource.GetLayer(0)
    self._shape_layer_defn = self._shape_layer.GetLayerDefn()

    self._graph = Graph()
    self._set_graph_properties()

    progress_increment = int(self._shape_layer.GetFeatureCount() / 100)
    progress = 0
    progress_bar = 0
    for feature in self._shape_layer:
      geom = feature.GetGeometryRef()
      length = geom.Length()

      start_vertex, end_vertex = self._add_graph_vertices(feature)
      self._add_graph_edge (feature, start_vertex, end_vertex, length)
      progress += 1
      if (with_progress):
        if (progress == progress_increment):
          progress = 0
          progress_bar += 1
          self.update_progress("Progress:  {n}%".format(n=str(progress_bar)))

  def save(self, outfile):
    """Save the processed graph to a GT binary file
    :param outfile: The full path to where you want the resulting GT file to be written
    """
    if (self._graph is not None):
      self._graph.save(outfile)
    else:
      print("You must first load a src file via the load() method.")