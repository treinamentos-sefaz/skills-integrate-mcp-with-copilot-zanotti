"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import json
import logging
import os
from pathlib import Path
import secrets
import time
from threading import Lock

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from .teacher_accounts import TEACHERS_FILE, password_hash

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

logger = logging.getLogger(__name__)
SESSION_SECONDS = 8 * 60 * 60
sessions: dict[str, float] = {}
sessions_lock = Lock()


class LoginRequest(BaseModel):
    username: str
    password: str


def require_teacher(request: Request, x_requested_with: str | None = Header(default=None)):
    if x_requested_with != "XMLHttpRequest":
        raise HTTPException(status_code=403, detail="Invalid request")
    token = request.cookies.get("teacher_session")
    with sessions_lock:
        expiry = sessions.get(token, 0) if token else 0
        if expiry <= time.time():
            if token:
                sessions.pop(token, None)
            raise HTTPException(status_code=401, detail="Teacher login required")


@app.post("/auth/login")
def login(credentials: LoginRequest, request: Request, response: Response):
    try:
        with TEACHERS_FILE.open(encoding="utf-8") as file:
            teachers = json.load(file)
        if not isinstance(teachers, dict):
            raise ValueError("Teacher file must contain a JSON object")
        record = teachers.get(credentials.username)
        if record is not None:
            salt = record["salt"]
            expected = record["password_hash"]
            if not isinstance(salt, str) or not isinstance(expected, str):
                raise ValueError("Invalid teacher credentials record")
            valid = secrets.compare_digest(password_hash(credentials.password, salt), expected)
        else:
            valid = False
    except (OSError, ValueError, TypeError, KeyError) as exc:
        logger.error("Cannot load teacher credentials: %s", exc)
        raise HTTPException(status_code=503, detail="Teacher login is not configured") from exc

    if not valid:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = secrets.token_urlsafe(32)
    now = time.time()
    with sessions_lock:
        expired = [key for key, expiry in sessions.items() if expiry <= now]
        for key in expired:
            del sessions[key]
        previous = request.cookies.get("teacher_session")
        if previous:
            sessions.pop(previous, None)
        sessions[token] = now + SESSION_SECONDS
    response.set_cookie(
        "teacher_session", token, max_age=SESSION_SECONDS, httponly=True,
        samesite="strict", secure=request.url.scheme == "https",
    )
    return {"message": "Logged in"}


@app.get("/auth/session")
def session(request: Request):
    token = request.cookies.get("teacher_session")
    with sessions_lock:
        expiry = sessions.get(token, 0) if token else 0
        if token and expiry <= time.time():
            sessions.pop(token, None)
    return {"authenticated": expiry > time.time()}


@app.post("/auth/logout", dependencies=[Depends(require_teacher)])
def logout(request: Request, response: Response):
    token = request.cookies.get("teacher_session")
    with sessions_lock:
        if token:
            sessions.pop(token, None)
    response.delete_cookie("teacher_session")
    return {"message": "Logged out"}

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup", dependencies=[Depends(require_teacher)])
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister", dependencies=[Depends(require_teacher)])
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
