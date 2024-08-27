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
        if self._index < 3:
            print(f"self._provider.fields(): {self._provider.fields()}")
        f.setValid(self._provider.isValid())
        
        #s1 = b'01030000A0551700000100000008000000C8826E431CA40F416BB568CCFC105941B81E85EB51382B40D06F1A7513A40F4145B5232CFD10594147E17A14AE472740207BDF49F4A30F41AF963E74FC10594147E17A14AE472740D4973318FDA30F41BE968314FC105941B81E85EB51382B40D4973318FDA30F41BE968314FC105941B81E85EB51382B409EB587E605A40F41ED96C8B4FB10594147E17A14AE4727401A23EB0F25A40F41F86F0A6CFC10594147E17A14AE472740C8826E431CA40F416BB568CCFC105941B81E85EB51382B40'
        #s1 = b'01030000000100000008000000c8826e431ca40f416bb568ccfc105941d06f1a7513a40f4145b5232cfd105941207bdf49f4a30f41af963e74fc105941d4973318fda30f41b8968314fc105941d4973318fda30f41be968314fc1059419eb587e605a40f41ed96c8b4fb1059411a23eb0f25a40f41f86f0a6cfc105941c8826e431ca40f416bb568ccfc105941'
        #wkt1 = from_wkb(s1)
        #print(wkt1)
        
        try:
            wktstring = from_wkb(next_result[self._index_geometry_column]).wkt
            wkbblob = from_wkb(next_result[self._index_geometry_column]).wkb
        except:
            wktstring = 'POLYGONZ (200000 6700000 0, 200000 6700010 0, 200010 6700010 0, 200000 6700000 0)'
            wkbblob = b'01030000000100000008000000c8826e431ca40f416bb568ccfc105941d06f1a7513a40f4145b5232cfd105941207bdf49f4a30f41af963e74fc105941d4973318fda30f41b8968314fc105941d4973318fda30f41be968314fc1059419eb587e605a40f41ed96c8b4fb1059411a23eb0f25a40f41f86f0a6cfc105941c8826e431ca40f416bb568ccfc105941'
       
        #print(f"wktstring': {wktstring}")

        #print(f"next_result[self._index_geometry_column]: {next_result[self._index_geometry_column]} self._index_geometry_column {self._index_geometry_column}")
        
        # print(QgsGeometry)
        geometry = QgsGeometry.fromWkt(wktstring)
        #geometry = QgsGeometry.fromWkb(wkbblob)
        #geometry = QgsGeometry.fromWkb(next_result[self._index_geometry_column])
        
        #p = QgsGeometry.fromWkt('POINT (200200 6700001)')
        #print(f"p {p}")
        
        #wkt1 = 'POLYGON (200000 6700000 0, 200000 6700010 0, 200010 6700010 0, 200000 6700000 0)'
        #geometry = QgsGeometry.fromWkt(wkt1)
       
        f.setGeometry(geometry) 
        self.geometryToDestinationCrs(f, self._transform)

        f.setId(self._index)
        self._index += 1

        for i in range(len(self._provider.fields())):
            #if i < 1:
            #    print(f"next_result[i]: {next_result[i]}")
            if self._index < 3:
                print (next_result[i])
            else:
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
