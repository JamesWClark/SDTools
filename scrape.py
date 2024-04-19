import os
import time
import requests
from bs4 import BeautifulSoup

def scrape_links(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    dict_hrefs = {}

    second_paragraph = soup.select_one('.entry-text article div p:nth-of-type(2)')
    lines = second_paragraph.decode_contents().split('<br/>')

    for line in lines:
        if line:
            category, link_tag = line.strip().split(' - ')
            link = BeautifulSoup(link_tag, 'html.parser').a['href']
            dict_hrefs[category] = link

    return dict_hrefs

def scrape_paste_bin(links):
    for category, link in links.items():
        if 'pastebin.com' in link:
            key = link.split('/')[-1]
            raw_link = f'https://pastebin.com/raw/{key}'
            response = requests.get(raw_link)
            with open(f'{category}.txt', 'w') as f:
                f.write(response.text)
                print("Scraped: ", category)
            delay = 5
            print("Pause for", delay, "seconds...")
            time.sleep(delay)  # delay for 1 second

def scrape_rentry(links):
    for category, link in links.items():
        if 'rentry.org' in link:
            response = requests.get(link)
            soup = BeautifulSoup(response.text, 'html.parser')
            text = soup.select_one('.entry-text article div p')
            lines = text.get_text().strip()
            with open(f'{category}.txt', 'w') as f:
                f.write(lines)
                print("Scraped: ", category)
            delay = 5
            print("Pause for", delay, "seconds...")
            time.sleep(delay)  # delay for 1 second

def remove_blank_lines_in_folder(folder_path):
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            with open(file_path, 'r') as f:
                lines = f.readlines()

            non_blank_lines = [line for line in lines if line.strip()]

            with open(file_path, 'w') as f:
                f.writelines(non_blank_lines)

# get all these links from the home page
links = scrape_links('https://rentry.org/NAIwildcards')

# download the content of each link
# scrape_paste_bin(links)
# scrape_rentry(links)

# remove_blank_lines_in_folder('C:/Users/JWC/git/Forge/extensions/sd-dynamic-prompts/wildcards/scrapenai')