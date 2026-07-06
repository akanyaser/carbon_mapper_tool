# Carbon Mapper Data Exploration Tool

A QGIS plugin for searching, downloading and analyzing Carbon Mapper methane (CH4) and carbon dioxide (CO2) datasets directly within QGIS.

This plugin integrates both the **Carbon Mapper STAC API** and the **Carbon Mapper Data API**, allowing users to discover datasets, download remote sensing assets, visualize emission sources, and perform statistical comparisons between multiple geographic regions.

> This project was developed as part of the **Geoinformatics Projects** course at **Politecnico di Milano**.

---

# - Supported Services

- Carbon Mapper STAC API
- Carbon Mapper Data API

Official websites:

- https://data.carbonmapper.org
- https://api.carbonmapper.org

---

#  Features

## - Dataset Discovery

- Search Carbon Mapper collections through the STAC API
- Search plume and source records through the Data API
- Filter datasets by:
  - Gas (CH4 / CO2)
  - Collection
  - Processing Level
  - Date Range
  - Area of Interest (AOI)

---

## - Asset Download

Download available Carbon Mapper assets directly into QGIS.

Supported asset types include:

- GeoTIFF
- PNG
- RGB Images
- Concentration Maps
- Plume Layers

---

## - Visualization

- Display plume locations on the QGIS map
- Display emission source locations
- Automatically create QGIS vector layers
- Load downloaded assets directly into the current project

---

## - Statistical Comparison Tool

The Statistical Comparison Tool allows users to compare multiple geographic regions using Carbon Mapper plume observations.

Users can:

- Select a polygon layer
- Choose an attribute field
- Compare two or more regions
- Select gas type
- Specify a date range
- Export comparison results as CSV

Calculated statistics include:

| Statistic | Unit |
|-----------|------|
| Number of Plumes | Count |
| Number of Emission Records | Count |
| Mean Emission | kg/hr |
| Median Emission | kg/hr |
| Minimum Emission | kg/hr |
| Maximum Emission | kg/hr |
| Standard Deviation | kg/hr |

---

## - User Interface

The plugin provides an interactive graphical interface including:

- Area of Interest selection
- Bounding Box tools
- STAC API search
- Data API search
- Download manager
- Statistical comparison interface
- CSV export
- Built-in Help & Documentation

---

# - Installation

## Requirements

- QGIS 3.22 or higher
- Python package:

```bash
pip install requests
```

---

## Manual Installation

Clone this repository:

```bash
git clone https://github.com/akanyaser/carbon_mapper_tool.git
```

Copy the plugin folder into your QGIS plugins directory.

### Windows

```text
C:\Users\<Username>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins
```

### Linux

```text
~/.local/share/QGIS/QGIS3/profiles/default/python/plugins
```

Restart QGIS and enable the plugin from:

**Plugins → Manage and Install Plugins**

---

# - Project Structure

```text
plugin.py
│
├── Main plugin controller

api/
└── carbon_api.py
    Carbon Mapper STAC API & Data API interface

statistical_tool.py
    Statistical comparison module

help_messages.py
    Plugin help messages

widget.ui
    Qt Designer user interface

metadata.txt
    Plugin metadata
```

---

# - Technologies

- Python
- PyQGIS
- Qt Designer
- Carbon Mapper STAC API
- Carbon Mapper Data API

---

# - Data Attribution and Terms of Use

This plugin provides access to publicly available Carbon Mapper datasets through the official Carbon Mapper STAC API and Data API.

Users should acknowledge **Carbon Mapper** as the original data provider when publishing analyses, maps or other derivative works generated using these datasets.

Use of the Carbon Mapper services and datasets is subject to the official Carbon Mapper Terms of Use:

https://carbonmapper.org/terms

This plugin is an independent academic project developed at **Politecnico di Milano** and is **not affiliated with or endorsed by Carbon Mapper**.

---

## License

This repository contains source code developed for academic purposes.

Carbon Mapper datasets are **not distributed** with this repository and remain subject to the Carbon Mapper Terms of Use.

---

#  Author

**Yaser Enes Akan**

Department of Civil and Environmental Engineering

Politecnico di Milano
