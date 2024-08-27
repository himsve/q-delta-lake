from qgis.core import QgsWkbTypes
from qgis.PyQt.Qt import QVariant

mapping_delta_lake_qgis_geometry = {
    "LineString": QgsWkbTypes.LineString,
    "MultiLineString": QgsWkbTypes.MultiLineString,
    "MultiPoint": QgsWkbTypes.MultiPolygon,
    "MultiPolygon": QgsWkbTypes.MultiPolygon,
    "Point": QgsWkbTypes.Point,
    "Polygon": QgsWkbTypes.Polygon,
    "PointZ": QgsWkbTypes.PointZ,
    "LineStringZ": QgsWkbTypes.LineStringZ,
    "PolygonZ": QgsWkbTypes.PolygonZ,
}

mapping_delta_lake_qgis_type = {
    "bigint": { "type": QVariant.Int, "type_name": "int" },
    "boolean": { "type": QVariant.Bool, "type_name": "bool" },
    "date": { "type": QVariant.Date, "type_name": "date" },
    "double": { "type": QVariant.Double, "type_name": "double" },
    "integer": { "type": QVariant.Int, "type_name": "int" },
    "timestamp": { "type": QVariant.DateTime, "type_name": "datetime" },
    "timestamp_ntz": { "type": QVariant.DateTime, "type_name": "datetime" },
    "string": { "type": QVariant.String, "type_name": "string" },
    "binary": { "type": QVariant.ByteArray, "type_name": "binary" },
    "struct": { "type": QVariant.Map, "type_name": "map" },
}
