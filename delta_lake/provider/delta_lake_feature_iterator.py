# standard
from __future__ import (
    annotations,   # used to manage type annotation for method that return Self in Python < 3.11
)

# PyQGIS
from qgis.core import (
    QgsAbstractFeatureIterator,
    QgsCoordinateTransform,
    QgsFeature,
    QgsFeatureRequest,
    QgsGeometry,
    QgsPoint,
)

from shapely import wkt, wkb, from_wkb, from_wkt

class DeltaLakeFeatureIterator(QgsAbstractFeatureIterator):
    def __init__(
        self,
        source,
        request: QgsFeatureRequest,
    ):
        """Constructor"""
        # FIXME: Handle QgsFeatureRequest.FilterExpression
        super().__init__(request)
        self._index = None
        self._iterator_tuples = None
        self._provider = source.get_provider()
        self._index_geometry_column = self._provider.get_index_geometry_column()
        ### !TODO
        self._current_fields = None
        self._iter_cnt = 0
        self._iter_max = None

        if not self._provider.isValid():
            return

        self._request = request if request is not None else QgsFeatureRequest()
        self._transform = QgsCoordinateTransform()

        if (
            self._request.destinationCrs().isValid()
            and self._request.destinationCrs() != self._provider.crs()
        ):
            self._transform = QgsCoordinateTransform(
                self._provider.crs(),
                self._request.destinationCrs(),
                self._request.transformContext(),
            )
        self.__iter__()

    def fetchFeature(self, f: QgsFeature) -> bool:
        """fetch next feature, return true on success

        :param f: Next feature
        :type f: QgsFeature
        :return: True if success
        :rtype: bool
        """
        if not self._provider.isValid():
            f.setValid(False)
            return False

        if self._index >= self._iter_max:
            f.setValid(False)
            raise StopIteration

        next_result = self._iterator_tuples[self._index]

        f.setFields(self._current_fields)

        f.setValid(True)

        # try:
        #     wktstring = from_wkb(next_result[self._index_geometry_column]).wkt
        #     #wkbblob = from_wkb(next_result[self._index_geometry_column]).wkb
        # except:
        #     wktstring = 'POLYGONZ (200000 6700000 0, 200000 6700010 0, 200010 6700010 0, 200000 6700000 0)'
        #     #wkbblob = b'01030000000100000008000000c8826e431ca40f416bb568ccfc105941d06f1a7513a40f4145b5232cfd105941207bdf49f4a30f41af963e74fc105941d4973318fda30f41b8968314fc105941d4973318fda30f41be968314fc1059419eb587e605a40f41ed96c8b4fb1059411a23eb0f25a40f41f86f0a6cfc105941c8826e431ca40f416bb568ccfc105941'
        # geometry = QgsGeometry.fromWkt(wktstring)

        geom_update: QgsGeometry = f.geometry()  # gets feature's existing geometry
        geom_update.fromWkb(next_result[self._index_geometry_column])  # overwrites geometry from wkb
        f.setGeometry(geom_update)

        # !TODO - trenger vi å transformere geo?
        self.geometryToDestinationCrs(f, self._transform)

        f.setId(self._index)
        self._index += 1

        # for i in range(len(self._provider.fields())):
        #     if i < 1:
        #         pass
        #     if self._index < 3:
        #         pass
        #     else:
        #         f.setAttribute(i, next_result[i])
        #
        return True

    def __iter__(self) -> DeltaLakeFeatureIterator:
        """Returns self as an iterator object"""
        self._iter_cnt = self._iter_cnt + 1
        # !TODO -remove this-
        print(f'-- Feature iterator {self._iter_cnt} --')
        self._current_fields = self._provider.fields()
        df = self._provider.get_dataframe()
        self._iter_max = len(df.index)
        self._iterator_tuples = df.values.tolist()
        self._index = 0
        return self

    def __next__(self) -> QgsFeature:
        """Returns the next value till current is lower than high"""
        f = QgsFeature()
        if not self.nextFeature(f):
            raise StopIteration
        else:
            return f

    def rewind(self) -> bool:
        """reset the iterator to the starting position"""
        if self._index < 0:
            return False
        self._index = 0
        return True

    def close(self) -> bool:
        """end of iterating: free the resources / lock"""
        # virtual bool close() = 0;
        self._iterator_tuples = None
        self._index = -1
        return True
