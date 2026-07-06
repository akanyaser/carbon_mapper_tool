
"""
Main plugin dialog module for the Carbon Mapper QGIS plugin.

This module initializes the plugin interface, loads the Qt Designer UI file,
connects search and download actions, queries Carbon Mapper STAC products for
the current QGIS map extent, displays returned products in a table, downloads
selected assets, and loads raster outputs into QGIS when applicable.
"""

import os
import requests
import json
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QApplication, QTableWidgetItem, QMessageBox, QComboBox, QFileDialog, QTabWidget, QDateEdit, QLabel, QGroupBox, QToolButton
from qgis.gui import QgsMapToolExtent
from qgis.core import Qgis, QgsPointXY, QgsRectangle, QgsProject, QgsRasterLayer, QgsVectorLayer, QgsFeature, QgsGeometry, QgsPoint, QgsMapLayer
from qgis.core import (
    QgsWkbTypes,
    QgsField
)
from qgis.PyQt.QtCore import QVariant

from .statistical_tool import StatisticalComparisonManager
from .help_messages import HelpMessages

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'widget.ui'))

class CarbonMapperPlugin(QDialog, FORM_CLASS):

    def __init__(self, iface):
        super(CarbonMapperPlugin, self).__init__()
        self.iface = iface
        self.action = None
        self.features = []
        self.map_tool = None
        self.all_collections = []  # Raw collection list from the live API
        self.source_features = []
        self.source_plume_map = {}
        self.assets_cache = {} # Asset cache
        self.plume_asset_cache = {} 

        self.setupUi(self)  # Load the interface
   
        self.setWindowTitle("Carbon Mapper Data Explorer")
        self.help_messages = HelpMessages(self)

        self.groupBox_data_api = self.findChild(
            QGroupBox,
            "groupBox_data_api"
        )

        self.groupBox_stac_api = self.findChild(
            QGroupBox,
            "groupBox_stac_api"
        )

        self.stac_combo_gas = self.findChild(
            QComboBox,
            "stac_combo_gas"
        )

        self.stac_combo_level = self.findChild(
            QComboBox,
            "stac_combo_level"
        )

        self.stac_combo_asset = self.findChild(
            QComboBox,
            "stac_combo_asset"
        )

        self.stac_asset_type_label = self.findChild(
            QLabel,
            "stac_api_asset_type_label"
        )

        self.stac_gas_label = self.findChild(
            QLabel,
            "stac_gas_type_label"
        )

        self.level_label = self.findChild(
            QLabel,
            "level_label"
        )

        self.data_asset_type_label = self.findChild(
            QLabel,
            "label_3"
        )

        self.token_label = self.findChild(
            QLabel,
            "label"
        )

        self.data_type_label = self.findChild(
            QLabel,
            "label_17"
        )
       
        self.stac_combo_collection = self.findChild(
           QComboBox,
           "stac_combo_collection"
        )

        self.stac_collection_label = self.findChild(
            QLabel,
            "collection_combo_label"
        )

        self.btn_info_data_type = self.findChild(
            QToolButton,
            "btn_info_data_type"
        )

        self.btn_info_gas = self.findChild(
            QToolButton,
            "btn_info_gas"
        )

        self.btn_info_asset = self.findChild(
            QToolButton,
            "btn_info_asset"
        )

        self.btn_info_stac_gas = self.findChild(
            QToolButton,
            "btn_info_stac_gas"
        )
        
        self.btn_info_level = self.findChild(
            QToolButton,
            "btn_info_level"
        )

        self.btn_info_collection = self.findChild(
            QToolButton,
            "btn_info_collection"
        )

        self.btn_info_stac_asset = self.findChild(
            QToolButton,
            "btn_info_stac_asset"
        )

        self.lbl_token_help = self.findChild(
            QLabel,
            "lbl_token_help"
        )

        self.btn_info_nor = self.findChild(
            QToolButton,
            "btn_info_nor"
        )

        self.btn_info_points = self.findChild(
            QToolButton,
            "btn_info_points"
        )

        self.btn_quick_tip = self.findChild(
            QToolButton,
            "btn_quick_tip"
        )

        self.btn_info_api_type = self.findChild(
            QToolButton,
            "btn_info_api_type"
        )

        info_buttons = [
            self.btn_info_data_type,
            self.btn_info_gas,
            self.btn_info_asset,
            self.btn_info_stac_gas,
            self.btn_info_level,
            self.btn_info_collection,
            self.btn_info_stac_asset,
            self.btn_info_nor,
            self.btn_info_points,
            self.btn_info_api_type
        ]

        for button in info_buttons:
            button.setText("ⓘ")

            button.setToolTip(
                "Show information"
            )

            button.setStyleSheet("""
                            QToolButton {
                                border: none;
                                background: transparent;
                                color: #2A6FD6;
                                font-size: 14px;
                                font-weight: bold;
                            }
                            
                            QToolButton:hover {
                                color: #0055CC;
                            }
                                 
                            QToolButton:pressed {
                                color: #003C8F;
                            }
            """)
                                 

        self.btn_info_data_type.clicked.connect(
            self.help_messages.show_data_type_info
        )

        self.btn_info_gas.clicked.connect(
            self.help_messages.show_gas_info
        )

        self.btn_info_asset.clicked.connect(
            self.help_messages.show_asset_info
        )

        self.btn_info_stac_gas.clicked.connect(
            self.help_messages.show_stac_gas_info
        )

        self.btn_info_level.clicked.connect(
            self.help_messages.show_level_info
        )

        self.btn_info_collection.clicked.connect(
            self.help_messages.show_collection_info
        )

        self.btn_info_stac_asset.clicked.connect(
            self.help_messages.show_stac_asset_info
        )

        self.btn_info_nor.clicked.connect(
            self.help_messages.show_records
        )

        self.btn_info_points.clicked.connect(
            self.help_messages.show_add_points
        )

        self.lbl_token_help.linkActivated.connect(
            self.open_token_help
        )

        self.btn_info_api_type.clicked.connect(
            self.help_messages.show_api_type_info
        )

        self.btn_quick_tip.clicked.connect(
            self.help_messages.show_quick_tip
        )


        # STARTING COMPARISON MANAGER
        self.statistical_manager = StatisticalComparisonManager(self)

        self.setup_ui_defaults()
        self.setup_three_level_comboboxes()
        self.update_api_mode()
        self.combo_data_type.currentIndexChanged.connect(
            self.update_table_headers
        )

        self.combo_api.currentIndexChanged.connect(
            self.update_api_mode
        )

        self.combo_data_type.currentIndexChanged.connect(
            self.update_asset_type_visibility
        )

        self.stac_combo_gas.currentIndexChanged.connect(
            self.filter_collections
        )

        self.stac_combo_level.currentIndexChanged.connect(
            self.filter_collections
        )

        self.stac_combo_collection.currentIndexChanged.connect(
            self.update_assets_for_collection
        )

        self.update_asset_type_visibility()
        self.combo_aoi_layer.hide()
    
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
            self.radio_layer_aoi.toggled.connect(self.toggle_aoi_mode)

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
        QgsProject.instance().layersAdded.connect(
            self.refresh_aoi_layers
        )
        QgsProject.instance().layersRemoved.connect(
            self.refresh_aoi_layers
        )

        #Opening the Related Plumes after clicking the source lines
        if hasattr(self, "products_table") and self.products_table:
            self.products_table.cellDoubleClicked.connect(
                self.open_source_plumes
            )
        
        if hasattr(self, 'btn_back_to_sources'):
            self.btn_back_to_sources.clicked.connect(
                self.back_to_sources
            )
            self.btn_back_to_sources.hide()
        
        if hasattr(self, "load_features_btn") and self.load_features_btn:
            self.load_features_btn.clicked.connect(
                self.load_selected_features_to_qgis
            )

        # We trigger the interface to automatically populate the lists when it loads for the first time.
        self.refresh_all_analysis_combos()
        self.refresh_aoi_layers()

    def setup_three_level_comboboxes(self):
        try:
            # --------------------------------------------------
            # DATA TYPE
            # --------------------------------------------------
            if hasattr(self, "combo_data_type"):
                self.combo_data_type.blockSignals(True)
                self.combo_data_type.clear()
                self.combo_data_type.addItems([
                    "Plumes",
                    "Sources"
                ])
                self.combo_data_type.blockSignals(False)
                self.update_table_headers()

            # --------------------------------------------------
            # GAS
            # --------------------------------------------------
            if hasattr(self, "combo_gas"):
                self.combo_gas.blockSignals(True)
                self.combo_gas.clear()
                self.combo_gas.addItems([
                    "All",
                    "CH4",
                    "CO2"
                ])
                self.combo_gas.blockSignals(False)

            if hasattr(self, "stac_combo_gas"):
                self.stac_combo_gas.blockSignals(True)
                self.stac_combo_gas.clear()
                self.stac_combo_gas.addItems([
                    "All",
                    "CH4",
                    "CO2"
                ])
                self.stac_combo_gas.blockSignals(False)


            # --------------------------------------------------
            # LEVEL
            # --------------------------------------------------
            if hasattr(self, "stac_combo_level"):
                self.stac_combo_level.blockSignals(True)
                self.stac_combo_level.clear()
                self.stac_combo_level.addItems([
                    "All",
                    "L2",
                    "L3",
                    "L4"
                ])
                self.stac_combo_level.blockSignals(False)

        except Exception as e:
            print(f"setup_three_level_comboboxes error: {e}")
        
        # STAC collections
        try:
            url = "https://api.carbonmapper.org/api/v1/stac/collections"
            response = requests.get(
                url,
                timeout=20
            )

            if response.status_code == 200:
                data = response.json()
                print(f"Loaded {len(data.get('collections', []))} STAC collections")
                self.all_collections = []
                
                for collection in data.get(
                    "collections",
                    []
                ):
                    coll_id = collection.get("id")

                    if coll_id:
                        self.all_collections.append(
                            coll_id
                        )
                self.filter_collections()
        
        except Exception as e:
            print(
                f"Collection loading failed: {e}"
            )
           

    def filter_collections(self):

        if self.combo_api.currentText() != "STAC API":
            return
        
        if not hasattr(self, "stac_combo_collection"):
            return
        
        selected_gas = self.stac_combo_gas.currentText().lower()
        selected_level = self.stac_combo_level.currentText().lower()

        self.stac_combo_collection.blockSignals(True)
        self.stac_combo_collection.clear()

        for coll in self.all_collections:
            coll_lower = coll.lower()
            
            # Gaz Kontrolü
            gas_match = (
                selected_gas == "all"
                or selected_gas in coll_lower
            )

            # Seviye Kontrolü
            level_match = (
                selected_level == "all"
                or coll_lower.startswith(selected_level)
            )

            if gas_match and level_match:
                display_name = coll
                self.stac_combo_collection.addItem(
                    display_name,
                    coll
                )

        self.stac_combo_collection.blockSignals(False)

       # After filtering the STAC collections, automatically update the available assets
        if self.stac_combo_collection.count() > 0:
            self.stac_combo_collection.setCurrentIndex(0)
            self.update_assets_for_collection()
        else:
            self.stac_combo_asset.clear()
            self.stac_combo_asset.addItem("No assets available")


    def update_assets_for_collection(self):

        self.stac_combo_asset.clear()

        # This function is only used by STAC API
        if self.combo_api.currentText() != "STAC API":
            return
        
        collection_id = self.stac_combo_collection.currentText()

        if not collection_id:
            return
        
        self.stac_combo_asset.clear()

        # cache
        if collection_id in self.assets_cache:
            self.stac_combo_asset.addItems(
                self.assets_cache[collection_id]
            )
            return
        
        try:
            search_url = (
                "https://api.carbonmapper.org/api/v1/stac/search"
            )

            payload = {
                "collections": [collection_id],
                "limit": 20
            }

            response = requests.post(
                search_url,
                json=payload,
                timeout=30
            )

            if response.status_code != 200:
                self.stac_combo_asset.addItem(
                    "No assets available"
                )
                return
            
            features = response.json().get(
                "features",
                []
            )

            if not features:
                 self.stac_combo_asset.addItem(
                     "There are no downloadable assets"
                 )

                 self.assets_cache[
                     collection_id
                 ] = ["There are no downloadable assets"]

                 return
            
            # Search all returned features until one contains assets
            for i, feature in enumerate(features):
                assets = feature.get(
                    "assets",
                    {}
                )

                if assets:
                    asset_names = sorted(
                        assets.keys()
                    )

                    self.stac_combo_asset.addItems(
                        asset_names
                    )


                    self.assets_cache[
                        collection_id
                    ] = asset_names

                    return
                
            # No feature contained assets
            print("No feature contains assets.")
            self.stac_combo_asset.addItem(
                "There are no downloadable assets"
            )

            self.assets_cache[
                collection_id
            ] = ["There are no downloadable assets"]

        except Exception as e:

            print(
                f"Asset loading error: {e}"
            )
    
    def refresh_aoi_layers(self):
        self.combo_aoi_layer.clear()

        print("AOI layer list refreshed")

        for layer in QgsProject.instance().mapLayers().values():
            if not isinstance(layer, QgsVectorLayer):
                continue
            
            if layer.geometryType() != QgsWkbTypes.PolygonGeometry:
                continue
            
            print(layer.name())
            
            self.combo_aoi_layer.addItem(
                layer.name(),
                layer
            )

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

        if hasattr(self, 'start_date_edit') and isinstance(self.start_date_edit, QDateEdit):
            self.start_date_edit.setCalendarPopup(True)
        if hasattr(self, 'end_date_edit') and isinstance(self.end_date_edit, QDateEdit):
            self.end_date_edit.setCalendarPopup(True)

        if hasattr(self, 'products_table') and self.products_table:
            self.update_table_headers()
            self.products_table.horizontalHeader().setStretchLastSection(True)

        if hasattr(self, 'toggle_aoi_mode'):
            self.toggle_aoi_mode()

        if hasattr(self, 'progress_bar') and self.progress_bar is not None:
            self.progress_bar.setMinimum(0)
            self.progress_bar.setMaximum(100)
            self.progress_bar.setValue(0)  
        
        if hasattr(self, "combo_api"):

            self.combo_api.clear()

            self.combo_api.addItems([
                "Data API",
                "STAC API"
            ])
            self.combo_api.setCurrentIndex(0)
            print(self.combo_api.count())
            
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

        self.update_api_mode()

    def switch_to_analysis_tab(self):
        if self.main_tab_widget:
            self.main_tab_widget.setCurrentIndex(2)
            self.refresh_all_analysis_combos()

    def toggle_aoi_mode(self):
        #Canvas AOI
        if self.radio_canvas_aoi.isChecked():
            self.aoi_btn.setEnabled(True)
            self.set_coordinate_fields_editable(False)
            self.combo_aoi_layer.hide()

        #Layer AOI
        elif self.radio_layer_aoi.isChecked():
            self.aoi_btn.setEnabled(False)
            self.set_coordinate_fields_editable(False)
            self.combo_aoi_layer.show()
        
        #Custom AOI
        else:
            self.aoi_btn.setEnabled(False)
            self.set_coordinate_fields_editable(True)
            self.combo_aoi_layer.hide()
    
    def update_api_mode(self):
        """
        Enable the correct API panel depending on the selected API.
        """
        if self.combo_api.count() == 0:
            return
        
        use_stac = (
            self.combo_api.currentText() == "STAC API"
        )

        # -------------------------
        # Enable / Disable groupboxes
        # -------------------------
        self.groupBox_data_api.setEnabled(
            not use_stac
        )

        self.groupBox_stac_api.setEnabled(
            use_stac
        )

        # -------------------------
        # Token
        # -------------------------
        self.token_input.setEnabled(use_stac)
        self.token_label.setEnabled(use_stac)

        if use_stac:
            self.token_input.setPlaceholderText(
                "Please paste your Carbon Mapper Token"
            )

            self.populate_stac_collections()

        else:
            self.token_input.clear()
            self.token_input.setPlaceholderText(
                "Token not required for Data API"
            )

            self.asset_combo.clear()
            self.asset_combo.addItems([
                "con_tif",
                "plume_tif",
                "plume_png",
                "rgb_tif",
                "rgb_png",
            ])


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
        if (
            hasattr(self, "radio_layer_aoi")
            and self.radio_layer_aoi.isChecked()
        ):
            
            layer = self.combo_aoi_layer.currentData()

            if not layer:
                return None
            
            extent = layer.extent()
            bbox = [
                round(extent.xMinimum(), 5),
                round(extent.yMinimum(), 5),
                round(extent.xMaximum(), 5),
                round(extent.yMaximum(), 5)
            ]

            print("LAYER BBOX =", bbox)
            return bbox
        
            
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
        if self.combo_api.currentText() == "Data API":
            self.handle_search_data_api()
        else:
            self.handle_search_stac_api()

    def handle_search_data_api(self):
        limit = (
            self.limit_spin.value()
            if hasattr(self, 'limit_spin') 
            else 10
        )
        
        bbox = self.get_current_bbox()
       
        if (
            hasattr(self, 'radio_custom_aoi') 
            and self.radio_custom_aoi 
            and self.radio_custom_aoi.isChecked()
        ):
            
            if not bbox:
                QMessageBox.warning(self, 
                                    "Coordinate Error", 
                                    "Please enter valid numeric values for Custom Bounding Box!"
                )

                return
            
        else:
            if (
                not bbox 
                or any(v is None for v in bbox) 
                or bbox == [0, 0, 0, 0]
            ):
                QMessageBox.warning(self, 
                                    "Validation Error", 
                                    "Please define a valid Area of Interest (AOI) on the canvas before searching!"
                )

                return
               
        
        start_widget = self.findChild(QDateEdit, 'start_date_edit')
        end_widget = self.findChild(QDateEdit, 'end_date_edit')
       
        start_dt = start_widget.date().toString("yyyy-MM-dd") if start_widget else "2024-01-01"
        end_dt = end_widget.date().toString("yyyy-MM-dd") if end_widget else "2026-12-31"
        datetime_range = f"{start_dt}/{end_dt}"

        gas = self.combo_gas.currentText()

        data_type = (
            self.combo_data_type.currentText()
        )

        self.features = []

        try:
            # ------------------------
            # PLUMES
            # ------------------------

            if data_type == "Plumes":
                from geoprojects.api.carbon_api import (
                    search_plume_csv
                )

                self.features = search_plume_csv(
                    bbox=bbox,
                    gas=gas,
                    limit=limit,
                    datetime_range=datetime_range
                )

            # ------------------------
            # SOURCES
            # ------------------------

            elif data_type == "Sources":
                from geoprojects.api.carbon_api import (
                    search_sources_csv
                )

                from geoprojects.api.carbon_api import(
                    get_source_plumes
                )

                self.features = search_sources_csv(
                    bbox=bbox,
                    gas=gas,
                    limit=limit,
                    datetime_range=datetime_range
                )

                self.source_features = self.features.copy()
                self.source_plume_map = {}

                for source in self.features:
                    source_name = source["source_name"]

                    plume_records = get_source_plumes(
                        source_name,
                        limit=100
                    )

                    plume_ids = []
                    for plume in plume_records:
                        plume_ids.append(
                            plume["plume_id"]
                        )
                    self.source_plume_map[source_name] = plume_ids


            print(
                f"Returned {len(self.features)} records."
            )

            print("DATA TYPE =", data_type)

            if self.features:
                print("FIRST RECORD:")

            self.populate_table(
                self.features
            )
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "Search Error",
                str(e)
            )

    def handle_search_stac_api(self):

        collection = self.stac_combo_collection.currentText()
        if not collection:
            return
        
        limit = (
            self.limit_spin.value()
            if hasattr(self, "limit_spin")
            else 10
        )

        bbox = self.get_current_bbox()

        if (
            hasattr(self, "radio_custom_aoi")
            and self.radio_custom_aoi
            and self.radio_custom_aoi.isChecked()
        ):
            if not bbox:
                 QMessageBox.warning(
                     self,
                     "Coordinate Error",
                     "Please enter valid numeric values for Custom Bounding Box!"
                 )
                 return
            
        else:
            if (
                not bbox
                or any(v is None for v in bbox)
                or bbox == [0, 0, 0, 0]
            ):
                    
                QMessageBox.warning(
                    self,
                    "Validation Error",
                    "Please define a valid AOI before searching!"
                )
                return
            
        start_widget = self.findChild(
            QDateEdit,
                "start_date_edit"
        )

        end_widget = self.findChild(
            QDateEdit,
            "end_date_edit"
        )

        start_dt = start_widget.date().toString(
            "yyyy-MM-dd"
        )

        end_dt = end_widget.date().toString(
            "yyyy-MM-dd"
        )

        datetime_range = (
            f"{start_dt}/{end_dt}"
        )
        
        url = "https://api.carbonmapper.org/api/v1/stac/search"

        payload = {
            "collections":[collection],
            "bbox": bbox,
            "datetime": datetime_range,
            "limit": limit
        }

        response = requests.post(
            url,
            json=payload,
            timeout=30
        )  

        if response.status_code != 200:
            QMessageBox.warning(
                self,
                "STAC",
                "Search failed."
            )

            return
        
        features = response.json().get(
            "features",
            []
        )

        if not features:
            QMessageBox.information(
                self,
                "No results",
                "No products found."
            )
            return
        
        table_features = []
        for feature in features:

            props = feature.get(
                "properties",
                {}
            )

            geometry = feature.get(
                "geometry",
                {}
            )

            coords = geometry.get(
                "coordinates",
                []
            )

            if geometry.get("type") == "Point":
                lon = coords[0]
                lat = coords[1]
            else:
                lon = coords[0][0][0]
                lat = coords[0][0][1]
                
            location = f"{lat:.5f}, {lon:.5f}"

            feature["plume_id"] = feature.get(
                "id",
                ""
            )

            feature["datetime"] = props.get(
                "datetime",
                ""
            )

            feature["place"] = location
            feature["region"] = ""
            feature["country"] = "-"
            feature["ipcc_sector"] = props.get(
                "cm:sector",
                "-"
            )

            table_features.append(feature)

        self.features = table_features
        self.populate_table(
            table_features
        )

        self.download_btn.setEnabled(True)
                    
    def populate_table(self, features):

        self.products_table.setRowCount(0)

        if self.combo_api.currentText() == "STAC API":
            data_type = "Plumes"
        else:
            data_type = self.combo_data_type.currentText()

        if not features:
            QMessageBox.information(
                self, 
                "No Results", 
                "No features found for the current parameters."
            )
            return
        
        for row_idx, feature in enumerate(features):

            self.products_table.insertRow(row_idx)

            # --------------------------
            # PLUME RECORD
            # --------------------------
            if data_type == "Plumes":
                feature_id = feature.get(
                    "plume_id",
                    "N/A"
                )

                date_str = feature.get(
                    "datetime",
                    "Unknown"
                )

                place = feature.get(
                    "place",
                    ""
                )

                region = feature.get(
                    "region",
                    ""
                )

                location = ", ".join(
                    x for x in [place, region]
                    if x
                )

                country = feature.get(
                    "country",
                    "Unknown"
                )

                sector = feature.get(
                    "ipcc_sector",
                    "Unknown"
                )

                if date_str != "Unknown":
                    date_str = date_str[:10]
                
            # --------------------------
            # SOURCE RECORD
            # --------------------------
            else:
                feature_id = feature.get(
                    "source_name",
                    "N/A"
                )   
                
                gas = feature.get(
                    "gas",
                    "Unknown" 
                )

                sector = feature.get(
                    "ipcc_sector",
                    "Unknown"
                )

                emission_raw = feature.get(
                    "source_emission",
                    ""
                )
                
                try:
                    emission = str(
                        round(
                            float(emission_raw),
                            2
                        )
                    )
                except:
                    emission = "Unknown"
          
                persistence = str(
                    round(
                        float(
                            feature.get(
                                "source_persistence",
                                0
                            )
                        ),
                        2
                    )
                )

            # Filling the Table for Plummes
            if data_type == "Plumes":
                self.products_table.setItem(
                    row_idx,
                    0,
                    QTableWidgetItem(feature_id) # Feature ID
                )

                self.products_table.setItem(
                    row_idx,
                    1,
                    QTableWidgetItem(date_str) # Date Info
                )

                self.products_table.setItem(
                    row_idx,
                    2,
                    QTableWidgetItem(location) # Region + Place Info
                )
                
                self.products_table.setItem(
                    row_idx,
                    3,
                    QTableWidgetItem(country) # Country Info
                )

                self.products_table.setItem(
                    row_idx,
                    4,
                    QTableWidgetItem(sector) # Sector Info
                )

                self.products_table.setItem(
                    row_idx,
                    5,
                    QTableWidgetItem(
                        "Ready to Download"
                    )
                )
            
            # Filling the Table for Source
            else:
                self.products_table.setItem(
                    row_idx,
                    0,
                    QTableWidgetItem(feature_id)
                )

                self.products_table.setItem(
                    row_idx,
                    1,
                    QTableWidgetItem(gas)
                )

                self.products_table.setItem(
                    row_idx,
                    2,
                    QTableWidgetItem(sector)
                )

                self.products_table.setItem(
                    row_idx,
                    3,
                    QTableWidgetItem(emission)
                )

                self.products_table.setItem(
                    row_idx,
                    4,
                    QTableWidgetItem(str(persistence))
                )

                self.products_table.setItem(
                    row_idx,
                    5,
                    QTableWidgetItem(
                        "Ready"
                    )
                )

    def update_table_headers(self):
        data_type = self.combo_data_type.currentText()

        if data_type == "Plumes":
            self.products_table.setColumnCount(6)
            self.products_table.setHorizontalHeaderLabels([
                "Feature ID",
                "Date",
                "Location",
                "Country",
                "Sector",
                "Status"
            ])

        else:
            self.products_table.setColumnCount(6)
            self.products_table.setHorizontalHeaderLabels([
                "Source Name",
                "Gas",
                "Sector",
                "Emission (kg/hr)",
                "Persistence",
                "Status"
            ])
        
        self.products_table.setRowCount(0)

    def open_source_plumes(self, row, column):
        # For enabling to work only for Source selected
        if self.combo_data_type.currentText() != "Sources":
            return
        
        try:
            source_feature = self.features[row]
            source_name = source_feature.get(
                "source_name"
            )

            if not source_name:
                QMessageBox.warning(
                    self,
                    "Source Error",
                    "Source name could not be found!"
                )
                return
            
            print(
                f"Loading plumes for source: {source_name}"
            )

            from geoprojects.api.carbon_api import (
                get_source_plumes
            )

            plumes = get_source_plumes(
                source_name,
                limit=100
            )

            if not plumes:
                QMessageBox.information(
                    self,
                    "No Plumes",
                    "No plumes records were returned for this source."
                )
                return
            
            #Now we will work with the plume list
            self.features = plumes

            # Temporarily switch the table to plume view
            self.combo_data_type.blockSignals(True)
            self.combo_data_type.setCurrentText(
                "Plumes"
            )

            self.update_asset_type_visibility()
            self.combo_data_type.blockSignals(False)
            self.update_table_headers()

            self.populate_table(
                self.features
            )

            self.btn_back_to_sources.show()

            QMessageBox.information(
                self,
                "Source Loaded",
                f"{len(plumes)} plume records loaded."
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Source Error",
                str(e)
            )

            print(
                f"open_source_plumes error: {e}"
            )

    def back_to_sources(self):
        if not self.source_features:
            return
        
        self.combo_data_type.setCurrentText(
            "Sources"
        )

        self.update_asset_type_visibility()

        self.features = self.source_features

        self.populate_table(
            self.features
        )

        self.btn_back_to_sources.hide()

    def update_asset_type_visibility(self):

        if self.combo_data_type.currentText() == "Sources":
             self.asset_combo.hide()
             self.data_asset_type_label.hide()
             self.btn_info_asset.hide()
             self.btn_quick_tip.show()

             
        else:
            self.asset_combo.show()
            self.data_asset_type_label.show()
            self.btn_info_asset.show()
            self.btn_quick_tip.hide()
    
    def load_selected_features_to_qgis(self):

        """
        Loads the currently displayed search results into QGIS as point layers.
        """
        data_type = self.combo_data_type.currentText()

        if data_type == "Plumes":
            self.create_plume_point_layer()

        elif data_type == "Sources":
            self.create_source_point_layer()
        
        else:
            QMessageBox.information(
                self,
                "Information",
                "This data type cannot be loaded as a point layer."
            )
    def get_qvariant_type(self, value):
        if isinstance(value, bool):
            return QVariant.Bool
        
        elif isinstance(value, int):
            return QVariant.Int
        
        elif isinstance(value, float):
            return QVariant.Double
        
        else:
            return QVariant.String

    def create_plume_point_layer(self):

        """
        Creates an empty memory point layer for plume locations.
        """

        layer = QgsVectorLayer(
            "Point?crs=EPSG:4326",
            "Plume Points",
            "memory"
        )

        if not layer.isValid():
            QMessageBox.warning(
                self,
                "Error",
                "Could not create memory layer."
            )
            return
        
        if not self.features:
            QMessageBox.warning(
                self,
                "Error",
                "No plume data available."
            )
            return

        provider = layer.dataProvider()
        sample = self.features[0]
        fields = []

        for key, value in sample.items():
            if key in [
                "plume_longitude",
                "plume_latitude"
            ]:
                continue
            
            fields.append(
                QgsField(
                    key,
                    self.get_qvariant_type(value)
                )
            )
        
        provider.addAttributes(fields)
        layer.updateFields()

        for feature in self.features:

            lon = float(feature["plume_longitude"])
            lat = float(feature["plume_latitude"])

            point = QgsFeature(layer.fields())

            point.setGeometry(
                QgsGeometry.fromPointXY(
                    QgsPointXY(lon, lat)
                )
            )

            attributes = []
            for key in sample.keys():
                if key in [
                    "plume_longitude",
                    "plume_latitude"
                ]:
                    continue
                
                value = feature.get(key)
                if value is None:
                    value = ""

                if isinstance(value, (list, dict)):
                    value = json.dumps(value)

                attributes.append(value)
            point.setAttributes(attributes)


            provider.addFeature(point)
       
        layer.updateExtents()
        layer.triggerRepaint()

        QgsProject.instance().addMapLayer(layer)

        QMessageBox.information(
             self,
             "Success",
             "Plume point layer added to QGIS."
         )

    
    def create_source_point_layer(self):

        """
        Creates an source layer for source locations.
        """

        layer = QgsVectorLayer(
            "Point?crs=EPSG:4326",
            "Source Points",
            "memory"
        )

        if not layer.isValid():
            QMessageBox.warning(
                self,
                "Error",
                "Could not create Source layer."
            )
            return
        
        if not self.features:
            QMessageBox.warning(
                self,
                "Error",
                "No source data available."
            )
            return

        provider = layer.dataProvider()
        sample = self.features[0]
        fields = []

        for key, value in sample.items():
            if key in [
                "source_longitude",
                "source_latitude"
            ]:
                continue
            
            fields.append(
                QgsField(
                    key,
                    self.get_qvariant_type(value)
                )
            )

        fields.append(
            QgsField(
                "plume_ids",
                QVariant.String
            )
        )

        provider.addAttributes(fields)
        layer.updateFields()

        for feature in self.features:

            lon = float(feature["source_longitude"])
            lat = float(feature["source_latitude"])

            point = QgsFeature(layer.fields())

            point.setGeometry(
                QgsGeometry.fromPointXY(
                    QgsPointXY(lon, lat)
                )
            )

            attributes = []
            for key in sample.keys():
                if key in [
                    "source_longitude",
                    "source_latitude"
                ]:
                    continue
                
                value = feature.get(key)

                if value is None:
                    value = ""

                if isinstance(value, (list, dict)):
                    value = json.dumps(value)

                attributes.append(value)

            plume_ids = self.source_plume_map.get(
                feature["source_name"],
                []
            )

            attributes.append(
                "\n".join(plume_ids)
            )

            point.setAttributes(attributes)
            provider.addFeature(point)
       
        layer.updateExtents()
        layer.triggerRepaint()

        QgsProject.instance().addMapLayer(layer)

        QMessageBox.information(
             self,
             "Success",
             "Source point layer added to QGIS."
         )
    
    def populate_stac_collections(self):
        self.filter_collections()
       

    def handle_download(self):

        # --------------------------------------------------
        # STAC API Download
        # --------------------------------------------------

        if self.combo_api.currentText() == "STAC API":
            self.handle_download_stac()
            return
        
        asset_combo = getattr(self, 'asset_combo', None)
        
       
        #  Capturing the raw API code using .currentData() during the download process.
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
                    self.products_table.setItem(i, 5, QTableWidgetItem("Downloading..."))
                    self.products_table.repaint()
               
                asset_type = (
                    asset_combo.currentText()
                    if asset_combo
                    else "con_tif"
                )
                
                asset_url = feature.get(asset_type)

                if not asset_url:
                    self.products_table.setItem(
                        i,
                        4,
                        QTableWidgetItem("Asset Missing")
                    )
                    continue

                file_path = download_asset(feature=feature, token=token, asset_name=asset_type, index=i, output_dir=output_dir)
               
                if file_path and os.path.exists(file_path):

                    if "plume_id" in feature:
                        feature_name = feature["plume_id"]
                    else:
                        feature_name = feature.get(
                            "id",
                            f"feature_{i}"
                        )
                    custom_layer_name = (
                        f"{asset_type}_{feature_name[:12]}"
                    )
                   
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
                        self.products_table.setItem(i, 5, QTableWidgetItem("Success"))
                else:
                    if hasattr(self, 'products_table') and self.products_table:
                        self.products_table.setItem(i, 5, QTableWidgetItem("Failed"))
            except Exception as e:
                print(f"An error occurred during the download: {str(e)}")
                if hasattr(self, 'products_table') and self.products_table:
                    self.products_table.setItem(i, 5, QTableWidgetItem("Error"))
            if hasattr(self, active_bar):
                getattr(self, active_bar).setValue(i + 1)

        QMessageBox.information(self, "Successful", f"{download_count} data products successfully processed!")
        self.refresh_all_analysis_combos()

    def handle_download_stac(self):
    
        import requests
        import os

        from geoprojects.utils.qgis_utils import add_raster_to_qgis

        selected_rows = (
            self.products_table.selectionModel().selectedRows()
        )

        if not selected_rows:
            QMessageBox.information(
                self,
                "Selection",
                "Please select a product"
            )
            return
        
        output_dir = self.output_dir_input.text().strip()

        if not output_dir:
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please Select an Output Directory"
            )
            return
        
        asset_name = (
            self.stac_combo_asset.currentText()
        )

        if (
            asset_name
             == "There are no downloadable assets"
        ):
            QMessageBox.information(
                self,
                "STAC API",
                "This collection does not contain downloadable assets."
            )
            return
        
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")

        download_count = 0
        
        for row in selected_rows:
            feature = self.features[row.row()]
            assets = feature.get(
                "assets",
                {}
            )

            asset = assets.get(
                asset_name
            )

            if not asset:
                self.products_table.setItem(
                    row.row(),
                    5,
                    QTableWidgetItem(
                        "Asset Missing"
                    )
                )
                continue
            
            href = asset.get(
                "href"
            )

            if not href:
                self.products_table.setItem(
                    row.row(),
                    5,
                    QTableWidgetItem(
                        "Invalid URL"
                    )
                )
                continue
            
            try:
                token = self.token_input.text().strip()
                headers = {}
                if token:
                    headers["Authorization"] = f"Bearer {token}"

                self.products_table.setItem(
                    row.row(),
                    5,
                    QTableWidgetItem("Downloading...")
                )
                QApplication.processEvents()

                response = requests.get(
                    href,
                    headers=headers,
                    stream=True,
                    timeout=(10, 120)
                )

                if response.status_code != 200:
                    self.products_table.setItem(
                        row.row(),
                        5,
                        QTableWidgetItem(
                            "Failed"
                        )
                    )
                    continue
                
                total_size = int(
                    response.headers.get(
                        "content-length",
                        0
                    )
                )

                downloaded = 0

                if total_size > 0:
                    self.progress_bar.setMaximum(total_size)
                    self.progress_bar.setValue(0)
                    self.progress_bar.setFormat("Downloading... %p%")
                else:
                    self.progress_bar.setMaximum(0)
                
                if "." in asset_name:
                    extension = "." + asset_name.split(".")[-1]
                else:
                    extension = os.path.splitext(href)[1]

                if not extension:
                    extension = ".dat"

                filename = (
                    feature["plume_id"]
                    + "_"
                    + asset_name
                )

                save_path = os.path.join(
                    output_dir,
                    filename
                )

                with open(
                    save_path,
                    "wb"
                ) as f:
                    
                    for chunk in response.iter_content(
                        chunk_size=8192
                    ):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                            if total_size > 0:
                                self.progress_bar.setValue(downloaded)
                            QApplication.processEvents()
                response.close()

                QApplication.processEvents()

                layer_name = (
                    feature["plume_id"]
                    + "-"
                    + asset_name
                )

                self.products_table.setItem(
                    row.row(),
                    5,
                    QTableWidgetItem("Loading...")
                )
                self.progress_bar.setValue(
                    self.progress_bar.maximum()
                )
                self.progress_bar.setFormat("Loading into QGIS...")
                QApplication.processEvents()

                if save_path.lower().endswith(
                    (".tif", ".png", ".jpg", ".jpeg" )
                ):
                    add_raster_to_qgis(
                        save_path,
                        layer_name
                    )

                    QApplication.processEvents()

                elif save_path.endswith((".geojson", ".json", ".shp")):
                    v_layer = QgsVectorLayer(
                        save_path,
                        layer_name,
                        "ogr"
                    )

                    if v_layer.isValid():
                        QgsProject.instance().addMapLayer(v_layer)

                self.products_table.setItem(
                    row.row(),
                    5,
                    QTableWidgetItem(
                        "Success"
                    )
                )

                download_count += 1

                self.progress_bar.setValue(
                    self.progress_bar.maximum()
                )
                self.progress_bar.setFormat("Completed")
                
                QApplication.processEvents()
            
            except Exception as e:
                print(e)

                self.products_table.setItem(
                    row.row(),
                    5,
                    QTableWidgetItem(
                        "Error"
                    )
                )

        QMessageBox.information(
            self,
            "Download Completed",
            f"{download_count} asset(s) were downloaded successfully"
        )

    def open_token_help(self):
        self.tabWidget.setCurrentIndex(3)





