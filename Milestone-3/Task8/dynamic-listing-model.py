import os
import time
import random
import requests
from datetime import datetime
from typing import List, Type
from pydantic import BaseModel, create_model
import html2text
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
import google.generativeai as genai
import streamlit as st
import pandas as pd

# Load environment variables
load_dotenv()
API_KEY = os.getenv('GOOGLE_API_KEY')

# Constants
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
]
HEADLESS_OPTIONS = ["--headless", "--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"]

SYSTEM_MESSAGE = """You are an intelligent text extraction and conversion assistant. 
Your task is to extract structured information from the given text and convert it into a pure JSON format. 
The JSON should contain only the structured data extracted from the text, focusing exclusively on the specified input fields."""

USER_MESSAGE = "Extract the following information from the provided text:\nPage content:\n\n"

# Set up Google Gemini API
if API_KEY:
    genai.configure(api_key=API_KEY)
else:
    raise ValueError("API Key is missing for Google Gemini API")

# Button to trigger scraping
def perform_scrape(url: str, fields: List[str], model="gemini-1.5-flash"):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    raw_html = fetch_html_selenium(url)
    markdown = html_to_markdown_with_readability(raw_html)
    save_raw_data(markdown, timestamp)
    
    # Define models dynamically based on user fields
    DynamicListingModel = create_dynamic_listing_model(fields)
    DynamicListingsContainer = create_listings_container_model(DynamicListingModel)
    
    # Get formatted data from Gemini
    formatted_data, input_tokens, output_tokens, total_cost = format_data_with_genai(
        markdown, DynamicListingsContainer, model, fields
    )
    
    # Save to dataframe and return details
    df = save_formatted_data(formatted_data, timestamp)
    return df, formatted_data, markdown, input_tokens, output_tokens, total_cost, timestamp

# Create dynamic listing model
def create_dynamic_listing_model(field_names: List[str]) -> Type[BaseModel]:
    field_definitions = {field: (str, ...) for field in field_names}
    return create_model('DynamicListingModel', **field_definitions)

# Create container model for listings
def create_listings_container_model(listing_model: Type[BaseModel]) -> Type[BaseModel]:
    return create_model('DynamicListingsContainer', listings=(List[listing_model], ...))

# Convert HTML to Markdown with readability
def html_to_markdown_with_readability(raw_html: str) -> str:
    markdown_converter = html2text.HTML2Text()
    markdown_converter.ignore_links = False
    return markdown_converter.handle(raw_html)

# Save raw HTML data for future reference with UTF-8 encoding
def save_raw_data(data, timestamp):
    with open(f"raw_data_{timestamp}.md", "w", encoding="utf-8") as file:
        file.write(data)

# Format data using Google Gemini AI
def format_data_with_genai(data, container_model, model="gemini-1.5-flash", fields=None):
    # Update prompt to specify fields
    specified_fields = ", ".join(fields) if fields else "all fields"
    prompt = f"{SYSTEM_MESSAGE} focusing on the following fields: {specified_fields}.\n" + USER_MESSAGE + data
    
    generative_model = genai.GenerativeModel(model)
    
    # Count input tokens
    input_tokens = generative_model.count_tokens(prompt)
    completion = generative_model.generate_content(prompt)
    
    # Process output
    usage_metadata = completion.usage_metadata
    token_counts = {
        "input_tokens": usage_metadata.prompt_token_count,
        "output_tokens": usage_metadata.candidates_token_count
    }
    
    formatted_data = completion.text
    total_cost = calculate_price(token_counts["input_tokens"], token_counts["output_tokens"], model)
    return formatted_data, token_counts["input_tokens"], token_counts["output_tokens"], total_cost

# Save formatted data to a DataFrame
def save_formatted_data(data, timestamp):
    df = pd.DataFrame([data])
    df.to_csv(f"formatted_data_{timestamp}.csv", index=False)
    return df

# Calculate cost of tokens
def calculate_price(input_tokens, output_tokens, model):
    cost_per_token = 0.001  # Example rate
    total_tokens = input_tokens + output_tokens
    return total_tokens * cost_per_token

# Selenium WebDriver setup and fetch HTML
def fetch_html_selenium(url: str) -> str:
    options = Options()
    options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
    for option in HEADLESS_OPTIONS:
        options.add_argument(option)
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)
    time.sleep(3)
    scroll_page(driver)
    html_content = driver.page_source
    driver.quit()
    return html_content

# Scroll page to load dynamic content
def scroll_page(driver):
    """Scroll in increments to fully load dynamic content."""
    total_height = int(driver.execute_script("return document.body.scrollHeight"))
    scroll_increment = 500  # Adjust based on the page's layout and loading behavior
    for height in range(0, total_height, scroll_increment):
        driver.execute_script(f"window.scrollTo(0, {height});")
        time.sleep(0.5)  # Adjust based on the loading speed
    driver.execute_script("window.scrollTo(0, 0);")

# Streamlit display
def display_results_in_streamlit(df, formatted_data, tokens, total_cost):
    st.write("Extracted Data Table")
    st.table(df)
    st.write("Formatted Data:")
    st.write(formatted_data)
    st.write("Token Counts")
    st.json(tokens)
    st.write(f"Total Cost: ${total_cost:.4f}")

# Streamlit interface
st.title("AI-Powered Web Scraper with Google Gemini API")
url = st.text_input("Enter URL to Scrape")
fields = st.text_area("Enter fields to extract (comma-separated)").split(',')

if st.button("Start Scraping"):
    if url and fields:
        df, formatted_data, markdown, input_tokens, output_tokens, total_cost, timestamp = perform_scrape(url, fields)
        display_results_in_streamlit(df, formatted_data, {"input_tokens": input_tokens, "output_tokens": output_tokens}, total_cost)
    else:
        st.warning("Please enter both a URL and fields to extract.")
import os
import time
import random
import requests
from datetime import datetime
from typing import List, Type
from pydantic import BaseModel, create_model
import html2text
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
import google.generativeai as genai
import streamlit as st
import pandas as pd

# Load environment variables
load_dotenv()
API_KEY = os.getenv('GOOGLE_API_KEY')

# Constants
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
]
HEADLESS_OPTIONS = ["--headless", "--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"]

SYSTEM_MESSAGE = """You are an intelligent text extraction and conversion assistant. 
Your task is to extract structured information from the given text and convert it into a pure JSON format. 
The JSON should contain only the structured data extracted from the text, focusing exclusively on the specified input fields."""

USER_MESSAGE = "Extract the following information from the provided text:\nPage content:\n\n"

# Set up Google Gemini API
if API_KEY:
    genai.configure(api_key=API_KEY)
else:
    raise ValueError("API Key is missing for Google Gemini API")

# Button to trigger scraping
def perform_scrape(url: str, fields: List[str], model="gemini-1.5-flash"):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    raw_html = fetch_html_selenium(url)
    markdown = html_to_markdown_with_readability(raw_html)
    save_raw_data(markdown, timestamp)
    
    # Define models dynamically based on user fields
    DynamicListingModel = create_dynamic_listing_model(fields)
    DynamicListingsContainer = create_listings_container_model(DynamicListingModel)
    
    # Get formatted data from Gemini
    formatted_data, input_tokens, output_tokens, total_cost = format_data_with_genai(
        markdown, DynamicListingsContainer, model, fields
    )
    
    # Save to dataframe and return details
    df = save_formatted_data(formatted_data, timestamp)
    return df, formatted_data, markdown, input_tokens, output_tokens, total_cost, timestamp

# Create dynamic listing model
def create_dynamic_listing_model(field_names: List[str]) -> Type[BaseModel]:
    field_definitions = {field: (str, ...) for field in field_names}
    return create_model('DynamicListingModel', **field_definitions)

# Create container model for listings
def create_listings_container_model(listing_model: Type[BaseModel]) -> Type[BaseModel]:
    return create_model('DynamicListingsContainer', listings=(List[listing_model], ...))

# Convert HTML to Markdown with readability
def html_to_markdown_with_readability(raw_html: str) -> str:
    markdown_converter = html2text.HTML2Text()
    markdown_converter.ignore_links = False
    return markdown_converter.handle(raw_html)

# Save raw HTML data for future reference with UTF-8 encoding
def save_raw_data(data, timestamp):
    with open(f"raw_data_{timestamp}.md", "w", encoding="utf-8") as file:
        file.write(data)

# Format data using Google Gemini AI
def format_data_with_genai(data, container_model, model="gemini-1.5-flash", fields=None):
    # Update prompt to specify fields
    specified_fields = ", ".join(fields) if fields else "all fields"
    prompt = f"{SYSTEM_MESSAGE} focusing on the following fields: {specified_fields}.\n" + USER_MESSAGE + data
    
    generative_model = genai.GenerativeModel(model)
    
    # Count input tokens
    input_tokens = generative_model.count_tokens(prompt)
    completion = generative_model.generate_content(prompt)
    
    # Process output
    usage_metadata = completion.usage_metadata
    token_counts = {
        "input_tokens": usage_metadata.prompt_token_count,
        "output_tokens": usage_metadata.candidates_token_count
    }
    
    formatted_data = completion.text
    total_cost = calculate_price(token_counts["input_tokens"], token_counts["output_tokens"], model)
    return formatted_data, token_counts["input_tokens"], token_counts["output_tokens"], total_cost

# Save formatted data to a DataFrame
def save_formatted_data(data, timestamp):
    df = pd.DataFrame([data])
    df.to_csv(f"formatted_data_{timestamp}.csv", index=False)
    return df

# Calculate cost of tokens
def calculate_price(input_tokens, output_tokens, model):
    cost_per_token = 0.001  # Example rate
    total_tokens = input_tokens + output_tokens
    return total_tokens * cost_per_token

# Selenium WebDriver setup and fetch HTML
def fetch_html_selenium(url: str) -> str:
    options = Options()
    options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
    for option in HEADLESS_OPTIONS:
        options.add_argument(option)
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)
    time.sleep(3)
    scroll_page(driver)
    html_content = driver.page_source
    driver.quit()
    return html_content

# Scroll page to load dynamic content
def scroll_page(driver):
    """Scroll in increments to fully load dynamic content."""
    total_height = int(driver.execute_script("return document.body.scrollHeight"))
    scroll_increment = 500  # Adjust based on the page's layout and loading behavior
    for height in range(0, total_height, scroll_increment):
        driver.execute_script(f"window.scrollTo(0, {height});")
        time.sleep(0.5)  # Adjust based on the loading speed
    driver.execute_script("window.scrollTo(0, 0);")

# Streamlit display
def display_results_in_streamlit(df, formatted_data, tokens, total_cost):
    st.write("Extracted Data Table")
    st.table(df)
    st.write("Formatted Data:")
    st.write(formatted_data)
    st.write("Token Counts")
    st.json(tokens)
    st.write(f"Total Cost: ${total_cost:.4f}")

# Streamlit interface
st.title("AI-Powered Web Scraper with Google Gemini API")
url = st.text_input("Enter URL to Scrape")
fields = st.text_area("Enter fields to extract (comma-separated)").split(',')

if st.button("Start Scraping"):
    if url and fields:
        df, formatted_data, markdown, input_tokens, output_tokens, total_cost, timestamp = perform_scrape(url, fields)
        display_results_in_streamlit(df, formatted_data, {"input_tokens": input_tokens, "output_tokens": output_tokens}, total_cost)
    else:
        st.warning("Please enter both a URL and fields to extract.")