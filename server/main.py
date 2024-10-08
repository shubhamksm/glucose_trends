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

@app.post("/upload-csv/")
async def upload_csv(file: UploadFile = File(...)):
    df = pd.read_csv(file.file, skiprows=[0], header=0)
    df = df[['Device Timestamp', 'Record Type', 'Historic Glucose mmol/L', 'Scan Glucose mmol/L', 
             'Rapid-Acting Insulin (units)', 'Long-Acting Insulin Value (units)']]
    
    df['Device Timestamp'] = pd.to_datetime(df['Device Timestamp'])
    df.to_sql('glucose_data', engine, if_exists='replace', index=False)
    
    return {"message": "CSV uploaded and processed successfully"}

@app.get("/glucose-trends/")
async def glucose_trends(insulin_type: str, min_dose: float, max_dose: float):
    query = f"""
    SELECT "Device Timestamp", "Historic Glucose mmol/L"
    FROM glucose_data
    WHERE "{insulin_type} (units)" BETWEEN {min_dose} AND {max_dose}
    ORDER BY "Device Timestamp"
    """
    df = pd.read_sql(query, engine)
    
    # Group by hour and calculate average glucose
    df['hour'] = df['Device Timestamp'].dt.hour
    hourly_avg = df.groupby('hour')['Historic Glucose mmol/L'].mean().reset_index()
    
    return hourly_avg.to_dict(orient='records')