
# Carbon Mapper Data Exploration Tool

A QGIS plugin for searching, downloading, visualizing, and analyzing Carbon Mapper methane (CH4) and carbon dioxide (CO2) datasets directly within QGIS.

The plugin integrates the **Carbon Mapper STAC API** and **Carbon Mapper Data API** to support dataset discovery, remote sensing asset downloads, plume and source visualization, and statistical comparisons between geographic regions.

This project was developed as part of the **Geoinformatics Projects** course at **Politecnico di Milano**.

## Supported Services

- Carbon Mapper STAC API
- Carbon Mapper Data API

Official websites:

- https://data.carbonmapper.org
- https://api.carbonmapper.org

## Features

### 1. Dataset Discovery

Search Carbon Mapper datasets and records using the available APIs.

Supported search filters include:

- Gas type (CH4 / CO2)
- Collection
- Processing level
- Date range
- Area of Interest (AOI)

### 2. Asset Download

Download available Carbon Mapper assets directly into QGIS.

Supported asset formats and products may include:

- GeoTIFF
- PNG and RGB imagery
- Concentration maps
- Plume-related products

Available assets depend on the selected dataset and collection.

### 3. Visualization

- Display plume and emission-source locations
- Create QGIS vector layers from available records
- Load downloaded raster assets into the current QGIS project

### 4. Statistical Comparison Tool

Compare multiple geographic regions using Carbon Mapper plume observations.

Users can:

- Select a polygon layer
- Choose an attribute field
- Compare two or more regions
- Select a gas type
- Specify a date range
- Export comparison results as CSV

The tool supports the following statistics, where the corresponding data are available:

| Statistic | Unit |
|---|---|
| Number of Plumes | Count |
| Number of Emission Records | Count |
| Mean Emission | kg/hr |
| Median Emission | kg/hr |
| Minimum Emission | kg/hr |
| Maximum Emission | kg/hr |
| Standard Deviation | kg/hr |

Emission statistics depend on the fields and records returned by the underlying data service. They should not be interpreted as independently measured emission rates unless supported by the source data.

### 5. User Interface

The plugin provides a graphical interface with features including:

- Map canvas and bounding-box AOI selection
- Layer-based AOI selection
- STAC API search
- Data API search
- Asset download controls
- Statistical comparison
- CSV export
- Built-in help and documentation

## Requirements

- QGIS 3.22 or later (as specified by the current project documentation; compatibility should be tested against the intended QGIS versions)
- Internet connection
- Python package: `requests`

Install the Python dependency in the Python environment used by QGIS if it is not already available:

```bash
pip install requests
```

Some STAC API operations may require a Carbon Mapper API token.

## Installation

### Manual Installation from GitHub

Clone the repository:

```bash
git clone https://github.com/akanyaser/carbon_mapper_tool.git
```

Copy the plugin folder into your QGIS plugins directory.

**Windows**

```text
%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\
```

**Linux**

```text
~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/
```

Restart QGIS and enable the plugin through:

**Plugins → Manage and Install Plugins**

> This is the manual installation procedure. Installation through the official QGIS Plugin Repository will be available after the plugin is accepted and published.

## Quick Start

### 1. Select an Area of Interest

Open the plugin and select one of the available AOI methods:

- Map canvas
- Manual bounding box
- Existing layer

Configure the search parameters and run the search.

### 2. Search and Download

Select the desired collection and asset, then start the download. Available products depend on the selected dataset.

### 3. Compare Geographic Regions

Open the statistical comparison interface and select:

- Polygon layer
- Attribute field
- Two or more regions
- Gas type
- Date range

Run the comparison and export the results as CSV if required.

## STAC API Authentication

Some STAC API operations require a Carbon Mapper API token.

To obtain a token:

1. Visit https://data.carbonmapper.org.
2. Sign in, if required.
3. Obtain an API token using the service's supported procedure.
4. Enter the token in the plugin's API token field.

Authentication requirements may vary by API operation.

The statistical comparison tool uses the Data API as implemented in this project. Confirm the authentication requirements of the relevant endpoint before relying on unauthenticated access.

## Project Structure

```text
carbon_mapper_tool/
├── api/
│   └── carbon_api.py
├── utils/
│   └── qgis_utils.py
├── __init__.py
├── help_messages.py
├── metadata.txt
├── plugin.py
├── statistical_tool.py
├── widget.ui
├── README.md
├── LICENSE
└── .gitignore
```

## Technologies

- Python
- PyQGIS
- Qt Designer
- Carbon Mapper STAC API
- Carbon Mapper Data API

## Data Attribution and Terms of Use

This plugin provides access to Carbon Mapper datasets through the relevant Carbon Mapper APIs.

Users should acknowledge **Carbon Mapper** as the data provider when publishing analyses, maps, or derivative products, and should comply with the applicable data and service terms:

https://carbonmapper.org/terms

This is an independent academic project developed at **Politecnico di Milano**. It is not affiliated with, endorsed by, or officially supported by Carbon Mapper.

## License

The plugin source code is distributed under the **GNU General Public License v2.0 (GPL-2.0)**, subject to the terms in the accompanying `LICENSE` file.

Carbon Mapper datasets are not distributed with this repository. Their use remains subject to the applicable Carbon Mapper data and service terms.

## Author

**Yaser Enes Akan**

Department of Civil and Environmental Engineering
Politecnico di Milano