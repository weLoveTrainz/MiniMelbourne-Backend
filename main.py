import pickle
import aiohttp
import uvicorn
from fastapi import FastAPI
import pandas as pd
from fastapi.middleware.cors import CORSMiddleware
from src.model import *

# define API urls
BASE = 'https://data-exchange-api.vicroads.vic.gov.au'
GTFS_R = '/opendata/v1/gtfsr/metrotrain-tripupdates'

# Define app
app = FastAPI()
# CORS allow origin any, change later
app.add_middleware(CORSMiddleware, allow_origins=["*"])


# This file contains the stations
with open('data/stops.txt', 'r') as file:
    stop_data = {r[0]: {'stop_id': r[0], 'stop_name': r[1], 'stop_lat': r[2], 'stop_lon': r[3]}
                 for r in list(map(lambda x: x.split(","), file.read().replace('"', '').split("\n")[1:]))[0:-1]}

# Contains the trip id along with the station ids and the times it stops at them
with open('data/stop_times.pkl', 'rb') as file:
    trip_stop_data = pickle.load(file)

# Contains the line data for each route
with open('data/shapes.pkl', 'rb') as file:
    shape_data = pickle.load(file)


# Endpoints defined below

@app.get('/stops', tags=['Station'], response_model=Stops)
async def get_stops() -> Stops:
    '''
    Return a list of all stops.

    '''
    return {'stop_list': [{'name': stop_inf['stop_name'], 'coords': [stop_inf['stop_lon'], stop_inf['stop_lat']], 'station_id': stop_inf['stop_id']}
                          for stop_id, stop_inf in stop_data.items()]}


@app.get('/shape/{trip_id}', tags=['Shape'], response_model=TripShape)
async def get_shape(trip_id: str) -> TripShape:
    # the shape id is within the trip_id
    shape_id = ".".join(trip_id.split('.')[2:])
    return {'stations': [station['stop_id'] for station in trip_stop_data[trip_id]], 'shape_file': [[coord['shape_pt_lon'], coord['shape_pt_lat']] for coord in shape_data[shape_id]]}


@app.get('/stops/stop_times/{trip_id}', tags=['Stop'], response_model=TripInfo)
async def get_trip_info_data(trip_id: str) -> TripInfo:
    return {'trip_id': trip_id, 'Trips': trip_stop_data[trip_id]}


if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8080)
