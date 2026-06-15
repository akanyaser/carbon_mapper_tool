
"""
Hotspot and plume detection module for the Carbon Mapper QGIS plugin.

This module reads a selected methane raster layer, applies an adaptive threshold,
creates a binary plume mask, removes small noisy clusters, polygonizes connected
plume regions, calculates plume geometry and CH4 intensity statistics, then saves
the final plume polygons as a GeoJSON layer and reports the analysis summary.
"""

import os
import processing
from datetime import datetime

from qgis.core import (
    QgsProject, QgsMapLayerType, QgsVectorLayer, QgsField,
    QgsFeature, QgsVectorFileWriter, QgsDistanceArea, QgsFillSymbol,
    QgsRasterBandStats
)
from qgis.analysis import QgsZonalStatistics
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import QMessageBox, QComboBox, QLineEdit, QTextEdit, QFileDialog


class AnalysisManager:
    def __init__(self, plugin):
        """
        Manages hotspot analysis operations for the plugin.
        :param plugin: Main QGIS plugin instance.
        """
        self.plugin = plugin

    def refresh_raster_layers(self, *args):
        """Scans active QGIS project layers and fills the raster combobox in the interface."""
        raster_combo = getattr(self.plugin, 'analysis_raster_combo', None) or self.plugin.findChild(QComboBox, "analysis_raster_combo")

        if raster_combo is None:
            print("[Carbon Mapper Hotspot] analysis_raster_combo was not found in the interface.")
            return

        current_raster_id = raster_combo.currentData()
        raster_combo.blockSignals(True)
        raster_combo.clear()

        layers = QgsProject.instance().mapLayers().values()
        raster_count = 0
        index_to_restore = -1

        for layer in layers:
            if layer and layer.isValid() and layer.type() == QgsMapLayerType.RasterLayer:
                layer_name = layer.name()
                if "OpenStreetMap" in layer_name or "Google" in layer_name:
                    continue

                raster_combo.addItem(layer_name, layer.id())
                if current_raster_id and layer.id() == current_raster_id:
                    index_to_restore = raster_count
                raster_count += 1

        if raster_count == 0:
            raster_combo.addItem("-- There is no active raster layer in the project --", None)
        elif index_to_restore != -1:
            raster_combo.setCurrentIndex(index_to_restore)
        else:
            raster_combo.setCurrentIndex(0)

        raster_combo.blockSignals(False)
        raster_combo.update()

    def browse_output_directory_hotspot(self):
        output_input = getattr(self.plugin, 'analysis_output_input', None) or self.plugin.findChild(QLineEdit, "analysis_output_input")
        if not output_input:
            QMessageBox.critical(self.plugin, "UI Error", "Could not find 'analysis_output_input' line edit!")
            return

        selected_dir = QFileDialog.getExistingDirectory(self.plugin, "Select Output Directory for Hotspot")
        if selected_dir:
            output_input.setText(selected_dir)

    def run_hotspot_analysis(self):
        """
        Runs threshold-based plume detection on the selected raster layer.

        Scientific workflow:
        Raster
        -> invalid/background mask
        -> adaptive threshold
        -> binary raster
        -> sieve filtering
        -> GDAL Polygonize
        -> minimum area filtering
        -> plume polygons
        -> Environmental Impact Analysis
        """
        raster_combo = getattr(self.plugin, 'analysis_raster_combo', None) or self.plugin.findChild(QComboBox, "analysis_raster_combo")
        output_input = getattr(self.plugin, 'analysis_output_input', None) or self.plugin.findChild(QLineEdit, "analysis_output_input")
        report_txt = getattr(self.plugin, 'analysis_report_txt', None) or self.plugin.findChild(QTextEdit, "analysis_report_txt")
        threshold_input = getattr(self.plugin, 'txt_threshold', None) or self.plugin.findChild(QLineEdit, "txt_threshold")

        if not raster_combo or raster_combo.currentIndex() == -1 or raster_combo.currentData() is None:
            QMessageBox.warning(self.plugin, "Analysis Error", "Please select a valid raster layer for Hotspot analysis!")
            return

        layer_id = raster_combo.currentData()
        raster_layer = QgsProject.instance().mapLayer(layer_id)
        if not raster_layer or not raster_layer.isValid():
            QMessageBox.critical(self.plugin, "Layer Error", "Selected raster layer is not valid or no longer in project!")
            return

        try:
            raw_text = threshold_input.text().strip().replace(',', '.') if threshold_input else ""
            user_threshold = float(raw_text) if raw_text else 1.5
        except (ValueError, AttributeError):
            QMessageBox.warning(self.plugin, "Input Error", "Please enter a valid numeric threshold value!")
            return

        output_dir = output_input.text().strip() if output_input else ""
        if not output_dir or not os.path.exists(output_dir):
            QMessageBox.warning(self.plugin, "Validation Error", "Please select a valid output directory using 'Browse' before running!")
            return

        if report_txt:
            report_txt.setText(
                "Analysis started...\n"
                "Raster statistics are being checked...\n"
                "Adaptive threshold, sieve filtering and polygonization will be applied.\n"
            )
            report_txt.repaint()

        try:
            provider = raster_layer.dataProvider()
            extent = raster_layer.extent()

            stats = provider.bandStatistics(
                1,
                QgsRasterBandStats.All,
                extent,
                0
            )

            min_actual_value = stats.minimumValue
            max_actual_value = stats.maximumValue
            mean_value = stats.mean
            stddev_value = stats.stdDev

            if max_actual_value <= user_threshold:
                QMessageBox.warning(
                    self.plugin,
                    "Threshold Warning",
                    "The threshold is higher than or equal to the maximum raster value. No plume polygon can be produced."
                )
                return

            # Conservative automatic threshold:
            # 1) user threshold protects manual control
            # 2) mean + 3*std targets statistical outliers
            # 3) 15% of max prevents low thresholds from selecting the full raster footprint
            statistical_threshold = mean_value + (3.0 * stddev_value)
            upper_tail_threshold = max_actual_value * 0.15
            final_threshold = max(user_threshold, statistical_threshold, upper_tail_threshold)

            if final_threshold >= max_actual_value:
                final_threshold = max(user_threshold, max_actual_value * 0.75)

            safe_layer_name = "".join([c if c.isalnum() else "_" for c in raster_layer.name()])
            safe_threshold = f"{final_threshold:.2f}".replace(".", "_").replace("-", "minus_")
            run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

            binary_raster_path = os.path.join(output_dir, f"binary_hotspot_{safe_layer_name}_{safe_threshold}_{run_id}.tif")
            sieved_raster_path = os.path.join(output_dir, f"sieved_hotspot_{safe_layer_name}_{safe_threshold}_{run_id}.tif")
            raw_polygon_path = os.path.join(output_dir, f"polygonized_raw_{safe_layer_name}_{safe_threshold}_{run_id}.geojson")
            geojson_path = os.path.join(output_dir, f"plume_vector_{safe_layer_name}_{safe_threshold}_{run_id}.geojson")

            # These parameters are intentionally conservative defaults.
            # They prevent single-pixel and tiny noisy clusters from becoming plume polygons.
            sieve_min_pixels = 8
            min_plume_area_m2 = 10000.0

            if report_txt:
                report_txt.setText(
                    "Analysis running...\n"
                    f"User threshold: {user_threshold:.4f} ppm/m\n"
                    f"Adaptive threshold: {final_threshold:.4f} ppm/m\n"
                    "Creating binary raster mask...\n"
                )
                report_txt.repaint()

            processing.run(
                "gdal:rastercalculator",
                {
                    "INPUT_A": raster_layer.source(),
                    "BAND_A": 1,
                    "FORMULA": f"((A >= {final_threshold}) * (A < 50000))",
                    "NO_DATA": 0,
                    "RTYPE": 0,
                    "OPTIONS": "",
                    "EXTRA": "",
                    "OUTPUT": binary_raster_path,
                }
            )

            if report_txt:
                report_txt.setText(
                    "Analysis running...\n"
                    "Binary raster created.\n"
                    "Removing tiny connected pixel noise with GDAL Sieve...\n"
                )
                report_txt.repaint()

            processing.run(
                "gdal:sieve",
                {
                    "INPUT": binary_raster_path,
                    "BAND": 1,
                    "THRESHOLD": sieve_min_pixels,
                    "EIGHT_CONNECTEDNESS": True,
                    "NO_MASK": False,
                    "MASK_LAYER": None,
                    "EXTRA": "",
                    "OUTPUT": sieved_raster_path,
                }
            )

            if report_txt:
                report_txt.setText(
                    "Analysis running...\n"
                    "Sieve filtering completed.\n"
                    "Converting connected plume cells into polygons with GDAL Polygonize...\n"
                )
                report_txt.repaint()

            processing.run(
                "gdal:polygonize",
                {
                    "INPUT": sieved_raster_path,
                    "BAND": 1,
                    "FIELD": "DN",
                    "EIGHT_CONNECTEDNESS": True,
                    "EXTRA": "",
                    "OUTPUT": raw_polygon_path,
                }
            )

            raw_layer = QgsVectorLayer(raw_polygon_path, "Raw_Polygonized_Plumes", "ogr")
            if not raw_layer.isValid():
                QMessageBox.critical(self.plugin, "Polygonize Error", "GDAL Polygonize output could not be loaded.")
                return

            crs = raster_layer.crs().authid()
            mem_layer = QgsVectorLayer(f"Polygon?crs={crs}", "Temporary_Plume_Polygons", "memory")
            mem_provider = mem_layer.dataProvider()
            mem_provider.addAttributes([
                QgsField("plume_id", QVariant.Int),
                QgsField("DN", QVariant.Int),
                QgsField("user_thr", QVariant.Double),
                QgsField("auto_thr", QVariant.Double),
                QgsField("threshold", QVariant.Double),
                QgsField("area_m2", QVariant.Double),
                QgsField("area_km2", QVariant.Double),
                QgsField("perim_m", QVariant.Double),
            ])
            mem_layer.updateFields()

            distance = QgsDistanceArea()
            distance.setSourceCrs(raster_layer.crs(), QgsProject.instance().transformContext())
            distance.setEllipsoid(QgsProject.instance().ellipsoid())

            features_to_add = []
            total_area_m2 = 0.0
            total_perimeter_m = 0.0
            plume_count = 0
            removed_small_polygons = 0

            for raw_feat in raw_layer.getFeatures():
                dn_value = raw_feat["DN"]

                try:
                    dn_value = int(dn_value)
                except (TypeError, ValueError):
                    continue

                if dn_value != 1:
                    continue

                geom = raw_feat.geometry()
                if not geom or geom.isEmpty():
                    continue

                area_m2 = distance.measureArea(geom)
                if area_m2 < min_plume_area_m2:
                    removed_small_polygons += 1
                    continue

                perimeter_m = distance.measurePerimeter(geom)

                plume_count += 1
                total_area_m2 += area_m2
                total_perimeter_m += perimeter_m

                feat = QgsFeature(mem_layer.fields())
                feat.setGeometry(geom)
                feat.setAttributes([
                    plume_count,
                    1,
                    user_threshold,
                    statistical_threshold,
                    final_threshold,
                    area_m2,
                    area_m2 / 1_000_000.0,
                    perimeter_m,
                ])
                features_to_add.append(feat)

            if plume_count == 0:
                QMessageBox.information(
                    self.plugin,
                    "No Plume Found",
                    "No plume polygon remained after thresholding, sieve filtering and minimum area filtering."
                )
                return

            mem_provider.addFeatures(features_to_add)
            mem_layer.updateExtents()

            zonal_flags = (
                QgsZonalStatistics.Count |
                QgsZonalStatistics.Sum |
                QgsZonalStatistics.Mean |
                QgsZonalStatistics.Max
            )

            zonal_stats = QgsZonalStatistics(
                mem_layer,
                raster_layer,
                "ch4_",
                1,
                zonal_flags
            )
            zonal_stats.calculateStatistics(None)

            total_pixel_count = 0
            total_ch4_sum = 0.0
            mean_values = []
            top_plume_id = None
            top_plume_max = None

            for plume_feat in mem_layer.getFeatures():
                try:
                    pixel_count = int(plume_feat["ch4_count"] or 0)
                except (TypeError, ValueError):
                    pixel_count = 0

                try:
                    ch4_sum = float(plume_feat["ch4_sum"] or 0.0)
                except (TypeError, ValueError):
                    ch4_sum = 0.0

                try:
                    ch4_mean = float(plume_feat["ch4_mean"])
                    mean_values.append(ch4_mean)
                except (TypeError, ValueError):
                    ch4_mean = None

                try:
                    ch4_max = float(plume_feat["ch4_max"])
                except (TypeError, ValueError):
                    ch4_max = None

                total_pixel_count += pixel_count
                total_ch4_sum += ch4_sum

                if ch4_max is not None and (top_plume_max is None or ch4_max > top_plume_max):
                    top_plume_max = ch4_max
                    top_plume_id = plume_feat["plume_id"]

            average_plume_mean = sum(mean_values) / len(mean_values) if mean_values else 0.0

            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = "GeoJSON"
            options.fileEncoding = "UTF-8"

            if os.path.exists(geojson_path):
                os.remove(geojson_path)

            ret = QgsVectorFileWriter.writeAsVectorFormatV3(
                mem_layer,
                geojson_path,
                QgsProject.instance().transformContext(),
                options
            )

            if ret[0] != QgsVectorFileWriter.NoError:
                QMessageBox.critical(self.plugin, "Write Error", f"Could not save plume GeoJSON:\n{ret}")
                return

            v_layer = QgsVectorLayer(geojson_path, f"Hotspot_Plumes_{raster_layer.name()}", "ogr")
            if not v_layer.isValid():
                QMessageBox.critical(self.plugin, "Layer Error", "Saved plume layer could not be loaded.")
                return

            QgsProject.instance().addMapLayer(v_layer)

            props = {
                "color": "255,0,0,100",
                "outline_color": "255,0,0,255",
                "outline_width": "0.4",
            }
            symbol = QgsFillSymbol.createSimple(props)
            v_layer.renderer().setSymbol(symbol)
            v_layer.triggerRepaint()

            if hasattr(self.plugin, 'refresh_plume_layers'):
                self.plugin.refresh_plume_layers()
            elif hasattr(self.plugin, 'plume_manager') and self.plugin.plume_manager:
                self.plugin.plume_manager.refresh_plume_layers()

        except Exception as e:
            QMessageBox.critical(self.plugin, "Analysis Failure", f"Hotspot polygonization failed:\n{str(e)}")
            return

        report = (
            f"==================================================\n"
            f"          CARBON MAPPER - PLUME ANALYSIS REPORT\n"
            f"==================================================\n\n"
            f"Input Raster:\n"
            f"{raster_layer.name()}\n\n"
            f"Detection Summary:\n"
            f"- Detected plume objects: {plume_count}\n"
            f"- Total plume area: {(total_area_m2 / 1_000_000.0):.4f} km2\n"
            f"- Total plume perimeter: {total_perimeter_m:.2f} m\n"
            f"- Removed small noise polygons: {removed_small_polygons}\n\n"
            f"CH4 Intensity Summary:\n"
            f"- Total plume pixels: {total_pixel_count}\n"
            f"- Average plume mean value: {average_plume_mean:.4f} ppm/m\n"
            f"- Strongest plume ID: {top_plume_id}\n"
            f"- Strongest plume max value: {(top_plume_max or 0.0):.4f} ppm/m\n"
            f"- Total CH4 raster sum inside plumes: {total_ch4_sum:.4f}\n\n"
            f"Threshold Used:\n"
            f"- User threshold: {user_threshold:.4f} ppm/m\n"
            f"- Applied effective threshold: {final_threshold:.4f} ppm/m\n\n"
            f"Output:\n"
            f"{geojson_path}\n\n"
            f"Status: COMPLETED\n"
            f"=================================================="
        )

        if report_txt:
            report_txt.setText(report)