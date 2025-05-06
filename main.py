from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from router import auth, user, role

app = FastAPI()


@app.get("/ping")
def read_root():
    return {"v": "1"}


origins = [
    "*",  # Allow all origins for WebSocket connections
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


app.include_router(auth.router)

app.include_router(user.router)

app.include_router(role.router)


