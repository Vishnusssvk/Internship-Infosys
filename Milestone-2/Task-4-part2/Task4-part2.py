import os
import re
import csv
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# -------------------- Helper Functions --------------------

def create_directory_if_not_exists(dir_path):
    """Ensures the directory exists by creating it if necessary."""
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

def sanitize_directory_name(dir_name):
    """Cleans the directory name to remove invalid characters."""
    return re.sub(r'[<>:"/\\|?*]', '', dir_name).strip()

def clean_string(s):
    """Cleans and sanitizes string input."""
    return str(s).replace('\u200b', '').strip()

# -------------------- Playwright Scraping Logic --------------------

def extract_data_from_page(browser_page, page_index):
    """Scrapes data from a single page."""
    print(f"Scraping page {page_index}...")

    try:
        browser_page.wait_for_selector('.result_hit', timeout=5000)
    except Exception as error:
        print(f"Error waiting for selector: {error}")
        return []

    result_items = browser_page.query_selector_all('.result_hit')

    scraped_data = []
    for item in result_items:
        title_element = item.query_selector('h3 a')
        title_value = clean_string(title_element.inner_text() if title_element else "N/A")

        schedule_element = item.query_selector('.clearfix.mt-1.mb-3.font-weight-bold')
        schedule_value = clean_string(schedule_element.inner_text() if schedule_element else "N/A")

        description_element = item.query_selector('.result-hit-body .mb-2')
        description_value = clean_string(description_element.inner_text() if description_element else "N/A")

        location_elements = item.query_selector_all('.comma_split_line')
        location_value = clean_string(", ".join([clean_string(loc.inner_text()) for loc in location_elements]) if location_elements else "N/A")

        phone_element = item.query_selector('.fa-phone + .comma_split_line, .fa-phone + a')
        phone_value = clean_string(phone_element.inner_text() if phone_element else "N/A")

        email_element = item.query_selector('.fa-envelope + a')
        email_value = clean_string(email_element.inner_text() if email_element else "N/A")

        website_element = item.query_selector('.fa-globe + a')
        website_value = clean_string(website_element.get_attribute('href') if website_element else "N/A")

        scraped_data.append([title_value, schedule_value, description_value, location_value, phone_value, email_value, website_value])

    print(f"Total listings scraped on page {page_index}: {len(scraped_data)}")
    return scraped_data

def scrape_all_pages_in_category(start_url, output_folder):
    """Scrapes all pages within a single category and writes to a CSV file."""
    complete_data = []

    with sync_playwright() as playwright:
        browser_instance = playwright.chromium.launch(headless=True)
        browser_page = browser_instance.new_page()

        page_index = 1
        while True:
            print(f"Scraping page {page_index}: {start_url}")
            browser_page.goto(start_url, wait_until="domcontentloaded")

            page_content = extract_data_from_page(browser_page, page_index)
            if not page_content:
                break  # Stop if no data found (end of pagination)

            complete_data.extend(page_content)

            # Check if there is a "Next" button to continue pagination
            next_page_button = browser_page.query_selector('ol.pagination .page-item:not(.d-none) .page-link.btn[title="Go to Next Page"]')
            if next_page_button:
                next_page_url = next_page_button.get_attribute('href')
                start_url = requests.compat.urljoin(start_url, next_page_url)  # Update URL for the next page
                page_index += 1
                browser_page.wait_for_timeout(1000)  # Wait for 1 second before loading the next page
            else:
                break

        browser_instance.close()

    # Write the scraped data to a CSV file
    csv_output_file = os.path.join(output_folder, "data.csv")
    with open(csv_output_file, mode='w', newline='', encoding='utf-8') as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(['Title', 'Schedule', 'Description', 'Location', 'Phone', 'Email', 'Website'])

        # Clean data before writing to the CSV
        for row in complete_data:
            cleaned_row = [clean_string(item) for item in row]
            csv_writer.writerow(cleaned_row)

    print(f"Data successfully written to {csv_output_file}")

# -------------------- Category Exploration Logic --------------------

def explore_and_scrape_categories(category_link, output_folder):
    """Explores the given link and scrapes available categories."""
    try:
        response = requests.get(category_link)
        response.raise_for_status()
        html_content = BeautifulSoup(response.text, 'html.parser')

        category_elements = html_content.find_all(['li', 'div'], class_='category-block')
        if not category_elements:
            print(f"No categories found at {category_link}, scraping this page directly...")
            scrape_all_pages_in_category(category_link, output_folder)
            return

        for category in category_elements:
            category_anchor = category.find('a')
            if category_anchor:
                category_name = clean_string(category_anchor.text)
                category_url = category_anchor['href']

                sanitized_name = sanitize_directory_name(category_name)
                subfolder_path = os.path.join(output_folder, sanitized_name)
                create_directory_if_not_exists(subfolder_path)

                next_category_url = requests.compat.urljoin(category_link, category_url)
                explore_and_scrape_categories(next_category_url, subfolder_path)

    except requests.RequestException as request_error:
        print(f"Failed to fetch {category_link}: {request_error}")

# -------------------- Main Execution --------------------

if __name__ == "__main__":
    initial_url = "https://directory.wigan.gov.uk/kb5/wigan/fsd/home.page"
    main_output_folder = "Wigan_Exploration"
    create_directory_if_not_exists(main_output_folder)

    explore_and_scrape_categories(initial_url, main_output_folder)
