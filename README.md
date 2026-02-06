# GTFS CDMX Metro Service Analysis

This project analyzes and visualizes the service quality of the Mexico City (CDMX) Metro system. It utilizes GTFS (General Transit Feed Specification) data, ridership information, and geospatial data to calculate a Service Quality Index (ICS) for each station. The project categorizes service levels and generates an interactive geographical map for better understanding of the Metro's operational efficiency and user experience.

## Key Features

*   **GTFS Data Processing**: Loads and filters GTFS data specifically for the CDMX Metro system.
*   **Ridership Analysis**: Integrates ridership data to derive station-specific metrics, contributing to the overall service quality assessment.
*   **Service Quality Index (ICS)**: Computes a comprehensive, weighted index based on station congestion and passenger waiting times.
*   **Service Level Categorization**: Classifies Metro stations into "Good", "Regular", or "Critical" service levels based on their calculated ICS.
*   **Interactive Map Visualization**: Generates an interactive HTML map that visually represents Metro lines and station-specific service quality indicators, allowing for easy exploration.
*   **Data Export**: Outputs detailed service analysis results, including the ICS and service levels, to a CSV file for further analysis or reporting.

## Project Structure

*   `data/`: Contains all raw input data, including GTFS files (`routes.csv`, `stops.csv`, `trips.txt`, `stop_times.txt`, `frequencies.txt`), ridership data (`afluenciastc_desglosado_12_2025.csv`), and geospatial files (.kmz for Metro lines and stations).
*   `analisis-gtf-cdmx.ipynb`: A Jupyter Notebook used for initial data exploration, understanding the GTFS structure, and preliminary visualizations.
*   `calidad_servicio.py`: The core Python script responsible for:
    *   Loading and processing all necessary data.
    *   Implementing the logic for ICS calculation.
    *   Generating the interactive Folium map.
    *   Exporting the final analysis results.
*   `analisis_calidad_servicio.csv`: The output CSV file containing the calculated service quality metrics for each station.
*   `mapa_calidad_servicio.html`: The generated interactive HTML map visualizing the service quality across the CDMX Metro system.
*   `main.py`: An auxiliary Python script that performs initial data loading and can generate a basic map, potentially an earlier version or for quick testing.

## Technologies Used

*   **Python**: The primary programming language for data processing and analysis.
*   **Pandas**: Essential library for data manipulation and analysis.
*   **Folium**: Used for creating interactive geographical maps.
*   **GeoPandas**: Utilized for handling and processing geospatial data (e.g., .kmz files).

## How to Run

To run the analysis and generate the outputs:

1.  Ensure you have Python installed, along with the necessary libraries (pandas, folium, geopandas, branca). You can install them via pip:
    ```bash
    pip install pandas folium geopandas branca
    ```
2.  Place your GTFS data, ridership data, and geospatial files in the `data/` directory as structured in this repository.
3.  Execute the main analysis script:
    ```bash
    python calidad_servicio.py
    ```
    This will generate `mapa_calidad_servicio.html` and `analisis_calidad_servicio.csv` in the project's root directory.
4.  You can open `mapa_calidad_servicio.html` in any web browser to view the interactive map.
5.  For initial data exploration or understanding the steps, you can open `analisis-gtf-cdmx.ipynb` in a Jupyter environment.

