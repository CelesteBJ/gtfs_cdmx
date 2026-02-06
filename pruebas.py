import pandas as pd
import folium
from folium import plugins
import os

# ================================
# 1. CONFIGURAR RUTA DE TUS ARCHIVOS
# ================================
# CAMBIA ESTA RUTA A DONDE ESTÁN TUS ARCHIVOS .TXT
ruta_gtfs = r"C:\Users\Celes\Documents\temp-gtfs\data"  # <-- ACTUALIZA ESTA RUTA

# Verificar que la carpeta existe
if not os.path.exists(ruta_gtfs):
    print(f"❌ ERROR: La carpeta {ruta_gtfs} no existe")
    print("Por favor, actualiza la variable 'ruta_gtfs' con la ruta correcta")
    exit()

print(f"📁 Buscando archivos en: {ruta_gtfs}")

# ================================
# 2. CARGAR TODOS TUS DATOS GTFS
# ================================
print("Cargando datos GTFS...")

try:
    agency = pd.read_csv(os.path.join(ruta_gtfs, 'agency.txt'))
    calendar = pd.read_csv(os.path.join(ruta_gtfs, 'calendar.txt'))
    frequencies = pd.read_csv(os.path.join(ruta_gtfs, 'frequencies.txt'))
    routes = pd.read_csv(os.path.join(ruta_gtfs, 'routes.csv'))
    shapes = pd.read_csv(os.path.join(ruta_gtfs, 'shapes.txt'))
    stop_times = pd.read_csv(os.path.join(ruta_gtfs, 'stop_times.txt'))
    stops = pd.read_csv(os.path.join(ruta_gtfs, 'stops.csv'))
    trips = pd.read_csv(os.path.join(ruta_gtfs, 'trips.txt'))
    
    print(f"✓ Cargados: {len(routes)} rutas, {len(stops)} paradas, {len(shapes['shape_id'].unique())} shapes")
    
except FileNotFoundError as e:
    print(f"❌ ERROR: No se encontró el archivo {e.filename}")
    print(f"Verifica que todos los archivos .txt estén en: {ruta_gtfs}")
    exit()

# ================================
# 3. CREAR MAPA BASE
# ================================
center_lat = stops['stop_lat'].mean()
center_lon = stops['stop_lon'].mean()

mapa = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=12,
    tiles='OpenStreetMap'
)

# ================================
# 4. DICCIONARIO DE COLORES POR RUTA
# ================================
colores = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 
           'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue', 
           'darkpurple', 'pink', 'lightblue', 'lightgreen', 'gray', 
           'black', 'lightgray']

route_colors = {}
for idx, route_id in enumerate(routes['route_id'].unique()):
    route_colors[route_id] = colores[idx % len(colores)]

# ================================
# 5. AGREGAR SHAPES (TRAZADO DE RUTAS)
# ================================
print("Dibujando rutas...")

# Merge para obtener route_id de cada shape
trips_shapes = trips[['route_id', 'shape_id']].drop_duplicates()

for shape_id in shapes['shape_id'].unique():
    shape_data = shapes[shapes['shape_id'] == shape_id].sort_values('shape_pt_sequence')
    coordinates = list(zip(shape_data['shape_pt_lat'], shape_data['shape_pt_lon']))
    
    # Obtener información de la ruta
    route_info = trips_shapes[trips_shapes['shape_id'] == shape_id]
    
    if not route_info.empty:
        route_id = route_info.iloc[0]['route_id']
        route_data = routes[routes['route_id'] == route_id]
        
        if not route_data.empty:
            route_name = route_data.iloc[0]['route_short_name'] if 'route_short_name' in route_data.columns else route_data.iloc[0]['route_long_name']
            color = route_colors.get(route_id, 'gray')
            
            folium.PolyLine(
                coordinates,
                color=color,
                weight=3,
                opacity=0.7,
                popup=f"Ruta: {route_name}"
            ).add_to(mapa)

# ================================
# 6. AGREGAR PARADAS
# ================================
print("Agregando paradas...")

# Crear grupos de marcadores para mejor rendimiento
marker_cluster = plugins.MarkerCluster().add_to(mapa)

for idx, stop in stops.iterrows():
    # Contar cuántas rutas pasan por esta parada
    rutas_en_parada = stop_times[stop_times['stop_id'] == stop['stop_id']]['trip_id'].unique()
    num_rutas = len(trips[trips['trip_id'].isin(rutas_en_parada)]['route_id'].unique())
    
    popup_text = f"""
    <b>{stop['stop_name']}</b><br>
    ID: {stop['stop_id']}<br>
    Rutas que pasan: {num_rutas}
    """
    
    folium.CircleMarker(
        location=[stop['stop_lat'], stop['stop_lon']],
        radius=5,
        popup=folium.Popup(popup_text, max_width=200),
        color='darkblue',
        fill=True,
        fillColor='lightblue',
        fillOpacity=0.7
    ).add_to(marker_cluster)

# ================================
# 7. AGREGAR LEYENDA DE RUTAS
# ================================
legend_html = '''
<div style="position: fixed; 
            bottom: 50px; right: 50px; width: 220px; height: auto; 
            background-color: white; z-index:9999; font-size:14px;
            border:2px solid grey; border-radius: 5px; padding: 10px">
<h4 style="margin-top:0;">Rutas</h4>
'''

for idx, row in routes.iterrows():
    route_id = row['route_id']
    route_name = row['route_short_name'] if 'route_short_name' in row and pd.notna(row['route_short_name']) else row['route_long_name']
    color = route_colors.get(route_id, 'gray')
    legend_html += f'<p style="margin:5px 0;"><span style="background-color:{color}; width:15px; height:15px; display:inline-block; margin-right:5px;"></span>{route_name}</p>'

legend_html += '</div>'
mapa.get_root().html.add_child(folium.Element(legend_html))

# ================================
# 8. GUARDAR MAPA
# ================================
output_file = os.path.join(ruta_gtfs, 'mapa_gtfs_completo.html')
mapa.save(output_file)
print(f"\n✓ ¡Mapa creado exitosamente!")
print(f"✓ Abre el archivo '{output_file}' en tu navegador\n")

# ================================
# 9. ESTADÍSTICAS OPCIONALES
# ================================
print("=== ESTADÍSTICAS DE TU GTFS ===")
print(f"Agencias: {len(agency)}")
print(f"Rutas: {len(routes)}")
print(f"Paradas: {len(stops)}")
print(f"Viajes únicos: {len(trips)}")
print(f"Shapes únicos: {len(shapes['shape_id'].unique())}")