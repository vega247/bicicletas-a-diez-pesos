-- Habilitar la extensión de datos espaciales (PostGIS)
CREATE EXTENSION IF NOT EXISTS postgis;

-- 1. Tabla Dimensional: Estaciones (Datos Estáticos)
CREATE TABLE IF NOT EXISTS dim_estaciones (
    station_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    capacity INT NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lon DOUBLE PRECISION NOT NULL,
    geom GEOMETRY(Point, 4326) -- Guarda el punto geográfico para consultas espaciales
);

-- 2. Tabla de Hechos: Histórico de Tráfico/Estatus (Datos Dinámicos)
CREATE TABLE IF NOT EXISTS fact_estatus_trafico (
    id_registro SERIAL PRIMARY KEY,
    station_id VARCHAR(50) REFERENCES dim_estaciones(station_id),
    num_bikes_available INT NOT NULL,
    num_docks_available INT NOT NULL,
    is_renting BOOLEAN NOT NULL,
    last_reported TIMESTAMP NOT NULL
);

-- Crear un índice por fecha para acelerar las consultas de series temporales de tu compañero
CREATE INDEX IF NOT EXISTS idx_fecha_reporte ON fact_estatus_trafico(last_reported);

-- Tabla de distancias de grafo entre estaciones
CREATE TABLE IF NOT EXISTS network_graph (
    id SERIAL PRIMARY KEY,
    origin_station_id VARCHAR(50) NOT NULL,
    dest_station_id VARCHAR(50) NOT NULL,
    origin_osmid BIGINT,
    dest_osmid BIGINT,
    distance_m DOUBLE PRECISION NOT NULL,
    geom GEOMETRY(LineString, 4326),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_network_graph_origin_dest ON network_graph(origin_station_id, dest_station_id);