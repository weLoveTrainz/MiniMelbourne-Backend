import pickle
import aiohttp
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_utils.tasks import repeat_every
import pandas as pd
from dotenv import load_dotenv
from src.model import *
from src.gtfs_pb2 import FeedMessage


# define API urls
BASE = 'https://data-exchange-api.vicroads.vic.gov.au'
GTFS_R = '/opendata/v1/gtfsr/metrotrain-tripupdates'

# Get live data -> digest -> serve -> get live data ....
live_data = FeedMessage()

# Define app
app = FastAPI()
# CORS allow origin any, change later
app.add_middleware(CORSMiddleware, allow_origins=["*"])

load_dotenv()
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


@app.get("/realtime", response_model=RealTimeData)
async def get_realtime() -> RealTimeData:
    '''
    Returns realtime GTFS data. Updated every 20 seconds.

    '''
    return {'timestamp': live_data.header.timestamp,
            'services': [{'service_id': f.id, "trip_id": f.vehicle.trip.trip_id,
                          "start_time": f.vehicle.trip.start_time, "start_date": f.vehicle.trip.start_date,
                         "latitude": f.vehicle.position.latitude, "longitude": f.vehicle.position.longitude,
                          "timestamp": f.vehicle.timestamp, "vehicle_id": f.vehicle.vehicle.id,
                          "occupancy": f.vehicle.occupancy_status if hasattr(f.vehicle, "occupancy_status") else None
                          } for f in live_data.entity]}


@repeat_every(seconds=20)
async def update_realtime() -> None:
    ''' 
    Updates in realtime.    
    The data stores the timestamp which can be used for updates.
    '''

    async with aiohttp.ClientSession() as session:
        async with session.get(url+gtfs, headers={'Ocp-Apim-Subscription-Key': environ['PrimaryKey']}) as response:
            live_data.ParseFromString(await response.read())


@app.on_event('startup')
async def startup() -> None:
    await update_realtime()

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8080)