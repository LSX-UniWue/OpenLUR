# OpenLUR Query Configuration Guide

This guide explains how to customize queries in OpenLUR using configuration files. By modifying these configurations, you can control which features are extracted, at what distances, and which spatial queries are run.

## Configuration File Basics

OpenLUR uses a JSON configuration file to define query parameters. You can specify this file using the `-c` or `--config` command-line option:

```bash
python osm_feature_generation.py map bremen_db 53.02 53.20 8.56 8.96 -p 16 -c query_config.json
```

If no configuration file is provided, OpenLUR will use default settings.

## Creating a Configuration File

Create a file named `query_config.json` with the following structure:

```json
{
    "polygon_ranges": [50, 100, 200, 400, 800, 1600, 3000],
    "road_ranges": [50, 100, 200, 400, 800, 1500],
    "landuse_types": [
        "commercial", 
        "industrial", 
        "residential", 
        "forest", 
        "meadow", 
        "orchard", 
        "farmland", 
        "vineyard", 
        "grass"
    ],
    "natural_types": [
        "grassland", 
        "scrub", 
        "tree", 
        "tree_row", 
        "wood"
    ],
    "distance_queries": {
        "point": [
            {"key": "highway", "value": "traffic_signals"}
        ],
        "line": [
            {"key": "highway", "value": "motorway"},
            {"key": "highway", "value": "primary"}
        ],
        "polygon": [
            {"key": "landuse", "value": "industrial"}
        ]
    }
}
```

## Configuration Elements

### 1. `polygon_ranges`

Defines the buffer distances (in meters) used for area-based polygon queries like land use.

```json
"polygon_ranges": [50, 100, 200, 400, 800, 1600, 3000]
```

**Performance Impact:** More ranges = more precise measurements but slower processing.

### 2. `road_ranges`

Defines the buffer distances (in meters) used for road length queries.

```json
"road_ranges": [50, 100, 200, 400, 800, 1500]
```

**Performance Impact:** More ranges = more precise measurements but slower processing.

### 3. `landuse_types`

List of land use types to extract from OpenStreetMap. Each type will generate multiple feature columns (one per distance in `polygon_ranges`).

```json
"landuse_types": [
    "commercial", 
    "industrial", 
    "residential", 
    "forest", 
    "meadow", 
    "orchard", 
    "farmland", 
    "vineyard", 
    "grass"
]
```

**Performance Impact:** More land use types = more comprehensive data but slower processing.

### 4. `natural_types`

List of natural feature types to extract from OpenStreetMap.

```json
"natural_types": [
    "grassland", 
    "scrub", 
    "tree", 
    "tree_row", 
    "wood"
]
```

**Performance Impact:** More natural types = more comprehensive data but slower processing.

### 5. `distance_queries`

Defines minimum distance queries to various features.

```json
"distance_queries": {
    "point": [
        {"key": "highway", "value": "traffic_signals"}
    ],
    "line": [
        {"key": "highway", "value": "motorway"},
        {"key": "highway", "value": "primary"}
    ],
    "polygon": [
        {"key": "landuse", "value": "industrial"}
    ]
}
```

**Performance Impact:** More distance queries = more comprehensive data but slower processing.

## Optimization Examples

### Minimal Configuration (Fastest)

```json
{
    "polygon_ranges": [50, 500, 3000],
    "road_ranges": [50, 500, 1500],
    "landuse_types": [
        "commercial", 
        "industrial", 
        "residential"
    ],
    "natural_types": [
        "wood"
    ],
    "distance_queries": {
        "point": [],
        "line": [
            {"key": "highway", "value": "motorway"}
        ],
        "polygon": []
    }
}
```

### Comprehensive Configuration (Most detailed but slower)

```json
{
    "polygon_ranges": [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000, 2500, 3000],
    "road_ranges": [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1500],
    "landuse_types": [
        "commercial", "industrial", "residential", "forest", 
        "meadow", "orchard", "farmland", "vineyard", "grass",
        "retail", "recreation_ground", "allotments", "cemetery"
    ],
    "natural_types": [
        "grassland", "scrub", "tree", "tree_row", "wood",
        "water", "wetland", "beach", "heath", "sand"
    ],
    "distance_queries": {
        "point": [
            {"key": "highway", "value": "traffic_signals"},
            {"key": "highway", "value": "bus_stop"},
            {"key": "railway", "value": "station"}
        ],
        "line": [
            {"key": "highway", "value": "motorway"},
            {"key": "highway", "value": "primary"},
            {"key": "highway", "value": "secondary"},
            {"key": "railway", "value": "rail"}
        ],
        "polygon": [
            {"key": "landuse", "value": "industrial"},
            {"key": "amenity", "value": "school"},
            {"key": "amenity", "value": "hospital"}
        ]
    }
}
```

## Custom OpenStreetMap Tags

You can query any OpenStreetMap tag. Common tags include:

### Land Use Tags
- `residential`, `industrial`, `commercial`, `retail`
- `forest`, `farmland`, `meadow`, `orchard`, `vineyard`, `grass`
- `recreation_ground`, `cemetery`, `allotments`

### Highway Types
- `motorway`, `trunk`, `primary`, `secondary`, `tertiary`
- `residential`, `service`, `footway`, `cycleway`, `path`

### Natural Features
- `water`, `wood`, `scrub`, `heath`, `grassland`, `wetland`
- `beach`, `sand`, `bare_rock`

### Amenities
- `school`, `university`, `hospital`, `kindergarten`
- `restaurant`, `cafe`, `fast_food`, `pub`, `bar`

## Troubleshooting

### Database Query Performance
- Start with fewer ranges and feature types
- Use the profiling tools to measure query performance
- Consider increasing the PostgreSQL work_mem setting for better spatial query performance

### Memory Usage
- If you encounter memory issues, reduce the number of feature types
- Consider processing your region in smaller chunks

### CPU Usage
- Adjust the `-p` parameter to match your system's CPU capabilities
- Too many workers can sometimes slow processing due to context switching

## Advanced Usage

### Create a Configuration for Pollution Modeling

```json
{
    "polygon_ranges": [50, 100, 250, 500, 1000, 2000, 3000],
    "road_ranges": [50, 100, 250, 500, 1000, 1500],
    "landuse_types": [
        "industrial", 
        "commercial", 
        "residential"
    ],
    "natural_types": [
        "wood", 
        "water"
    ],
    "distance_queries": {
        "point": [],
        "line": [
            {"key": "highway", "value": "motorway"},
            {"key": "highway", "value": "primary"},
            {"key": "highway", "value": "secondary"}
        ],
        "polygon": [
            {"key": "landuse", "value": "industrial"}
        ]
    }
}
```

### Create a Configuration for Green Space Analysis

```json
{
    "polygon_ranges": [50, 100, 250, 500, 1000, 2000, 3000],
    "road_ranges": [50, 100, 250, 500],
    "landuse_types": [
        "forest", 
        "meadow", 
        "orchard", 
        "farmland", 
        "grass",
        "recreation_ground", 
        "allotments", 
        "cemetery"
    ],
    "natural_types": [
        "grassland", 
        "scrub", 
        "tree", 
        "tree_row", 
        "wood",
        "water", 
        "wetland", 
        "beach", 
        "heath"
    ],
    "distance_queries": {
        "point": [],
        "line": [],
        "polygon": [
            {"key": "leisure", "value": "park"},
            {"key": "leisure", "value": "garden"}
        ]
    }
}
```
