import folium

# Coordenadas del Centro Histórico de la Ciudad de México
mapa = folium.Map(location=(19.4326, -99.1332))

mapa.save("test/index.html")


## pandas
import pandas as pd

# cargando rutas de el servicio del metro de la cdmx
rutas=pd.read_csv("data/routes.csv")
rutas_metro=rutas[rutas["agency_id"]=="METRO"]
print(rutas_metro.head())

# obetener estaciones unicas del metro de la cdmx
estaciones=pd.read_csv("data/stops.csv")
estaciones_metro=estaciones[estaciones["stop_name"].str.startswith("Metro")]
print(estaciones_metro.head())

import geopandas as gd
rutas=gd.read_file("data/STC_Metro_estaciones.kmz")
print(rutas.columns)