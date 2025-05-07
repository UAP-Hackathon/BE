from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from router import auth, user, role, admin, jobseeker

app = FastAPI()

# Health check endpoint
@app.get("/ping")
def read_root():
    return {"v": "1"}

# Define allowed origins
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
     
    "https://b407-37-111-213-187.ngrok-free.app",
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
]

# Add CORS middleware with proper configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "Accept",
        "Origin",
        "X-Requested-With",
        "SESSION",
        "Access-Control-Allow-Origin",
        "Access-Control-Allow-Credentials",
    ],
    expose_headers=[
        "Content-Type",
        "Authorization",
        "Access-Control-Allow-Origin",
        "Access-Control-Allow-Credentials",
    ],
    max_age=3600,
)

# Include routers
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(role.router)
app.include_router(admin.router)
app.include_router(jobseeker.router)