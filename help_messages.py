
from qgis.PyQt.QtWidgets import QMessageBox

class HelpMessages:

    def __init__(self, parent):
        self.parent = parent

    def show_data_type_info(self):
        QMessageBox.information(
            self.parent,
            "Data Type",
            """
            Select the type of Carbon Mapper observations.

            Plumes: Individual methane or CO2 detections.

            Sources: Groups of recurring plume detections representing likely emission sources.
            
            (For more information, see the Carbon Mapper API documentation.)
            """
        )
    
    def show_gas_info(self):
        QMessageBox.information(
            self.parent,
            "Gas Type",
            """
            CH4: Methane.

            CO2: Carbon Dioxide.
            
            (For more information, see the Carbon Mapper API documentation.)
            """
        )
    
        
    def show_asset_info(self):
        QMessageBox.information(
            self.parent,
            "Asset Type",
            """
            Select which downloadable product will be retrieved.
            Examples: 
            • Concentration raster
            • RGB imagery
            • Plume mask
            • GeoTIFF
            • PNG

            (For more information, see the Carbon Mapper API documentation.)
            """
        )

    def show_stac_gas_info(self):
        QMessageBox.information(
            self.parent,
            "STAC Gas Type",
            """
            Select the gas collection.
            
            CH4: Methane 
            
            CO2: Carbon Dioxide

            (For more information, see the Carbon Mapper API documentation.)
            """
        )

    def show_level_info(self):
        QMessageBox.information(
            self.parent,
            "Product Level",
            """
            L2: Retrieved concentration products.
            L3: Plume detection products.
            L4: Source aggregation products.
            
            (For more information, see the Carbon Mapper API documentation.)
            """
        )

    def show_collection_info(self):
        QMessageBox.information(
            self.parent,
            "Collection",
            """
            Collections organize Carbon Mapper products according to
            • gas
            • processing level
            • algorithm version

            (For more information, see the Carbon Mapper API documentation.)
            """
        )

    def show_stac_asset_info(self):
        QMessageBox.information(
            self.parent,
            "STAC Asset",
            """
            Choose which downloadable asset you want.
            Examples:
            • GeoTIFF
            • PNG
            • RGB imagery
            • Concentration raster
            • Plume outline

            (For more information, see the Carbon Mapper API documentation.)
            """
        )

    def show_api_type_info(self):
        QMessageBox.information(
            self.parent,
            "API Type",
            """
    Choose which Carbon Mapper service you want to use.
    • Data API:Returns processed Carbon Mapper observations
    (plumes and sources) with searchable metadata.
    Recommended for most users.

    • STAC API:Provides direct access to Carbon Mapper data assets,
    collections and downloadable files following the STAC 
    (SpatioTemporal Asset Catalog) standard. Use this option
    if you need specific imagery, GeoTIFFs or collection assets.
    

    (For more information, see the Carbon Mapper API documentation.)
            """
        )

    def show_records(self):
        QMessageBox.information(
            self.parent,
            "Number of Records",
            """
            Limits how many plume or source records
            are requested from the Carbon Mapper API.

            Smaller values return results faster.
            Larger values may increase download time.
            """
        )

    def show_add_points(self):
        QMessageBox.information(
            self.parent,
            "Display in QGIS",
            """
            Creates a temporary point layer from the
            downloaded Carbon Mapper records.

            The layer is added directly to your current
            QGIS project and can be explored,
            styled and queried like any other layer.
            """
        )

    def show_quick_tip(self):
        QMessageBox.information(
            self.parent,
            "Quick Tip",
            """
            Source Mode
            
            Double-click any source row to open all
            plume detections associated with that source.

            Use the "Back to Sources" button to return
            to the source list.
            """
        )










