import streamlit as st
import requests
import pandas as pd

# --------- API Configuration ----------
API_BASE_URL = "http://backend:8000/scrape"


# --------- Streamlit UI ----------
st.set_page_config(page_title="Restaurant Scraper", layout="centered")

st.title("🍽️ Restaurant Platform Scraper")
st.markdown("Enter a restaurant URL from **Swiggy**, **Zomato**, or **MyStore** to scrape data.")

url_input = st.text_input("Restaurant URL")

if st.button("Scrape Data"):
    if not url_input:
        st.error("Please enter a valid URL.")
    else:
        with st.spinner("Scraping in progress..."):
            try:
                response = requests.post(API_BASE_URL, json={"url": url_input})
                response.raise_for_status()
                data = response.json()

                st.success(f"Scraping successful for {data['restaurant']} in {data['city']} ({data['platform'].capitalize()})")
                st.write(f"Total Items Found: {data['item_count']}")

                # Display data
                df = pd.DataFrame(data["data"])
                st.dataframe(df)

                # Download links (if hosted or saved to a public bucket)
                if data.get("items_csv"):
                    st.markdown(f"📄 [Download Items CSV]({API_BASE_URL}/{data['items_csv']})", unsafe_allow_html=True)
                if data.get("offers_csv"):
                    st.markdown(f"🎁 [Download Offers CSV]({API_BASE_URL}/{data['offers_csv']})", unsafe_allow_html=True)

            except requests.exceptions.HTTPError as http_err:
                st.error(f"HTTP error: {response.status_code} - {response.json().get('detail')}")
            except Exception as e:
                st.error(f"Unexpected error: {str(e)}")
