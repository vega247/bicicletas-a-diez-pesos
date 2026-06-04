import requests
import psycopg2
from datetime import datetime
import time
from prefect import flow, task, get_run_logger

# Parámetros globales de conexión
CONN_PARAMS = {
    "host": "localhost",
    "database": "ecobici_db",
    "user": "alejandro_user",
    "password": "ecobici_password",
    "port": 5432
}

@task(retries=3, retry_delay_seconds=60, description="Descarga el estado de las estaciones desde la API de Lyft")
def extraer_datos_api():
    logger = get_run_logger()
    url_status = "https://gbfs.mex.lyftbikes.com/gbfs/es/station_status.json"
    
    logger.info("Iniciando la descarga de datos desde la API de Ecobici...")
    response = requests.get(url_status)
    response.raise_for_status()
    
    data = response.json()
    return data['data']['stations']

@task(description="Limpia e inserta los datos de estatus en la tabla fact_estatus_trafico")
def cargar_datos_postgres(estaciones):
    logger = get_run_logger()
    
    try:
        conn = psycopg2.connect(**CONN_PARAMS)
        cursor = conn.cursor()
        
        query_insert = """
            INSERT INTO fact_estatus_trafico 
            (station_id, num_bikes_available, num_docks_available, is_renting, last_reported)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (station_id, last_reported) DO NOTHING;
        """
        
        registros_insertados = 0
        for est in estaciones:
            fecha_reporte = datetime.fromtimestamp(est['last_reported'])
            valores = (
                est['station_id'],
                est['num_bikes_available'],
                est['num_docks_available'],
                est['is_renting'] == 1,
                fecha_reporte
            )
            cursor.execute(query_insert, valores)
            registros_insertados += 1
            
        conn.commit()
        logger.info(f"Ingesta exitosa: {registros_insertados} estados de estaciones guardados.")
        
    except Exception as e:
        logger.error(f"Error al insertar datos en Postgres: {e}")
        if 'conn' in locals() and conn:
            conn.rollback()
        raise e  # Lanzamos el error para que Prefect sepa que la tarea falló
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'conn' in locals() and conn:
            conn.close()

@flow(name="ETL_Ecobici_Tiempo_Real")
def ecobici_pipeline():
    # 1. Extraer
    estaciones = extraer_datos_api()
    # 2. Cargar
    cargar_datos_postgres(estaciones)

if __name__ == "__main__":
    # Ejecución manual inmediata para probar el flujo
    ecobici_pipeline.serve(
	name="ingesta-ecobici-intervalo",
	interval=600,
	description="Pipeline automatizado que recolecta el estatus de Ecobici cada 10 minutos"
    )
