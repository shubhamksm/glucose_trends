import os
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime, timedelta
import logging

# Configure the logger
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)


load_dotenv()
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)

# Column name mapping
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
    
    # Parse the timestamp with the correct format
    df['timestamp'] = pd.to_datetime(df['timestamp'], format='%d-%m-%Y %H:%M')
    
    # Convert numeric columns to appropriate types
    numeric_columns = ['historic_glucose', 'scan_glucose', 'rapid_acting_insulin', 'long_acting_insulin']
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df.to_sql('glucose_data', engine, if_exists='replace', index=False)
    
    return {"message": "CSV uploaded and processed successfully"}

from typing import List

@app.get("/glucose-trends/")
async def glucose_trends(
    insulin_type: str, 
    min_dose: float, 
    max_dose: float, 
    limit: int = 10,  # Default to 10 records per page
    offset: int = 0  # Offset for pagination
):
    # Adjusting for the correct insulin column name
    insulin_column = 'rapid_acting_insulin' if insulin_type == 'rapid' else 'long_acting_insulin'
    
    # Query to fetch all instances of insulin taken in the dose range, with pagination
    query = f"""
    SELECT timestamp, {insulin_column} as units_taken, historic_glucose, scan_glucose
    FROM glucose_data
    WHERE {insulin_column} BETWEEN {min_dose} AND {max_dose}
    ORDER BY timestamp
    LIMIT {limit} OFFSET {offset}
    """
    
    insulin_df = pd.read_sql(query, engine)
    
    # Log the insulin records for inspection
    logger.debug(f"Fetched Insulin Records: {insulin_df}")

    # If no records found, return early
    if insulin_df.empty:
        return {"message": "No insulin records found in the specified range."}
    
    # For each instance of insulin taken, get the glucose data in the 48-hour range (24 hours before and after)
    results = []
    
    for _, row in insulin_df.iterrows():
        insulin_timestamp = row['timestamp']
        units_taken = row['units_taken']  # Get the number of units taken
        
        # Calculate the 48-hour range (24 hours before and 24 hours after)
        start_time = insulin_timestamp - pd.Timedelta(hours=24)
        end_time = insulin_timestamp + pd.Timedelta(hours=24)

        # Query to fetch all relevant columns within the 48-hour range
        glucose_query = f"""
        SELECT timestamp, historic_glucose, scan_glucose, rapid_acting_insulin, long_acting_insulin
        FROM glucose_data
        WHERE timestamp BETWEEN '{start_time}' AND '{end_time}'
        ORDER BY timestamp
        """
        
        glucose_df = pd.read_sql(glucose_query, engine)

        # Log the fetched glucose data for this insulin timestamp
        logger.debug(f"Fetched Glucose Data for Insulin at {insulin_timestamp}: {glucose_df}")

        # Filter rows with valid `historic_glucose` data
        df_filtered = glucose_df[glucose_df['historic_glucose'].notna()]

        # Group by hour and calculate average glucose for rows that have valid `historic_glucose`
        df_filtered['hour'] = df_filtered['timestamp'].dt.floor('H')
        hourly_avg = df_filtered.groupby('hour')['historic_glucose'].mean().reset_index()

        # Add a flag for the hour when insulin was taken
        hourly_avg['insulin_taken'] = hourly_avg['hour'].apply(
            lambda hour: hour == insulin_timestamp.floor('H')
        )

        # Format the hour to a more readable string
        hourly_avg['hour'] = hourly_avg['hour'].dt.strftime("%I:%M %p, %d %b - %Y")

        # Append the result for this insulin instance
        results.append({
            "insulin_timestamp": insulin_timestamp.strftime("%I:%M %p, %d %b - %Y"),
            "units_taken": units_taken,  # Include the units of insulin taken
            "glucose_trends": hourly_avg.to_dict(orient='records')
        })

    # Log the final result
    logger.debug(f"Final Results: {results}")

    return results


# Add this function to test the database connection
@app.get("/test-db-connection")
async def test_db_connection():
    try:
        with engine.connect() as connection:
            result = connection.execute("SELECT 1")
            return {"message": "Database connection successful"}
    except Exception as e:
        return {"error": f"Database connection failed: {str(e)}"}

# Add this function to check the DATABASE_URL
@app.get("/check-db-url")
async def check_db_url():
    return {"DATABASE_URL": DATABASE_URL}