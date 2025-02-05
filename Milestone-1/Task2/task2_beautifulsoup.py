import requests
from bs4 import BeautifulSoup
import csv
import os

# Base URL
base_url = "https://publiclibraries.com"

def scrape_state_links():
    url = f"{base_url}/state/"
    response = requests.get(url)
    
    # Check if the request was successful
    if response.status_code != 200:
        print(f"Failed to retrieve the page. Status code: {response.status_code}")
        return []

    soup = BeautifulSoup(response.content, "html.parser")

    # Locate the state links section
    state_links_section = soup.find("div", class_="entry-content")
    if not state_links_section:
        print("Unable to find the state links section.")
        return []

    # Extract state links
    state_links = []
    for a_tag in state_links_section.find_all("a"):
        state_name = a_tag.text.strip()
        state_url = a_tag['href'].strip()  # Make sure to strip any extra spaces
        full_url = f"{base_url}{state_url}" if not state_url.startswith("http") else state_url
        state_links.append([state_name, full_url])

    # Save state links to a CSV file
    with open("state_links.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["State", "URL"])
        writer.writerows(state_links)

    return state_links

def scrape_libraries_for_state(state_name, state_url):
    response = requests.get(state_url)
    if response.status_code != 200:
        print(f"Failed to retrieve data for {state_name}. Status code: {response.status_code}")
        return

    soup = BeautifulSoup(response.content, "html.parser")

    # Find the table with library data
    table = soup.find("table")
    if not table:
        print(f"No library data found for {state_name}.")
        return

    # Extract headers and rows
    headers = [th.text.strip() for th in table.find_all("th")]
    rows = [[td.text.strip() for td in row.find_all("td")] for row in table.find_all("tr")[1:]]

    # Save to a CSV file
    os.makedirs("state_libraries", exist_ok=True)
    file_path = f"state_libraries/{state_name}.csv"
    
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    print(f"Data for {state_name} saved to {file_path}.")

if __name__ == "__main__":
    state_links = scrape_state_links()

    for state_name, state_url in state_links:
        scrape_libraries_for_state(state_name, state_url)
