import pickle
import aiohttp
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_utils.tasks import repeat_every
import pandas as pd
from os import environ
from dotenv import load_dotenv
from src.model import *
from src.gtfs_pb2 import FeedMessage
from datetime import datetime
from math import floor
import random


# define API urls
GTFS_R = 'https://data-exchange-api.vicroads.vic.gov.au/opendata/v1/gtfsr/metrotrain-vehicleposition-updates'
GTFS_T = 'https://data-exchange-api.vicroads.vic.gov.au/opendata/v1/gtfsr/metrotrain-tripupdates'
# Get live data -> digest -> serve -> get live data ....
location_data = FeedMessage()
update_data = FeedMessage()

# Define app
app = FastAPI()
# CORS allow origin any, change later
app.add_middleware(CORSMiddleware, allow_origins=["*"])

load_dotenv()
# This file contains the stations
with open('data/stops.txt', 'r') as file:
    stop_data = {r[0]: {'stop_id': r[0], 'stop_name': r[1], 'stop_lat': r[2], 'stop_lon': r[3]}
                 for r in list(map(lambda x: x.split(","), file.read().replace('"', '').split("\n")[1:]))[0:-1]}

with open('data/routes.txt', 'r') as file:
    route_data = {r[0]: {'route_id': r[0], 'route_long_name': r[3]}
                  for r in list(map(lambda x: x.split(","), file.read().replace('"', '').split("\n")[1:]))[0:-1]}

# Contains the trip id along with the station ids and the times it stops at them
with open('data/stop_times.pkl', 'rb') as file:
    trip_stop_data = pickle.load(file)

with open('data/stop_times_rand.pkl', 'rb') as file:
    trip_stop_dict_data = pickle.load(file)

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
# Need to modify structur of th
async def get_trip_info_data(trip_id: str) -> TripInfo:
    return {'trip_id': trip_id, 'Trips': trip_stop_data[trip_id]}


@app.get('/stops/stop_times_dict/{trip_id}', tags=['Stop'], response_model=TripInfoDict)
async def get_trip_info_dict_data(trip_id: str) -> TripInfoDict:
    return {'trip_id': trip_id, 'Trips': trip_stop_dict_data[trip_id]}


@app.get('/est_realtime', response_model=EstRealTime)
async def get_est_realtime() -> EstRealTime:
    '''
    Estimates the locations of services that are active. Gets the start date, and then finds the approximate location of the train.

    '''
    retrieve = await get_trip_update_curr()  # Get current
    trip_data_curr = retrieve['trips']
    now = datetime.now()
    current_time = datetime.strptime(now.strftime("%H:%M:%S"), "%H:%M:%S")
    # shapeNum * (curr_time-start_time)/(finish_time-start_time)

    def est_pos(trip_id: str):
        '''
        Estimate the position at which the train is
        '''
        shape_id = ".".join(trip_id.split(".")[2:])
        return max(0, min(floor(len(shape_data[shape_id])*(current_time -
                                                           datetime.strptime(trip_stop_data[trip_id][0]['arrival_time'], "%H:%M:%S")).seconds/(datetime.strptime(trip_stop_data[trip_id][-1]['arrival_time'], "%H:%M:%S") -
                                                                                                                                               datetime.strptime(trip_stop_data[trip_id][0]['arrival_time'], "%H:%M:%S")).seconds), len(shape_data[shape_id])-1))

    def get_shape_pos(trip_id):
        # Get the estimated value
        lat_lon = shape_data[".".join(
            trip_id.split(".")[2:])][est_pos(trip_id)]
        return [lat_lon['shape_pt_lon'], lat_lon['shape_pt_lat']]

    return {'timestamp': datetime.now().timestamp(),
            'services': [{'trip_id': s['trip_id'], 'start_time':s['start_time'], 'coords':get_shape_pos(s['trip_id'])} for s in trip_data_curr]}


@app.get("/realtime", response_model=RealTimeData)
async def get_realtime() -> RealTimeData:
    '''
    Returns realtime GTFS data. Updated every 20 seconds.
    NOT WORKING
    '''

    return {'timestamp': location_data.header.timestamp,
            'services': [{'service_id': f.id, "trip_id": f.vehicle.trip.trip_id,
                          "start_time": f.vehicle.trip.start_time, "start_date": f.vehicle.trip.start_date,
                         "latitude": f.vehicle.position.latitude, "longitude": f.vehicle.position.longitude,
                          "timestamp": f.vehicle.timestamp, "vehicle_id": f.vehicle.vehicle.id,
                          "occupancy": f.vehicle.occupancy_status if hasattr(f.vehicle, "occupancy_status") else None
                          } for f in location_data.entity]}


@app.get("/trip_update", response_model=TripUpdates)
async def get_trip_update() -> TripUpdates:
    #print(update_data)
    return {
        'timestamp': update_data.header.timestamp,
        'trips': [
            {'trip_id': curr.trip_update.trip.trip_id, 'start_time': curr.trip_update.trip.start_time, 'start_date': curr.trip_update.trip.start_date,
             'stopping_pattern': [{"arrival": stop_seq.arrival.time, "departure": stop_seq.departure.time, "sequence_id": stop_seq.stop_sequence} for stop_seq in curr.trip_update.stop_time_update]}
            for curr in update_data.entity
        ]
    }


@app.get("/trip_update_current", response_model=TripUpdates)
async def get_trip_update_curr() -> TripUpdates:
    '''
    Get all active services
    '''
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")

    return {
        'timestamp': update_data.header.timestamp,
        'trips': [
            {'trip_id': curr.trip_update.trip.trip_id, 'start_time': curr.trip_update.trip.start_time, 'start_date': curr.trip_update.trip.start_date,
             'stopping_pattern': [{"arrival": stop_seq.arrival.time, "departure": stop_seq.departure.time, "sequence_id": stop_seq.stop_sequence} for stop_seq in curr.trip_update.stop_time_update]}
            # if curr.trip_update.trip.start_time < current_time < trip_stop_data[curr.trip_update.trip.trip_id][-1]['arrival_time']
            for curr in update_data.entity
        ]
    }


@app.get("/current_station/{trip_id}", response_model=CurrentStop)
async def get_current_stop(trip_id: str) -> CurrentStop:
    trip_info = await get_trip_info_data(trip_id)
    stops = trip_info["Trips"]

    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")

    # We want the last station that the train was at
    i = 0
    current_stop = stops[i]
    while (current_time > current_stop['arrival_time']) and (i < len(stops) - 1):
        i += 1
        current_stop = stops[i]

    current_stop = stops[max(i - 1, 0)]

    stop_id = str(current_stop['stop_id'])

    return {
        'completed': i == len(stops) - 1,
        'stop': {
            'name': stop_data[stop_id]['stop_name'],
            'station_id': stop_id,
            'coords': [stop_data[stop_id]['stop_lat'], stop_data[stop_id]['stop_lon']]
        }
    }


@app.get("/next_station/{trip_id}", response_model=NextStop)
async def get_current_stop(trip_id: str) -> NextStop:
    trip_info = await get_trip_info_data(trip_id)
    stops = trip_info["Trips"]

    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")

    # We want the next station the train will be at
    i = 0
    current_stop = stops[i]
    while (current_time > current_stop['arrival_time']) and (i < len(stops) - 1):
        i += 1
        current_stop = stops[i]

    if (i == len(stops) - 1):
        # The route is completed so we return None
        return {
            'stop': None,
            'arrival': None
        }

    stop_id = str(current_stop['stop_id'])

    return {
        'stop': {
            'name': stop_data[stop_id]['stop_name'],
            'station_id': stop_id,
            'coords': [stop_data[stop_id]['stop_lat'], stop_data[stop_id]['stop_lon']]
        },
        'arrival': current_stop['arrival_time']
    }


@app.get("/occupancy/{trip_id}", response_model=Occupancy)
async def get_occupancy(trip_id: str) -> Occupancy:
    return random.randint(0, 6)


@app.get("/stop_occupancy/{stop_id}", response_model=CarParkOccupancy)
async def get_stop_occupanct(stop_id: str) -> CarParkOccupancy:
    return random.randint(0, 100)


@app.get("/train_line/{trip_id}", response_model=TrainLine)
async def get_train_line(trip_id: str) -> TrainLine:
    for key in route_data:
        if key in trip_id:
            return {
                'trip_id': trip_id,
                'line_name': route_data[key]['route_long_name']
            }


@repeat_every(seconds=20)
async def update_realtime() -> None:
    '''
    Updates in realtime.
    The data stores the timestamp which can be used for updates.
    '''

    async with aiohttp.ClientSession() as session:
        async with session.get(GTFS_R, headers={'Ocp-Apim-Subscription-Key': environ['PrimaryKey']}) as response:
            location_data.ParseFromString(await response.read())
        async with session.get(GTFS_T, headers={'Ocp-Apim-Subscription-Key': environ['PrimaryKey']}) as response:
            new_stream = await response.read()
            if len(new_stream) < 200:
                return
            update_data.ParseFromString(new_stream)


@app.on_event('startup')
async def startup() -> None:
    await update_realtime()

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8080)
