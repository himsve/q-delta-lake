from __future__ import annotations

import os
import weakref
from pathlib import Path
from typing import Union
import json
from requests.exceptions import HTTPError

import pandas as pd
from shapely import from_wkt, total_bounds

from qgis.core import (
    Qgis,
    QgsProject,
    QgsCoordinateReferenceSystem,
    QgsDataProvider,
    QgsFeature,
    QgsFeatureIterator,
    QgsFeatureRequest,
    QgsField,
    QgsFields,
    QgsVectorDataProvider,
    QgsWkbTypes,
    QgsReadWriteContext,
    QgsMessageLog,
    QgsRectangle
)

from . import delta_lake_feature_iterator, delta_lake_feature_source
from .delta_lake_feature_iterator import DeltaLakeFeatureIterator
from .delta_lake_feature_source import DeltaLakeFeatureSource
from .mappings import (
    mapping_delta_lake_qgis_geometry,
    mapping_delta_lake_qgis_type,
)
from .toolbelt.log_handler import PluginLogger

from ..__about__ import (
    DIR_PLUGIN_ROOT,
    __version__
)

# conditional imports
try:
    import delta_sharing
    from delta_sharing import SharingClient
    from delta_sharing.protocol import Metadata

    PluginLogger.log(message="Dependencies loaded from Python installation.")
except ImportError:
    PluginLogger.log(
        message="Import from Python installation failed. Trying to load from "
        "embedded external libs.",
        log_level=0,
        push=False,
    )
    import site

    site.addsitedir(os.path.join(DIR_PLUGIN_ROOT, "embedded_external_libs"))
    import delta_sharing
    from delta_sharing import SharingClient
    from delta_sharing.protocol import Metadata

    PluginLogger.log(
        message=f"Dependencies loaded from embedded external libs: {__version__=}"
    )


class DeltaLakeProvider(QgsVectorDataProvider):
    def __init__(
        self,
        provider_options=QgsDataProvider.ProviderOptions(),
        flags=QgsDataProvider.ReadFlags(),
        connection_profile_path: Union[str, Path, None] = None,
        share_name: Union[str, None] = None,
        schema_name: Union[str, None] = None,
        table_name: Union[str, None] = None,
        epsg_id: Union[int, None] = None,
    ):
        self._is_valid = False

        self._wkb_type = None
        self._geometry_column = None
        self._fields = None
        self._feature_count = None
        self._primary_key = None
        self._dataframe = None
        self._schema_fields = None
        self._schema = None
        self._metadata = None
        self._table_uri = None
        self._extent = None

        self._provider_options = provider_options
        self._flags = flags

        self._client: Union[SharingClient, None] = None
        self._connection_profile_path = connection_profile_path
        self._share_name = share_name
        self._schema_name = schema_name
        self._table_name = table_name
        self._epsg_id = epsg_id
        self._uri = encode_uri_from_values(connection_profile_path,
                                           share_name, schema_name, table_name, epsg_id)

        super().__init__(self._uri)

        if epsg_id:
            self._crs = QgsCoordinateReferenceSystem.fromEpsgId(epsg_id)
        else:
            self._crs = QgsCoordinateReferenceSystem()
        self._table_uri, self._client = self._connect_database(connection_profile_path,
                                                               share_name, schema_name, table_name)
        weakref.finalize(self, self._disconnect_database)
        self._is_valid = True

    @classmethod
    def providerKey(cls) -> str:
        """Returns the provider key"""
        return "delta_lake"

    def name(self) -> str:
        """Return the name of provider

        :return: Name of provider
        :rtype: str
        """
        return self.providerKey()

    @classmethod
    def description(cls) -> str:
        """Returns the provider description"""
        return "Delta Lake"

    @classmethod
    def create_provider(cls, uri, provider_options, flags=QgsDataProvider.ReadFlags()):
        return DeltaLakeProvider(provider_options, flags, **decode_uri(uri))

    def capabilities(self) -> QgsVectorDataProvider.Capabilities:
        return QgsVectorDataProvider.Capabilities(QgsVectorDataProvider.NoCapabilities)

    @classmethod
    def layer_name(cls, share_name, schema_name, table_name) -> str:
        return f"{share_name}.{schema_name}.{table_name}"

    def featureCount(self) -> int:
        """returns the number of entities in the table"""
        if not self._is_valid:
            self._feature_count = 0
        else:
            self._feature_count = len(self._dataframe)
        return self._feature_count

    def isValid(self) -> bool:
        return self._is_valid

    def _connect_database(self, connection_profile_path,
                          share_name, schema_name, table_name) -> tuple[str, SharingClient]:
        table_uri, client = _client_connect(connection_profile_path,
                                            share_name, schema_name, table_name)
        qlog(table_uri)
        try:
            self._metadata: Metadata = delta_sharing.get_table_metadata(table_uri)
            self._schema = json.loads(self._metadata.schema_string)
            self._schema_fields = self._schema['fields']
            geometry_column_list = [(i, f['name']) for i, f in enumerate(self._schema_fields)
                                    if "<geometry>" in f['metadata'].get('comment', '--')]
            self._geometry_column = geometry_column_list[0][1] if len(geometry_column_list) > 0 else None
            self._index_geometry_column = geometry_column_list[0][0] if len(geometry_column_list) > 0 else None
            qlog(self._index_geometry_column)
            qlog(self._geometry_column)
            self._dataframe: pd.DataFrame = delta_sharing.load_as_pandas(table_uri)
        except FileNotFoundError as e:
            PluginLogger.log(
                self.tr(
                    "File not found when loading data {}, are you on an allowed network?".format(table_uri)
                ),
                log_level=2,
                push=True,
            )
            raise e

        return table_uri, client

    def _disconnect_database(self):
        self._dataframe = self._dataframe[0:0]
        self._dataframe = None
        self._metadata = None
        self._client = None

    def get_dataframe(self):
        return self._dataframe

    def get_index_geometry_column(self):
        return self._index_geometry_column

    def wkbType(self) -> QgsWkbTypes:
        """Detects the geometry type of the table, converts and return it to
        QgsWkbTypes.
        """
        if not self._wkb_type:
            self._wkb_type = QgsWkbTypes.Unknown
            if self._is_valid and self._geometry_column is not None:
                # get the first occurring value in the geometry column
                geometry_delta_lake = from_wkt(self._dataframe[self._geometry_column].bfill()[0],
                                               on_invalid="warn").geom_type
                self._wkb_type = mapping_delta_lake_qgis_geometry.get(geometry_delta_lake,
                                                                      QgsWkbTypes.Unknown)
                if self._wkb_type == QgsWkbTypes.Unknown:
                    PluginLogger.log(
                        self.tr(
                            "Geometry type {} not supported".format(geometry_delta_lake)
                        ),
                        log_level=2,
                        duration=15,
                        push=True,
                    )
        return self._wkb_type

    def get_geometry_column(self) -> str:
        """Returns the name of the geometry column"""
        return self._geometry_column

    def primary_key(self) -> int:
        # delta shares do not have primary keys
        self._primary_key = -1
        return self._primary_key

    def fields(self) -> QgsFields:
        """Detects field name and type. Converts the type into a QVariant, and returns a
        QgsFields containing QgsFields.
        """
        if not self._fields:
            self._fields = QgsFields()
            if self._is_valid:
                for field in self._schema_fields:
                    qlog(str(field))
                    qlog(str(mapping_delta_lake_qgis_type[field['type']]))
                    qgs_field = QgsField(field['name'], type=mapping_delta_lake_qgis_type[field['type']]['type'],
                                         typeName=mapping_delta_lake_qgis_type[field['type']]['type_name'])
                    self._fields.append(qgs_field)
        return self._fields

    def extent(self) -> QgsRectangle:
        """Calculates the extent and returns a QgsRectangle"""
        if not self._extent:
            if not self._is_valid:
                self._extent = QgsRectangle()
                PluginLogger.log(
                    message="Using empty extent because geometry is not valid",
                    log_level=4,
                )
            else:
                extent_bounds = total_bounds(from_wkt(self._dataframe[self._geometry_column]))
                self._extent = QgsRectangle(*extent_bounds)

                PluginLogger.log(
                    message="Extent calculated for {}: "
                    "xmin={}, xmax={}, ymin={}, ymax={}".format(
                        self._table_uri, *extent_bounds
                    ),
                    log_level=4,
                )
        return self._extent

    def updateExtents(self) -> None:
        """Update extent"""
        return self._extent.setMinimal()

    def dataSourceUri(self, expandAuthConfig=False):
        """Returns the data source specification: uri.

        :param bool expandAuthConfig: expand credentials (unused)
        :returns: the data source uri
        """
        return self._uri

    def crs(self):
        return self._crs

    def featureSource(self):
        return DeltaLakeFeatureSource(self)

    def storageType(self):
        return "DeltaSharing"

    def get_table(self) -> str:
        """Get the table name

        :return: table name
        :rtype: str
        """
        return self._table_name

    def uniqueValues(self, fieldIndex) -> set:
        """Returns the unique values of a field

        :param fieldIndex: Index of field
        :type fieldIndex: int
        """
        column_name = self.fields().field(fieldIndex).name()
        return self._dataframe[column_name].unique()

    def getFeatures(self, request=QgsFeatureRequest()) -> QgsFeature:
        """Return feature iterator"""
        return QgsFeatureIterator(
            DeltaLakeFeatureIterator(
                DeltaLakeFeatureSource(self), request
            )
        )

    def subsetString(self) -> str:
        return ""

    def setSubsetString(self, subsetString: str) -> bool:
        return False

    def supportsSubsetString(self) -> bool:
        # the provider does not handle subsets at the moment
        return False


def _table_uri(connection_profile_path,
               share_name, schema_name, table_name):
    return f"{connection_profile_path}#{share_name}.{schema_name}.{table_name}"


def _client_connect(connection_profile_path,
                    share_name, schema_name, table_name) -> tuple[str, SharingClient]:
    """Open a connection to the DeltaLake table

    :return: client object
    :rtype: delta_lake.SharingClient
    """
    # determine which database to use
    if connection_profile_path is None:
        raise FileNotFoundError("Connection profile path cannot be None on connection.")

    path_profile = Path(connection_profile_path).resolve()
    if not path_profile.is_file():
        raise FileNotFoundError(
            "Connection profile path does not exist: {}".format(
                connection_profile_path
            )
        )

    table_uri = _table_uri(connection_profile_path, share_name, schema_name, table_name)
    PluginLogger.log(
        message="Using the table URI defined at object level: {}".format(
            table_uri
        ),
        log_level=4,
        push=False,
    )

    try:
        client = SharingClient(path_profile)

        PluginLogger.log(
            message="Creation of sharing client {} succeeded.".format(path_profile),
            log_level=0,
            push=False,
        )

        return table_uri, client

    except HTTPError as exc:
        PluginLogger.log(
            "Connection to {} failed. Trace: {}".format(path_profile, exc),
            log_level=2,
            push=True,
        )
        raise exc


def _uri_intermediate_structure(connection_profile_path: str,
                                share_name: str, schema_name: str, table_name: str, epsg_id: int):
    return {"connection_profile_path": connection_profile_path,
            "share_name": share_name,
            "schema_name": schema_name,
            "table_name": table_name,
            "epsg_id": epsg_id}


def decode_uri(uri: str) -> dict[str, Union[str, int]]:
    """Breaks a provider data source URI into its component paths
    (e.g. connection profile path, share_name, etc.).

    :param str uri: uri to convert
    :returns: dict of components as strings
    """
    connection_profile_path = ""
    share_name = ""
    schema_name = ""
    table_name = ""
    epsg_id = ""

    for variable in uri.split(" "):
        key, value = variable.split("=")
        if key == "connection_profile_path":
            connection_profile_path = value
        elif key == "share_name":
            share_name = value
        elif key == "schema_name":
            schema_name = value
        elif key == "table_name":
            table_name = value
        elif key == "epsg_id":
            epsg_id = int(value)

    if Qgis.QGIS_VERSION_INT < 33000:
        # The logic to parse an uri and convert the path from
        # relative to absolute is:
        # 1. call `QGsVectorLayer::decodedSource()` to parse the
        # uri and convert the path with `readPath`
        # 2. call `QgsProviderMetadata.decodeUri()` to parse the uri
        # which already contains an absolute path.
        #
        # However, prior to QGIS 3.30, this does not work for delta_lake
        # provider. Indeed, the behavior of each provider was
        # hardcoded in the function `QGsVectorLayer::decodedSource()`
        # and it could not handle delta_lake provider.
        # Since, QGIS 3.30, this has been delegated to
        # QgsProviderMetadata::relativeToAbsoluteUri. This allows
        # each provider to have its own behavior and fix the issue
        # for delta_lake provider.
        #
        # Since it is not possible to override
        # QGsVectorLayer::decodedSource(), prior to QGIS 3.30, the
        # uri used to call `decodeUri` contains a
        # relative path instead of an absolute one. By calling
        # `readPath`, this solves the issue.
        connection_profile_path = QgsProject.instance() \
            .pathResolver().readPath(connection_profile_path)
    return _uri_intermediate_structure(connection_profile_path,
                                       share_name, schema_name, table_name, epsg_id)


def encode_uri(parts: dict[str, str]) -> str:
    """Reassembles a provider data source URI from its component paths
    (e.g. connection profile path, share_name, etc).

    :param Dict[str, str] parts: parts as returned by decodeUri
    :returns: uri as string
    """
    uri = f"connection_profile_path={parts['connection_profile_path']} " \
        f"share_name={parts['share_name']} schema_name={parts['schema_name']} " \
        f"table_name={parts['table_name']} epsg_id={parts['epsg_id']}"
    return uri


def encode_uri_from_values(connection_profile_path: str,
                           share_name: str, schema_name: str, table_name: str, epsg_id: int) -> str:
    return encode_uri(_uri_intermediate_structure(connection_profile_path,
                                                  share_name, schema_name, table_name, epsg_id))


def absolute_to_relative_uri(uri: str, context: QgsReadWriteContext) -> str:
    """Convert an absolute uri to a relative one

    The uri is parsed and then the path converted to a relative path by writePath
    Then, a new uri with a relative path is encoded.

    This only works for QGIS 3.30 and above as it did not exist before.
    Before this version, it is not possible to save an uri as relative in a project.

    :example:

    uri = f"connection_profile_path=/home/test/config.profile
            share_name=share schema_name=schema table_name=cities epsg_id=4326"
    relative_uri = f"connection_profile_path=./config.profile
                     share_name=share schema_name=schema table_name=cities epsg_id=4326"

    :param str uri: uri to convert
    :param QgsReadWriteContext context: qgis context
    :returns: uri with a relative path
    """
    decoded_uri = decode_uri(uri)
    decoded_uri["connection_profile_path"] = context.pathResolver() \
        .writePath(decoded_uri["connection_profile_path"])
    return encode_uri(decoded_uri)


def relative_to_absolute_uri(uri: str, context: QgsReadWriteContext) -> str:
    """Convert a relative uri to an absolute one

    The uri is parsed and then the path converted to an absolute path by readPath
    Then, a new uri with an absolute path is encoded.

    This only works for QGIS 3.30 and above as it did not exist before.

    :example:

    uri = f"connection_profile_path=./config.profile
            share_name=share schema_name=schema table_name=cities epsg_id=4326"
    absolute_uri = f"connection_profile_path=/home/test/config.profile
                     share_name=share schema_name=schema table_name=cities epsg_id=4326"

    :param str uri: uri to convert
    :param QgsReadWriteContext context: qgis context
    :returns: uri with an absolute path
    """
    decoded_uri = decode_uri(uri)
    decoded_uri["connection_profile_path"] = context.pathResolver() \
        .readPath(decoded_uri["connection_profile_path"])
    return encode_uri(decoded_uri)


def qlog(message):
    QgsMessageLog.logMessage(message=str(message), tag="log")
