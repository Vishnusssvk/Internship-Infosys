import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import json

# Base URL
base_url = "https://publiclibraries.com"

# Directory to save library data
# os.makedirs("state_libraries", exist_ok=True)

def scrape_state_links():
    url = f"{base_url}/state/"
    response = requests.get(url)

    if response.status_code != 200:
        st.error(f"Failed to retrieve the state links. Status code: {response.status_code}")
        return []

    soup = BeautifulSoup(response.content, "html.parser")
    state_links_section = soup.find("div", class_="entry-content")
    if not state_links_section:
        st.error("Unable to find the state links section.")
        return []

    # Extract and return state links
    state_links = []
    for a_tag in state_links_section.find_all("a"):
        state_name = a_tag.text.strip()
        state_url = a_tag['href'].strip()
        full_url = f"{base_url}{state_url}" if not state_url.startswith("http") else state_url
        state_links.append([state_name, full_url])

    return state_links

def scrape_libraries_for_state(state_url):
    response = requests.get(state_url)
    if response.status_code != 200:
        st.error(f"Failed to retrieve library data. Status code: {response.status_code}")
        return pd.DataFrame()

    soup = BeautifulSoup(response.content, "html.parser")
    table = soup.find("table")
    if not table:
        st.warning("No library data found.")
        return pd.DataFrame()

    # Extract headers and rows into a DataFrame
    headers = [th.text.strip() for th in table.find_all("th")]
    rows = [[td.text.strip() for td in row.find_all("td")] for row in table.find_all("tr")[1:]]
    return pd.DataFrame(rows, columns=headers)

def download_file(data, file_type):
    """Helper function to download data in CSV, Excel, or JSON format."""
    if file_type == "CSV":
        return data.to_csv(index=False).encode('utf-8')
    elif file_type == "Excel":
        excel_path = "library_data.xlsx"
        data.to_excel(excel_path, index=False, engine='openpyxl')
        with open(excel_path, 'rb') as f:
            return f.read()
    elif file_type == "JSON":
        return data.to_json(orient="records", indent=2).encode('utf-8')

# Streamlit App
st.title(" Public Libraries Information")


# Step 1: Scrape state links and display in a dropdown
state_links = scrape_state_links()
if state_links:
    state_names = [state[0] for state in state_links]
    selected_state = st.selectbox("Select a state:", state_names)

    # Step 2: Display library data for the selected state
    if selected_state:
        state_url = dict(state_links)[selected_state]
        data = scrape_libraries_for_state(state_url)

        if not data.empty:
            st.dataframe(data)

            # Step 3: Download menu with CSV, Excel, and JSON options
            st.subheader("Download Data")
            download_option = st.selectbox("Choose a format:", ["CSV", "Excel", "JSON"])

            if st.button("Download"):
                file_data = download_file(data, download_option)
                file_extension = download_option.lower()
                mime_type = (
                    "text/csv" if file_extension == "csv" else
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.xlxs"
                    if file_extension == "excel" else "application/json"
                )

                st.download_button(
                    label=f"Download {download_option}",
                    data=file_data,
                    file_name=f"library_data.{file_extension}",
                    mime=mime_type
                )
