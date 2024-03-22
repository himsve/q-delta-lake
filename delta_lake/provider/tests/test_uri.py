# coding=utf-8
"""URI tests"""

__author__ = 'kooijman.richard@gmail.com'
__date__ = '2024-03-15'
__copyright__ = 'Copyright 2024, Richard Kooijman'

import unittest
import urllib.parse
from delta_lake.provider.delta_lake_provider import (
    _uri_intermediate_structure,
    encode_uri_from_values, decode_uri,
    relative_to_absolute_uri, absolute_to_relative_uri)
from qgis.core import (
    QgsReadWriteContext,
)


class UriTest(unittest.TestCase):
    """Test URI work"""

    def setUp(self) -> None:
        self.connection_profile_path = "/Users/richardkooijman/Downloads/config 1.share"
        self.share_name = "share_name"
        self.schema_name = "schema_name"
        self.table_name = "table_name"
        self.epsg_id = 28992

    def test_structure(self):
        """Test the structure"""
        structure = _uri_intermediate_structure(self.connection_profile_path,
                                                self.share_name, self.schema_name, self.table_name, self.epsg_id)
        self.assertDictEqual(structure,
                             {"connection_profile_path": urllib.parse.unquote_plus(self.connection_profile_path),
                              "share_name": self.share_name,
                              "schema_name": self.schema_name,
                              "table_name": self.table_name,
                              "epsg_id": self.epsg_id})

    def test_uri_encode(self):
        """Test the encoding"""
        uri = encode_uri_from_values(self.connection_profile_path,
                                     self.share_name, self.schema_name, self.table_name, self.epsg_id)
        self.assertEqual(uri,
                         f"connection_profile_path={urllib.parse.quote_plus(self.connection_profile_path, safe='/')} "
                         f"share_name={self.share_name} schema_name={self.schema_name} "
                         f"table_name={self.table_name} epsg_id={self.epsg_id}")

    def test_uri_decode(self):
        """Test the decoding"""
        uri = (f"connection_profile_path={urllib.parse.quote_plus(self.connection_profile_path, safe='/')} "
               f"share_name={self.share_name} schema_name={self.schema_name} "
               f"table_name={self.table_name} epsg_id={self.epsg_id}")
        self.assertDictEqual(decode_uri(uri),
                             {"connection_profile_path": self.connection_profile_path,
                              "share_name": self.share_name,
                              "schema_name": self.schema_name,
                              "table_name": self.table_name,
                              "epsg_id": self.epsg_id}
                             )

    def test_uri_relative_to_absolute(self):
        uri = (f"connection_profile_path={urllib.parse.quote_plus(self.connection_profile_path, safe='/')} "
               f"share_name={self.share_name} schema_name={self.schema_name} "
               f"table_name={self.table_name} epsg_id={self.epsg_id}")
        self.assertEqual(relative_to_absolute_uri(uri, QgsReadWriteContext()), uri)

    def test_uri_absolute_to_relative_uri(self):
        uri = (f"connection_profile_path={urllib.parse.quote_plus(self.connection_profile_path, safe='/')} "
               f"share_name={self.share_name} schema_name={self.schema_name} "
               f"table_name={self.table_name} epsg_id={self.epsg_id}")
        self.assertEqual(absolute_to_relative_uri(uri, QgsReadWriteContext()), uri)


if __name__ == "__main__":
    suite = unittest.makeSuite(UriTest)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
