from qgis.core import QgsProviderMetadata, QgsReadWriteContext

from .delta_lake_provider import (
    DeltaLakeProvider, decode_uri, encode_uri, encode_uri_from_values,
    absolute_to_relative_uri, relative_to_absolute_uri
)


class DeltaLakeProviderMetadata(QgsProviderMetadata):
    def __init__(self):
        super().__init__(
            DeltaLakeProvider.providerKey(),
            DeltaLakeProvider.description(),
            DeltaLakeProvider.create_provider,
        )

    def decodeUri(self, uri: str) -> dict[str, str]:
        return decode_uri(uri)

    def encodeUri(self, parts: dict[str, str]) -> str:
        return encode_uri(parts)

    @staticmethod
    def encodeUriFromValues(connection_profile_path: str,
                            share_name: str, schema_name: str, table_name: str, epsg_id: int) -> str:
        return encode_uri_from_values(connection_profile_path,
                                      share_name, schema_name, table_name, epsg_id)

    def absoluteToRelativeUri(self, uri: str, context: QgsReadWriteContext) -> str:
        return absolute_to_relative_uri(uri, context)

    def relativeToAbsoluteUri(self, uri: str, context: QgsReadWriteContext) -> str:
        return relative_to_absolute_uri(uri, context)
