import os
from qgis.core import (
    QgsProject,
    QgsRasterLayer,
    QgsCoordinateTransform,
    QgsCoordinateReferenceSystem
)

def get_bbox_from_canvas(iface):
    canvas = iface.mapCanvas()
    extent = canvas.extent()
    source_crs = canvas.mapSettings().destinationCrs()
    target_crs = QgsCoordinateReferenceSystem("EPSG:4326")

    transform = QgsCoordinateTransform(
        source_crs,
        target_crs,
        QgsProject.instance()
    )

    extent_4326 = transform.transformBoundingBox(extent)
    bbox = [
        extent_4326.xMinimum(),
        extent_4326.yMinimum(),
        extent_4326.xMaximum(),
        extent_4326.yMaximum()
    ]
    return bbox


def add_raster_to_qgis(file_path, layer_name=None):
    if layer_name is None:
        # os.path.basename işletim sistemine göre en doğru dosya adını çeker
        layer_name = os.path.basename(file_path)

    layer = QgsRasterLayer(file_path, layer_name)

    if layer.isValid():
        QgsProject.instance().addMapLayer(layer)
        return True
    else:
        raise Exception(f"Raster layer is not valid. Path: {file_path}")