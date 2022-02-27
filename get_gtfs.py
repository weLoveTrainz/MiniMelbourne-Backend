'''
Updates the static GTFS data, which updates every week.

'''
import requests
import os.path
from zipfile import ZipFile
from functools import reduce
import shutil
import pandas as pd
import pickle

# Get if it doesn't exist

with open('gtfs.zip', 'wb') as file:
    file.write(
        requests.get(
            'http://data.ptv.vic.gov.au/downloads/gtfs.zip', stream=True).content)

with ZipFile('gtfs.zip', 'r') as archive:
    # Get only Metro VIC data
    for file in archive.namelist():
        if file.startswith('2/'):
            archive.extract(file, '')

with ZipFile('2/google_transit.zip') as inner_archive:
    # Get routes, shapes, stop_times stations
    inner_archive.extractall(path='data', members=['routes.txt', 'shapes.txt',
                                                   'stop_times.txt', 'stops.txt', 'trips.txt'])

shutil.rmtree('2')

# Generate stopping sequences (times), drop most details
stop_times = pd.read_csv("data/stop_times.txt", parse_dates=["arrival_time", "departure_time"]).drop(
    ['stop_headsign', 'pickup_type',
        'drop_off_type',
        'departure_time', 'shape_dist_traveled'], axis=1)

# Serialize by grouping on trip_id, then generate a dictionary indexed trip_id, refactor
with open('data/stop_times.pkl', 'wb') as pk:
    pickle.dump(reduce(lambda x, y: x | y,
                       [{service: data.drop(['trip_id', 'stop_sequence'], axis=1).to_dict('records')} for service, data in stop_times.groupby('trip_id')]), pk)

# Do it again but have random access compatable as opposed to sequence
with open('data/stop_times_rand.pkl', 'wb') as pk:
    pickle.dump(reduce(lambda x, y: x | y, [{service: {seq["stop_sequence"]: seq for seq in data.drop(
        ['trip_id'], axis=1).to_dict('records')}} for service, data in stop_times.groupby('trip_id')]), pk)


# Generate dictionary indexed by shape_id
shapes = pd.read_csv(
    'data/shapes.txt').drop(['shape_pt_sequence', 'shape_dist_traveled'], axis=1)

# For each unique shape, group together into a sequence of points (forms a line)
with open('data/shapes.pkl', 'wb') as pkl:
    pickle.dump(reduce(lambda x, y: x | y,
                       [{service: data.drop(['shape_id'], axis=1).to_dict('records')} for service, data in shapes.groupby('shape_id')]), pkl)
