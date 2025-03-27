import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json
from dotenv import load_dotenv
import os
import requests

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
products = df["Product"].unique() # Extract list of unique products

# Fetch latest currency conversion rates (base = USD)
EXCHANGE_API_URL = "https://v6.exchangerate-api.com/v6/b03ae4404090b6a8b1281057/latest/USD"
response = requests.get(EXCHANGE_API_URL)
# st.write("Actual URL fetched from:", response.url)
# st.write("Raw response content:", response.text)
conversion_rates = response.json().get("conversion_rates", {})
# st.write("Fetched exchange rates:", conversion_rates)

def convert_to_usd(amount, currency):
    try:
        rate = conversion_rates.get(currency)
        if rate:
            # st.write("Looking for rate for:", currency)
            return round(amount / rate, 2)
            # st.write("Rate found:", rates.get(currency))
        else:
            return None
    except Exception:
        return None

# Add a new column for converted USD prices
df["Amount (USD)"] = df.apply(lambda row:convert_to_usd(row["Amount"], row["Currency"]),axis=1)

# Streamlit UI
st.title("Global Pricing")
st.write("View the latest pricing of digital products from different regions.")
selected_product = st.selectbox("Select a product", products) # Allow users to select a product
product_df = df[df["Product"] == selected_product] # Filter to selected product

# Keep only the latest entry per region
product_df["Timestamp"] = pd.to_datetime(product_df["Timestamp"])
latest_df = product_df.sort_values("Timestamp").groupby("Region", as_index=False).last()

# Show results
st.write(f"Latest prices for **{selected_product}**")
df_sorted = latest_df.sort_values(by="Amount (USD)")
st.dataframe(df_sorted)