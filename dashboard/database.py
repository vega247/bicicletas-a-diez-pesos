from sqlalchemy import create_engine, text
import pandas as pd
import streamlit as st

@st.cache_data(ttl=600)
def consultar_ocupacion_estaciones():
    DATABASE_URI = "postgresql://alejandro_user:ecobici_password@localhost:5432/ecobici_db"
    
    query = """
        SELECT *
        FROM (
            SELECT 
                s.station_id,
                s.num_bikes_available,
                s.num_docks_available,
                s.last_reported,
                d.geom,
                d.capacity,
                d."name",
                ST_Y(d.geom) AS lat,
                ST_X(d.geom) AS lon
            FROM fact_estatus_trafico AS s
            LEFT JOIN dim_estaciones AS d
            ON d.station_id = s.station_id
        ) AS sub
        WHERE capacity > 0
            AND "name" NOT ILIKE '%temporal%'
    """
    try:
        engine = create_engine(DATABASE_URI)
        with engine.connect() as connection:
            df_estaciones = pd.read_sql_query(text(query), connection)
        return df_estaciones
    except Exception as e:
        print(f"Error al consultar la base de datos con SQLAlchemy: {e}")
        return None

@st.cache_data(ttl=3600)
def consultar_distancias_extremas():
    DATABASE_URI = "postgresql://alejandro_user:ecobici_password@localhost:5432/ecobici_db"
    
    query = """
        WITH matriz_distancias AS (
            SELECT 
                a.station_id AS origen_id,
                a.name AS origen_nombre,
                b.station_id AS destino_id,
                b.name AS destino_nombre,
                -- Calculamos la distancia en metros entre la estación A y la B
                ST_Distance(a.geom::geography, b.geom::geography) AS distancia_metros
            FROM (SELECT * FROM dim_estaciones WHERE capacity > 0 AND "name" NOT ILIKE '%temporal%') AS a
            CROSS JOIN (SELECT * FROM dim_estaciones WHERE capacity > 0 AND "name" NOT ILIKE '%temporal%') AS b
            -- Evitamos calcular la distancia de una estación consigo misma
            WHERE a.station_id <> b.station_id
        ),
        rankings AS (
            SELECT 
                origen_id,
                origen_nombre,
                destino_id,
                destino_nombre,
                distancia_metros,
                -- Evaluamos cuáles son las más cercanas y más lejanas
                ROW_NUMBER() OVER(PARTITION BY origen_id ORDER BY distancia_metros ASC) AS rank_cercana,
                ROW_NUMBER() OVER(PARTITION BY origen_id ORDER BY distancia_metros DESC) AS rank_lejana
            FROM matriz_distancias
        )
        SELECT 
            r1.origen_id,
            r1.origen_nombre,
            -- Datos de la estación más cercana
            r1.destino_nombre AS estacion_mas_cercana,
            ROUND(r1.distancia_metros::numeric, 2) AS distancia_min_metros,
            -- Datos de la estación más lejana
            r2.destino_nombre AS estacion_mas_lejana,
            ROUND(r2.distancia_metros::numeric, 2) AS distancia_max_metros
        FROM rankings r1
        JOIN rankings r2 ON r1.origen_id = r2.origen_id
        WHERE r1.rank_cercana = 1 AND r2.rank_lejana = 1;
    """
    try:
        engine = create_engine(DATABASE_URI)
        with engine.connect() as connection:
            df_distancia_estaciones = pd.read_sql_query(text(query), connection)
        return df_distancia_estaciones
    except Exception as e:
        print(f"Error al calcular distancias: {e}")
        return None
    
