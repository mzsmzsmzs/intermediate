Here’s the updated implementation with the following changes:

Notification Service:

Added a GET /notifications API to fetch all notifications.
Added a GET /notifications/{id} API to fetch a specific notification by ID.
Weather Service:

Added a GET /weather API to fetch all weather alerts sent.
Added a GET /weather/{id} API to fetch a specific weather alert by ID.
Notification Service
This service logs and fetches notifications.

python
Copy code
# notification_service.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# FastAPI App
app = FastAPI()

# SQLite Database Setup
DATABASE_URL = "sqlite:///./notifications.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

# Notification Model
class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    message = Column(Text, nullable=False)
    location = Column(String(255), nullable=False)
    severity = Column(String(50), nullable=False)
    created_at = Column(TIMESTAMP, nullable=False)

Base.metadata.create_all(bind=engine)

# Pydantic Schema
class NotificationSchema(BaseModel):
    message: str
    location: str
    severity: str

@app.post("/notifications")
def create_notification(notification: NotificationSchema):
    session = SessionLocal()
    new_notification = Notification(
        message=notification.message,
        location=notification.location,
        severity=notification.severity,
    )
    session.add(new_notification)
    session.commit()
    return {"message": "Notification logged successfully"}

@app.get("/notifications")
def get_notifications():
    session = SessionLocal()
    notifications = session.query(Notification).all()
    return notifications

@app.get("/notifications/{id}")
def get_notification_by_id(id: int):
    session = SessionLocal()
    notification = session.query(Notification).filter(Notification.id == id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification
Weather Service
This service sends weather alerts and fetches weather data.

python
Copy code
# weather_service.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import requests

# FastAPI App
app = FastAPI()

# SQLite Database Setup
DATABASE_URL = "sqlite:///./weather_data.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

# Weather Data Model
class WeatherData(Base):
    __tablename__ = "weather_data"
    id = Column(Integer, primary_key=True, index=True)
    location = Column(String(255), nullable=False)
    condition = Column(String(50), nullable=False)
    severity = Column(String(50), nullable=False)
    created_at = Column(TIMESTAMP, nullable=False)

Base.metadata.create_all(bind=engine)

# Pydantic Schema
class WeatherDataSchema(BaseModel):
    location: str
    condition: str
    severity: str

@app.post("/weather")
def send_weather_alert(weather: WeatherDataSchema):
    session = SessionLocal()
    # Store Weather Data
    new_weather = WeatherData(
        location=weather.location,
        condition=weather.condition,
        severity=weather.severity,
    )
    session.add(new_weather)
    session.commit()

    # If severity is critical, notify the Notification Service
    if weather.severity.lower() in ["storm", "flood", "extreme heat"]:
        notification = {
            "message": f"Severe weather alert: {weather.condition} in {weather.location}",
            "location": weather.location,
            "severity": weather.severity,
        }
        try:
            response = requests.post("http://localhost:8001/notifications", json=notification)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    return {"message": "Weather alert logged and notification sent if necessary"}

@app.get("/weather")
def get_all_weather():
    session = SessionLocal()
    weather_data = session.query(WeatherData).all()
    return weather_data

@app.get("/weather/{id}")
def get_weather_by_id(id: int):
    session = SessionLocal()
    weather = session.query(WeatherData).filter(WeatherData.id == id).first()
    if not weather:
        raise HTTPException(status_code=404, detail="Weather alert not found")
    return weather
Running Both Services:
Start the Notification Service:

bash
Copy code
uvicorn notification_service:app --host 0.0.0.0 --port 8001
Start the Weather Service:

bash
Copy code
uvicorn weather_service:app --host 0.0.0.0 --port 8000
Example API Calls:
1. Post Weather Data (Weather Service):
bash
Copy code
curl -X POST "http://localhost:8000/weather" \
-H "Content-Type: application/json" \
-d '{"location": "New York", "condition": "Storm", "severity": "Storm"}'
2. Get All Weather Data (Weather Service):
bash
Copy code
curl -X GET "http://localhost:8000/weather"
3. Get Weather Data by ID (Weather Service):
bash
Copy code
curl -X GET "http://localhost:8000/weather/1"
4. Get All Notifications (Notification Service):
bash
Copy code
curl -X GET "http://localhost:8001/notifications"
5. Get Notification by ID (Notification Service):
bash
Copy code
curl -X GET "http://localhost:8001/notifications/1"
