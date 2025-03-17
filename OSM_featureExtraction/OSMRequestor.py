import psycopg2
from operator import add
import json
import os
import threading
from OSM_featureExtraction.pgpool import PgConnectionPool

# Global configuration singleton
_GLOBAL_CONFIG = None
_CONFIG_LOADED_FROM = None

def load_config(config_file=None):
    """Load configuration from file and cache it globally"""
    global _GLOBAL_CONFIG, _CONFIG_LOADED_FROM
    
    # Default configuration
    default_config = {
        "polygon_ranges": [50, 100, 200, 400, 800, 1600, 3000],
        "road_ranges": [50, 100, 200, 400, 800, 1500],
        "landuse_types": [
            "commercial", "industrial", "residential", "forest", 
            "meadow", "orchard", "farmland", "vineyard", "grass"
        ],
        "natural_types": ["grassland", "scrub", "tree", "tree_row", "wood"],
        "distance_queries": {
            "point": [{"key": "highway", "value": "traffic_signals"}],
            "line": [
                {"key": "highway", "value": "motorway"},
                {"key": "highway", "value": "primary"}
            ],
            "polygon": [{"key": "landuse", "value": "industrial"}]
        }
    }
    
    # If we already loaded this config file, return the cached version
    if _GLOBAL_CONFIG is not None and _CONFIG_LOADED_FROM == config_file:
        return _GLOBAL_CONFIG
    
    # Start with default config
    config = default_config
    
    # Load custom configuration if provided
    if config_file and os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                custom_config = json.load(f)
                # Update default config with custom settings
                for key, value in custom_config.items():
                    config[key] = value
            print(f"Loaded custom query configuration from {config_file}")
        except Exception as e:
            print(f"Error loading configuration file: {e}")
            print("Using default configuration")
    
    # Cache the config
    _GLOBAL_CONFIG = config
    _CONFIG_LOADED_FROM = config_file
    
    return config


class Requestor:

    def __init__(self, database, db_host="172.18.0.2", db_port="5432", config_file=None):
        # Initialize connection pool (creates new or gets existing)
        self.pool = PgConnectionPool.get_pool(
            dbname=database, 
            host=db_host, 
            port=db_port,
            min_conn=5,
            max_conn=min(32, os.cpu_count() * 2)
        )
        
        # Get connection from pool
        self.conn = self.pool.get_connection()
        self.cur = self.conn.cursor()
        
        # Track thread ID
        self.thread_id = threading.get_ident()
        
        # Load configuration (will use cached version if available)
        self.config = load_config(config_file)

    def query_osm_polygone(self, lon_query, lat_query, radii, key, value):
        query = "SELECT "
        basic_query = "sum(ST_Area(ST_Intersection(geo, ST_Buffer(geography(ST_SetSRID(ST_MakePoint(%s, %s),4326)), %s))))"
        additional_values = []
        for radius in radii:
            query = query + basic_query + " , "
            additional_values.append(lon_query)
            additional_values.append(lat_query)
            additional_values.append(radius)

        query = query[
            :-2] + "FROM planet_osm_polygon WHERE ST_DWithin(geo, geography(ST_MakePoint(%s, %s)), %s) AND \"{}\" = %s;".format(key)

        additional_values.append(lon_query)
        additional_values.append(lat_query)
        additional_values.append(max(radii))
        additional_values.append(value)
        
        self.cur.execute(query, tuple(additional_values))
        return {"{}_{}m".format(value, d): (0 if v is None else v) for d, v in zip(radii, self.cur.fetchone())}

    def query_osm_line(self, lon_query, lat_query, radius, key, value):
        self.cur.execute(
            "SELECT sum(ST_Length(ST_Intersection(geo, ST_Buffer(geography(ST_SetSRID(ST_MakePoint(%s, %s),4326)), %s)))) FROM planet_osm_line WHERE ST_DWithin(geo, geography(ST_MakePoint(%s, %s)), %s) AND {} = %s;".format(
                key),
            (lon_query, lat_query, radius, lon_query, lat_query, radius, value))
        return {"{}_{}m".format(value, radius): self.cur.fetchone()[0]}

    def query_osm_highway(self, lon_query, lat_query, radii):
        query = """
        SELECT highway,
        """
        
        # Build dynamic part of query for each radius
        for i, radius in enumerate(radii):
            query += f"""
            sum(CASE 
                WHEN ST_DWithin(geo, geography(ST_SetSRID(ST_MakePoint(%s, %s),4326)), {radius})
                THEN ST_Length(ST_Intersection(geo, ST_Buffer(geography(ST_SetSRID(ST_MakePoint(%s, %s),4326)), {radius})))
                ELSE 0
            END) as length_{radius}"""
            
            if i < len(radii) - 1:
                query += ","
            
        query += """
        FROM planet_osm_line
        WHERE ST_DWithin(geo, geography(ST_MakePoint(%s, %s)), %s)
        AND highway IN ('motorway', 'trunk', 'primary', 'secondary')
        GROUP BY highway;
        """
        
        # Prepare parameters
        params = []
        for _ in radii:
            params.extend([lon_query, lat_query, lon_query, lat_query])
        params.extend([lon_query, lat_query, max(radii)])
        
        self.cur.execute(query, tuple(params))
        
        # Process results
        results = self.cur.fetchall()
        
        # Initialize result dictionaries
        big_road_results = {"bigRoad_{}m".format(r): 0 for r in radii}
        
        # Process each row (highway type)
        for row in results:
            highway_type = row[0]
            
            # For each radius, add the length to the appropriate category
            for i, radius in enumerate(radii):
                length = row[i+1] if row[i+1] is not None else 0
                big_road_results[f"bigRoad_{radius}m"] += length
                
        return big_road_results

    def query_osm_local_road(self, lon_query, lat_query, radii):
        query = """
        SELECT highway,
        """
        
        # Build dynamic part of query for each radius
        for i, radius in enumerate(radii):
            query += f"""
            sum(CASE 
                WHEN ST_DWithin(geo, geography(ST_SetSRID(ST_MakePoint(%s, %s),4326)), {radius})
                THEN ST_Length(ST_Intersection(geo, ST_Buffer(geography(ST_SetSRID(ST_MakePoint(%s, %s),4326)), {radius})))
                ELSE 0
            END) as length_{radius}"""
            
            if i < len(radii) - 1:
                query += ","
            
        query += """
        FROM planet_osm_line
        WHERE ST_DWithin(geo, geography(ST_MakePoint(%s, %s)), %s)
        AND highway IN ('tertiary', 'residential')
        GROUP BY highway;
        """
        
        # Prepare parameters
        params = []
        for _ in radii:
            params.extend([lon_query, lat_query, lon_query, lat_query])
        params.extend([lon_query, lat_query, max(radii)])
        
        self.cur.execute(query, tuple(params))
        
        # Process results
        results = self.cur.fetchall()
        
        # Initialize result dictionaries
        small_road_results = {"smallRoad_{}m".format(r): 0 for r in radii}
        
        # Process each row (highway type)
        for row in results:
            highway_type = row[0]
            
            # For each radius, add the length to the appropriate category
            for i, radius in enumerate(radii):
                length = row[i+1] if row[i+1] is not None else 0
                small_road_results[f"smallRoad_{radius}m"] += length
                
        return small_road_results

    def query_osm_line_distance(self, lon_query, lat_query, key, value):
        query = "SELECT min(ST_Distance(geo, geography(ST_SetSRID(ST_MakePoint(%s,%s),4326)))) FROM planet_osm_line WHERE {} = %s;".format(
            key)
        self.cur.execute(query, (lon_query, lat_query, value))
        return {value: self.cur.fetchone()[0]}

    def query_osm_point_distance(self, lon_query, lat_query, key, value):
        query = "SELECT min(ST_Distance(geo, geography(ST_SetSRID(ST_MakePoint(%s,%s),4326)))) FROM planet_osm_point WHERE {} = %s;".format(
            key)
        self.cur.execute(query, (lon_query, lat_query, value))
        return {value: self.cur.fetchone()[0]}

    def query_osm_polygon_distance(self, lon_query, lat_query, key, value):
        query = "SELECT min(ST_Distance(geo, geography(ST_SetSRID(ST_MakePoint(%s,%s),4326)))) FROM planet_osm_polygon WHERE {} = %s;".format(
            key)
        self.cur.execute(query, (lon_query, lat_query, value))
        return {value: self.cur.fetchone()[0]}

    def create_features(self, lon, lat):
        features = {}
        try:
            # Use configured ranges
            polygon_ranges = self.config["polygon_ranges"]
            road_ranges = self.config["road_ranges"]
            
            # Land use polygon queries
            for land_type in self.config["landuse_types"]:
                features.update(self.query_osm_polygone(lon, lat, polygon_ranges, "landuse", land_type))
            
            # Natural polygon queries
            for natural_type in self.config["natural_types"]:
                features.update(self.query_osm_polygone(lon, lat, polygon_ranges, "natural", natural_type))
            
            # Road queries
            features.update(self.query_osm_highway(lon, lat, road_ranges))
            features.update(self.query_osm_local_road(lon, lat, road_ranges))
            
            # Distance queries
            for point_query in self.config["distance_queries"]["point"]:
                features.update(self.query_osm_point_distance(lon, lat, point_query["key"], point_query["value"]))
                
            for line_query in self.config["distance_queries"]["line"]:
                features.update(self.query_osm_line_distance(lon, lat, line_query["key"], line_query["value"]))
                
            for poly_query in self.config["distance_queries"]["polygon"]:
                features.update(self.query_osm_polygon_distance(lon, lat, poly_query["key"], poly_query["value"]))
            
        except Exception as e:
            print(e)
            print("error at point {}, {}".format(lat, lon))
            return {}
        return features

    def close(self):
        """Return connection to the pool instead of closing it"""
        if hasattr(self, 'cur') and self.cur:
            self.cur.close()
            self.cur = None
            
        # Return connection to pool
        if hasattr(self, 'pool') and self.pool:
            self.pool.return_connection(self.thread_id)