import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Set up Chrome options
chrome_options = Options()
chrome_options.add_argument("--headless")  

# Set up the webdriver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# URL of the webpage containing the data
url = "https://www.semrush.com/website/top/global/e-commerce-and-retail/"  
driver.get(url)

# Scraping the data from the table 
rows = driver.find_elements(By.XPATH, '//table/tbody/tr')

# Create a CSV file to save the scraped data
with open('retail_websites2.csv', mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(["Position", "Website", "Change", "Visits", "Pages/Visit", "Bounce Rate"])  
    # Iterate through table rows
    for row in rows:
        cols = row.find_elements(By.TAG_NAME, 'td')
        position = cols[0].text
        website = cols[1].text
        change = cols[2].text
        visits = cols[3].text
        pages_per_visit = cols[4].text
        bounce_rate = cols[5].text
        # Write the data into the CSV file
        writer.writerow([position, website, change, visits, pages_per_visit, bounce_rate])

driver.quit()
