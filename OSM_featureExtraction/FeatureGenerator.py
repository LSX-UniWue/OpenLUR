import argparse
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from OSM_featureExtraction import OSMRequestor
from utils.wgs84_ch1903 import *
import pyarrow as pa
import pyarrow.csv as pacsv
import time
import os
import json

class FeatureGenerator:

    def __init__(self, dbname, filename=None, outpath=None, config_file=None, db_host="172.18.0.2", db_port="5432"):
        self.dbname = dbname
        self.filename = dbname + ".csv" if filename is None else filename
        self.outpath = "" if outpath is None else outpath
        self.featuremethods = [self.getStandardFeatures]
        self.data = []
        self.db_host = db_host
        self.db_port = db_port
        self.config_file = config_file
        
        # Track performance metrics
        self.performance_metrics = {
            'feature_extraction_time': 0,
            'total_points_processed': 0,
            'points_per_second': 0
        }

    def generateMap(self, latmin, latmax, lonmin, lonmax, granularity=0.01):
        """Generate grid points based on the specified granularity."""
        print(f"Generating map grid points with granularity {granularity}...")
        self.data = [
            [lat, lon]
            for lat in np.arange(latmin, latmax, granularity)
            for lon in np.arange(lonmin, lonmax, granularity)
        ]
        print(f"Generated {len(self.data)} grid points")

    def set_data_from_pandas(self, df, lon="longitude", lat="latitude", value="value"):
        """Set data from a Pandas DataFrame."""
        self.data = list(df[[lat, lon, value]].values)
        print(f"Loaded {len(self.data)} points from DataFrame")

    def preproc_landuse_features_parallel(self, n_workers=1):
        """Parallelized feature preprocessing with performance tracking."""
        print(f"Starting parallel feature extraction with {n_workers} workers...")
        
        start_time = time.time()
        
        # For better performance with joblib, batch the data
        batch_size = max(1, len(self.data) // (n_workers * 10))  # Aim for 10 batches per worker
        batches = [self.data[i:i + batch_size] for i in range(0, len(self.data), batch_size)]
        
        print(f"Processing {len(batches)} batches of approximately {batch_size} points each")
        
        # Process batches in parallel
        processed_batches = Parallel(n_jobs=n_workers, verbose=10)(
            delayed(self._process_batch)(batch) for batch in batches)
        
        # Flatten results
        data_new = [item for sublist in processed_batches for item in sublist]
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Update performance metrics
        self.performance_metrics['feature_extraction_time'] = processing_time
        self.performance_metrics['total_points_processed'] = len(self.data)
        self.performance_metrics['points_per_second'] = len(self.data) / processing_time
        
        print(f"Feature extraction completed in {processing_time:.2f} seconds")
        print(f"Processed {len(self.data)} points at {self.performance_metrics['points_per_second']:.2f} points/second")
        
        self.data_with_features = pd.DataFrame(data_new)
        return data_new

    def _process_batch(self, batch):
        """Process a batch of points."""
        return [self.preproc_single(row) for row in batch]

    def preproc_single(self, row):
        """Preprocess a single row."""
        lat, lon = row[0], row[1]
        target = 0 if len(row) == 2 else row[2]
        row_new = {"latitude": lat, "longitude": lon, "target": target}
        for method in self.featuremethods:
            row_new.update(method(lat, lon))
        return row_new

    def getStandardFeatures(self, lat, lon):
        """Fetch standard features for given coordinates."""
        requestor = OSMRequestor.Requestor(self.dbname, self.db_host, self.db_port, self.config_file)
        features = requestor.create_features(lon, lat)
        requestor.close()  # Close connection to avoid resource leaks
        return features

    def saveFeatures(self):
        """Save features to a CSV file using PyArrow for better performance."""
        outfile = f"{self.outpath}{self.filename[:-4]}_mapfeatures.csv"
        print(f"Saving features to {outfile}...")
        
        # Convert to PyArrow table and write to CSV
        table = pa.Table.from_pandas(self.data_with_features)
        pacsv.write_csv(table, outfile)
        
        print("File saved successfully using PyArrow.")
        print(f"Performance summary:")
        print(f"  - Total time: {self.performance_metrics['feature_extraction_time']:.2f} seconds")
        print(f"  - Points processed: {self.performance_metrics['total_points_processed']}")
        print(f"  - Processing rate: {self.performance_metrics['points_per_second']:.2f} points/second")
        
        return outfile

    def add_featuremethod(self, featuremethod):
        """Add custom feature extraction methods."""
        self.featuremethods.append(featuremethod)


def main(database, file, n_workers, granularity=0.001, config_file=None, db_host="172.18.0.2", db_port="5432"):
    print(f"Processing file: {file} for database: {database}")
    fg = FeatureGenerator(database, file, None, config_file, db_host, db_port)
    df = pd.read_csv(file)
    latmin, latmax = df["latitude"].min(), df["latitude"].max()
    lonmin, lonmax = df["longitude"].min(), df["longitude"].max()

    # Generate map grid
    fg.generateMap(latmin, latmax, lonmin, lonmax, granularity=granularity)

    # Perform feature extraction
    fg.preproc_landuse_features_parallel(n_workers)

    # Save features
    fg.saveFeatures()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("database", help="Choose database you previously made", type=str)
    parser.add_argument("file", help="File to build features for", type=str)
    parser.add_argument("-n", "--nWorkers", help="Number of parallel processes", type=int, default=1)
    parser.add_argument("-g", "--granularity", help="Granularity for grid generation", type=float, default=0.001)
    parser.add_argument("-c", "--config", help="Path to JSON configuration file for queries", type=str, default=None)
    parser.add_argument("--db-host", help="Database host IP address", type=str, default="172.18.0.2")
    parser.add_argument("--db-port", help="Database port", type=str, default="5432")

    args = parser.parse_args()
    main(args.database, args.file, args.nWorkers, args.granularity, args.config, args.db_host, args.db_port)