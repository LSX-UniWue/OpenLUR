import logging
import pickle
import time

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from regression_runner import run_regression
from utils.DataLoader import Dataset
from utils.color import Color

logging.basicConfig(format='%(levelname)s [%(name)s]:%(message)s', level=logging.INFO)

features = [
    "os",
    # "laei_small",
    # "laei",
    # "both"
]
# feature_type=features[3]

modelnames = [
    "AutoML",
    "Random_Forest_random_search",
    "Random_Forest_Standard",
    # "GAM"
]
iterations = 40


def run_londondata_mapper(args):
    model, iterations = args
    run_londondata(model, iterations=iterations)


def run_londondata(model, iterations=2, filename=None):
    x_train, y_train, x_test, y_test = Dataset.laeiOSM()

    logging.info("Start model {}".format(model))

    starttime = time.time()
    results = []
    for i in range(iterations):
        results.append(run_regression(model, x_train, y_train, x_test, y_test))

    results = pd.concat(results, ignore_index=True)
    timediff = time.time() - starttime

    search_results = results[results.type == "search"]
    logging.info(
        Color.BOLD + Color.GREEN + "Meaned over {} iterations ({} minutes each), the model {} reached a RMSE of {}, MAE of {} and R2 of {}.".format(
            iterations, timediff / 60 / iterations, model, search_results.rmse.mean(), search_results.mae.mean(),
            search_results.r2.mean()) + Color.END)
    if filename:
        pickle.dump(results, open(filename, "wb"))


def run_on_both(model, iterations=2, filename=None, season=1):
    x_train_laei, y_train_laei, x_test_laei, y_test_laei = Dataset.laeiOSM()
    x_train_os, y_train_os, x_test_os, y_test_os = Dataset.OpenSenseOSM(season)

    logging.info("Start model {} on {}".format(model, feature_type))
    starttime = time.time()
    results = []
    for i in range(iterations):

        # select 180 points from laei:
        idx = np.random.choice(x_train_laei.shape[0], 180, replace=False)
        x_train_laei_split = x_train_laei[idx, :]
        y_train_laei_split = y_train_laei[idx]

        # select 20 points from laei (test):
        idx = np.random.choice(x_test_laei.shape[0], 20, replace=False)
        x_test_laei_split = x_test_laei[idx, :]
        y_test_laei_split = y_test_laei[idx]

        # split os in 180/20
        x_train_os_split, x_test_os_split, y_train_os_split, y_test_os_split = train_test_split(x_train_os, y_train_os,
                                                                                                test_size=0.1,
                                                                                                random_state=42)

        # Scaling y-values as differences from mean
        laei_mean = np.mean(y_train_laei_split)
        os_mean = np.mean(y_train_os_split)

        y_train_laei_split = y_train_laei_split - laei_mean
        y_test_laei_split = y_test_laei_split - laei_mean

        y_train_os_split = y_train_os_split - os_mean
        y_test_os_split = y_test_os_split - os_mean

        if feature_type == "both":
            # concatenate os and laei data
            x_train = np.concatenate((x_train_laei_split, x_train_os_split), axis=0)
            x_test = np.concatenate((x_test_laei_split, x_test_os_split), axis=0)
            y_train = np.concatenate((y_train_laei_split, y_train_os_split), axis=0)
            y_test = np.concatenate((y_test_laei_split, y_test_os_split), axis=0)
        elif feature_type == "laei_small":
            x_train = x_train_laei_split
            y_train = y_train_laei_split
            x_test = x_test_laei_split
            y_test = y_test_laei_split
        elif feature_type == "laei":
            x_train = x_train_laei
            y_train = y_train_laei
            x_test = x_test_laei
            y_test = y_test_laei
        elif feature_type == "os":
            x_train = x_train_os_split
            y_train = y_train_os_split
            x_test = x_test_os_split
            y_test = y_test_os_split
        else:
            break

        results.append(run_regression(model, x_train, y_train, x_test, y_test))

    results = pd.concat(results, ignore_index=True)
    timediff = time.time() - starttime

    logging.info(
        Color.BOLD + Color.GREEN + "Results  for model {}, time needed: {:.2f} minutes, mean R2 on test: {:.2f}:".format(
            model, timediff / 60, results[results["type"] == "test"]["r2"].mean()) + Color.END)
    logging.debug(results.groupby("type").r2.mean())

    if filename:
        pickle.dump(results, open(filename, "wb"))
        logging.info("saved in {}".format(filename))
    logging.info(" ")
    logging.info(" ")


if __name__ == "__main__":
    logging.info("start")

    for feature_type in features:
        for model in modelnames:
            # run_londondata(model, iterations=iterations, filename="output/{}_longrun.p".format(model))
            run_on_both(model, iterations=iterations,
                        filename="output/{}_train_{}_{}_iterations.p".format(model, feature_type, iterations))
