
"""
Carbon Mapper API helper module for the QGIS plugin.

This module sends STAC search requests to the Carbon Mapper API and downloads
selected asset files with the provided access token. Downloaded files are saved
to the user's Downloads folder so they can be loaded by QGIS afterward.
"""

from urllib.parse import quote
import os
import requests
import csv
from io import StringIO

SEARCH_URL = (
    "https://api.carbonmapper.org/api/v1/stac/search"
)

def search_plume_csv(
        gas=None,
        bbox=None,
        datetime_range=None,
        limit=500,
        offset=0
):
    url = (
        "https://api.carbonmapper.org/api/v1/catalog/plume-csv"
    )

    params = [
        ("limit", limit),
        ("offset", offset)
    ]
    
    if gas and gas.lower() != "all":
        params.append(
            ("plume_gas", gas.upper())
        )
    
    #AOI
    if bbox and len(bbox) ==4:

        xmin, ymin, xmax, ymax = bbox

        params.extend([
            ("bbox", xmin),
            ("bbox", ymin),
            ("bbox", xmax),
            ("bbox", ymax)
        ])
    
    #datetime
    if datetime_range:
        params.append(
            ("datetime", datetime_range)
        )

    r = requests.get(
        url,
        params=params,
        timeout=60
    )

    print("REQUEST URL:")
    print(r.url)

    if r.status_code != 200:
        raise Exception(
            f"Data API error: {r.status_code}"
        )
    
    csv_reader = csv.DictReader(
        StringIO(r.text)
    )

    rows = list(csv_reader)

    if rows:
        print("FIRST RECORD:")
        print(rows[0])

    print(
        f"Data API returned {len(rows)} plume records."
    )

    return rows

def search_sources_csv(
        bbox=None,
        limit=50,
        gas=None,
        datetime_range=None
):
    url = (
        "https://api.carbonmapper.org/api/v1/catalog/sources-csv"
    )

    params = []
    
    params.append(
        ("limit", limit)
    )

    if gas and gas.lower() != "all":
        params.append(
            ("plume_gas", gas.upper())
        )
    
    #AOI
    if bbox and len(bbox) ==4:

        xmin, ymin, xmax, ymax = bbox

        params.extend([
            ("bbox", xmin),
            ("bbox", ymin),
            ("bbox", xmax),
            ("bbox", ymax)
        ])

    #datetime
    if datetime_range:
        params.append(
            ("datetime", datetime_range)
        )

    r = requests.get(
        url,
        params=params,
        timeout=30
    )

    print("REQUEST URL:")
    print(r.url)

    if r.status_code != 200:
        raise Exception(
            f"Data API error: {r.status_code}"
        )
    
    csv_reader = csv.DictReader(
        StringIO(r.text)
    )

    rows = list(csv_reader)

    #UI Limit
    if limit:
        rows = rows[:limit] 

    print(
        f"Data API returned {len(rows)} source records."
    )

    return rows

def search_data(collection, bbox, datetime_range, limit=10, token=""):
    """
    Carbon Mapper's guaranteed function for searching the STAC API. 
    The token parameter is now mandatory for search authorization.
    """
    payload = {
        "collections": [collection],
        "bbox": bbox,
        "datetime": datetime_range,
        "limit": limit
    }

    # We also notify the server of the token when making a search.
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = requests.post(SEARCH_URL, json=payload, headers=headers)
        if response.status_code != 200:
            raise Exception(f"STAC API returned status code {response.status_code} | Details: {response.text}")
        
        data = response.json()
        return data.get("features", [])
    except Exception as e:
        # Hatayı plugin.py yakalasın diye yukarı fırlatıyoruz
        raise Exception(f"Search failed: {str(e)}")

def get_source_plumes(
        source_name,
        limit=10
):
    """
    Returns plume records belonging to a source.
    """
    encoded_source = quote(source_name, safe="")

    url = (
        "https://api.carbonmapper.org/api/v1/catalog/"
        f"source-plumes-csv/{encoded_source}"
    )

    params = {
        "limit": limit
    }

    r = requests.get(
        url,
        params=params,
        timeout=30
    )

    print("REQUEST URL:")
    print(r.url)

    if r.status_code != 200:
        raise Exception(
            f"Source plume API error: {r.status_code}"
        )
    
    csv_reader = csv.DictReader(
        StringIO(r.text)
    )

    rows = list(csv_reader)

    print(
        f"Returned {len(rows)} plume records."
    )

    if rows:
        print("FIRST PLUME:")
        print(rows[0])

        print("AVAILABLE COLUMNS:")
        print(rows[0].keys())

    return rows

def get_all_plumes(
        bbox=None,
        gas=None,
        datetime_range=None
):
    all_rows = []
    offset = 0
    limit = 500

    while True:
        rows = search_plume_csv(
            bbox=bbox,
            gas=gas,
            datetime_range=datetime_range,
            limit=limit,
            offset=offset
        )

        if not rows:
            break

        all_rows.extend(rows)

        print(
            f"Downloaded {len(rows)} rows "
            f"(offset={offset})"
        )

        if len(rows) < limit:
            break
        
        offset += limit

    print(
        f"TOTAL ROWS: {len(all_rows)}"
    )

    return all_rows


def download_asset(feature, token="", asset_name="con_tif", index=0, output_dir=""):
    """
    Saves the selected asset file to the download folder (output_dir) specified by the user.
    Optimized for Data API Signed URLs without broken standalone calls.
    """
    try:

        # ----------------------------------
        # Data API URL
        # ----------------------------------

        download_url = feature.get(
            asset_name
        )

        if not download_url:
            print(
                f"{asset_name} URL not found."
            )

            return None
        
        print(f"Starting download: "
              f"{download_url[:80]}..."
        )

        # ----------------------------------
        # Download
        # ----------------------------------

        response = requests.get(
            download_url,
            stream=True,
            timeout=60
        )

        if response.status_code != 200:
            print(
                f"Download failed: "
                f"{response.status_code}"
            )

            return None
        
        # ----------------------------------
        # File Extension
        # ----------------------------------

        if asset_name.endswith("_tif"):
            ext = ".tif"

        elif asset_name.endswith("_png"):
            ext = ".png"

        elif asset_name.endswith("_json"):
            ext = ".json"

        else:
            ext = ""

        # ----------------------------------
        # File Name
        # ----------------------------------

        feature_id = feature.get(
            "plume_id",
            feature.get(
                "source_name",
                f"asset_{index}"
            )
        )

        file_name = (
            f"{feature_id}_{asset_name}{ext}"
        )

        # ----------------------------------
        # Output Directory
        # ----------------------------------

        if (
            output_dir
            and os.path.exists(output_dir)
        ):
            save_path = os.path.join(
                output_dir,
                file_name
            )

        else:
            downloads_dir = os.path.join(
                os.path.expanduser("~"),
                "Downloads"
            )

            save_path = os.path.join(
                downloads_dir,
                file_name
            )
        
        # ----------------------------------
        # Save
        # ----------------------------------

        with open(save_path, "wb") as f:
            for chunk in response.iter_content(
                chunk_size=8192
            ):
                if chunk:
                    f.write(chunk)
        
        print(
            f"SUCCESS: {save_path}"
        )

        return save_path
    
    except Exception as e:
        print(
            f"download_asset error: {e}"
        )

        return None


    

            
