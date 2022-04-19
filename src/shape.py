import pickle
from os import environ

from fastapi import APIRouter, Body
from fastapi.encoders import jsonable_encoder
from dotenv import load_dotenv

from src.model import *


router = APIRouter()

with open('data/stop_times.pkl', 'rb') as file:
    trip_stop_data = pickle.load(file)

# Contains the line data for each route
with open('data/shapes.pkl', 'rb') as file:
    shape_data = pickle.load(file)


@router.get('/{trip_id}', response_model=TripShape)
async def get_shape(trip_id: str) -> TripShape:
    # the shape id is within the trip_id

    shape_id = ".".join(trip_id.split('.')[2:])
    if trip_id not in trip_stop_data:
        return {'stations': [], 'shape_file': []}

    return {'stations': [station['stop_id'] for station in trip_stop_data[trip_id]], 'shape_file': [[coord['shape_pt_lon'], coord['shape_pt_lat']] for coord in shape_data[shape_id]]}
