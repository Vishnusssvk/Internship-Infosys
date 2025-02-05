import csv
import json
import time
import pandas as pd
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementNotInteractableException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import streamlit as st

# Common function to set up the WebDriver
def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Uncomment for headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver

# Scrape Behance Assets with search functionality
def scrape_behance_assets(search_keyword, num_cards):
    driver = setup_driver()
    driver.get("https://www.behance.net/assets?tracking_source=nav20")

    # Wait for the search input to be present
    try:
        search_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Search Assets..."]'))  # Selector for Assets
        )
        search_input.clear()  # Clear any existing text
        search_input.send_keys(search_keyword)
        search_input.send_keys(Keys.RETURN)
        time.sleep(3)  # Give time for the results to load
    except (TimeoutException, ElementNotInteractableException):
        st.error("Search input field not found on Assets page.")
        driver.quit()
        return pd.DataFrame()  # Return an empty DataFrame

    asset_cards = []
    start_time = time.time()

    while len(asset_cards) < num_cards:
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
        time.sleep(2)

        cards = driver.find_elements(By.CSS_SELECTOR, 'div.ProjectCoverNeue-root-B1h')
        if len(cards) == len(asset_cards):
            break
        asset_cards = cards

        # Timeout condition
        if time.time() - start_time > 30:
            break

    scraped_assets = []
    for card in asset_cards[:num_cards]:
        try:
            title = card.get_attribute('aria-label') or "N/A"
            href = card.find_element(By.CSS_SELECTOR, 'a[href]').get_attribute('href') or "N/A"
            # These could be different elements; adjust accordingly based on your inspection
            appreciations = driver.execute_script(
                "return arguments[0].querySelector('span[title]').getAttribute('title')", card
            ) or "0"
            views = driver.execute_script(
                "return arguments[0].querySelector('span[title]').getAttribute('title')", card
            ) or "0"
            scraped_assets.append({
                "Title": title,
                "Project URL": href,
                "Appreciations": appreciations,
                "Views": views
            })
        except NoSuchElementException:
            pass  # Skip on error without logging

    driver.quit()
    return pd.DataFrame(scraped_assets)

# Scrape Behance Jobs with search functionality
def scrape_behance_jobs(search_keyword, num_cards):
    driver = setup_driver()
    driver.get("https://www.behance.net/joblist?tracking_source=nav20")

    # Wait for the search input to be present
    try:
        search_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Search Full-Time Jobs..."]'))  # Updated selector for Jobs
        )
        search_input.clear()  # Clear any existing text
        search_input.send_keys(search_keyword)
        search_input.send_keys(Keys.RETURN)
        time.sleep(3)  # Give time for the results to load
    except (TimeoutException, ElementNotInteractableException):
        st.error("Search input field not found on Jobs page.")
        driver.quit()
        return pd.DataFrame()  # Return an empty DataFrame

    job_cards = []
    start_time = time.time()

    while len(job_cards) < num_cards:
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
        time.sleep(2)

        cards = driver.find_elements(By.XPATH, '//div[contains(@class, "e2e-JobCard-card")]')
        if len(cards) == len(job_cards):
            break
        job_cards = cards

        # Timeout condition
        if time.time() - start_time > 30:
            break

    scraped_jobs = []
    for card in job_cards[:num_cards]:
        try:
            title = card.find_element(By.XPATH, './/h3').text.strip() or "N/A"
            company = card.find_element(By.XPATH, './/p[contains(@class, "JobCard-company-GQS")]').text.strip() or "N/A"
            location = card.find_element(By.XPATH, './/p[contains(@class, "JobCard-jobLocation-sjd")]').text.strip() or "N/A"
            time_posted = card.find_element(By.XPATH, './/span[contains(@class, "JobCard-time-Cvz")]').text.strip() or "N/A"
            scraped_jobs.append({
                "Title": title,
                "Company": company,
                "Location": location,
                "Time Posted": time_posted
            })
        except NoSuchElementException:
            pass  # Skip on error without logging

    driver.quit()
    return pd.DataFrame(scraped_jobs)

# Function to download data in multiple formats
def download_file(data, file_type):
    buffer = BytesIO()
    if file_type == "CSV":
        data.to_csv(buffer, index=False)
    elif file_type == "Excel":
        data.to_excel(buffer, index=False, engine='openpyxl')
    elif file_type == "JSON":
        buffer.write(data.to_json(orient="records").encode())
    buffer.seek(0)
    return buffer

# Streamlit UI
st.title("Behance Scraper")
st.subheader("Choose what to scrape:")
option = st.selectbox("Select an option:", ["Assets", "Jobs"])

search_keyword = st.text_input("Enter search keyword:")
num_records = st.number_input("Enter the number of records to scrape:", min_value=1, max_value=500, value=10)

if st.button("Scrape"):
    if search_keyword:
        if option == "Assets":
            data = scrape_behance_assets(search_keyword, num_records)
        elif option == "Jobs":
            data = scrape_behance_jobs(search_keyword, num_records)

        st.subheader("Scraped Data")
        if not data.empty:
            st.write(data)
        else:
            st.warning("No matches found.")

        # File download section
        file_type = st.selectbox("Choose file type for download:", ["CSV", "Excel", "JSON"])
        st.download_button(
            label=f"Download {file_type}",
            data=download_file(data, file_type),
            file_name=f"behance_data.{file_type.lower()}",
            mime=f"text/{file_type.lower()}"
        )
    else:
        st.warning("Please enter a search keyword before scraping.")
