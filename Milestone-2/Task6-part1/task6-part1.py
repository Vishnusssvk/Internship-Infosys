import csv
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException

def scrape_behance_jobs(num_cards):
    # Set up headless Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Initialize WebDriver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.get("https://www.behance.net/joblist?tracking_source=nav20")

    print("Scrolling and loading jobs...")
    job_cards = []

    # Scroll and load content dynamically
    while len(job_cards) < num_cards:
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
        time.sleep(2)  # Wait for content to load

        cards = driver.find_elements(By.XPATH, '//div[contains(@class, "e2e-JobCard-card")]')
        print(f"Found {len(cards)} cards so far.")

        if len(cards) == len(job_cards):  # Stop if no new cards found
            print("Reached the bottom or no more content.")
            break

        job_cards = cards

    # Extract details from each job card
    scraped_jobs = []
    for card in job_cards[:num_cards]:
        try:
            # Extracting title
            title = card.find_element(By.XPATH, './/h3').text.strip() or "N/A"
            company = card.find_element(By.XPATH, './/p[contains(@class, "JobCard-company-GQS")]').text.strip() or "N/A"
            location = card.find_element(By.XPATH, './/p[contains(@class, "JobCard-jobLocation-sjd")]').text.strip() or "N/A"
            time_posted = card.find_element(By.XPATH, './/span[contains(@class, "JobCard-time-Cvz")]').text.strip() or "N/A"

            # Store the extracted details (excluding description)
            scraped_jobs.append({
                "Title": title,
                "Company": company,
                "Location": location,
                "Time Posted": time_posted
            })
        except NoSuchElementException as e:
            print(f"Error extracting data from a card: {e}. Skipping...")

    driver.quit()

    # Save results to CSV (excluding description)
    with open('behance_jobs.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["Title", "Company", "Location", "Time Posted"])
        writer.writeheader()
        writer.writerows(scraped_jobs)

    print("\nScraped jobs saved to 'behance_jobs.csv'.")

if __name__ == "__main__":
    scrape_behance_jobs(300)
