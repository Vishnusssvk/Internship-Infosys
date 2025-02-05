import os
import time
import random
import requests
import json
import pandas as pd
from datetime import datetime
from typing import List, Type, Dict, Any, Tuple
from pydantic import BaseModel, create_model
import html2text
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
import google.generativeai as genai
import streamlit as st
from typing import List, Optional
from tools import *
# Load environment variables
load_dotenv()
API_KEY = os.getenv('GOOGLE_API_KEY')
if not API_KEY:
    raise ValueError("Please set the GOOGLE_API_KEY environment variable")
# Configure Gemini
genai.configure(api_key=API_KEY)
HEADLESS_OPTIONS = ["--headless", "--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"]

SYSTEM_MESSAGE = """You are an intelligent text extraction and conversion assistant. 
Your task is to extract structured information from the given text and convert it into a pure JSON format. 
Format the output as a JSON array of objects, with each object containing the specified fields.
Extract ALL available entries that match the specified fields.
Do not include any markdown formatting or code block indicators in your response."""

def check_pagination(driver) -> tuple[bool, Optional[List[str]]]:
    """
    Check if the page has pagination and return pagination links if found.
    Returns: (has_pagination, pagination_links)
    """
    common_pagination_selectors = [
        "//ul[contains(@class, 'pagination')]//a",
        "//div[contains(@class, 'pagination')]//a",
        "//nav[contains(@class, 'pagination')]//a",
        "//a[contains(@class, 'page-link')]",
        "//a[contains(@class, 'pagination')]",
        "//button[contains(@class, 'pagination')]"
    ]
    
    for selector in common_pagination_selectors:
        try:
            pagination_elements = driver.find_elements(By.XPATH, selector)
            if pagination_elements:
                # Extract unique href values, filtering out None and javascript:void(0)
                links = list(set(
                    elem.get_attribute('href') for elem in pagination_elements
                    if elem.get_attribute('href') and 
                    'javascript:void(0)' not in elem.get_attribute('href').lower()
                ))
                if links:
                    return True, links
        except:
            continue
    
    return False, None


# def scroll_page(driver, max_scrolls: int = 5) -> bool:
#     """
#     Scroll the page to load dynamic content.
#     Returns: True if page was scrollable, False otherwise
#     """
#     initial_height = driver.execute_script("return document.body.scrollHeight")
#     scrolled = False
    
#     for _ in range(max_scrolls):
#         previous_height = driver.execute_script("return document.body.scrollHeight")
#         driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
#         time.sleep(2)
        
#         new_height = driver.execute_script("return document.body.scrollHeight")
#         if new_height == previous_height:
#             break
#         scrolled = True
    
#     return scrolled


def fetch_html_selenium(url: str) -> dict:
    """
    Fetches HTML content using Selenium with support for both infinite scroll and pagination.
    Returns a dictionary containing the HTML content and metadata about the scraping process.
    """
    options = Options()
    options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
    for option in HEADLESS_OPTIONS:
        options.add_argument(option)
    
    driver = None
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.set_page_load_timeout(30)
        
        result = {
            'html_content': [],
            'pages_scraped': 0,
            'scraping_method': 'single_page',
            'success': False
        }
        
        # Load initial page
        with st.spinner("Loading webpage..."):
            driver.get(url)
            time.sleep(3)
        
        # First try scrolling
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        is_scrollable = scroll_page(driver)
        if is_scrollable:
            result['html_content'].append(driver.page_source)
            result['pages_scraped'] = 1
            result['scraping_method'] = 'infinite_scroll'
            result['success'] = True
        else:
            # If not scrollable, check for pagination
            has_pagination, pagination_links = check_pagination(driver)
            
            if has_pagination and pagination_links:
                result['scraping_method'] = 'pagination'
                # Add the first page
                result['html_content'].append(driver.page_source)
                result['pages_scraped'] += 1
                
                # Scrape subsequent pages
                for page_url in pagination_links[:10]:  # Limit to 10 pages for safety
                    try:
                        with st.spinner(f"Loading page {result['pages_scraped'] + 1}..."):
                            driver.get(page_url)
                            time.sleep(3)
                            
                            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                            result['html_content'].append(driver.page_source)
                            result['pages_scraped'] += 1
                    except Exception as e:
                        st.warning(f"Failed to load page {page_url}: {str(e)}")
                        break
                
                result['success'] = True
            else:
                # No pagination or scrolling - just get the single page
                result['html_content'].append(driver.page_source)
                result['pages_scraped'] = 1
                result['scraping_method'] = 'single_page'
                result['success'] = True
        
        if not result['html_content']:
            raise ValueError("No HTML content retrieved")
        
        return result
    
    except Exception as e:
        raise ValueError(f"Failed to fetch HTML: {str(e)}")
    
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


def scroll_page(driver: webdriver.Chrome) -> None:
    """Scrolls the page to load dynamic content."""
    try:
        with st.spinner("Scrolling page to load dynamic content..."):
            last_height = driver.execute_script("return document.body.scrollHeight")
            
            scroll_progress = st.progress(0)
            while True:
                for i in range(0, last_height, 800):
                    driver.execute_script(f"window.scrollTo(0, {i});")
                    progress = min(i / last_height, 1.0)
                    scroll_progress.progress(progress)
                    time.sleep(0.1)
                
                time.sleep(2)
                new_height = driver.execute_script("return document.body.scrollHeight")
                
                if new_height == last_height:
                    break
                    
                last_height = new_height
            
            driver.execute_script("window.scrollTo(0, 0);")
            scroll_progress.progress(1.0)
            
    except Exception as e:
        pass  

def format_data_with_genai(data: str, fields: List[str], model: str) -> Tuple[List[Dict], int, int, float]:
    """Format data using selected AI model."""
    field_list = ", ".join(field.strip() for field in fields)
    prompt = f"""{SYSTEM_MESSAGE}
Please extract the following fields: {field_list}
Return ONLY a complete, valid JSON array where each object contains these fields.
Extract ALL available entries that match these fields.
Example format: [{{"field1": "value1"}}, {{"field1": "value2"}}]

{data}"""
    
    if model == "gemini flash-1.5":
        generative_model = genai.GenerativeModel("gemini-1.5-flash")
    else:
        st.error("Selected model is not supported")
        st.stop()
        
    input_tokens = generative_model.count_tokens(prompt)
    completion = generative_model.generate_content(prompt)
    
    usage_metadata = completion.usage_metadata
    token_counts = {
        "input_tokens": usage_metadata.prompt_token_count,
        "output_tokens": usage_metadata.candidates_token_count
    }
    
    try:
        formatted_data = json.loads(completion.text)
        if not isinstance(formatted_data, list):
            formatted_data = [formatted_data]
    except json.JSONDecodeError:
        return [], input_tokens, token_counts["output_tokens"], 0
        
    total_cost = (token_counts["input_tokens"] + token_counts["output_tokens"]) * 0.001
    return formatted_data, token_counts["input_tokens"], token_counts["output_tokens"], total_cost

def perform_scrape(url: str, fields: List[str], model: str) -> Tuple[pd.DataFrame, int, int, float]:
    """Main scraping function."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    with st.spinner("Fetching webpage content..."):
        raw_html = fetch_html_selenium(url)
        markdown = markdown = html_to_markdown_with_readability("".join(raw_html['html_content']))
    
    chunks = split_text_into_chunks(markdown, chunk_size=8000)
    
    all_formatted_data = []
    total_input_tokens = 0
    total_output_tokens = 0
    total_cost = 0
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, chunk in enumerate(chunks):
        try:
            status_text.text(f"Processing chunk {i+1} of {len(chunks)}...")
            progress_bar.progress((i + 1) / len(chunks))
            
            formatted_data, input_tokens, output_tokens, chunk_cost = format_data_with_genai(
                chunk, fields, model
            )
            
            all_formatted_data.extend(formatted_data)
            total_input_tokens += input_tokens
            total_output_tokens += output_tokens
            total_cost += chunk_cost
            
        except Exception as e:
            continue  # Suppress error messages for individual chunks
    
    if not all_formatted_data:
        st.error("No data was extracted. Please check your fields and try again.")
        return pd.DataFrame(), 0, 0, 0
        
    return pd.DataFrame(all_formatted_data), total_input_tokens, total_output_tokens, total_cost