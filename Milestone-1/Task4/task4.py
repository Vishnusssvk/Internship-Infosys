import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin

def scrape_data(url):
    data = []
    while url:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        result_containers = soup.find_all('div', class_='result_hit_header')
        for container in result_containers:
            name = container.find('h3').text.strip()

            # Find the contact information section (sibling of result container)
            contact_section = container.find_next_sibling('div', class_='contact-links')

            # Extract contact information if the section exists
            if contact_section:
                telephone = contact_section.find('a', href=lambda href: href.startswith('tel:')).text.strip() if contact_section.find('a', href=lambda href: href.startswith('tel:')) else ""
                email_link = contact_section.find('a', href=lambda href: href.startswith('mailto:'))
                email = email_link['href'].split('mailto:')[1] if email_link else ""
                website_link = contact_section.find('a', href=lambda href: href.startswith('http'))
                website = website_link['href'] if website_link else ""
            else:
                telephone = ""
                email = ""
                website = ""

            data.append({'name': name, 'telephone': telephone, 'email': email, 'website': website})

        # Handle pagination - check for the "Next Page" link using the page-link class
        next_page_link = soup.find('a', class_='page-link', title="Go to Next Page")
        if next_page_link:
            next_page_url = next_page_link['href']
            url = urljoin(response.url, next_page_url)  # Handle relative URLs by joining with base URL
        else:
            url = None

    return data

def main():
    url = 'https://directory.wigan.gov.uk/kb5/wigan/fsd/results.page?healthchannel=6&sr='
    data = scrape_data(url)

    # Convert scraped data to DataFrame
    df = pd.DataFrame(data)

    # Save DataFrame to CSV file
    df.to_csv('task1.csv', index=False)
    print("Scraping completed and data saved to task4.csv")

if __name__ == '__main__':
    main()
