import os
import re
import csv
import requests
import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import streamlit as st
import asyncio
import sys
import logging 
from io import BytesIO

# Set logging to ERROR level to suppress unnecessary logs
logging.basicConfig(level=logging.ERROR)

# Ensure ProactorEventLoopPolicy on Windows to avoid subprocess issues
if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

def create_directory_if_not_exists(dir_path):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

def sanitize_directory_name(dir_name):
    return re.sub(r'[<>:"/\\|?*]', '', dir_name).strip()

def clean_string(s):
    return str(s).replace('\u200b', '').strip()

def fetch_child_categories(category_link):
    try:
        response = requests.get(category_link)
        response.raise_for_status()
        html_content = BeautifulSoup(response.text, 'html.parser')

        category_elements = html_content.find_all(['li', 'div'], class_='category-block')
        categories = {}
        for category in category_elements:
            category_anchor = category.find('a')
            if category_anchor:
                name = clean_string(category_anchor.text)
                url = category_anchor['href']
                full_url = requests.compat.urljoin(category_link, url)
                categories[name] = full_url
        return categories
    except requests.RequestException as error:
        st.error(f"Failed to fetch {category_link}: {error}")
        return {}

def extract_data_from_page(page):
    result_items = page.query_selector_all('.result_hit')
    scraped_data = []

    for item in result_items:
        title = item.query_selector('h3 a')
        schedule = item.query_selector('.clearfix.mt-1.mb-3.font-weight-bold')
        description = item.query_selector('.result-hit-body .mb-2')
        location = item.query_selector_all('.comma_split_line')
        phone = item.query_selector('.fa-phone + .comma_split_line, .fa-phone + a')
        email = item.query_selector('.fa-envelope + a')
        website = item.query_selector('.fa-globe + a')

        scraped_data.append([
            clean_string(title.inner_text() if title else "N/A"),
            clean_string(schedule.inner_text() if schedule else "N/A"),
            clean_string(description.inner_text() if description else "N/A"),
            clean_string(", ".join([loc.inner_text() for loc in location]) if location else "N/A"),
            clean_string(phone.inner_text() if phone else "N/A"),
            clean_string(email.inner_text() if email else "N/A"),
            clean_string(website.get_attribute('href') if website else "N/A"),
        ])

    return scraped_data

def scrape_all_pages_in_category(start_url):
    complete_data = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()

        while True:
            page.goto(start_url, wait_until="domcontentloaded")
            data = extract_data_from_page(page)
            if not data:
                break

            complete_data.extend(data)

            next_button = page.query_selector('ol.pagination .page-link[title="Go to Next Page"]')
            if next_button:
                next_url = next_button.get_attribute('href')
                if next_url:
                    start_url = requests.compat.urljoin(start_url, next_url)
                    page.wait_for_timeout(1000)
                else:
                    break
            else:
                break

        browser.close()

    if complete_data:
        df = pd.DataFrame(complete_data, columns=['Title', 'Schedule', 'Description', 'Location', 'Phone', 'Email', 'Website'])
        st.dataframe(df)

        csv = df.to_csv(index=False).encode('utf-8')
        excel = BytesIO()
        df.to_excel(excel, index=False, engine='xlsxwriter')
        excel.seek(0)
        json = df.to_json(orient='records').encode('utf-8')

        st.download_button("Download as CSV", data=csv, file_name="scraped_data.csv", mime="text/csv")
        st.download_button("Download as Excel", data=excel, file_name="scraped_data.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.download_button("Download as JSON", data=json, file_name="scraped_data.json", mime="application/json")
    else:
        st.warning("No data to display...........")

def main():
    st.title("Dynamic Web Scraper for Wigan Directory")
    st.write("Select a category to scrape data dynamically.")

    initial_url = "https://directory.wigan.gov.uk/kb5/wigan/fsd/home.page"
    selected_category_url = initial_url

    while True:
        categories = fetch_child_categories(selected_category_url)
        if not categories:
            st.warning("No further categories found. Scraping this page directly...")
            scrape_all_pages_in_category(selected_category_url)
            break

        category_name = st.selectbox("Select a category", options=list(categories.keys()))
        if not category_name:
            st.stop()

        selected_category_url = categories[category_name]

if __name__ == "__main__":
    main()
