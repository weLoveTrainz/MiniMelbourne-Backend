import pickle
from os import environ

from fastapi import APIRouter, Body
from fastapi.encoders import jsonable_encoder

from src.model import *


with open('data/stops.txt', 'r') as file:
    stop_data = {r[0]: {'stop_id': r[0], 'stop_name': r[1], 'stop_lat': r[2], 'stop_lon': r[3]}
                 for r in list(map(lambda x: x.split(","), file.read().replace('"', '').split("\n")[1:]))[0:-1]}

# Contains the trip id along with the station ids and the times it stops at them
with open('data/stop_times.pkl', 'rb') as file:
    trip_stop_data = pickle.load(file)

with open('data/stop_times_rand.pkl', 'rb') as file:
    trip_stop_dict_data = pickle.load(file)

router = APIRouter()

@router.get('/', tags=['Station'], response_model=Stops)
async def get_stops() -> Stops:
    '''
    Return a list of all stops.

    '''
    return {'stop_list': [{'name': stop_inf['stop_name'], 'coords': [stop_inf['stop_lon'], stop_inf['stop_lat']], 'station_id': stop_inf['stop_id']}
                          for stop_id, stop_inf in stop_data.items()]}

@router.get('/stop_times/{trip_id}', tags=['Stop'], response_model=TripInfo)
async def get_trip_info_data(trip_id: str) -> TripInfo:
    return {'trip_id': trip_id, 'Trips': trip_stop_data[trip_id]}


@router.get('/stop_times_dict/{trip_id}', tags=['Stop'], response_model=TripInfoDict)
async def get_trip_info_dict_data(trip_id: str) -> TripInfoDict:
    return {'trip_id': trip_id, 'Trips': trip_stop_dict_data[trip_id]}