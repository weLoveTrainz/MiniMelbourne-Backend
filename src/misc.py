from turfpy.measurement import nearest_point
from geojson import Point, Feature, FeatureCollection
from datetime import datetime
from fastapi import APIRouter, Body
from src.stops import get_trip_info_data, stop_data
from src.model import *

router = APIRouter()


with open('data/routes.txt', 'r') as file:
    route_data = {r[0]: {'route_id': r[0], 'route_long_name': r[3]}
                  for r in list(map(lambda x: x.split(","), file.read().replace('"', '').split("\n")[1:]))[0:-1]}

@router.get("/next_station/{trip_id}", response_model=NextStop)
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
            'next_stop': None,
            'arrival': None
        }

    stop_id = str(current_stop['stop_id'])

    return {
        'next_stop': stop_data[stop_id]['stop_name'],
        'arrival': current_stop['arrival_time']
    }

async def get_next_stop(trip_id: str, lat_lon: list[float]) -> NextStop:
    '''
    Implements getting next station, given position and trip_id

    use turfpy
    Put stations along line
    Find point closest to line  
    Set max(numstations, nextpoint) as next station
    this will break for if train is very close to next station, so use time as failsafe
    if time below assume havent reached station, else assume past station
    ''' 
    trip_info = await get_trip_info_data(trip_id)
    stops = trip_info["Trips"]

    fc = FeatureCollection([Feature(geometry=Point(stop_coord)) for stop_coord in stops])

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
            'next_stop': None,
            'arrival': None
        }

    stop_id = str(current_stop['stop_id'])

    return {
        'next_stop': stop_data[stop_id]['stop_name'],
        'arrival': current_stop['arrival_time']}



@router.get("/train_line/{trip_id}", response_model=TrainLine)
async def get_train_line(trip_id: str) -> TrainLine:
    for key in route_data:
        if key in trip_id:
            return {
                'trip_id': trip_id,
                'line_name': route_data[key]['route_long_name']
            }
