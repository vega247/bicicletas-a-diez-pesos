import requests
import psycopg2
from datetime import datetime
import time

def capturar_estatus_tiempo_real():
    url_status = "https://gbfs.mex.lyftbikes.com/gbfs/es/station_status.json"
    
    conn_params = {
        "host": "localhost",
        "database": "ecobici_db",
        "user": "alejandro_user",
        "password": "ecobici_password",
        "port": 5432
    }
    
    try:
        # 1. Descargar el estatus de la API
        response = requests.get(url_status)
        response.raise_for_status()
        data = response.json()
        estaciones = data['data']['stations']
        
        # 2. Conectar a Postgres
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        
        query_insert = """
            INSERT INTO fact_estatus_trafico 
            (station_id, num_bikes_available, num_docks_available, is_renting, last_reported)
            VALUES (%s, %s, %s, %s, %s);
        """
        
        registros_insertados = 0
        for est in estaciones:
            # Convertir el timestamp UNIX que da Lyft a un formato TIMESTAMP de Postgres
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
        print(f"[{datetime.now()}] Ingesta exitosa: {registros_insertados} estados de estaciones guardados.")
        
    except Exception as e:
        print(f"Error durante la ingesta dinámica: {e}")
        if 'conn' in locals() and conn:
            conn.rollback()
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    # De forma temporal para probar tu script localmente antes de usar un orquestador,
    # podemos hacer que corra en un bucle infinito cada 5 minutos (300 segundos)
    print("Iniciando extractor dinámico de Ecobici... Presiona Ctrl+C para detener.")
    while True:
        capturar_estatus_tiempo_real()
        time.sleep(300)