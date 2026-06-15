
"""
Carbon Mapper API helper module for the QGIS plugin.

This module sends STAC search requests to the Carbon Mapper API and downloads
selected asset files with the provided access token. Downloaded files are saved
to the user's Downloads folder so they can be loaded by QGIS afterward.
"""

import os
import requests
from qgis.PyQt.QtWidgets import QMessageBox

SEARCH_URL = "https://api.carbonmapper.org/api/v1/stac/search"

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


def download_asset(feature, token, asset_name="cmf.tif", index=0, output_dir=""):
    """
    Saves the selected asset file to the download folder (output_dir) specified by the user.
    """
    try:
        assets = feature.get("assets", {})
        if asset_name not in assets:
            return None

        download_url = assets[asset_name].get("href")
        if not download_url:
            return None

        headers = {"Authorization": f"Bearer {token}"}
        # stream=True allows large map files to be downloaded in chunks without bloating memory.
        response = requests.get(download_url, headers=headers, stream=True)
        
        if response.status_code != 200:
            return None

        #  IF THE USER SELECTS A FOLDER, SAVE THE FINDINGS THERE; IF NOT, SAVE TO THE DEFAULT LOCATION.
        if output_dir and os.path.exists(output_dir):
            # Specify the file name (we add feature_id and index to avoid conflicts)
            file_name = f"{feature.get('id', 'asset')}_{index}_{asset_name}"
            save_path = os.path.join(output_dir, file_name)
        else:
            # Backup plan: We are targeting the "Downloads" folder in the user's Windows profile.
            downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
            file_name = f"feature_{index}_{asset_name}"
            save_path = os.path.join(downloads_dir, file_name)

        # We are writing the file to the disk in parts.
        with open(save_path, 'wb') as f:
            # We conserve RAM by writing to disk in blocks of 8192 bytes.
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return save_path # We return the full downloaded file path so that QGIS can load it as a layer.

    except Exception as e:
        return None