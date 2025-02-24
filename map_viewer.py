import sqlite3
import folium
import webbrowser
import time
import os
from config import DB_NAME
from constollers import get_all_ais_data


def get_latest_ship_positions():
    rows = get_all_ais_data()

    ship_positions = []
    for row in rows:
        mmsi = row["mmsi"]
        lat = row["lat"]
        lon = row["lon"]
        sog = row["sog"]
        cog = row["cog"]
        if lat and lon:
            ship_positions.append((mmsi, lat, lon, sog, cog))

    return ship_positions

def generate_map():
    ship_positions = get_latest_ship_positions()

    if ship_positions:
        lat_center, lon_center = ship_positions[0][1], ship_positions[0][2]
    else:
        lat_center, lon_center = 0, 0

    ship_map = folium.Map(location=[lat_center, lon_center], zoom_start=5)

    for mmsi, lat, lon, sog, cog in ship_positions:
        folium.Marker(
            location=[lat, lon],
            popup=f"MMSI: {mmsi}\nLat: {lat}, Lon: {lon}\nSpeed: {sog} knots\nCourse: {cog}°",
            icon=folium.Icon(color="blue", icon="ship", prefix="fa")
        ).add_to(ship_map)

    map_filename = "ship_map.html"
    ship_map.save(map_filename)
    return os.path.abspath(map_filename)
    # webbrowser.open_new_tab("file://" + os.path.abspath(map_filename))


if __name__ == "__main__":
    while True:
        generate_map()
        print("Peta diperbarui...")
        time.sleep(10)