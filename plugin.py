
"""
Main plugin dialog module for the Carbon Mapper QGIS plugin.

This module initializes the plugin interface, loads the Qt Designer UI file,
connects search and download actions, queries Carbon Mapper STAC products for
the current QGIS map extent, displays returned products in a table, downloads
selected assets, and loads raster outputs into QGIS when applicable.
"""

import os
import numpy as np
import requests
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QObject, QEvent
from qgis.PyQt.QtWidgets import QDialog, QTableWidgetItem, QMessageBox, QComboBox, QPushButton, QLineEdit, QRadioButton, QFileDialog, QTextEdit, QTabWidget, QDateEdit
from qgis.gui import QgsMapToolExtent
from qgis.core import Qgis, QgsPointXY, QgsRectangle, QgsProject, QgsRasterLayer, QgsVectorLayer, QgsFeature, QgsGeometry, QgsPoint, QgsMapLayer

from .analysis import AnalysisManager
from .plume_environment_analysis import PlumeEnvironmentalAnalysisManager

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'widget.ui'))

class CarbonMapperPlugin(QDialog, FORM_CLASS):

    def __init__(self, iface):
        super(CarbonMapperPlugin, self).__init__()
        self.iface = iface
        self.action = None
        self.features = []
        self.map_tool = None
        self.all_collections = []  # Raw collection list from the live API
        self.assets_cache = {}  # Asset cache

        self.setupUi(self)  # Load the interface
   
        self.setWindowTitle("Carbon Mapper Tool")
       
        # STARTING TWO SEPARATE ANALYSIS MANAGERS
        self.analysis_manager = AnalysisManager(self)
        self.plume_manager = PlumeEnvironmentalAnalysisManager(self)

        self.setup_ui_defaults()
        self.setup_three_level_comboboxes()
        self.collection_combo.currentIndexChanged.connect(
            self.update_assets_for_collection
        )

        # Basic Element Links (AOI & Download Tabs)
        if hasattr(self, 'search_btn') and self.search_btn:
            self.search_btn.clicked.connect(self.handle_search)
        if hasattr(self, 'download_btn') and self.download_btn:
            self.download_btn.clicked.connect(self.handle_download)
        if hasattr(self, 'aoi_btn') and self.aoi_btn:
            self.aoi_btn.clicked.connect(self.start_aoi_selection)
        if hasattr(self, 'browse_dir_btn') and self.browse_dir_btn:
            self.browse_dir_btn.clicked.connect(self.browse_output_directory)
        if hasattr(self, 'radio_canvas_aoi') and hasattr(self, 'radio_custom_aoi'):
            self.radio_canvas_aoi.toggled.connect(self.toggle_aoi_mode)
            self.radio_custom_aoi.toggled.connect(self.toggle_aoi_mode)

        #  Tab Switching Buttons Links
        if hasattr(self, 'next_btn') and self.next_btn:
            self.next_btn.clicked.connect(self.switch_to_download_tab)
        if hasattr(self, 'download_prev_btn') and self.download_prev_btn:
            self.download_prev_btn.clicked.connect(self.switch_to_aoi_tab)
        if hasattr(self, 'download_next_btn') and self.download_next_btn:
            self.download_next_btn.clicked.connect(self.switch_to_analysis_tab)
        if hasattr(self, 'analysis_prev_btn') and self.analysis_prev_btn:
            self.analysis_prev_btn.clicked.connect(self.switch_to_download_tab)

        #  SEPARATED MODULE SIGNAL LINKS
        # LEFT PANEL: Hotspot Analysis (analysis.py)
        if hasattr(self, 'analysis_btn') and self.analysis_btn:
            self.analysis_btn.clicked.connect(self.analysis_manager.run_hotspot_analysis)
        if hasattr(self, 'analysis_browse_btn') and self.analysis_browse_btn:
            self.analysis_browse_btn.clicked.connect(self.analysis_manager.browse_output_directory_hotspot)

        # RIGHT PANEL: Plume Environmental Impact Analysis (plume_environment_analysis.py)
        if hasattr(self, 'btn_run_analysis_ei') and self.btn_run_analysis_ei:
            self.btn_run_analysis_ei.clicked.connect(self.plume_manager.run_environmental_analysis)
        if hasattr(self, 'btn_browse_ei') and self.btn_browse_ei:
            self.btn_browse_ei.clicked.connect(self.plume_manager.browse_output_directory_ei)

        #  Global Tab Change Listeners and QGIS Layer Triggers
        self.main_tab_widget = self.findChild(QTabWidget, "tabWidget")
       
        if self.main_tab_widget:
            print(" The main tab (tabWidget) was successfully found and the listener is connected.")
            self.main_tab_widget.currentChanged.connect(self.on_tab_changed)
        else:
            print("ERROR: The object named 'tabWidget' could not be found using findChild!")

        # In QGIS Layer Changes, we refresh the lists for both managers.
        QgsProject.instance().layersAdded.connect(self.refresh_all_analysis_combos)
        QgsProject.instance().layersRemoved.connect(self.refresh_all_analysis_combos)

        # We trigger the interface to automatically populate the lists when it loads for the first time.
        self.refresh_all_analysis_combos()

    # DYNAMIC LIVE API AND CHAINED FILTERING LOGIC
    def setup_three_level_comboboxes(self):
        try:
            url = "https://api.carbonmapper.org/api/v1/stac/collections"
            response = requests.get(url, timeout=20)
            if response.status_code != 200:
                return
            
            data = response.json()
            self.all_collections = []

            for collection in data.get("collections", []):
                coll_id = collection.get("id")

                if coll_id:
                    self.all_collections.append(coll_id)

            print("Bulunan collectionlar:")
            print(self.all_collections)

            # GAS
            if hasattr(self, "combo_gas"):
                self.combo_gas.blockSignals(True)
                self.combo_gas.clear()
                self.combo_gas.addItems([
                    "All",
                    "CH4",
                    "CO2"
                ])
            
                self.combo_gas.blockSignals(False)

            # LEVEL
            if hasattr(self, "combo_level"):
                self.combo_level.blockSignals(True)
                self.combo_level.clear()
                self.combo_level.addItems([
                    "All",
                    "L2",
                    "L3",
                    "L4"
                ])

                self.combo_level.blockSignals(False)
            
            try:
                self.combo_gas.currentIndexChanged.disconnect()
            except:
                pass
            
            try:
                self.combo_level.currentIndexChanged.disconnect()
            except:
                pass
            
            self.combo_gas.currentIndexChanged.connect(
                self.filter_collections
            )

            self.combo_level.currentIndexChanged.connect(
                self.filter_collections
            )

            self.filter_collections()
        
        except Exception as e:
            print(f"setup_three_level_comboboxes error: {e}")

    def filter_collections(self):
        if not hasattr(self, "collection_combo"):
            return
        
        selected_gas = self.combo_gas.currentText().lower()
        selected_level = self.combo_level.currentText().lower()

        self.collection_combo.clear()

        for coll in self.all_collections:
            # Performing a string check to prevent the code from breaking.
            coll_lower = coll.lower()
            
            # First step is checking the gas
            # The selected gas will match if it is "all" or if it appears in the collection name (e.g., CH4 or CO2).
            gas_match = (
                selected_gas == "all"
                or selected_gas in coll_lower
            )

            # Second step is checking the product level
            # Matches if the selected level is "all" or if the collection name starts with that level (l2 or l3)
            level_match = (
                selected_level == "all"
                or coll_lower.startswith(selected_level)
            )

            # Third step is adding to the combo
            if gas_match and level_match:
                display_name = coll
                self.collection_combo.addItem(
                    display_name,
                    coll
                )

    def update_assets_for_collection(self):
        collection_id = self.collection_combo.currentData()
        if not collection_id:
            return

        self.asset_combo.clear()

        # If caching exists, do not make an API call.
        if collection_id in self.assets_cache:
            self.asset_combo.addItems(self.assets_cache[collection_id])
            return

        try:
            search_url = "https://api.carbonmapper.org/api/v1/stac/search"

            payload = {
                "collections": [collection_id],
                "limit": 1
            }

            response = requests.post(
                search_url,
                json=payload,
                timeout=20
            )

            if response.status_code != 200:
                return

            data = response.json()
            features = data.get("features", [])

            if not features:
                self.asset_combo.addItem("No assets available")
                self.assets_cache[collection_id] = ["No assets available"]
                return

            assets = features[0].get("assets", {})

            if assets:
                asset_names = sorted(assets.keys())
                self.asset_combo.addItems(asset_names)
                self.assets_cache[collection_id] = asset_names
            else:
                self.asset_combo.addItem("No assets available")
                self.assets_cache[collection_id] = ["No assets available"]

        except Exception as e:
            print(f"Asset loading error: {e}")

    def initGui(self):
        from qgis.PyQt.QtWidgets import QAction
        self.action = QAction("Carbon Mapper Tool", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&Carbon Mapper", self.action)

    def unload(self):
        if self.action:
            self.iface.removePluginMenu("&Carbon Mapper", self.action)
            self.iface.removeToolBarIcon(self.action)

    def run(self):
        self.refresh_all_analysis_combos()
        self.setup_ui_defaults()
        
        # Setting up the live API structure and fill in the boxes before the interface is revealed.
        self.setup_three_level_comboboxes()
        
        self.show()
        if hasattr(self, 'tabWidget'):
            self.tabWidget.setCurrentIndex(0) # 0, Area of Interest tab.

        # ---HELP & DOCUMENTATION---
        from qgis.PyQt.QtWidgets import QTextBrowser
       
        help_browser = self.findChild(QTextBrowser, "txt_help_guide")
       
        if help_browser:
            print("'txt_help_guide' found, loading documentation....")
            help_text = """
            <div style="font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; padding: 5px; color: #333333;">
               
                <div style="text-align: left; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid #cccccc;">
                    <h2 style="color: #1a365d; margin: 0; font-size: 18px; font-weight: bold;">Carbon Mapper CH4 & CO2 Monitoring Tool</h2>
                    <p style="margin: 5px 0 0 0; color: #666666; font-size: 12px;">Advanced Remote Sensing Core Analytics Plugin for QGIS</p>
                </div>

                <p>Welcome to the Carbon Mapper Data Manager Plugin. This specialized tool allows you to connect directly to the Carbon Mapper airborne and satellite index to download and analyze high-emission methane (CH4) and carbon dioxide (CO2) plume data matrix maps inside QGIS.</p>
               
                <h3 style="color: #1a365d; font-size: 14px; margin-top: 20px; margin-bottom: 8px; font-weight: bold;">
                    1. Requirements:
                </h3>
                <ul style="margin-left: 0; padding-left: 20px; margin-top: 5px;">
                    <li style="margin-bottom: 5px;"><b>QGIS Installed:</b> Version 3.22 or higher.</li>
                    <li style="margin-bottom: 5px;"><b>Python Environment:</b> Secure internet connection accessible by QGIS core network handlers.</li>
                    <li style="margin-bottom: 5px;"><b>Required Packages:</b> Ensure the baseline network dependency is ready via the OSGeo4W Shell or terminal:
                        <br/><code style="background-color: #f5f5f5; padding: 3px 6px; border: 1px solid #dddddd; border-radius: 3px; font-size: 11px; display: inline-block; margin-top: 5px; color: #333333; font-family: Consolas, Monaco, monospace;">pip install requests</code>
                    <li style="margin-bottom: 5px;"><b>Core Subsystems:<b> This plugin natively leverages QGIS Processing Framework and GDAL core algorithms (gdal:sieve, gdal:polygonize). No heavy matrix libraries are required.
                    </li>
                </ul>
               
                <h3 style="color: #1a365d; font-size: 14px; margin-top: 20px; margin-bottom: 8px; font-weight: bold;">
                    2. How to Get Your API Token:
                </h3>
                <p>To query datasets from the Carbon Mapper archive, an official API infrastructure access credential is necessary. Follow these steps:</p>
                <ol style="margin-left: 0; padding-left: 20px; margin-top: 5px;">
                    <li style="margin-bottom: 6px;">Visit the data portal at <a href="https://data.carbonmapper.org" style="color: #0066cc; text-decoration: underline;">https://data.carbonmapper.org</a>.</li>
                    <li style="margin-bottom: 6px;">Register a verified account or log into your researcher workspace.</li>
                    <li style="margin-bottom: 6px;">Navigate to your <b>User Profile / Developer Settings</b> panel on the dashboard interface.</li>
                    <li style="margin-bottom: 6px;">Locate the <b>API Keys</b> section and trigger the "Generate New Access Token" action.</li>
                    <li style="margin-bottom: 6px;">Copy the securely generated alphanumeric hash token string.</li>
                    <li style="margin-bottom: 6px;">Paste the copied string directly into the <b>API Token Input Box</b> located inside the first tab of this plugin to handle authorization during live asset streams.</li>
                </ol>
                <div style="background-color: #f9f9f9; border: 1px solid #dddddd; padding: 10px; margin: 15px 0; border-radius: 4px; font-size: 12px;">
                    <b>Important Note:</b> Guard your API key securely. If queries unexpectedly fail with authorization faults, refresh your token on the portal or re-verify that the input sequence does not contain accidental trailing spaces.
                </div>

                <h3 style="color: #1a365d; font-size: 14px; margin-top: 20px; margin-bottom: 8px; font-weight: bold;">
                    3. Using the Plugin:
                </h3>
                <ul style="margin-left: 0; padding-left: 20px; margin-top: 5px; list-style-type: square;">
                    <li style="margin-bottom: 8px;"><b>Step 1: Select Your AOI (Area of Interest)</b>
                        <br/><span style="color: #555555; font-size: 12px;">Choose Map Canvas extent or type manual bounding coordinates to limit the target search boundary footprint grid.</span>
                    </li>
                    <li style="margin-bottom: 8px;"><b>Step 2: Filter Parameters & Query Index</b>
                        <br/><span style="color: #555555; font-size: 12px;">Choose the appropriate or filtered collection layer, configure operational target date frames, and tap [Search Data Products].</span>
                    </li>
                    <li style="margin-bottom: 8px;"><b>Step 3: Select Asset and Download</b>
                        <br/><span style="color: #555555; font-size: 12px;">Highlight rows in the catalog registry table, determine your desired data type component, define a local storage output path, and click [Download and Load into Canvas].</span>
                    </li>
                    <li style="margin-bottom: 8px;"><b>Step 4: Execute Core Scientific Engines (Analysis Tab)</b>
                        <br/><span style="color: #555555; font-size: 12px;"><b>Left Side (Hotspot Analysis):</b> Left Side (Hotspot Analysis): Scans the active raster layer to dynamically generate verified emission core polygons based on your specified ppm.m adaptive concentration thresholds and automatic GDAL Sieve noise filtering.</span>
                        <br/><span style="color: #555555; font-size: 12px;"><b>Right Side (Plume Environmental Impact Analysis):</b> Reads the extracted plume vector boundaries, evaluates them against a continuous 12-point multi-criteria risk index, updates the layer's internal attribute database tables, and creates a report for institutional workflows.</span>
                    </li>
                </ul>

                <hr style="border: 0; border-top: 1px solid #eeeeee; margin-top: 25px; margin-bottom: 15px;"/>
                <p style="color: #777777; font-size: 11px; text-align: center; margin: 0;">
                    <b>Academic Project / Institutional Operations Support Contact:</b> If you experience unexpected exceptions, check the QGIS log panels or coordinate with your university laboratory supervisor.
                </p>
            </div>
            """
            help_browser.setHtml(help_text)
        else:
            print("ERROR: 'txt_help_guide' not found in QTextBrowser interface!")

    def setup_ui_defaults(self):
        if hasattr(self, 'collection_combo') and self.collection_combo is not None:
            self.collection_combo.clear()
            
        if hasattr(self, 'asset_combo') and self.asset_combo is not None:
            self.asset_combo.clear()
            self.asset_combo.addItems(["cmf.tif", "data.tif", "browse.png", "metadata.json", "plume.geojson"])

        if hasattr(self, 'start_date_edit') and isinstance(self.start_date_edit, QDateEdit):
            self.start_date_edit.setCalendarPopup(True)
        if hasattr(self, 'end_date_edit') and isinstance(self.end_date_edit, QDateEdit):
            self.end_date_edit.setCalendarPopup(True)

        if hasattr(self, 'products_table') and self.products_table:
            self.products_table.setColumnCount(4)
            self.products_table.setHorizontalHeaderLabels(["Feature ID", "Product Level", "Acquisition Date", "Status"])
            self.products_table.horizontalHeader().setStretchLastSection(True)

        if hasattr(self, 'toggle_aoi_mode'):
            self.toggle_aoi_mode()

        if hasattr(self, 'progress_bar') and self.progress_bar is not None:
            self.progress_bar.setMinimum(0)
            self.progress_bar.setMaximum(100)
            self.progress_bar.setValue(0)  

        self.refresh_all_analysis_combos()

    def refresh_all_analysis_combos(self):
        """Triggering the layer refresh logic in both separate analytics managers."""
        if hasattr(self, 'analysis_manager') and self.analysis_manager:
            self.analysis_manager.refresh_raster_layers()
        if hasattr(self, 'plume_manager') and self.plume_manager:
            self.plume_manager.refresh_plume_layers()

    def on_tab_changed(self, index):
        print(f"The tab has changed! The new active tab index.: {index}")
        if index == 2: # If the Analysis tab is open, it automatically refreshes the layer lists.
            print("The analytics tab has been detected, and layers are being refreshed for both analytics managers...")
            self.refresh_all_analysis_combos()

    def browse_output_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory", "")
        if dir_path and hasattr(self, 'output_dir_input') and self.output_dir_input:
            self.output_dir_input.setText(dir_path)

    def switch_to_aoi_tab(self):
        if self.main_tab_widget: self.main_tab_widget.setCurrentIndex(0)

    def switch_to_download_tab(self):
        if hasattr(self, 'radio_custom_aoi') and self.radio_custom_aoi and self.radio_custom_aoi.isChecked():
            bbox = self.get_current_bbox()
            if not bbox:
                QMessageBox.warning(self, "Coordinate Error", "Please enter valid numeric values for Custom Bounding Box before proceeding!")
                return
        if self.main_tab_widget: self.main_tab_widget.setCurrentIndex(1)

    def switch_to_analysis_tab(self):
        if self.main_tab_widget:
            self.main_tab_widget.setCurrentIndex(2)
            self.refresh_all_analysis_combos()

    def toggle_aoi_mode(self):
        if hasattr(self, 'radio_canvas_aoi') and self.radio_canvas_aoi and self.radio_canvas_aoi.isChecked():
            if hasattr(self, 'aoi_btn') and self.aoi_btn: self.aoi_btn.setEnabled(True)
            self.set_coordinate_fields_editable(False)
        else:
            if hasattr(self, 'aoi_btn') and self.aoi_btn: self.aoi_btn.setEnabled(False)
            self.set_coordinate_fields_editable(True)

    def set_coordinate_fields_editable(self, status):
        for field_name in ['txt_north', 'txt_west', 'txt_south', 'txt_east']:
            if hasattr(self, field_name):
                field = getattr(self, field_name)
                if field: field.setReadOnly(not status)

    def start_aoi_selection(self):
        self.hide()
        self.map_tool = QgsMapToolExtent(self.iface.mapCanvas())
        self.iface.mapCanvas().setMapTool(self.map_tool)
        self.map_tool.extentChanged.connect(self.aoi_selection_finished)

    def aoi_selection_finished(self, extent):
        self.iface.mapCanvas().unsetMapTool(self.map_tool)
        if extent:
            if hasattr(self, 'txt_north') and self.txt_north: self.txt_north.setText(str(round(extent.yMaximum(), 5)))
            if hasattr(self, 'txt_south') and self.txt_south: self.txt_south.setText(str(round(extent.yMinimum(), 5)))
            if hasattr(self, 'txt_east') and self.txt_east: self.txt_east.setText(str(round(extent.xMaximum(), 5)))
            if hasattr(self, 'txt_west') and self.txt_west: self.txt_west.setText(str(round(extent.xMinimum(), 5)))
        self.show()

    def get_current_bbox(self):
        from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsRectangle, QgsProject
        try:
            n = float(self.txt_north.text().strip())
            w = float(self.txt_west.text().strip())
            s = float(self.txt_south.text().strip())
            e = float(self.txt_east.text().strip())
        except (ValueError, AttributeError):
            return None

        if abs(w) > 180 or abs(n) > 90:
            try:
                src_crs = self.iface.mapCanvas().mapSettings().destinationCrs()
                dest_crs = QgsCoordinateReferenceSystem("EPSG:4326")
                transform = QgsCoordinateTransform(src_crs, dest_crs, QgsProject.instance())
                rect = QgsRectangle(w, s, e, n)
                transformed_rect = transform.transformBoundingBox(rect)
                return [
                    round(transformed_rect.xMinimum(), 5),
                    round(transformed_rect.yMinimum(), 5),
                    round(transformed_rect.xMaximum(), 5),
                    round(transformed_rect.yMaximum(), 5)
                ]
            except Exception as transform_error:
                print(f" CRS Transformation Error: {str(transform_error)}")
                return [w, s, e, n]
        else:
            return [w, s, e, n]

    def handle_search(self):
        # Reading the selection from the hidden API code in the background using `.currentData()`!
        combo = getattr(self, 'collection_combo', None)
        if not combo or combo.currentIndex() == -1:
            QMessageBox.warning(self, "UI Error", "Collection selection error!")
            return
       
        limit = self.limit_spin.value() if hasattr(self, 'limit_spin') else 10
        bbox = self.get_current_bbox()
       
        if hasattr(self, 'radio_custom_aoi') and self.radio_custom_aoi and self.radio_custom_aoi.isChecked():
            if not bbox:
                QMessageBox.warning(self, "Coordinate Error", "Please enter valid numeric values for Custom Bounding Box!")
                return
        else:
            if not bbox or any(v is None for v in bbox) or bbox == [0, 0, 0, 0]:
                QMessageBox.warning(self, "Validation Error", "Please define a valid Area of Interest (AOI) on the canvas before searching!")
                return
               
        #  Retrieving the actual API code (l2b-ch4, etc.) with `.currentData()`.
        collection = combo.currentData() if combo.currentData() else "l2b-ch4"
        collections_to_try = [collection]
        if collection == "l3a-plumes":
            collections_to_try.append("plumes")
       
        start_widget = self.findChild(QDateEdit, 'start_date_edit')
        end_widget = self.findChild(QDateEdit, 'end_date_edit')
       
        start_dt = start_widget.date().toString("yyyy-MM-dd") if start_widget else "2024-01-01"
        end_dt = end_widget.date().toString("yyyy-MM-dd") if end_widget else "2026-01-01"
        datetime_range = f"{start_dt}/{end_dt}"

        token = self.token_input.text().strip() if hasattr(self, 'token_input') else ""

        if bbox:
            bbox = [
                round(bbox[0] - 0.5, 5),
                round(bbox[1] - 0.5, 5),
                round(bbox[2] + 0.5, 5),
                round(bbox[3] + 0.5, 5)
            ]

        from geoprojects.api.carbon_api import search_data
       
        self.features = []
        for coll in collections_to_try:
            print(f"Carbon Mapper API call is being made... Package: {coll}")
            print(f"BBOX: {bbox} |  Time Range: {datetime_range}")
            try:
                res = search_data(collection=coll, bbox=bbox, datetime_range=datetime_range, limit=limit, token=token)
                if res:
                    self.features = res
                    collection = coll
                    print(f" {coll} The products were successfully found in the package!")
                    break
            except Exception as e:
                print(f" {coll} Search failed, trying another variation... Error: {str(e)}")

        try:
            if hasattr(self, 'products_table') and self.products_table:
                self.populate_table(self.features, collection)
        except Exception as e:
            QMessageBox.critical(self, "API Error", f"An error occurred while updating table:\n{str(e)}")

    def populate_table(self, features, collection_name):
        self.products_table.setRowCount(0)
        if not features:
            QMessageBox.information(self, "No Results", "No features found for the current parameters.")
            return
        for row_idx, feature in enumerate(features):
            self.products_table.insertRow(row_idx)
            self.products_table.setItem(row_idx, 0, QTableWidgetItem(feature.get("id", "N/A")))
            self.products_table.setItem(row_idx, 1, QTableWidgetItem(collection_name.upper()))
            date_str = feature.get("properties", {}).get("datetime", "Unknown")
            if date_str != "Unknown": date_str = date_str[:10]
            self.products_table.setItem(row_idx, 2, QTableWidgetItem(date_str))
            self.products_table.setItem(row_idx, 3, QTableWidgetItem("Ready to Download"))

    def handle_download(self):
        asset_combo = getattr(self, 'asset_combo', None)
        coll_combo = getattr(self, 'collection_combo', None)
       
        #  Capturing the raw API code using .currentData() during the download process.
        collection = coll_combo.currentData() if (coll_combo and coll_combo.currentData()) else "l2b-ch4"
        token = self.token_input.text().strip() if hasattr(self, 'token_input') else ""

        if not self.features:
            QMessageBox.information(self, "Info", "Please perform a search first.")
            return
           
        output_dir = self.output_dir_input.text().strip() if hasattr(self, 'output_dir_input') else ""
        if not output_dir:
            QMessageBox.warning(self, "Validation Error", "Please select an Output Directory before downloading!")
            return

        from geoprojects.api.carbon_api import download_asset
        from geoprojects.utils.qgis_utils import add_raster_to_qgis

        total_files = len(self.features)
        download_count = 0
        active_bar = 'progress_bar' if hasattr(self, 'progress_bar') else 'progressBar'
        if hasattr(self, active_bar):
            getattr(self, active_bar).setMaximum(total_files)
            getattr(self, active_bar).setValue(0)

        for i, feature in enumerate(self.features):
            try:
                if hasattr(self, 'products_table') and self.products_table:
                    self.products_table.setItem(i, 3, QTableWidgetItem("Downloading..."))
                    self.products_table.repaint()
               
                assets = feature.get('assets', {})
               
                user_selected_asset = asset_combo.currentText() if (asset_combo and asset_combo.currentText()) else None
               
                asset_type = None
               
                if user_selected_asset and user_selected_asset in assets:
                    asset_type = user_selected_asset
               
                elif "l3a" in collection:
                    asset_type = next((k for k in assets.keys() if 'geojson' in k.lower()), None)
                   
                    if not asset_type:
                        asset_type = next((k for k in assets.keys() if 'plume' in k.lower() or 'vis' in k.lower()), None)
                   
                    if not asset_type and assets:
                        asset_type = list(assets.keys())[0]
                else:
                    asset_type = user_selected_asset if user_selected_asset else "cmf.tif"

                if not asset_type:
                    print(f" {feature['id']} No available asset was found!")
                    if hasattr(self, 'products_table') and self.products_table:
                        self.products_table.setItem(i, 3, QTableWidgetItem("No Asset"))
                    continue

                print(f"The actual asset name to be downloaded: {asset_type}")

                file_path = download_asset(feature=feature, token=token, asset_name=asset_type, index=i, output_dir=output_dir)
               
                if file_path and os.path.exists(file_path):
                    custom_layer_name = f"{collection}_{feature['id'][:8]}_{i}"
                   
                    if file_path.endswith(".tif"):
                        add_raster_to_qgis(file_path, custom_layer_name)
                    elif file_path.endswith(".png") or file_path.endswith(".jpg"):
                        add_raster_to_qgis(file_path, custom_layer_name)
                    elif file_path.endswith(".geojson") or file_path.endswith(".shp") or file_path.endswith(".json"):
                        v_layer = QgsVectorLayer(file_path, custom_layer_name, "ogr")
                        if v_layer.isValid():
                            QgsProject.instance().addMapLayer(v_layer)
                        else:
                            print(f"An error occurred while loading the vector layer: {file_path}")
                           
                    download_count += 1
                    if hasattr(self, 'products_table') and self.products_table:
                        self.products_table.setItem(i, 3, QTableWidgetItem("Success"))
                else:
                    if hasattr(self, 'products_table') and self.products_table:
                        self.products_table.setItem(i, 3, QTableWidgetItem("Failed"))
            except Exception as e:
                print(f"An error occurred during the download: {str(e)}")
                if hasattr(self, 'products_table') and self.products_table:
                    self.products_table.setItem(i, 3, QTableWidgetItem("Error"))
            if hasattr(self, active_bar):
                getattr(self, active_bar).setValue(i + 1)

        QMessageBox.information(self, "Successful", f"{download_count} data products successfully processed!")
        self.refresh_all_analysis_combos()