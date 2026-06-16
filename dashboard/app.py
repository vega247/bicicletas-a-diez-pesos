import streamlit as st
import pandas as pd

# Importar tus funciones desde tus módulos modificados
from database import consultar_ocupacion_estaciones, consultar_distancias_extremas
from graficas import promedio_bicis, generar_grafica_barras, agrupar_estaciones_por_cercania, generar_mapa_clusters

# --- CONFIGURACIÓN DE LA INTERFAZ ---
st.set_page_config(page_title="Dashboard Ecobici", layout="wide", page_icon="🚲")

st.title("🚲 Dashboard de Analítica Urbana: Ecobici")
st.markdown("Plataforma interactiva para el monitoreo de disponibilidad física y proximidad de estaciones.")
st.write("---")

# --- CONTROLADORES DE LA BARRA LATERAL ---
st.sidebar.header("⚙️ Configuración del Análisis")

# Carga inicial de datos desde PostgreSQL
df_estaciones = consultar_ocupacion_estaciones()

if df_estaciones is not None:
    # 1. Aseguramos que la columna sea de tipo datetime
    df_estaciones["last_reported"] = pd.to_datetime(
        df_estaciones["last_reported"]
    )

    # 2. Ordenamos por fecha de la más reciente a la más antigua
    df_estaciones_ordenado = df_estaciones.sort_values(
        by="last_reported", ascending=False
    )

    # 3. Nos quedamos con el primer registro de cada estación (que será el más nuevo)
    df_estaciones_ultima_hora = df_estaciones_ordenado.drop_duplicates(
        subset="station_id", keep="first"
    )
    # Selector de horas para filtrar las gráficas temporales
    hora_inicio, hora_fin = st.sidebar.slider(
        "Filtro de Horario (Gráfica de barras):",
        min_value=0, max_value=23, value=(6, 22)
    )
    
    # Selector del número de clusters para el mapa espacial
    # n_zonas = st.sidebar.slider(
    #     "Número de Clusters Geoespaciales:",
    #     min_value=10, max_value=40, value=25
    # )
    
    # --- ORGANIZACIÓN POR PESTAÑAS (TABS) ---
    tab_disponibilidad, tab_distancias = st.tabs(["📊 Disponibilidad y Cobertura", "📏 Análisis de Proximidad"])
    
    with tab_disponibilidad:
        # 1. Fila de KPIs Informativos
        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1:
            st.metric("Total de Bicicletas Disponibles", f"{int(df_estaciones_ultima_hora['num_bikes_available'].sum()):,}")
        with kpi2:
            st.metric("Estaciones Totales Activas", f"{df_estaciones['station_id'].nunique()}")
        with kpi3:
            st.metric("Espacios Disponibles (Docks)", f"{int(df_estaciones_ultima_hora['num_docks_available'].sum()):,}")
            
        st.write("---")
        
        # 2. Distribución de Gráfica y Mapa lado a lado
        col_izq, col_der = st.columns([1, 1.2])
        
        with col_izq:
            st.subheader("Disponibilidad Promedio por Día")
            st.caption(f"Filtrado en el rango seleccionado de las {hora_inicio:02d}:00 a las {hora_fin:02d}:00 hrs.")
            
            # Procesamiento temporal con Pandas
            df_fechas = promedio_bicis(df_estaciones, agrupacion=['station_id', 'dia', 'hora'])
            df_grafica = df_fechas[
                (df_fechas['hora'].astype(int) >= hora_inicio) & 
                (df_fechas['hora'].astype(int) <= hora_fin)
            ]
            
            # Generar y pintar la figura de Matplotlib
            fig_barras = generar_grafica_barras(df_grafica)
            st.pyplot(fig_barras)
            
        with col_der:
            st.subheader("Mapa de Macro-Zonas por Demanda")
            st.caption(f"Estaciones consolidadas algoritmicamente en 25 regiones urbanas.")
            
            # Ejecutar agrupamiento por K-Means y pintar mapa de calor espacial
            df_cluster, resumen_clusters = agrupar_estaciones_por_cercania(df_estaciones, n_clusters=25)
            fig_mapa = generar_mapa_clusters(df_cluster, resumen_clusters)
            st.pyplot(fig_mapa)

    with tab_distancias:
        st.subheader("Matriz de Distancias Extremas Geográficas")
        st.markdown("Consulta procesada nativamente mediante indexación espacial en **PostGIS**.")
        
        df_distancias = consultar_distancias_extremas()
        
        if df_distancias is not None:
            # Buscador en tiempo real por cadena de texto
            criterio = st.text_input("🔍 Filtrar estación de origen por nombre:")
            if criterio:
                df_mostrar = df_distancias[df_distancias['origen_nombre'].str.contains(criterio, case=False)]
            else:
                df_mostrar = df_distancias
                
            st.dataframe(
                df_mostrar,
                column_config={
                    "origen_id": "ID Origen",
                    "origen_nombre": "Estación de Origen",
                    "estacion_mas_cercana": "📍 Vecino Más Cercano",
                    "distancia_min_metros": "Distancia Mínima (m)",
                    "estacion_mas_lejana": "🗺️ Vecino Más Lejano",
                    "distancia_max_metros": "Distancia Máxima (m)"
                },
                hide_index=True,
                use_container_width=True
            )
else:
    st.error("No se pudo establecer la conexión inicial con la base de datos PostgreSQL.")