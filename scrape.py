import requests
from bs4 import BeautifulSoup

def scrape_links(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    list_hrefs = []

    for link in soup.find_all('a'):
        href = link.get('href')
        if 'pastebin.com' in href or 'rentry.org' in href:
            list_hrefs.append(href)
        else:
            print('Skipping link:', href)

    return list_hrefs

links = scrape_links('https://rentry.org/NAIwildcards')

for link in links:
    print(link)