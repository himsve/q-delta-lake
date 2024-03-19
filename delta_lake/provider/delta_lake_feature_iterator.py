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
)


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

        try:
            next_result = next(self._iterator_tuples)
        except StopIteration:
            f.setValid(False)
            return False

        f.setFields(self._provider.fields())
        f.setValid(self._provider.isValid())
        geometry = QgsGeometry.fromWkt(next_result[self._index_geometry_column])
        f.setGeometry(geometry)
        self.geometryToDestinationCrs(f, self._transform)

        f.setId(self._index)
        self._index += 1

        for i in range(len(self._provider.fields())):
            f.setAttribute(i, next_result[i])

        return True

    def __iter__(self) -> DeltaLakeFeatureIterator:
        """Returns self as an iterator object"""
        self._iterator_tuples = self._provider.get_dataframe().itertuples(index=False, name=None)
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
        self.__iter__()
        return True

    def close(self) -> bool:
        """end of iterating: free the resources / lock"""
        # virtual bool close() = 0;
        self._iterator_tuples = None
        self._index = -1
        return True
