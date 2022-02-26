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

class Occupancy(int, Enum):
    '''
    If available, displays how crowded the train is.
    '''
    EMPTY = 0
    MANY_SEATS_AVAILABLE = 1
    FEW_SEATS_AVAILABLE = 2
    STANDING_ROOM_ONLY = 3
    CRUSHED_STANDING_ROOM_ONLY = 4
    FULL = 5
    NOT_ACCEPTING_PASSENGERS = 6

class Service(BaseModel):
    '''
    (GTFS-R) - Details for a running service.
    '''
    service_id: str = Field(
        ..., description='Indicates the service type, which is the days of the week when the line runs')
    trip_id: str = Field(..., description='This ID comes in the form: <NUM>.<SERVE_TYPE>.<Metro=2>-<LINE>-<ALT>-mjp-1.<X>.<DIRECTION>')
    start_time: str = Field(...,
                            description='Time of the form HH:MM:SS. Can carry over 24:00')
    start_date: str
    latitude: float
    longitude: float
    timestamp: int = Field(..., description='Epoch Timestamp')
    vehicle_id: str
    occupancy: Occupancy | None

class RealTimeData(BaseModel):
    '''
    List of all realtime trains with locations.

    '''
    timestamp: int
    services: list[Service]

class StopSequence(BaseModel):
    arrival: int
    departure: int
    sequence_id: int


class TripUpdate(BaseModel):
    trip_id: str
    start_time: str
    start_date: str
    stopping_pattern: list[StopSequence]

class TripUpdates(BaseModel):
    timestamp: str
    trips: list[TripUpdate]

class CurrentStop(BaseModel):
    completed: bool
    stop: Stop

class NextStop(BaseModel):
    # None if the route is completed so no next stop
    stop: Stop | None
    arrival: str | None
