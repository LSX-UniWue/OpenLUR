OpenLUR is a off-the-shelf solution for globally available land use regression for e.g. pollution prediction.

# Changes from Origianl code files
- Use `\"{}\"` instead of {} in OSMRequestor.py, line 23
  
Reason :
Using `\"{}\"` in the query string ensures that the column name is properly quoted and interpreted by the SQL engine, which helps in avoiding syntax errors and ensures compatibility with PostgreSQL's handling of identifiers.
Without the double quotes, if key was a reserved word or contained special characters, it could cause a syntax error or unexpected behavior in the SQL query.
- Change NumPy version from 1.16.2 to 1.21.0

# Requirements
- python3 (3.9.21) with requirements from requirements.txt
- osm2pgsql
- docker (recommended)
- docker-compose (recommended)
  
## Steps to run Project :
### Pre-steps while run
1. Install the requirements from Requirements.txt
2. create a new directory/folder named "OSM-data" in "OpenLUR > OSM_featureExtraction" 
# TODO: do not reccommnend a folder that is also used for code. Recommend data instead
4. Download data in .osm.pbf file from OpenStreetMap (link : https://download.geofabrik.de/) and navigate it to OpenLUR > OSM_featureExtraction > OSM-data

### Feature extraction from OpenStreetMap
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
For Example
```
        python3 osm_feature_generation.py map bremen_db 53.02 53.20 8.56 8.96
```
#TODO: I am getting a database unreachable error. How do I fix this?
```Password is "docker"```

### Using a file file with latitude and longitude values:
        python3 osm_feature_generation.py file <databasename in lowercase (e.g. city name)> <file (csv-file with lat and lon columns)> (-v <value to keep in the output file, optional>)
The file needs to contain at least three columns named latitude, longitude, value. The first two specify the coordinates at which to compute the features and value is the target variable that will be copied to the output file (can be empty or containing 0 if not needed, but will produce errors if its not there).

Additionally the optional arguments -_p_ and -_f_ can be included at the end of the command to specify the number of threads to use (default: 1) and optionally a osm file to use.

- By default it works only on 1 thread/processor/cpu
- Use "-p 16" (if number of processors in your machine = 16), else Use **"-p $(nproc)"** to use maximum number of processors [at the end of command]
  
  ```
        python3 osm_feature_generation.py map <databasename in lowercase (e.g. city name)> <minimum latitude> <maximum latitude> <minimum longitude> <maximum longitude> -p $(nproc)
  ```
If the osm file is not provided, the script will try download it from geofabrik.de (which depending on the status of the osm-geofabrik servers might or might not work).

In this case the command to generate features would be

        python3 osm_feature_generation.py file <databasename in lowercase (e.g. city name)> <file (csv-file with latitude and longitude columns)> -f <path to the osm/osm.pbf file> -p <NUM_THREADS>
Output
The output is a csv file (filename indicated in the command line output) containing lat, lon, value (if specified) and the land usage features.
