from os import environ
import aiohttp
import asyncio
from fastapi import APIRouter, Body, WebSocket
from fastapi.encoders import jsonable_encoder
from fastapi_utils.tasks import repeat_every
from dotenv import load_dotenv

from src.model import *
from src.gtfs_pb2 import FeedMessage
from src.misc import get_current_stop

router = APIRouter()

location_data = FeedMessage()
update_data = FeedMessage()

# define API urls
GTFS_R = 'https://data-exchange-api.vicroads.vic.gov.au/opendata/v1/gtfsr/metrotrain-vehicleposition-updates'
GTFS_T = 'https://data-exchange-api.vicroads.vic.gov.au/opendata/v1/gtfsr/metrotrain-tripupdates'

# Get token
load_dotenv()


@router.get("/", response_model=RealTimeData)
async def get_realtime() -> RealTimeData:
    '''
    Returns realtime GTFS data. Updated every 20 seconds.

    '''

    return {'timestamp': location_data.header.timestamp,
            'services': [{'service_id': f.id, "trip_id": f.vehicle.trip.trip_id,
                          "start_time": f.vehicle.trip.start_time, "start_date": f.vehicle.trip.start_date,
                         "latitude": f.vehicle.position.latitude, "longitude": f.vehicle.position.longitude,
                          "timestamp": f.vehicle.timestamp, "vehicle_id": f.vehicle.vehicle.id,
                          "occupancy": f.vehicle.occupancy_status if hasattr(f.vehicle, "occupancy_status") else None } 
                          | await get_current_stop(f.vehicle.trip.trip_id) for f in location_data.entity]}

@router.get("/trip_update", response_model=TripUpdates)
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


@router.on_event("startup")
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
            update_data.ParseFromString(new_stream)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept() # Open connection

    while True:
        try:
            await asyncio.sleep(10) # Send new every 10 
            await websocket.send_json(await get_realtime())
        except Exception as e:
            print(f'Error: {e}')
            break 
    # Halt WS connection
