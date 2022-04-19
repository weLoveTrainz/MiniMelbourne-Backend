from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.realtime import router as RealTime
from src.shape import router as Shape 
from src.stops import router as Stops
from src.misc import router as Misc 

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"])

app.include_router(RealTime, tags=["Realtime"], prefix="/realtime")
app.include_router(Shape, tags=["Shape"],prefix="/shape")
app.include_router(Stops, tags=["Stops"],prefix="/stops")
app.include_router(Misc, tags=["Misc"],prefix="")