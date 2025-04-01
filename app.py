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

# Streamlit UI
st.title("Compare Software Prices by Country")
st.badge("Beta", color="grey")
st.markdown("""
Looking to save on software?

This tool helps you compare prices for products like **Adobe Creative Cloud**, **VPN services**, and other **digital tools** across multiple countries. Prices are shown in your preferred currency using **real-time exchange rates**.

Discover where software is cheapest — and how using a **VPN** can unlock major savings.
""")
st.divider()
selected_product = st.selectbox("Choose a product to compare", products) # Allow users to select a product

# Get exchange API key
try:
    exchange_api_key = st.secrets.get("EXCHANGE_API_KEY")
except Exception:
    exchange_api_key = None

# Fallback to .env
if not exchange_api_key:
    exchange_api_key = os.getenv("EXCHANGE_API_KEY")

if not exchange_api_key:
    st.error("Missing EXCHANGE_API_KEY in secrets or environment variables.")

# Fetch latest currency conversion rates (base = USD)
EXCHANGE_API_URL = f"https://v6.exchangerate-api.com/v6/{exchange_api_key}/latest/USD"
response = requests.get(EXCHANGE_API_URL)
# st.write("Actual URL fetched from:", response.url)
# st.write("Raw response content:", response.text)
conversion_rates = response.json().get("conversion_rates", {})
# st.write("Fetched exchange rates:", conversion_rates)

# Streamlit UI
target_currency = st.selectbox("Display prices in:", sorted(conversion_rates.keys()), index=sorted(conversion_rates.keys()).index("USD")) # Allow users to select currency


# Convert currency
def convert_currency(amount, from_currency):
    try:
        from_rate = conversion_rates.get(from_currency)
        to_rate = conversion_rates.get(target_currency)
        if from_rate and to_rate:
            return round((amount / from_rate) * to_rate, 2)
        else:
            return None
    except Exception:
        return None

# Add a new column for converted prices
df["Converted Amount"] = df.apply(lambda row: convert_currency(row["Amount"], row["Currency"]),axis=1)

# Filter to selected product
product_df = df[df["Product"] == selected_product]

# Keep only the latest entry per region
product_df["Timestamp"] = pd.to_datetime(product_df["Timestamp"])
last_updated = product_df["Timestamp"].max()
latest_df = product_df.sort_values("Timestamp").groupby("Region", as_index=False).last()
df_sorted = latest_df.sort_values(by="Converted Amount") # Sort by converted amount

# Append currency code to Converted Amount values
df_sorted["Converted Amount"] = df_sorted["Converted Amount"].map(
    lambda x: f"{x:.2f} {target_currency}" if pd.notnull(x) else "N/A"
)

# Show results
st.subheader(f"Latest prices for **{selected_product}**")
columns_to_show = ["Region", "Converted Amount", "Period"]

# Highlight cheapest option
# def highlight_min_row(s):
#     is_min = s["Converted Amount"] == df_sorted["Converted Amount"].min()
#     return ['background-color: #d4edda' if is_min else '' for _ in s]
#
# # Format converted amount to 2 decimal places (as string)
# df_sorted["Converted Amount"] = df_sorted["Converted Amount"].map(lambda x: f"{x:.2f} {target_currency}")
#
# styled_df = df_sorted[columns_to_show].style.apply(highlight_min_row, axis=1)

# Cheapest option callout
cheapest_region = latest_df.loc[latest_df["Converted Amount"].idxmin(), "Region"]
cheapest_price = latest_df["Converted Amount"].min()
st.success(f"💰 Best deal: **{cheapest_region}** at **{cheapest_price:.2f}** {target_currency}")

# Display dataframe
st.dataframe(df_sorted[columns_to_show], hide_index=1)

# "Last updated" timestamp
formatted_time = last_updated.strftime("%B %d, %Y at %H:%M")
st.caption(f"Last updated: {formatted_time}")

st.divider()

# VPN promo section

st.markdown("### 🌍 Save with a VPN")

st.markdown("""
Prices for tools like Adobe Creative Cloud vary by region.  
With a **VPN**, you can access the best regional deals — even if you're not in that country.

Try these trusted VPNs (affiliate links):

- 🔒 [**NordVPN** – Up to 70% off](https://your-affiliate-link.com)
- 🦈 [**Surfshark** – One of the cheapest VPNs](https://your-affiliate-link.com)
- 🌐 [**ExpressVPN** – Fast, secure, and global](https://your-affiliate-link.com)

> Use a VPN, choose the region with the lowest price, and subscribe directly. Easy.
""")


# FAQ Section
with st.expander("ℹ️ How does this work?"):
    st.markdown("""
    We track official prices from product websites across different countries.

    Each day, we:
    - ✅ Scrape pricing pages from selected regions
    - 💱 Convert prices to your preferred currency
    - 🔁 Update this dashboard with the latest rates and values

    **Why do prices vary by country?**  
    Companies often adjust pricing based on local income levels, tax rules, or currency differences. A VPN can let you access those prices — from anywhere.
    """)

with st.expander("📌 Is it legal to buy from another region?"):
    st.markdown("""
    In most cases, **yes** — as long as the vendor accepts your payment method.

    However, always review the service's **terms of use** and be aware that some companies may enforce geo-restrictions. Using a VPN typically works, but use at your own discretion.
    """)

# Tip section
st.markdown("""
### 🧠 Quick Tip: Always compare before subscribing

Prices can change frequently — sometimes daily — depending on region and currency.
Make sure you’re getting the best deal by checking this tool first!
""")

st.divider()

# Newsletter / CTA
st.markdown("""
**Want updates when prices drop?**  
📬 [Join the waitlist](#) to get notified when we launch tracking alerts.
""")