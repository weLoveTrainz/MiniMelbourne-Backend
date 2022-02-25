from enum import Enum
from pydantic import BaseModel, Field


class Stop(BaseModel):
    name: str = Field(..., description="Station name")
    station_id: str 
    coords: list[float]


class Stops(BaseModel):
    stop_list: list[Stop]

class TripShape(BaseModel):

    shape_file: list[list[float]] # line file, list of long lats (!! note the ordering)
    stations: list[str]


class TripStop(BaseModel):
    arrival_time: str 
    stop_id: str 

class TripInfo(BaseModel):
    trip_id: str 
    Trips: list[TripStop] = Field(...,description="List of stations along with their arrival time")