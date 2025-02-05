import os
import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st
import json

# Function to create a folder if it doesn't exist
def create_folder(folder_name):
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

# Function to sanitize folder names
def sanitize_folder_name(folder_name):
    return re.sub(r'[\\/*?:"<>|]', '_', folder_name).strip()

# Function to write data to CSV file
def write_to_csv(data, file_path):
    data.to_csv(file_path, index=False, encoding='utf-8')

# Function to write data to XML file using 'etree' parser
def write_to_xml(data, file_path):
    data.to_xml(file_path, index=False, encoding='utf-8', parser='etree')

# Function to write data to JSON file
def write_to_json(data, file_path):
    data.to_json(file_path, orient="records", lines=True)

# Function to scrape data from the page
def scrape_data_from_page(soup):
    data = []
    results = soup.select("[id^=hit-]")
    
    for result in results:
        entry = {
            "Title": result.select_one("h3 a").get_text(strip=True) if result.select_one("h3 a") else "N/A",
            "Schedule": result.select_one(".mt-1.mb-3.font-weight-bold").get_text(strip=True) if result.select_one(".mt-1.mb-3.font-weight-bold") else "N/A",
            "Description": result.select_one("div.result-hit-body > div.mb-2, div.mb-2").get_text(strip=True) if result.select_one("div.result-hit-body > div.mb-2, div.mb-2") else "N/A",
            "Address": " ".join([span.get_text(strip=True) for span in result.select(".mb-3.text-muted .comma_split_line")]) if result.select(".mb-3.text-muted .comma_split_line") else "N/A",
            "Phone": result.select_one(".contact-links ul li:nth-child(1) span.comma_split_line.d-none.d-sm-block.text-body").get_text(strip=True) if result.select_one(".contact-links ul li:nth-child(1) span.comma_split_line.d-none.d-sm-block.text-body") else "N/A",
            "Email": result.select_one(".contact-links ul li:nth-child(2) a").get("href").replace("mailto:", "").strip() if result.select_one(".contact-links ul li:nth-child(2) a") else "N/A",
            "Website": result.select_one(".contact-links ul li:nth-child(3) a").get("href").strip() if result.select_one(".contact-links ul li:nth-child(3) a") else "N/A"
        }
        data.append(entry)
    
    return pd.DataFrame(data)

# Function to scrape all pages of a category
def scrape_category_pages(url):
    all_data = pd.DataFrame()
    while url:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Scrape data from the current page
        page_data = scrape_data_from_page(soup)
        all_data = pd.concat([all_data, page_data], ignore_index=True)

        # Find the next page link
        active_page = soup.select_one("nav > ol > li.page-item.active")
        if active_page:
            next_page = active_page.find_next_sibling("li")
            if next_page and next_page.find("a"):
                url = requests.compat.urljoin(url, next_page.find("a")['href'])
            else:
                url = None  # No more pages
        else:
            url = None
    return all_data

# Recursive function to fetch all nested categories and subcategories
def fetch_nested_categories(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    nested_categories = {}
    
    for block in soup.find_all(['li', 'div'], class_='category-block'):
        sub_link = block.find('a')
        if sub_link:
            sub_name = sub_link.find('div', class_='card-body').text.strip()
            sub_href = sub_link['href']
            full_sub_url = requests.compat.urljoin(url, sub_href)
            nested_categories[sub_name] = full_sub_url
    return nested_categories

# Function to display dropdowns for nested categories and fetch the selected subcategory URL
def select_nested_category(url):
    nested_categories = fetch_nested_categories(url)
    if nested_categories:
        selected_subcategory = st.selectbox("Select a Subcategory", list(nested_categories.keys()))
        next_url = nested_categories[selected_subcategory]
        return select_nested_category(next_url)  # Recursive call to handle further nesting
    else:
        return url  # No more subcategories, return the final URL for scraping

# Streamlit Interface
st.title("Wigan Directory Data Scraper")
st.write("Select a category and subcategory to scrape data from the Wigan directory.")

# Main base URL
base_url = "https://directory.wigan.gov.uk/kb5/wigan/fsd/home.page"

# Use recursive dropdowns to get the final subcategory URL for scraping
selected_url = select_nested_category(base_url)

# Scrape Data
if st.button("Scrape Data"):
    with st.spinner("Scraping data..."):
        scraped_data = scrape_category_pages(selected_url)
        st.success("Data scraping completed!")

    # Display scraped data
    st.dataframe(scraped_data)

    # Save files for download
    folder = 'Wigan_Scraped_Data'
    create_folder(folder)
    csv_path = os.path.join(folder, f"{sanitize_folder_name(selected_url)}.csv")
    xml_path = os.path.join(folder, f"{sanitize_folder_name(selected_url)}.xml")
    json_path = os.path.join(folder, f"{sanitize_folder_name(selected_url)}.json")

    write_to_csv(scraped_data, csv_path)
    write_to_xml(scraped_data, xml_path)
    write_to_json(scraped_data, json_path)

    # Download buttons for CSV, XML, and JSON arranged horizontally
    col1, col2, col3 = st.columns(3)

    with col1:
        with open(csv_path, "rb") as csv_file:
            st.download_button(label="Download CSV", data=csv_file, file_name=f"{sanitize_folder_name(selected_url)}.csv", mime="text/csv")

    with col2:
        with open(xml_path, "rb") as xml_file:
            st.download_button(label="Download XML", data=xml_file, file_name=f"{sanitize_folder_name(selected_url)}.xml", mime="application/xml")

    with col3:
        with open(json_path, "rb") as json_file:
            st.download_button(label="Download JSON", data=json_file, file_name=f"{sanitize_folder_name(selected_url)}.json", mime="application/json")