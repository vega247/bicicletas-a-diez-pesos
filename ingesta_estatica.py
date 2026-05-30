import requests
import psycopg2

def poblar_estaciones():
    # 1. URL de información estática de Ecobici
    url_info = "https://gbfs.mex.lyftbikes.com/gbfs/es/station_information.json"
    
    # 2. Conexión a la base de datos local en Docker
    # Como el script corre en tu máquina (Host), te conectas a 'localhost' en el puerto 5432
    conn_params = {
        "host": "localhost",
        "database": "ecobici_db",
        "user": "alejandro_user",
        "password": "ecobici_password",
        "port": 5432
    }
    
    try:
        # Descargar datos de la API
        print("Descargando datos de estaciones desde Lyft API...")
        response = requests.get(url_info)
        response.raise_for_status()
        data = response.json()
        estaciones = data['data']['stations']
        
        # Conectar a Postgres
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        
        print(f"Insertando/Actualizando {len(estaciones)} estaciones en la base de datos...")
        
        query_upsert = """
            INSERT INTO dim_estaciones (station_id, name, capacity, lat, lon, geom)
            VALUES (%s, %s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
            ON CONFLICT (station_id) 
            DO UPDATE SET 
                name = EXCLUDED.name,
                capacity = EXCLUDED.capacity,
                lat = EXCLUDED.lat,
                lon = EXCLUDED.lon,
                geom = EXCLUDED.geom;
        """
        
        for est in estaciones:
            # Preparar los valores. Nota cómo duplicamos lon y lat para la función PostGIS
            valores = (
                est['station_id'],
                est['name'],
                est['capacity'],
                est['lat'],
                est['lon'],
                est['lon'], # Para ST_MakePoint(lon, lat)
                est['lat']  # Para ST_MakePoint(lon, lat)
            )
            cursor.execute(query_upsert, valores)
            
        # Confirmar los cambios en la base de datos
        conn.commit()
        print("¡Proceso terminado con éxito! Tabla dim_estaciones poblada.")
        
    except Exception as e:
        print(f"Error durante la ingesta: {e}")
        if 'conn' in locals() and conn:
            conn.rollback()
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    poblar_estaciones()