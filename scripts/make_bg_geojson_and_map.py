#!/usr/bin/env python3
"""
Download Kansas block-group TIGER/Line shapefile, merge with
`census_patient_percent.csv`, and produce a GeoJSON and a Folium choropleth map.

Run: python3 scripts/make_bg_geojson_and_map.py

Requirements: geopandas, pandas, requests, folium
"""
import os
import io
import zipfile
import requests
import tempfile

import pandas as pd
import geopandas as gpd
import folium
from folium.features import GeoJsonTooltip


TIGER_BG_URL = "https://www2.census.gov/geo/tiger/TIGER2022/BG/tl_2022_20_bg.zip"
CSV_PATH = "census_patient_percent.csv"
OUT_DIR = "data"
GEOJSON_OUT = os.path.join(OUT_DIR, "ks_bg_merged.geojson")
MAP_OUT = "SVH_bg_map.html"


def download_and_extract(url, target_dir):
    r = requests.get(url, stream=True)
    r.raise_for_status()
    with tempfile.TemporaryDirectory() as td:
        zpath = os.path.join(td, "tiger.zip")
        with open(zpath, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        with zipfile.ZipFile(zpath, "r") as z:
            z.extractall(target_dir)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    print("Downloading TIGER BG shapefile (Kansas)...")
    shp_dir = os.path.join(OUT_DIR, "tiger_bg")
    os.makedirs(shp_dir, exist_ok=True)
    download_and_extract(TIGER_BG_URL, shp_dir)

    # find .shp in extracted files
    shp_file = None
    for fn in os.listdir(shp_dir):
        if fn.lower().endswith('.shp') and 'bg' in fn.lower():
            shp_file = os.path.join(shp_dir, fn)
            break
    if shp_file is None:
        raise FileNotFoundError('Could not find shapefile in downloaded TIGER package')

    print(f"Reading shapefile {shp_file}...")
    gdf = gpd.read_file(shp_file)

    print("Reading CSV data...")
    df = pd.read_csv(CSV_PATH, dtype={"CensusCode": str})

    # Ensure GEOID column in shapefile and CensusCode are comparable
    if 'GEOID' in gdf.columns:
        gdf['GEOID'] = gdf['GEOID'].astype(str)
    else:
        raise KeyError('Expected GEOID column in TIGER BG shapefile')

    df['CensusCode'] = df['CensusCode'].astype(str)

    print('Merging CSV into GeoDataFrame on GEOID <- CensusCode...')
    merged = gdf.merge(df, left_on='GEOID', right_on='CensusCode', how='left')

    print(f"Writing merged GeoJSON to {GEOJSON_OUT}...")
    merged.to_file(GEOJSON_OUT, driver='GeoJSON')

    # Build folium map
    print('Building Folium choropleth map...')
    # center map on Kansas roughly or average of points if available
    if 'CENTLAT' in df.columns and 'CENTLON' in df.columns:
        try:
            lat = df['CENTLAT'].astype(float).mean()
            lon = df['CENTLON'].astype(float).mean()
        except Exception:
            lat, lon = 38.5, -98.0
    else:
        lat, lon = 38.5, -98.0

    m = folium.Map(location=[lat, lon], zoom_start=6, tiles='cartodbpositron')

    # choropleth using PatientPercent
    folium.Choropleth(
        geo_data=GEOJSON_OUT,
        name='Patient Percent',
        data=df,
        columns=['CensusCode', 'PatientPercent'],
        key_on='feature.properties.GEOID',
        fill_color='YlOrRd',
        nan_fill_color='transparent',
        fill_opacity=0.7,
        line_opacity=0.1,
        legend_name='Patient Percent'
    ).add_to(m)

    # Add tooltip
    folium.GeoJson(
        GEOJSON_OUT,
        style_function=lambda feature: {'fillOpacity': 0, 'weight': 0},
        tooltip=GeoJsonTooltip(fields=['GEOID', 'PatientPercent', 'PopulationValue', 'PatientNumber'],
                               aliases=['GEOID', 'PatientPercent', 'Population', 'Patients'],
                               localize=True)
    ).add_to(m)

    # Add point markers from CSV using CENTLAT/CENTLON, sorted by PatientPercent
    if 'CENTLAT' in df.columns and 'CENTLON' in df.columns:
        pts = df.dropna(subset=['CENTLAT', 'CENTLON']).copy()
        # ensure numeric
        pts['CENTLAT'] = pts['CENTLAT'].astype(float)
        pts['CENTLON'] = pts['CENTLON'].astype(float)
        pts['PatientPercent'] = pd.to_numeric(pts['PatientPercent'], errors='coerce')

        # sort ascending so highest PatientPercent are drawn last (on top)
        pts_sorted = pts.sort_values('PatientPercent', ascending=True)

        fg = folium.FeatureGroup(name='Points (by PatientPercent)', show=True)
        for _, r in pts_sorted.iterrows():
            try:
                pct = float(r['PatientPercent']) if pd.notna(r['PatientPercent']) else 0.0
            except Exception:
                pct = 0.0
            # scale radius for visibility
            radius = max(2, pct * 1000)
            popup = (f"GEOID: {r.get('CensusCode','')}<br>"
                     f"PatientPercent: {pct:.5f}<br>"
                     f"Population: {r.get('PopulationValue','')}<br>"
                     f"Patients: {r.get('PatientNumber','')}")
            folium.CircleMarker(
                location=[r['CENTLAT'], r['CENTLON']],
                radius=radius,
                color='#d73027',
                fill=True,
                fill_color='#fc8d59',
                fill_opacity=0.7,
                weight=0.5,
                popup=folium.Popup(popup, max_width=300)
            ).add_to(fg)
        fg.add_to(m)

    folium.LayerControl().add_to(m)
    print(f"Saving map to {MAP_OUT}...")
    m.save(MAP_OUT)
    print('Done. Open SVH_bg_map.html to view the block-group choropleth.')


if __name__ == '__main__':
    main()
