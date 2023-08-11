OpenLUR is a off-the-shelf solution for globally available land use regression for e.g. pollution prediction.

# Requirements

- python3 with requirements from requirements.txt
- osm2pgsql
- docker (recommended)
- docker-compose (recommended)

# Usage

## Feature extraction from OpenStreetMap

First start docker-container for the PostGIS database: 
```
        docker-compose up -d
```
Alternatively you have to have a postgres database with postgis extension.

The next steps are based upon the application scenario: 

You can extract features either for a grid 
```
        python3 osm_feature_generation.py map <databasename in lowercase (e.g. city name)> <minimum latitude> <maximum latitude> <minimum longitude> <maximum longitude>
```

### Using a file file with latitude and longitude values:
```
        python3 osm_feature_generation.py file <databasename in lowercase (e.g. city name)> <file (csv-file with lat and lon columns)> (-v <value to keep in the output file, optional>)
```
The file needs to contain at least three columns named *latitude*, *longitude*, *value*. The first two specify the coordinates at which to compute the features and value is the target variable that will be copied to the output file (can be empty or containing 0 if not needed, but will produce errors if its not there).

Additionally the optional arguments *-p* and *-f* can be included at the end of the command to specify the number of threads to use (default: 1) and optionally a osm file to use. If the osm file is not provided, the script will try download it from geofabrik.de (which depending on the status of the osm-geofabrik servers might or might not work).

In this case the command to generate features would be
```
        python3 osm_feature_generation.py file <databasename in lowercase (e.g. city name)> <file (csv-file with latitude and longitude columns)> -f <path to the osm/osm.pbf file> -p <NUM_THREADS>
```

### Output
The output is a csv file (filename indicated in the command line output) containing lat, lon, value (if specified) and the land usage features.


## Recreation of paper experiments

(will be available upon published paper)

