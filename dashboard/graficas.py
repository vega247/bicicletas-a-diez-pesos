import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.cm as cm
from sklearn.cluster import KMeans

def promedio_bicis(consultar_ocupacion_estaciones, agrupacion=['station_id','dia']):
    bicicletas = consultar_ocupacion_estaciones.copy()
    bicicletas['last_reported'] = pd.to_datetime(bicicletas['last_reported'])
    bicicletas['periodo'] = bicicletas['last_reported'].dt.strftime('%Y%m%d%H')
    bicicletas['hora'] = bicicletas['last_reported'].dt.strftime('%H')
    bicicletas['dia'] = bicicletas['last_reported'].dt.strftime('%A')

    bicis_agrupadas = bicicletas.groupby(agrupacion)['num_bikes_available'].mean().reset_index()
    bicis_agrupadas = bicis_agrupadas.rename(columns={'num_bikes_available': 'promedio_bicis_disponibles'})    
    bicis_agrupadas['promedio_bicis_disponibles'] = bicis_agrupadas['promedio_bicis_disponibles'].round(2)
    return bicis_agrupadas

def generar_grafica_barras(df_promedios):
    dias_ordenados = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    df_promedios['dia'] = pd.Categorical(df_promedios['dia'], categories=dias_ordenados, ordered=True)
    df_resumen_dia = df_promedios.groupby('dia', observed=False)['promedio_bicis_disponibles'].mean().reset_index()

    fig, ax = plt.subplots(figsize=(6, 4))
    colores = cm.Blues([0.4 + (x/7)*0.5 for x in range(7)])
    
    ax.bar(df_resumen_dia['dia'], df_resumen_dia['promedio_bicis_disponibles'], color=colores, edgecolor='none')
    ax.set_ylabel("Promedio de Bicis Disponibles", fontsize=10)
    ax.set_xlabel("Día de la Semana", fontsize=10)
    ax.tick_params(axis='x', rotation=30)
    ax.grid(axis='y', linestyle=':', alpha=0.6)
    plt.tight_layout()
    return fig

def agrupar_estaciones_por_cercania(df_estaciones, n_clusters=25):
    # Archivo local donde se guardará la estructura del clúster
    CSV_CACHE = "cluster_de_estaciones.csv"

    # Filtramos las estaciones únicas y válidas desde los datos que vienen de la BD
    cols = ["station_id", "lat", "lon"]
    df_limpio = df_estaciones.dropna(subset=["lat", "lon"]).copy()
    df_coordenadas_actuales = df_limpio[cols].drop_duplicates().copy()

    recalcular = True

    # 1. Intentar leer el CSV si ya existe en el disco
    if os.path.exists(CSV_CACHE):
        try:
            df_cache = pd.read_csv(CSV_CACHE)

            # VALIDACIÓN CLAVE: Verificamos si el set de estaciones cambió o si cambió el número de clústers
            mismo_numero_estaciones = len(df_cache) == len(
                df_coordenadas_actuales
            )
            mismos_ids = set(df_cache["station_id"]) == set(
                df_coordenadas_actuales["station_id"]
            )
            mismo_n_clusters = df_cache["cluster_id"].nunique() == n_clusters

            if (
                mismo_numero_estaciones
                and mismos_ids
                and mismo_n_clusters
            ):
                # Si todo coincide, usamos el CSV y evitamos el K-Means
                df_coordenadas = df_cache
                recalcular = False
        except Exception:
            # Si el CSV está corrupto por alguna razón, forzamos el recálculo
            recalcular = True

    # 2. Si no existe el CSV o los datos cambiaron, ejecutamos K-Means
    if recalcular:
        df_coordenadas = df_coordenadas_actuales

        X = df_coordenadas[["lat", "lon"]]
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        df_coordenadas["cluster_id"] = kmeans.fit_predict(X)

        # Guardamos en disco para las próximas ejecuciones
        df_coordenadas.to_csv(CSV_CACHE, index=False)

    # 3. Cruzamos de vuelta con los datos de tráfico dinámicos para sumar las bicicletas
    df_dinamico = pd.merge(
        df_limpio,
        df_coordenadas[["station_id", "cluster_id"]],
        on="station_id",
        how="left",
    )

    # Agregamos los datos para el mapa de calor
    resumen_clusters = (
        df_dinamico.groupby("cluster_id")
        .agg(
            lat_centro=("lat", "mean"),
            lon_centro=("lon", "mean"),
            total_bicis_disponibles=("num_bikes_available", "sum"),
            total_estaciones=("station_id", "nunique"),
        )
        .reset_index()
    )

    return df_dinamico, resumen_clusters

def generar_mapa_clusters(df_estaciones_cluster, resumen_clusters):
    fig, ax = plt.subplots(figsize=(8, 7))
    
    # Estaciones individuales de fondo de forma sutil
    ax.scatter(df_estaciones_cluster['lon'], df_estaciones_cluster['lat'], c='gray', alpha=0.15, s=8)
    
    # Clusters con tamaño según su cantidad de estaciones e intensidad según sus bicicletas disponibles
    sc = ax.scatter(
        resumen_clusters['lon_centro'], 
        resumen_clusters['lat_centro'],
        c=resumen_clusters['total_bicis_disponibles'],
        cmap='YlOrRd', # De amarillo (pocas) a rojo oscuro (muchas)
        s=resumen_clusters['total_estaciones'] * 120, 
        alpha=0.85, 
        edgecolors='black', 
        linewidth=1
    )
    
    ax.set_xlabel("Longitud", fontsize=9)
    ax.set_ylabel("Latitud", fontsize=9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(True, linestyle='--', alpha=0.3)
    
    cbar = plt.colorbar(sc, ax=ax)
    cbar.set_label("Bicicletas Disponibles en la Zona", fontsize=10)
    plt.tight_layout()
    return fig