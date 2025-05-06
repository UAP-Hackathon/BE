from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from router import auth, user, role, admin, jobseeker

app = FastAPI()


@app.get("/ping")
def read_root():
    return {"v": "1"}


# When using allow_credentials=True, you cannot use wildcard "*" for origins
# You must specify exact origins
origins = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
    "https://8466-103-133-201-141.ngrok-free.app",  # Add your ngrok URL from the error message
    "https://8466.103.133.201.141.ngrok-free.app" ,  # Alternative format of the ngrok URL
    "http://localhost:3001",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Specific origins instead of wildcard
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Specific methods
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With", "SESSION"],  # Specific headers
    expose_headers=["Content-Type", "Authorization"],
    max_age=600  # Cache preflight requests for 10 minutes
)


app.include_router(auth.router)

app.include_router(user.router)

app.include_router(role.router)

app.include_router(admin.router)

app.include_router(jobseeker.router)

