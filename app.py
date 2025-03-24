import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Load credentials from environment variable
credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
if not credentials_json:
    raise ValueError("GOOGLE_CREDENTIALS_JSON environment variable is not set.")
SERVICE_ACCOUNT_FILE = "credentials.json"

# Parse the JSON string into a dictionary
creds_info = json.loads(credentials_json)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]

creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)

# Connect to Google Sheets
gc = gspread.authorize(creds)

# Open the Google Sheet (replace with your sheet name)
SHEET_NAME = "Global Pricing"
spreadsheet = gc.open(SHEET_NAME)

# Select the first worksheet
worksheet = spreadsheet.sheet1

# Load data
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# Streamlit UI
st.title("Adobe Global Pricing Data")
st.write("This app displays the latest Adobe pricing data from different regions.")

st.dataframe(df)