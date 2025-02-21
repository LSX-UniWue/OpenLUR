import argparse
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from OSM_featureExtraction import OSMRequestor
from utils.wgs84_ch1903 import *
import pyarrow as pa
import pyarrow.csv as pacsv

class FeatureGenerator:

    def __init__(self, dbname, filename=None, outpath=None):
        self.dbname = dbname
        self.filename = dbname + ".csv" if filename is None else filename
        self.outpath = "" if outpath is None else outpath
        self.featuremethods = [self.getStandardFeatures]
        self.data = []

    def generateMap(self, latmin, latmax, lonmin, lonmax, granularity=0.01):
        """Generate grid points based on the specified granularity."""
        print("Generating map grid points...")
        self.data = [
            [lat, lon]
            for lat in np.arange(latmin, latmax, granularity)
            for lon in np.arange(lonmin, lonmax, granularity)
        ]

    def set_data_from_pandas(self, df, lon="longitude", lat="latitude", value="value"):
        """Set data from a Pandas DataFrame."""
        self.data = list(df[[lat, lon, value]].values)

    def preproc_landuse_features_parallel(self, n_workers=1):
        """Parallelized feature preprocessing."""
        print(f"Starting parallel feature extraction with {n_workers} workers...")

        data_new = Parallel(n_jobs=n_workers, verbose=10)(
            delayed(self.preproc_single)(row) for row in self.data)
        self.data_with_features = pd.DataFrame(data_new)
        return data_new

#    def preproc_landuse_features(self):
#    # Sequential feature preprocessing using a normal for loop.
#        print("Starting sequential feature extraction...")
#
#        data_new = []
#        total_len = len(self.data)
#
#        for i, row in enumerate(self.data):
#            data_new.append(self.preproc_single(row))
#
#        # Provide progress feedback every 100 rows
#            if i % 100 == 0:
#                print(f"Processed {i}/{total_len} rows ({(i / total_len) * 100:.2f}%)")
#
#        self.data_with_features = pd.DataFrame(data_new)
#        print("Feature extraction completed.")
#        return data_new

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
        requestor = OSMRequestor.Requestor(self.dbname)
        return requestor.create_features(lon, lat)

    def saveFeatures(self):
        """Save features to a CSV file using PyArrow for better performance."""
        outfile = f"{self.outpath}{self.filename[:-4]}_mapfeatures.csv"
        print(f"Saving features to {outfile}...")
        table = pa.Table.from_pandas(self.data_with_features)
        pacsv.write_csv(table, outfile)
        print("File saved successfully using PyArrow.")
        return outfile

    def add_featuremethod(self, featuremethod):
        """Add custom feature extraction methods."""
        self.featuremethods.append(featuremethod)


def main(database, file, n_workers, granularity=0.001):
    print(f"Processing file: {file} for database: {database}")
    fg = FeatureGenerator(database)
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

    args = parser.parse_args()
    main(args.database, args.file, args.nWorkers, args.granularity)
