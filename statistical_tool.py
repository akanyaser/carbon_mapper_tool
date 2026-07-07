"""
Statistical Comparison Tool

Compares Carbon Mapper observations between two selected
geographic regions (countries or polygons) for a selected
date range and gas type.

Outputs summary statistics such as:

- Number of plumes
- Mean emission
- Median emission
- Maximum emission
- Minimum emission
- Standard deviation
"""

from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QDateEdit,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QTextEdit,
    QHeaderView,
    QFileDialog,
    QCompleter,
    QLineEdit,
    QListView,
    QToolButton,
    QListWidget
)

from qgis.PyQt.QtCore import (
    Qt,
    QDate,
    QStringListModel,
    QSortFilterProxyModel
)

from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsFeatureRequest,
    QgsWkbTypes,
    QgsGeometry,
    QgsPointXY
)

from .api.carbon_api import (
    search_plume_csv,
    get_all_plumes
) 

import statistics

class StatisticalComparisonManager:

    def __init__(self, dialog):

        self.dialog = dialog

        self.combo_polygon_layer = dialog.findChild(
            QComboBox,
            "combo_polygon_layer"
        )

        self.combo_compare_gas = dialog.findChild(
            QComboBox,
            "combo_compare_gas"
        )

        self.start_date = dialog.findChild(
            QDateEdit,
            "start_compare_date"
        )

        self.end_date = dialog.findChild(
            QDateEdit,
            "end_compare_date"
        )

        self.list_regions = dialog.findChild(
            QListWidget,
            "list_regions"
        )

        self.btn_compare = dialog.findChild(
            QPushButton,
            "btn_compare"
        )

        self.combo_compare_field = dialog.findChild(
            QComboBox,
            "combo_compare_field"
        )

        self.table_statistics = dialog.findChild(
            QTableWidget,
            "table_statistics"
        )

        self.btn_export_statistics = dialog.findChild(
            QPushButton,
            "btn_export_statistics"
        )

        self.btn_export_statistics.clicked.connect(
            self.export_statistics_csv
        )
        
        self.combo_compare_gas.addItems(
            [
                "CH4",
                "CO2",
                "ALL"
            ]
        )

        self.btn_compare.clicked.connect(
            self.run_comparison
        )

        QgsProject.instance().layersAdded.connect(
            self.refresh_polygon_layers
        )

        QgsProject.instance().layersRemoved.connect(
            self.refresh_polygon_layers
        )

        self.refresh_polygon_layers()

    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

    def refresh_polygon_layers(self):
        self.combo_polygon_layer.clear()

        for layer in QgsProject.instance().mapLayers().values():
            if not isinstance(layer, QgsVectorLayer):
                continue
            
            if layer.geometryType() != QgsWkbTypes.PolygonGeometry:
                continue
            
            self.combo_polygon_layer.addItem(
                layer.name(),
                layer
            )
            print(layer.crs().authid())

        self.combo_polygon_layer.currentIndexChanged.connect(
            self.refresh_compare_fields
        )

        self.combo_polygon_layer.currentIndexChanged.connect(
            self.refresh_regions
        )

        self.combo_compare_field.currentIndexChanged.connect(
            self.refresh_regions
        )


        self.refresh_compare_fields()

        self.refresh_regions()
    
    def refresh_compare_fields(self):
        self.combo_compare_field.clear()
        layer = self.combo_polygon_layer.currentData()
        if layer is None:
            return
        
        for field in layer.fields():
            self.combo_compare_field.addItem(field.name())


    def refresh_regions(self):
        self.list_regions.clear()

        layer = self.combo_polygon_layer.currentData()

        if layer is None:
            return
        
        field_name = self.combo_compare_field.currentText()

        if not field_name:
            return

        names = []

        for feature in layer.getFeatures():
            value = feature[field_name]

            if value is not None and str(value).strip():
                names.append(str(value))

        names = sorted(set(names))

        self.list_regions.addItems(names)

    def make_combo_searchable(self, combo):
        combo.setEditable(True)
        line_edit = combo.lineEdit()
        model = QStringListModel()
        countries = []

        for i in range(combo.count()):
            countries.append(
                combo.itemText(i)
            )

        model.setStringList(countries)
        proxy = QSortFilterProxyModel(combo)
        proxy.setSourceModel(model)
        proxy.setFilterCaseSensitivity(
            Qt.CaseInsensitive
        )
        proxy.setFilterRegularExpression("")

        completer = QCompleter(proxy)
        completer.setCompletionMode(
            QCompleter.PopupCompletion
        )
        completer.setCaseSensitivity(
            Qt.CaseInsensitive
        )

        combo.setCompleter(completer)

    def filter_items(text):
        proxy.setFilterRegularExpression(text)

        line_edit.textEdited.connect(
            filter_items
        )
    
        
    def run_comparison(self):
        
        polygon_layer = (
            self.combo_polygon_layer.currentData()
        )

        selected_regions = [
            item.text()
            for item in self.list_regions.selectedItems()
        ]
        
        gas = (
            self.combo_compare_gas.currentText()
        )

        start_date = (
            self.start_date.date().toString("yyyy-MM-dd")
        )

        end_date = (
            self.end_date.date().toString("yyyy-MM-dd")
        )

        print(selected_regions)

        if len(selected_regions) < 2:
            QMessageBox.warning(
                self,
                "Selection",
                "Please select at least two regions."
            )
            return


        region_geometries = self.load_region_geometries(
            polygon_layer,
            selected_regions
        )

        if len(region_geometries) != len(selected_regions):
            QMessageBox.warning(
                self.dialog,
                "Geometry Error",
                "One or more selected regions could not be found."
            )

            return

        print(polygon_layer.crs().toWkt())

        region_plumes = {}

        for region in selected_regions:
            region_plumes[region] = self.load_region_plumes(
                region_geometries[region],
                gas,
                start_date,
                end_date
            )

        region_stats = self.calculate_region_statistics(
            region_plumes,
            selected_regions
        )

        self.last_regions = selected_regions
        self.last_region_stats = region_stats

        self.show_statistics(
            selected_regions,
            region_stats
        )

        for region in selected_regions:
            print("---------------------")
            print(region)
            print(region_stats[region])
    
    def load_region_plumes(
            self,
            geometry,
            gas,
            start_date,
            end_date
    ):
        bbox = geometry.boundingBox()
        bbox_values = [
            bbox.xMinimum(),
            bbox.yMinimum(),
            bbox.xMaximum(),
            bbox.yMaximum()
        ]

        plumes = get_all_plumes(
            bbox=bbox_values,
            gas=gas,
            datetime_range=f"{start_date}/{end_date}"
        )

        region_plumes = []

        for plume in plumes:
            try:
                lon = float(plume["plume_longitude"])
                lat = float(plume["plume_latitude"])
            
            except:
                continue
            
            point = QgsGeometry.fromPointXY(
                QgsPointXY(lon, lat)
            )
            
            if geometry.contains(point):
                region_plumes.append(plume)

        return region_plumes
    
    def calculate_region_statistics(
            self,
            region_plumes,
            selected_regions
    ):
        region_stats = {}

        for region in selected_regions:
            region_stats[region] = self.calculate_statistics(
                region_plumes[region]
            )

        return region_stats
    
    def load_region_geometries(
            self,
            polygon_layer,
            selected_regions
    ):
        region_geometries = {}

        for region in selected_regions:
            geometry = self.get_region_geometry(
                polygon_layer,
                region
            )

            if geometry is not None:
                region_geometries[region] = geometry
            
        return region_geometries

    def get_region_geometry(
            self,
            layer,
            region_name
    ):
        field_name = self.combo_compare_field.currentText()

        for feature in layer.getFeatures():
            if str(feature[field_name]) == str(region_name):
                 geometry = feature.geometry()

                 return geometry

        return None
     
    def calculate_statistics(
            self,
            plumes
    ):
        emissions = []

        for plume in plumes:
            try:
                emissions.append(
                    float(plume["emission_auto"])
                )
            except:
                pass
            
        if not emissions:
            return {
                "plumes": 0,
                "count": 0,
                "mean": 0,
                "median": 0,
                "minimum": 0,
                "maximum": 0,
                "std": 0
            }
        
        stats = {
            "plumes": len(plumes),
            "count": len(emissions),
            "mean": statistics.mean(emissions),
            "median": statistics.median(emissions),
            "minimum": min(emissions),
            "maximum": max(emissions),
            "std": statistics.stdev(emissions)
                if len(emissions) > 1 else 0
        }

        return stats
    
    def show_statistics(
            self,
            selected_regions,
            region_stats
    ):
        metrics = [
            ("Plume Count", "plumes"),
            ("Emission Record Count", "count"),
            ("Mean Emission (kg/hr)", "mean"),
            ("Median Emission (kg/hr)", "median"),
            ("Minimum Emisison (kg/hr)", "minimum"),
            ("Maximum Emission (kg/hr)", "maximum"),
            ("Std. Deviation (kg/hr)", "std")
        ]

        self.table_statistics.setRowCount(len(metrics))
        self.table_statistics.setColumnCount(
            len(selected_regions) + 1
        )

        headers = ["Statistic"] + selected_regions
        self.table_statistics.setHorizontalHeaderLabels(headers)

        for row, (metric_name, metric_key) in enumerate(metrics):
            self.table_statistics.setItem(
                row,
                0,
                QTableWidgetItem(metric_name)
            )

            for col, region in enumerate(selected_regions, start=1):
                value = region_stats.get(region, {}).get(metric_key, 0)

                if isinstance(value, float):
                    value = round(value, 2)
                
                self.table_statistics.setItem(
                    row,
                    col,
                    QTableWidgetItem(str(value))
                )

        self.table_statistics.resizeColumnsToContents()
        self.table_statistics.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )

        self.table_statistics.verticalHeader().setVisible(False)

    def export_statistics_csv(self):
        if not hasattr(self, "last_region_stats"):
            QMessageBox.information(
                self.dialog,
                "Export",
                "Please run a comparison first."
            )
            return
        
        default_name = "_vs_".join(self.last_regions)
        filename, _ = QFileDialog.getSaveFileName(
            self.dialog,
            "Save Statistics",
            f"{default_name}.csv",
            "CSV Files (*.csv)"
        )

        if not filename:
            return
        
        metrics = [
            ("Plume Count", "plumes"),
            ("Emission Record Count", "count"),
            ("Mean Emission (kg/hr)", "mean"),
            ("Median Emission (kg/hr)", "median"),
            ("Minimum Emission (kg/hr)", "minimum"),
            ("Maximum Emission (kg/hr)", "maximum"),
            ("Std. Deviation (kg/hr)", "std")
        ]

        import csv

        with open(
            filename,
            "w",
            newline="",
            encoding="utf-8"
        ) as f:
            writer = csv.writer(f)

            headers = ["Statistic"] + self.last_regions
            writer.writerow(headers)

            for metric_name, metric_key in metrics:
                row = [metric_name]

                for region in self.last_regions:
                    value = self.last_region_stats[region][metric_key]

                    if isinstance(value, float):
                        value = round(value, 2)
                    
                    row.append(value)
                writer.writerow(row)

        QMessageBox.information(
            self.dialog,
            "Export",
            "Statistics exported successfully."
        )















            







       