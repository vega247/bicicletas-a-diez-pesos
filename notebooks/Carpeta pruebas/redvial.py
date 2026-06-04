import osmnx as ox
import geopandas as gpd

# Configuración
ox.settings.use_cache = True
ox.settings.log_console = True

# Nombre del lugar
place_name = "Ciudad de México, México"

# Descargar red vial para vehículos
G = ox.graph_from_place(
    place_name,
    network_type="drive"
)

# Convertir a GeoDataFrames
nodes, edges = ox.graph_to_gdfs(G)

print(f"Nodos: {len(nodes):,}")
print(f"Segmentos viales: {len(edges):,}")

# Guardar como GeoPackage
edges.to_file("red_vial_cdmx.gpkg", layer="vialidades", driver="GPKG")

# Guardar como Shapefile (opcional)
edges.to_file("red_vial_cdmx.shp")

print("Archivo guardado correctamente.")