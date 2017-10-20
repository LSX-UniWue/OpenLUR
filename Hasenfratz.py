import paths
import scipy.io as sio
import numpy as np

from clean_data import clean_data
from calculate_ha_pollution import calculate_ha_pollution

def feature(feat, row, col):
	LAT = 0
	LON = 1
	# Subtract 1 from column because of matlab (index starts with 1)
	n = feat[(feat[:, LAT] == row[LAT]) & (feat[:, LON] == row[LON]), col - 1]
	if len(n) == 0:
		n = 0
	return n


def feature_sum(feat, row, col):
	LAT = 0
	LON = 1
	ind = ((feat[:, LAT] == row[LAT]) & (feat[:, LON] == row[LON]))
	n = []
	# temp = feat[ind,:]
	for c in col:
		# n.append(temp[c])
		n.append(feat[ind, c])
	if len(n) == 0:
		n = 0
	n = np.sum(n)
	return n


data = sio.loadmat(paths.filtereddatadir + 'pm_01042012_30062012_filtered.mat')['data']
bounds = sio.loadmat(paths.rootdir + 'bounds')['bounds'][0]

IND_AVG_DATA = 3
GEO_ACC = 4

# Clean Data
print("Shape before cleaning: ", data.shape)
data = clean_data(data, IND_AVG_DATA=IND_AVG_DATA, GEO_ACC=GEO_ACC)
print("Shape after cleaning: ", data.shape)

LAT = 1
LON = 2

pm_ha_numpy = calculate_ha_pollution(data, bounds, LAT=LAT, LON=LON, IND_AVG_DATA=IND_AVG_DATA)

del data

LAT = 0
LON = 1

print("Training shape with tram depots: ({}, {})".format(len(pm_ha_numpy), len(pm_ha_numpy[1])))

# Tram depots
ha_depots = [[681800, 247400], [681700, 247400], [681700, 247500], [681700, 249500], [683700, 251500], [679400, 248500],
             [683400, 249900], [683400, 249800], [682500, 243400]]

# check if Tram depot in bounding box
for depot in ha_depots:
	pm_ha_numpy = pm_ha_numpy[~((pm_ha_numpy[:, LAT] == depot[LAT]) & (pm_ha_numpy[:, LON] == depot[LON])), :]

pm_ha = pm_ha_numpy.tolist()

del pm_ha_numpy


# Load land use data
pop = sio.loadmat(paths.landusedir + 'population_zh_2011.mat')['pop']
indus = sio.loadmat(paths.landusedir + 'industry_zh_2008.mat')['indus']
floor_level = sio.loadmat(paths.landusedir + 'floorlevel_zh_2011.mat')['floor_level']
heating_oil_gas = sio.loadmat(paths.landusedir + 'heatinggasoil_zh_2011.mat')['heating_oil_gas']
elev = sio.loadmat(paths.landusedir + 'elevation_zh.mat')['elev']
street_size_max = sio.loadmat(paths.landusedir + 'streetsize_max_zh.mat')['street_size_max']
street_length = sio.loadmat(paths.landusedir + 'streetlength_zh.mat')['street_length']
dist2street = sio.loadmat(paths.landusedir + 'dist_to_street.mat')['dist2street']
dist2signal = sio.loadmat(paths.landusedir + 'dist_to_signal.mat')['dist2signal']
dist2traffic = sio.loadmat(paths.landusedir + 'dist_to_traffic_ugz.mat')['dist2traffic']
slope_exp = sio.loadmat(paths.landusedir + 'slope_exp_zh.mat')['slope_exp']
traffic = sio.loadmat(paths.landusedir + 'traffic_zh_2007.mat')['traffic']
traffic_ugz = sio.loadmat(paths.landusedir + 'traffic_ugz_2013.mat')['traffic_ugz']

# Append land use data to pm data
print("Training shape without tram depots: ({}, {})".format(len(pm_ha), len(pm_ha[1])))
for row in pm_ha:
	row.append(feature(pop, row, 2))
	row.append(feature_sum(indus, row, [2, 3, 4]))
	row.append(feature(floor_level, row, 2))
	row.append(feature(heating_oil_gas, row, 2))
	row.append(feature(elev, row, 2))
	row.append(feature(street_size_max, row, 2))
	row.append(feature(dist2signal, row, 2))
	row.append(feature(dist2street, row, 2))
	row.append(feature(slope_exp, row, 2))
	row.append(feature(slope_exp, row, 3))
	row.append(feature_sum(traffic, row, [10, 11]))
	row.append(feature(dist2street, row, 3))
	row.append(feature(dist2street, row, 4))
	row.append(feature(dist2traffic, row, 2))
	row.append(feature(dist2traffic, row, 3))
	row.append(feature(traffic_ugz, row, 5))

print("Training shape with features: ({}, {})".format(len(pm_ha), len(pm_ha[1])))


# Simple GAM
# todo: Cross validation, other .mat files
print("Training model")
pm_ha_numpy = np.array(pm_ha)

from pygam import LinearGAM
from pygam.utils import generate_X_grid

# gam = LinearGAM(n_splines=10).gridsearch(pm_ha_numpy[:,-16:], pm_ha_numpy[:,2])
# XX = generate_X_grid(gam)

# gam.summary()

# print(gam.accuracy(pm_ha_numpy[:,-16:], pm_ha_numpy[:,2]))

from sklearn.model_selection import cross_val_score
gam = LinearGAM(n_splines=10)
scores = cross_val_score(model, train_data_np[:, 8:], train_data_np[:, 2], cv=5)
