import pandas as pd
import os
import folium
import branca.colormap as cm

# ==============================
# CONFIG
# ==============================
RUTA_GTFS = r"C:\Users\Celes\Documents\temp-gtfs\data"
SALIDA_CSV = r"C:\Users\Celes\Documents\temp-gtfs\analisis_eficacia_servicio.csv"
SALIDA_HTML = r"C:\Users\Celes\Documents\temp-gtfs\mapa_analisis_calidad.html"

# Colores distintivos para las líneas del Metro
COLORES_METRO = {
    "1":  "#E10098",  # Rosa
    "2":  "#0052A5",  # Azul
    "3":  "#9B9B9B",  # Verde olivo
    "4":  "#6AC6E3",  # Cian
    "5":  "#F6D200",  # Amarillo
    "6":  "#E10600",  # Rojo
    "7":  "#F39200",  # Naranja
    "8":  "#00A651",  # Verde
    "9":  "#6E2C91",  # Café
    "A":  "#8ED6F8",  # Morado claro
    "B":  "#B0B0B0",  # Gris
    "12": "#C7B200"   # Dorado
}

# ==============================
# LOAD GTFS & AFLUENCIA DATA
# ==============================
def load(name, encoding='utf-8'):
    for ext in ['.txt', '.csv']:
        p = os.path.join(RUTA_GTFS, name + ext)
        if os.path.exists(p):
            try:
                return pd.read_csv(p, encoding=encoding)
            except UnicodeDecodeError:
                return pd.read_csv(p, encoding='latin1') # Fallback
    raise FileNotFoundError(f"No se encontró {name}")

print("Cargando datos...")
routes      = load('routes')
trips       = load('trips')
stops       = load('stops')
stop_times  = load('stop_times')
frequencies = load('frequencies')
# Se carga con cp1252 para intentar corregir problemas de codificación.
afluencia_metro = load("afluenciastc_desglosado_12_2025", encoding='cp1252')
shapes = load('shapes') if os.path.exists(os.path.join(RUTA_GTFS, 'shapes.txt')) else pd.DataFrame()


# ==============================
# FILTRAR DATOS RECIENTES Y SISTEMA METRO
# ==============================
print("Filtrando datos para años 2025-2026 y sistema METRO...")

# Filtrar por año
afluencia_metro = afluencia_metro[afluencia_metro['anio'].isin([2025, 2026])].copy()

metro_agency_ids = ['STC', 'METRO']
metro_routes = routes[routes['agency_id'].isin(metro_agency_ids)]
metro_trips = trips[trips['route_id'].isin(metro_routes['route_id'])]
metro_stop_times = stop_times[stop_times['trip_id'].isin(metro_trips['trip_id'])]

# ==============================
# 1. CALCULAR AFLUENCIA TOTAL POR ESTACIÓN
# ==============================
print("Calculando afluencia por estación...")
afluencia_metro['estacion_norm'] = afluencia_metro['estacion'].str.upper().str.strip()
afluencia_por_estacion = afluencia_metro.groupby('estacion_norm')['afluencia'].sum().reset_index()

# ==============================
# 2. CALCULAR FRECUENCIA (HEADWAY) PROMEDIO POR RUTA
# ==============================
print("Calculando frecuencia promedio por ruta...")
metro_frequencies = frequencies[frequencies['trip_id'].isin(metro_trips['trip_id'])]
freq_with_route = metro_frequencies.merge(metro_trips[['trip_id', 'route_id']], on='trip_id')
freq_por_ruta = freq_with_route.groupby('route_id')['headway_secs'].mean().reset_index()
freq_por_ruta.rename(columns={'headway_secs': 'headway_ruta_promedio'}, inplace=True)

# ==============================
# 3. ASOCIAR ESTACIONES CON RUTAS Y FRECUENCIAS
# ==============================
print("Asociando estaciones con sus rutas y frecuencias...")
rutas_por_estacion = metro_stop_times.merge(metro_trips[['trip_id', 'route_id']], on='trip_id')[['stop_id', 'route_id']].drop_duplicates()
rutas_freq_por_estacion = rutas_por_estacion.merge(freq_por_ruta, on='route_id')

# ==============================
# 4. CALCULAR FRECUENCIA Y COORDENADAS PROMEDIO POR NOMBRE DE ESTACIÓN
# ==============================
print("Calculando frecuencia y coordenadas promedio por nombre de estación...")
metro_stop_ids = metro_stop_times['stop_id'].unique()
metro_stops = stops[stops['stop_id'].isin(metro_stop_ids)].copy()
metro_stops['stop_name_norm'] = metro_stops['stop_name'].str.upper().str.strip()

rutas_freq_con_nombre_y_coords = rutas_freq_por_estacion.merge(
    metro_stops[['stop_id', 'stop_name_norm', 'stop_lat', 'stop_lon']], on='stop_id'
)

agg_dict = {
    'headway_ruta_promedio': 'mean',
    'stop_lat': 'mean',
    'stop_lon': 'mean'
}
freq_por_nombre_estacion = rutas_freq_con_nombre_y_coords.groupby('stop_name_norm').agg(agg_dict).reset_index()
freq_por_nombre_estacion.rename(columns={'headway_ruta_promedio': 'headway_estacion_promedio_secs'}, inplace=True)
freq_por_nombre_estacion['headway_estacion_promedio_min'] = freq_por_nombre_estacion['headway_estacion_promedio_secs'] / 60

# ==============================
# 5. UNIR AFLUENCIA Y FRECUENCIA POR NOMBRE DE ESTACIÓN
# ==============================
print("Uniendo afluencia y datos de frecuencia por nombre de estación...")
analisis_df = afluencia_por_estacion.merge(
    freq_por_nombre_estacion,
    left_on='estacion_norm',
    right_on='stop_name_norm',
    how='inner'
)

# ==============================
# 6. CALCULAR ÍNDICE DE CONGESTIÓN (AJUSTADO)
# ==============================
print("Calculando índice de congestión ajustado...")
if not analisis_df.empty:
    # Nuevo cálculo del índice de congestión: (Afluencia en millones) * Espera Promedio en Minutos
    analisis_df['indice_congestion'] = (analisis_df['afluencia'] / 1000000) * analisis_df['headway_estacion_promedio_min']
else:
    analisis_df['indice_congestion'] = None

# ==============================
# 7. GENERAR MAPA DE ANÁLISIS
# ==============================
if not analisis_df.empty:
    print("Generando mapa de análisis...")
    mapa = folium.Map(location=[analisis_df['stop_lat'].mean(), analisis_df['stop_lon'].mean()], zoom_start=11, tiles='CartoDB positron')

    # --- Dibujar líneas del Metro ---
    metro_routes_info = metro_routes[['route_id', 'route_short_name']].drop_duplicates()

    if not shapes.empty:
        metro_shape_ids = metro_trips[metro_trips['shape_id'].notna()]['shape_id'].unique()
        metro_shapes = shapes[shapes['shape_id'].isin(metro_shape_ids)]

        for route_idx, route_row in metro_routes_info.iterrows():
            route_id = route_row['route_id']
            line_number = str(route_row['route_short_name'])
            color = COLORES_METRO.get(line_number, '#999999')

            shapes_for_route = metro_trips[metro_trips['route_id'] == route_id]['shape_id'].dropna().unique()

            for shape_id_val in shapes_for_route:
                s = metro_shapes[metro_shapes.shape_id == shape_id_val].sort_values('shape_pt_sequence')
                if len(s) < 2:
                    continue
                coords = list(zip(s.shape_pt_lat, s.shape_pt_lon))
                folium.PolyLine(
                    coords,
                    color=color,
                    weight=4,
                    opacity=0.7,
                    tooltip=f"Línea {line_number}"
                ).add_to(mapa)
    else: # Fallback: trazar líneas conectando paradas si no hay datos de shapes.txt
        print("No se encontraron datos de 'shapes.txt' para las líneas del Metro. Trazando líneas a partir de las paradas.")
        for route_idx, route_row in metro_routes_info.iterrows():
            route_id = route_row['route_id']
            line_number = str(route_row['route_short_name'])
            color = COLORES_METRO.get(line_number, '#999999')

            stops_for_route = (
                metro_stop_times[metro_stop_times['trip_id'].isin(metro_trips[metro_trips['route_id'] == route_id]['trip_id'])]
                .merge(stops, on='stop_id')
                .sort_values('stop_sequence')
                .drop_duplicates(subset=['stop_id'])
            )
            if len(stops_for_route) < 2:
                continue
            coords = list(zip(stops_for_route.stop_lat, stops_for_route.stop_lon))
            folium.PolyLine(
                coords,
                color=color,
                weight=3,
                opacity=0.5,
                tooltip=f"Línea {line_number}"
            ).add_to(mapa)
    # --- Fin Dibujar líneas del Metro ---

    # Escala de color para el índice de congestión
    min_idx = analisis_df['indice_congestion'].min()
    max_idx = analisis_df['indice_congestion'].max()
    colormap = cm.LinearColormap(colors=['yellow', 'orange', 'red'], vmin=min_idx, vmax=max_idx)
    colormap.caption = 'Índice de Congestión (Millones de Afluencia * Espera en Minutos)'
    mapa.add_child(colormap)

    # Añadir círculos de afluencia por estación
    for _, row in analisis_df.iterrows():
        popup_text = f"""
        <b>Estación:</b> {row['stop_name_norm']}<br>
        <b>Afluencia (2025-26):</b> {int(row['afluencia']):,}<br>
        <b>Espera Promedio:</b> {round(row['headway_estacion_promedio_min'], 2)} min<br>
        <b>Índice Congestión:</b> {round(row['indice_congestion'], 2):,}<br>
        """
        
        folium.CircleMarker(
            location=[row['stop_lat'], row['stop_lon']],
            radius=max(3, row['afluencia'] / 6000000), # Escala el radio para visualización
            color=colormap(row['indice_congestion']),
            fill=True,
            fill_opacity=0.7,
            popup=folium.Popup(popup_text, max_width=300)
        ).add_to(mapa)

    mapa.save(SALIDA_HTML)
    print(f"✓ Mapa generado en: {SALIDA_HTML}")
else:
    print("No se generó el mapa porque no se encontraron datos coincidentes.")

# ==============================
# 8. GUARDAR REPORTE CSV
# ==============================
if not analisis_df.empty:
    analisis_df = analisis_df.sort_values('indice_congestion', ascending=False)
    reporte_final = analisis_df[[
        'stop_name_norm',
        'afluencia',
        'headway_estacion_promedio_min',
        'indice_congestion',
        'stop_lat',
        'stop_lon'
    ]]
    reporte_final.rename(columns={
        'stop_name_norm': 'Estacion',
        'afluencia': 'Afluencia_Total_2025_26',
        'headway_estacion_promedio_min': 'Espera_Promedio_Minutos',
        'indice_congestion': 'Indice_Congestion',
        'stop_lat': 'Latitud',
        'stop_lon': 'Longitud'
    }, inplace=True)
    
    print(f"Guardando análisis en: {SALIDA_CSV}")
    reporte_final.to_csv(SALIDA_CSV, index=False, float_format='%.2f')
else:
    reporte_final = pd.DataFrame(columns=['Estacion', 'Afluencia_Total_2025_26', 'Espera_Promedio_Minutos', 'Indice_Congestion', 'Latitud', 'Longitud'])
    print(f"Guardando reporte vacío en: {SALIDA_CSV}")
    reporte_final.to_csv(SALIDA_CSV, index=False)

print("✓ Análisis completado.")
