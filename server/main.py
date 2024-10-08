import os
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime, timedelta

load_dotenv()
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)

column_mapping = {
    'Device Timestamp': 'timestamp',
    'Record Type': 'record_type',
    'Historic Glucose mmol/L': 'historic_glucose',
    'Scan Glucose mmol/L': 'scan_glucose',
    'Rapid-Acting Insulin (units)': 'rapid_acting_insulin',
    'Long-Acting Insulin Value (units)': 'long_acting_insulin'
}

@app.post("/upload-csv/")
async def upload_csv(file: UploadFile = File(...)):
    df = pd.read_csv(file.file, skiprows=[0], header=0)
    
    # Select and rename columns
    df = df[column_mapping.keys()].rename(columns=column_mapping)
    
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.to_sql('glucose_data', engine, if_exists='replace', index=False)
    
    return {"message": "CSV uploaded and processed successfully"}

@app.get("/glucose-trends/")
async def glucose_trends(insulin_type: str, min_dose: float, max_dose: float):
    insulin_column = 'rapid_acting_insulin' if insulin_type == 'rapid' else 'long_acting_insulin'
    
    query = f"""
    SELECT timestamp, historic_glucose
    FROM glucose_data
    WHERE {insulin_column} BETWEEN {min_dose} AND {max_dose}
    ORDER BY timestamp
    """
    df = pd.read_sql(query, engine)
    
    # Group by hour and calculate average glucose
    df['hour'] = df['timestamp'].dt.hour
    hourly_avg = df.groupby('hour')['historic_glucose'].mean().reset_index()
    
    return hourly_avg.to_dict(orient='records')