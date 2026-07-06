# Carbon Mapper Data Exploration Tool

A QGIS plugin for searching, downloading and analyzing Carbon Mapper methane (CH4) and carbon dioxide (CO2) datasets directly within QGIS.

The plugin integrates both the Carbon Mapper STAC API and Data API, allowing users to discover plume products, download remote sensing assets, visualize emission sources, and perform statistical comparisons between multiple geographic regions.

---

## 🌍 Supported APIs

- Carbon Mapper STAC API
- Carbon Mapper Data API

---

## ✨ Main Features

### 🔍 Search Datasets
- Search Carbon Mapper datasets using the STAC API
- Search plume and source records using the Data API
- Filter by:
  - Gas (CH4 / CO2)
  - Collection
  - Product Level
  - Date Range
  - Area of Interest (AOI)

### 📥 Download Assets
- Download available raster and vector assets directly from Carbon Mapper.
- Supported assets include:
  - GeoTIFF
  - PNG
  - RGB Images
  - Concentration Maps
  - Plume Layers

### 🗺️ Visualization
- Display plume locations on the QGIS map.
- Display emission source locations.
- Automatically create QGIS vector layers.

### 📊 Statistical Comparison Tool
Compare multiple regions using Carbon Mapper plume observations.

Supported statistics include:

- Number of Plumes
- Number of Emission Records
- Mean Emission (kg/hr)
- Median Emission (kg/hr)
- Minimum Emission (kg/hr)
- Maximum Emission (kg/hr)
- Standard Deviation (kg/hr)

Results can be exported as CSV.

### 🎯 User Interface

- Interactive AOI selection
- Attribute selection from polygon layers
- Multiple region selection
- Dynamic filtering
- Built-in help window

---

## ⚙️ Installation

Install the required Python package inside the QGIS Python environment:

```bash
pip install requests
```

### Manual Installation

Clone this repository:

```bash
git clone https://github.com/akanyaser/carbon_mapper_tool.git
```

Copy the plugin folder into your QGIS plugins directory.

Windows:

```text
C:\Users\<Username>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins
```

Linux:

```text
~/.local/share/QGIS/QGIS3/profiles/default/python/plugins
```

Restart QGIS and enable the plugin from:

Plugins → Manage and Install Plugins

---

## 📦 Project Structure

```text
plugin.py                 Main plugin controller
carbon_api.py             Carbon Mapper API interface
statistical_tool.py       Statistical comparison module
help_messages.py          Help window
widget.ui                 Main user interface
metadata.txt              Plugin metadata
```

---

## 🛠 Technologies

- Python
- PyQGIS
- Qt Designer
- Carbon Mapper STAC API
- Carbon Mapper Data API

---

## 👨‍💻 Author

Yaser Enes Akan

Department of Civil and Environmental Engineering

Politecnico di Milano
