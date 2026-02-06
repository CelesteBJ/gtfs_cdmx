import pandas as pd
import os
import folium
import branca.colormap as cm

# ==============================
# CONFIGURACIÓN
# ==============================
BASE_DIR = r"C:\Users\Celes\Documents\temp-gtfs"
RUTA_GTFS = os.path.join(BASE_DIR, "data")

SALIDA_HTML = os.path.join(BASE_DIR, "mapa_calidad_servicio.html")
SALIDA_CSV  = os.path.join(BASE_DIR, "analisis_calidad_servicio.csv")

COLORES_METRO = {
    "1":  "#E10098",
    "2":  "#0052A5",
    "3":  "#9B9B9B",
    "4":  "#6AC6E3",
    "5":  "#F6D200",
    "6":  "#E10600",
    "7":  "#F39200",
    "8":  "#00A651",
    "9":  "#6E2C91",
    "A":  "#8ED6F8",
    "B":  "#B0B0B0",
    "12": "#C7B200"
}

# ==============================
# FUNCIÓN DE CARGA
# ==============================
def load(name, encoding="utf-8"):
    for ext in [".txt", ".csv"]:
        path = os.path.join(RUTA_GTFS, name + ext)
        if os.path.exists(path):
            try:
                return pd.read_csv(path, encoding=encoding)
            except UnicodeDecodeError:
                return pd.read_csv(path, encoding="latin1")
    raise FileNotFoundError(f"No se encontró {name}")

# ==============================
# CARGA DE DATOS
# ==============================
routes      = load("routes")
trips       = load("trips")
stops       = load("stops")
stop_times  = load("stop_times")
frequencies = load("frequencies")
afluencia   = load("afluenciastc_desglosado_12_2025", encoding="cp1252")

shapes_path = os.path.join(RUTA_GTFS, "shapes.txt")
shapes = load("shapes") if os.path.exists(shapes_path) else pd.DataFrame()

# ==============================
# FILTRO METRO
# ==============================
afluencia = afluencia[afluencia["anio"].isin([2025, 2026])].copy()

metro_routes = routes[routes["agency_id"].isin(["STC", "METRO"])]
metro_trips = trips[trips["route_id"].isin(metro_routes["route_id"])]
metro_stop_times = stop_times[stop_times["trip_id"].isin(metro_trips["trip_id"])]

# ==============================
# AFLUENCIA POR ESTACIÓN
# ==============================
afluencia["estacion_norm"] = afluencia["estacion"].str.upper().str.strip()

afluencia_est = (
    afluencia
    .groupby("estacion_norm", as_index=False)
    .agg(afluencia=("afluencia", "sum"))
)

# ==============================
# FRECUENCIA PROMEDIO
# ==============================
freq = frequencies[frequencies["trip_id"].isin(metro_trips["trip_id"])]
freq = freq.merge(metro_trips[["trip_id", "route_id"]], on="trip_id")

freq_ruta = (
    freq
    .groupby("route_id", as_index=False)
    .agg(headway_secs=("headway_secs", "mean"))
)

# ==============================
# ESTACIONES + FRECUENCIA + COORDS
# ==============================
rutas_est = (
    metro_stop_times
    .merge(metro_trips[["trip_id", "route_id"]], on="trip_id")
    [["stop_id", "route_id"]]
    .drop_duplicates()
    .merge(freq_ruta, on="route_id")
)

metro_stops = stops[stops["stop_id"].isin(metro_stop_times["stop_id"])].copy()
metro_stops["stop_name_norm"] = metro_stops["stop_name"].str.upper().str.strip()

rutas_est = rutas_est.merge(
    metro_stops[["stop_id", "stop_name_norm", "stop_lat", "stop_lon"]],
    on="stop_id"
)

freq_est = (
    rutas_est
    .groupby("stop_name_norm", as_index=False)
    .agg(
        headway_secs=("headway_secs", "mean"),
        stop_lat=("stop_lat", "mean"),
        stop_lon=("stop_lon", "mean")
    )
)

freq_est["headway_min"] = freq_est["headway_secs"] / 60

# ==============================
# UNIÓN FINAL
# ==============================
df = afluencia_est.merge(
    freq_est,
    left_on="estacion_norm",
    right_on="stop_name_norm",
    how="inner"
)

# ==============================
# ÍNDICE DE CALIDAD DEL SERVICIO (ICS)
# ==============================
df["indice_congestion"] = (df["afluencia"] / 1_000_000) * df["headway_min"]

IC_MAX = df["indice_congestion"].quantile(0.95)
ESPERA_MAX = 15

df["congestion_norm"] = (df["indice_congestion"] / IC_MAX).clip(0, 1)
df["espera_norm"] = (df["headway_min"] / ESPERA_MAX).clip(0, 1)

df["ICS"] = 0.6 * df["congestion_norm"] + 0.4 * df["espera_norm"]

df["nivel_servicio"] = pd.cut(
    df["ICS"],
    bins=[0, 0.3, 0.6, 1],
    labels=["Bueno", "Regular", "Crítico"],
    include_lowest=True
)

# ==============================
# MAPA (FOLIUM)
# ==============================
mapa = folium.Map(
    location=[df["stop_lat"].mean(), df["stop_lon"].mean()],
    zoom_start=11,
    tiles="CartoDB positron"
)

# ---- LÍNEAS DEL METRO ----
routes_info = metro_routes[["route_id", "route_short_name"]].drop_duplicates()

if not shapes.empty:
    shape_ids = metro_trips["shape_id"].dropna().unique()
    metro_shapes = shapes[shapes["shape_id"].isin(shape_ids)]

    for _, r in routes_info.iterrows():
        linea = str(r["route_short_name"])
        color = COLORES_METRO.get(linea, "#999999")

        for sid in metro_trips[metro_trips["route_id"] == r["route_id"]]["shape_id"].dropna().unique():
            s = metro_shapes[metro_shapes["shape_id"] == sid].sort_values("shape_pt_sequence")
            if len(s) > 1:
                folium.PolyLine(
                    list(zip(s.shape_pt_lat, s.shape_pt_lon)),
                    color=color,
                    weight=4,
                    opacity=0.7,
                    tooltip=f"Línea {linea}"
                ).add_to(mapa)
else:
    for _, r in routes_info.iterrows():
        linea = str(r["route_short_name"])
        color = COLORES_METRO.get(linea, "#999999")

        st = (
            metro_stop_times[metro_stop_times["trip_id"].isin(
                metro_trips[metro_trips["route_id"] == r["route_id"]]["trip_id"]
            )]
            .merge(stops, on="stop_id")
            .sort_values("stop_sequence")
            .drop_duplicates("stop_id")
        )

        if len(st) > 1:
            folium.PolyLine(
                list(zip(st.stop_lat, st.stop_lon)),
                color=color,
                weight=3,
                opacity=0.5,
                tooltip=f"Línea {linea}"
            ).add_to(mapa)

# ---- ESTACIONES (ICS) ----
colormap = cm.LinearColormap(
    colors=["green", "yellow", "orange", "red"],
    vmin=0,
    vmax=1,
    caption="Índice de Calidad del Servicio"
)
mapa.add_child(colormap)

for _, row in df.iterrows():
    folium.CircleMarker(
        location=[row["stop_lat"], row["stop_lon"]],
        radius=max(3, row["afluencia"] / 6_000_000),
        color=colormap(row["ICS"]),
        fill=True,
        fill_opacity=0.7,
        popup=f"""
        <b>Estación:</b> {row['stop_name_norm']}<br>
        <b>Afluencia:</b> {int(row['afluencia']):,}<br>
        <b>Espera:</b> {row['headway_min']:.2f} min<br>
        <b>ICS:</b> {row['ICS']:.2f}<br>
        <b>Nivel:</b> <b>{row['nivel_servicio']}</b>
        """
    ).add_to(mapa)

# ==============================
# GUARDAR SALIDAS
# ==============================
mapa.save(SALIDA_HTML)

df_final = df[[
    "stop_name_norm",
    "afluencia",
    "headway_min",
    "indice_congestion",
    "ICS",
    "nivel_servicio",
    "stop_lat",
    "stop_lon"
]].rename(columns={
    "stop_name_norm": "Estacion",
    "afluencia": "Afluencia_Total_2025_26",
    "headway_min": "Espera_Promedio_Minutos",
    "indice_congestion": "Indice_Congestion",
    "ICS": "Indice_Calidad_Servicio",
    "nivel_servicio": "Nivel_Servicio",
    "stop_lat": "Latitud",
    "stop_lon": "Longitud"
})

df_final.to_csv(SALIDA_CSV, index=False, float_format="%.2f")