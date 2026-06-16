# Carbon Mapper CH4 & CO2 Monitoring Tool

A QGIS plugin for downloading and analyzing high-emission methane (CH4) and carbon dioxide (CO2) plume datasets.
This study was carried out as part of an institutional software blueprint and geospatial analysis framework to evaluate localized atmospheric disruptions.

## 🌍 Dataset Supported

This plugin specifically supports data from:
**Carbon Mapper STAC API Archive**
🔗 https://data.carbonmapper.org

## 🧭 Features

* AOI selection (Visual Map Canvas extent or manual bounding box)
* Parameter configuration (Gas collection type, processing levels, date frames)
* Secure data authentication via Carbon Mapper API Bearer Tokens
* Raster Thresholding & Hotspot Isolation (`AnalysisManager` pipeline)
* Adaptive morphological filtering and vector plume extraction (`GDAL Sieve` & `GDAL Polygonize`)
* Multi-criteria environmental risk scoring (`PlumeEnvironmentalAnalysisManager`)
* Automated internal attribute database table enrichment
* QGIS layer registry canvas integration and layout synchronization

## ⚙️ Installation

Before installing the plugin, please make sure to install the following package in the QGIS Python environment: `pip install requests`

### Option 1: Manual Installation

1. Clone or download this repository.
2. Copy the entire folder into your QGIS plugins directory:
```text
# Typical plugin path for Windows:
C:\Users\<YourUsername>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins

# For macOS or Linux:
~/.local/share/QGIS/QGIS3/profiles/default/python/plugins
