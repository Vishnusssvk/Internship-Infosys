import requests
from bs4 import BeautifulSoup
import os
import re

def ensure_directory_exists(directory):
    """Ensures the directory exists by creating it if necessary."""
    if not os.path.exists(directory):
        os.makedirs(directory)

def clean_directory_name(directory_name):
    """Cleans the directory name to remove invalid characters."""
    # Remove invalid characters and strip spaces
    return re.sub(r'[<>:"/\\|?*]', '', directory_name).strip()

def explore_and_scrape(link, destination_folder):
    """Explores the given link and scrapes available categories."""
    try:
        # Fetch the webpage content
        response = requests.get(link)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all category containers (li or div elements)
        containers = soup.find_all(['li', 'div'], class_='category-block')

        # Stop if no containers are found
        if not containers:
            print(f"No categories found at {link}")
            return

        for container in containers:
            anchor = container.find('a')
            if anchor:
                # Extract category name and its link
                category_name = anchor.text.strip()
                category_link = anchor['href']

                # Clean the category name for directory usage
                valid_name = clean_directory_name(category_name)

                # Build the destination folder path
                subfolder = os.path.join(destination_folder, valid_name)
                ensure_directory_exists(subfolder)

                # Form the full URL for the next category
                next_url = requests.compat.urljoin(link, category_link)

                # Recursively explore the next category
                explore_and_scrape(next_url, subfolder)
    except requests.RequestException as err:
        print(f"Failed to fetch {link}: {err}")

# Main execution starts here
if __name__ == "__main__":
    # Base link to start from
    start_url = "https://directory.wigan.gov.uk/kb5/wigan/fsd/home.page"

    # Root folder for storing results
    root_folder = "Wigan_Exploration"
    ensure_directory_exists(root_folder)

    # Begin scraping from the base URL
    explore_and_scrape(start_url, root_folder)
