import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json
from dotenv import load_dotenv
import os
import requests

# Import font from Google Fonts
st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,200..800&display=swap" rel="stylesheet">
    <style>
    html, body, div, span, p, label, section, h1, h2, h3, h4, h5, h6 {
        font-family: 'Bricolage Grotesque', sans-serif !important;
    }
    .stMarkdown, .stDataFrame, .css-ffhzg2, .css-1v0mbdj, .css-1d391kg {
        font-family: 'Bricolage Grotesque', sans-serif !important;
    }
    </style>
""", unsafe_allow_html=True)

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
@st.cache_data(ttl=86400) # Cache for 24 hours
def load_sheet_data(sheet_name):
    spreadsheet = gc.open(sheet_name)
    worksheet = spreadsheet.sheet1 # Select the first worksheet
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

df = load_sheet_data("Global Pricing")

products = df["Product"].unique() # Extract list of unique products

# Streamlit UI
st.markdown("# Compare Software Prices by Country")
st.badge("Beta", color="grey")
st.markdown("""
Looking to save on software?

This tool helps you compare prices for products like **Adobe Creative Cloud**, **VPN services**, and other **digital tools** across multiple countries. Prices are shown in your preferred currency using **real-time exchange rates**.

""")
st.divider()

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
@st.cache_data(ttl=86400) # Cache for 24 hours
def fetch_conversion_rates(api_key):
    url = f"https://v6.exchangerate-api.com/v6/{exchange_api_key}/latest/USD"
    response = requests.get(url)
    return response.json().get("conversion_rates", {})

# st.write("Actual URL fetched from:", response.url)
# st.write("Raw response content:", response.text)
conversion_rates = fetch_conversion_rates(exchange_api_key)
# st.write("Fetched exchange rates:", conversion_rates)

# Streamlit UI
col1, col2 = st.columns([3, 1])

with col1:
    selected_product = st.selectbox("**Choose a product to compare**", products) # Allow users to select a product
with col2:
    target_currency = st.selectbox("**Display prices in**", sorted(conversion_rates.keys()), index=sorted(conversion_rates.keys()).index("USD")) # Allow users to select currency


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
columns_to_show = ["Region Name", "Converted Amount", "Period"]

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
cheapest_region = latest_df.loc[latest_df["Converted Amount"].idxmin(), "Region Name"]
cheapest_price = latest_df["Converted Amount"].min()
with st.container(border=1):
    st.badge("**CHEAPEST REGION**", color="green")
    st.markdown(f"### :green[{cheapest_region}] for :primary-background[**{cheapest_price:.2f}**:small[{target_currency}]]")

# Display dataframe
region_count = len(latest_df)
with st.expander(f"View prices across all **{region_count}** regions"):
    st.dataframe(df_sorted[columns_to_show], hide_index=1)

# "Last updated" timestamp
formatted_time = last_updated.strftime("%B %d, %Y at %H:%M")
st.caption(f"Last updated: {formatted_time}")

st.divider()

# VPN promo section
# st.subheader("Get the best price")
# st.markdown("""
# Prices for tools like Adobe Creative Cloud vary by region.
# With a **VPN**, you can access the best regional deals — even if you're not in that country.
# """)
# col1, col2 = st.columns(2, border=True)
# with col1:
#     st.markdown("### Step 1")
#     st.markdown("**Set Your Region with a VPN**")
#     st.markdown(f"To get the best price, connect to **{cheapest_region}**.")
#     st.link_button("🌍 Get NordVPN", "https://go.nordvpn.net/aff_c?offer_id=15&aff_id=120959&url_id=902", type="primary")
#
# with col2:
#     st.markdown("### Step 2")
#     st.markdown(f"**Get {selected_product}**")
#     st.markdown("Buy from the official website.")
#     st.link_button("🎁 Buy Adobe Creative Cloud", "https://your-adobe-affiliate-link.com", type="primary")
#
#
# # FAQ Section
# with st.expander("ℹ️ How does this work?"):
#     st.markdown("""
#     We track official prices from product websites across different countries.
#
#     Each day, we:
#     - ✅ Scrape pricing pages from selected regions
#     - 💱 Convert prices to your preferred currency
#     - 🔁 Update this dashboard with the latest rates and values
#
#     **Why do prices vary by country?**
#     Companies often adjust pricing based on local income levels, tax rules, or currency differences. A VPN can let you access those prices — from anywhere.
#     """)
#
# with st.expander("📌 Is it legal to buy from another region?"):
#     st.markdown("""
#     In most cases, **yes** — as long as the vendor accepts your payment method.
#
#     However, always review the service's **terms of use** and be aware that some companies may enforce geo-restrictions. Using a VPN typically works, but use at your own discretion.
#     """)

# Tip section
st.markdown("""
### 🧠 Quick Tip: Always compare before subscribing

Prices can change frequently — sometimes daily — depending on region and currency.
Make sure you’re getting the best deal by checking this tool first!
""")

st.divider()

# Footer
st.markdown("""
---
[Home](#) | [FAQ](#) | [Privacy Policy](#) | [Terms](#) | [Contact](#)  
_This site uses affiliate links. We may earn a small commission when you click through — at no extra cost to you._  
""")

# Newsletter / CTA
st.markdown("""
**Want updates when prices drop?**  
📬 [Join the waitlist](#) to get notified when we launch tracking alerts.
""")