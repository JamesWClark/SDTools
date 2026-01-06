import os
import time
import requests
import random
import argparse
import sys
from bs4 import BeautifulSoup

def scrape_links(url):
    # https://rentry.org/NAIwildcards
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

def scrape_imdb(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    names = soup.select('#main h3.lister-item-header a')

    text = "{"
    for name in names:
        text += name.text.strip() + " | "
    text = text[:-3] + "}"
    print(text)


def download_images_from_html(file_path, output_folder):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }

    # Ensure the output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Load the HTML file
    with open(file_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')

    # Find all <img> elements
    img_elements = soup.find_all('img')
    print(f"Found {len(img_elements)} <img> elements.")

    failed_downloads = []

    for img in img_elements:
        img_url = img.get('src')
        if img_url:
            # Modify the URL to remove the `.md` part
            high_res_url = img_url.replace('.md', '')

            # Extract the filename from the high-res URL
            img_filename = os.path.basename(high_res_url)

            # Attempt to download the high-resolution image
            try:
                response = requests.get(high_res_url, headers=headers, stream=True)
                if response.status_code == 200:
                    img_path = os.path.join(output_folder, img_filename)
                    with open(img_path, 'wb') as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)
                    print(f"Downloaded high-resolution image: {img_filename}")
                else:
                    # Fallback to the original URL with `.md` if the high-res image fails
                    print(f"High-resolution image not found, falling back to original: {img_url}")
                    response = requests.get(img_url, headers=headers, stream=True)
                    if response.status_code == 200:
                        img_path = os.path.join(output_folder, os.path.basename(img_url))
                        with open(img_path, 'wb') as f:
                            for chunk in response.iter_content(1024):
                                f.write(chunk)
                        print(f"Downloaded fallback image: {os.path.basename(img_url)}")
                    else:
                        print(f"Failed to download fallback image: {img_url} (Status code: {response.status_code})")
                        failed_downloads.append(img_url)
            except Exception as e:
                print(f"Error downloading {high_res_url}: {e}")
                failed_downloads.append(high_res_url)

            # Random delay to mimic human behavior
            delay = random.uniform(4, 9)
            print(f"Sleeping for {delay:.2f} seconds...")
            time.sleep(delay)
        else:
            print(f"No valid src attribute found for img element: {img}")

    # Log failed downloads
    if failed_downloads:
        with open(os.path.join(output_folder, 'failed_downloads.log'), 'w') as log_file:
            log_file.write('\n'.join(failed_downloads))
        print(f"Logged {len(failed_downloads)} failed downloads to 'failed_downloads.log'.")

def scrape_and_download_images(file_path, output_folder):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }

    # Ensure the output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Load the HTML file
    with open(file_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')

    # Find all <img> elements
    img_elements = soup.find_all('img')
    total_images = len(img_elements)
    print(f"Found {total_images} <img> elements.")

    failed_downloads = []

    for index, img in enumerate(img_elements, start=1):
        img_url = img.get('src')
        if img_url:
            # Display the current progress
            print(f"{index}/{total_images}: Processing {img_url}")

            # Modify the URL to remove '_300px' before the file extension
            high_res_url = img_url.replace('_300px', '')

            # Extract the filename from the high-res URL
            img_filename = os.path.basename(high_res_url)

            # Attempt to download the high-resolution image
            try:
                response = requests.get(high_res_url, headers=headers, stream=True)
                if response.status_code == 200:
                    img_path = os.path.join(output_folder, img_filename)
                    with open(img_path, 'wb') as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)
                    print(f"Downloaded high-resolution image: {img_filename}")
                else:
                    # Fallback to the original URL with '_300px' if the high-res image fails
                    print(f"High-resolution image not found, falling back to original: {img_url}")
                    response = requests.get(img_url, headers=headers, stream=True)
                    if response.status_code == 200:
                        img_path = os.path.join(output_folder, os.path.basename(img_url))
                        with open(img_path, 'wb') as f:
                            for chunk in response.iter_content(1024):
                                f.write(chunk)
                        print(f"Downloaded fallback image: {os.path.basename(img_url)}")
                    else:
                        print(f"Failed to download fallback image: {img_url} (Status code: {response.status_code})")
                        failed_downloads.append(img_url)
            except Exception as e:
                print(f"Error downloading {high_res_url}: {e}")
                failed_downloads.append(high_res_url)

            # Random delay to mimic human behavior
            delay = random.uniform(3, 6)
            print(f"Sleeping for {delay:.2f} seconds...")
            time.sleep(delay)
        else:
            print(f"{index}/{total_images}: No valid src attribute found for img element: {img}")

    # Log failed downloads
    if failed_downloads:
        with open(os.path.join(output_folder, 'failed_downloads.log'), 'w') as log_file:
            log_file.write('\n'.join(failed_downloads))
        print(f"Logged {len(failed_downloads)} failed downloads to 'failed_downloads.log'.")

def scrape_sample(file_path, output_folder):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }

    # Ensure the output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Load the HTML file
    with open(file_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')

    # Find all <img> elements
    img_elements = soup.find_all('img')
    total_images = len(img_elements)
    print(f"Found {total_images} <img> elements.")

    failed_downloads = []

    for index, img in enumerate(img_elements, start=1):
        img_url = img.get('src')
        if img_url:
            # Display the current progress
            print(f"{index}/{total_images}: Processing {img_url}")

            # Modify the URL to remove '.md' if present
            if '.md' in img_url:
                high_res_url = img_url.replace('.md', '')
            else:
                high_res_url = img_url

            # Extract the filename from the high-res URL
            img_filename = os.path.basename(high_res_url)

            # Attempt to download the high-resolution image
            try:
                response = requests.get(high_res_url, headers=headers, stream=True)
                if response.status_code == 200:
                    img_path = os.path.join(output_folder, img_filename)
                    with open(img_path, 'wb') as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)
                    print(f"Downloaded high-resolution image: {img_filename}")
                else:
                    print(f"Failed to download image: {high_res_url} (Status code: {response.status_code})")
                    failed_downloads.append(high_res_url)
            except Exception as e:
                print(f"Error downloading {high_res_url}: {e}")
                failed_downloads.append(high_res_url)

            # Random delay to mimic human behavior
            delay = random.uniform(1,3)
            print(f"Sleeping for {delay:.2f} seconds...")
            time.sleep(delay)
        else:
            print(f"{index}/{total_images}: No valid src attribute found for img element: {img}")

    # Log failed downloads
    if failed_downloads:
        with open(os.path.join(output_folder, 'failed_downloads.log'), 'w') as log_file:
            log_file.write('\n'.join(failed_downloads))
        print(f"Logged {len(failed_downloads)} failed downloads to 'failed_downloads.log'.")

def scrape_devonjenelle(file_path, output_folder):
    import os
    import time
    import requests
    from bs4 import BeautifulSoup

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }

    # Ensure the output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Load the HTML file
    with open(file_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')

    # Find all <img> elements
    img_elements = soup.find_all('img')
    total_images = len(img_elements)
    print(f"Found {total_images} <img> elements.")

    failed_downloads = []

    for index, img in enumerate(img_elements, start=1):
        img_url = img.get('src')
        if img_url:
            # Display the current progress
            print(f"{index}/{total_images}: Processing {img_url}")

            # Sanitize the filename by removing query parameters
            img_filename = os.path.basename(img_url.split('?')[0])

            # Attempt to download the image
            try:
                response = requests.get(img_url, headers=headers, stream=True)
                if response.status_code == 200:
                    img_path = os.path.join(output_folder, img_filename)
                    with open(img_path, 'wb') as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)
                    print(f"Downloaded image: {img_filename}")
                else:
                    print(f"Failed to download image: {img_url} (Status code: {response.status_code})")
                    failed_downloads.append(img_url)
            except Exception as e:
                print(f"Error downloading {img_url}: {e}")
                failed_downloads.append(img_url)

            # Pause for 0.7 seconds
            time.sleep(0.7)
        else:
            print(f"{index}/{total_images}: No valid src attribute found for img element: {img}")

    # Log failed downloads
    if failed_downloads:
        print(f"Failed to download the following images:")
        for failed_url in failed_downloads:
            print(f"- {failed_url}")

def scrape_listal_images(url, output_folder):
    import os
    import time
    import requests
    from bs4 import BeautifulSoup

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }

    # Ensure the output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Send a request to the URL
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch the page: {url} (Status code: {response.status_code})")
        return

    # Parse the HTML content
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find all <img> elements in the page
    img_elements = soup.find_all('img')
    total_images = len(img_elements)
    print(f"Found {total_images} <img> elements.")

    failed_downloads = []

    for index, img in enumerate(img_elements, start=1):
        thumbnail_url = img.get('src')
        if thumbnail_url and 'lisimg.com' in thumbnail_url:
            # Extract the common identifier from the thumbnail URL
            try:
                common_id = thumbnail_url.split('/')[-1].split('.')[0]  # Extract the ID (e.g., "25797991")
                high_res_url = f"https://ilarge.lisimg.com/image/{common_id}/1080full-devon-jenelle.jpg"

                # Display the current progress
                print(f"{index}/{total_images}: Attempting {high_res_url}")

                # Extract the filename from the high-resolution URL
                img_filename = os.path.basename(high_res_url)

                # Check if the file already exists
                img_path = os.path.join(output_folder, img_filename)
                if os.path.exists(img_path):
                    print(f"File already exists, skipping: {img_path}")
                    continue

                # Attempt to download the high-resolution image
                response = requests.get(high_res_url, headers=headers, stream=True)
                if response.status_code == 200:
                    with open(img_path, 'wb') as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)
                    print(f"Downloaded image: {img_filename}")
                else:
                    print(f"Failed to download image: {high_res_url} (Status code: {response.status_code})")
                    failed_downloads.append(high_res_url)

                # Pause for 0.7 seconds
                time.sleep(0.7)
            except Exception as e:
                print(f"Error processing {thumbnail_url}: {e}")
                failed_downloads.append(thumbnail_url)
        else:
            print(f"{index}/{total_images}: No valid thumbnail URL found for img element: {img}")

    # Log failed downloads
    if failed_downloads:
        print(f"Failed to download the following images:")
        for failed_url in failed_downloads:
            print(f"- {failed_url}")

def scrape_devonjenelle_images(file_path, output_folder):
    import os
    import requests
    from bs4 import BeautifulSoup

    # Ensure the output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Load the HTML file
    with open(file_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')

    # Find all <a> elements wrapping images
    anchor_elements = soup.find_all('a', href=True)
    total_links = len(anchor_elements)
    print(f"Found {total_links} anchor elements with href attributes.")

    failed_downloads = []

    for index, anchor in enumerate(anchor_elements, start=1):
        href = anchor['href']
        # Check if the href points to an image file
        if href.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            # Display the current progress
            print(f"{index}/{total_links}: Processing {href}")

            # Extract the filename from the URL
            img_filename = os.path.basename(href)

            # Check if the file already exists
            img_path = os.path.join(output_folder, img_filename)
            if os.path.exists(img_path):
                print(f"File already exists, skipping: {img_path}")
                continue

            # Attempt to download the image
            try:
                response = requests.get(href, stream=True)
                if response.status_code == 200:
                    with open(img_path, 'wb') as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)
                    print(f"Downloaded image: {img_filename}")
                else:
                    print(f"Failed to download image: {href} (Status code: {response.status_code})")
                    failed_downloads.append(href)
            except Exception as e:
                print(f"Error downloading {href}: {e}")
                failed_downloads.append(href)
        else:
            print(f"{index}/{total_links}: Skipping non-image link: {href}")

    # Log failed downloads
    if failed_downloads:
        print(f"Failed to download the following images:")
        for failed_url in failed_downloads:
            print(f"- {failed_url}")

def download_blob(blob_url, output_folder):
    """
    Downloads a blob (e.g., video) from the given URL and saves it to the specified folder.

    :param blob_url: The URL of the blob to download.
    :param output_folder: The folder where the blob will be saved.
    """
    import os
    import requests

    # Ensure the output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Extract the file name from the blob URL
    file_name = os.path.basename(blob_url)
    output_path = os.path.join(output_folder, file_name)

    try:
        response = requests.get(blob_url, stream=True)
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            print(f"Downloaded blob to: {output_path}")
        else:
            print(f"Failed to download blob: {blob_url} (Status code: {response.status_code})")
    except Exception as e:
        print(f"Error downloading blob from {blob_url}: {e}")

def scrape_fapellosu(file_path, output_folder):
    # Ensure the output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Load the HTML file
    with open(file_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')

    # Find all <img> elements in the page
    img_elements = soup.find_all('img')
    total_images = len(img_elements)
    print(f"Found {total_images} <img> elements.")

    failed_downloads = []

    for index, img in enumerate(img_elements, start=1):
        img_url = img.get('src')
        if img_url:
            # Remove `_300px` from the URL to get the high-resolution version
            high_res_url = img_url.replace('_300px', '')

            # Display the current progress
            print(f"{index}/{total_images}: Processing {high_res_url}")

            # Extract the filename from the URL
            img_filename = os.path.basename(high_res_url)

            # Check if the file already exists
            img_path = os.path.join(output_folder, img_filename)
            if os.path.exists(img_path):
                print(f"File already exists, skipping: {img_path}")
                continue

            # Attempt to download the high-resolution image
            try:
                response = requests.get(high_res_url, stream=True)
                if response.status_code == 200:
                    with open(img_path, 'wb') as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)
                    print(f"Downloaded image: {img_filename}")
                else:
                    print(f"Failed to download image: {high_res_url} (Status code: {response.status_code})")
                    failed_downloads.append(high_res_url)
            except Exception as e:
                print(f"Error downloading {high_res_url}: {e}")
                failed_downloads.append(high_res_url)
        else:
            print(f"{index}/{total_images}: No valid src attribute found for img element: {img}")

    # Log failed downloads
    if failed_downloads:
        print(f"Failed to download the following images:")
        for failed_url in failed_downloads:
            print(f"- {failed_url}")

def scrape8muses_recursive(url, output_folder=None, rename_pattern=None):
    """
    Scrapes 8muses galleries, detecting if the URL points to a single gallery or multiple galleries.
    If multiple galleries are found, creates subfolders and scrapes each one.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        html_content = response.text
        print(f"Successfully fetched: {url}")
    except Exception as e:
        print(f"Error fetching URL {url}: {e}")
        return
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find all anchor elements with class "c-tile t-hover"
    anchor_elements = soup.find_all('a', class_='c-tile t-hover')
    
    if not anchor_elements:
        print(f"No galleries found at {url}")
        return
    
    # Check if this is a gallery of images or a gallery of galleries
    # by checking href patterns - this is more reliable than checking for images
    is_image_gallery = False
    is_gallery_list = False
    
    # First check all anchors for href patterns
    for anchor in anchor_elements:
        href = anchor.get('href')
        if href:
            if '/comics/album/' in href and '/comics/picture/' not in href:
                # This is a sub-gallery link
                is_gallery_list = True
            elif '/comics/picture/' in href:
                # This is an individual picture link
                is_image_gallery = True
    
    # Handle mixed galleries (both images and sub-galleries)
    if is_image_gallery and is_gallery_list:
        # This is a mixed gallery - scrape both the main images and sub-galleries
        print(f"Detected mixed gallery (images + sub-galleries)")
        
        # Extract the last path component from the URL to create base folder
        url_path = url.rstrip('/').split('/')
        base_folder_name = url_path[-1]
        
        if output_folder:
            base_path = os.path.join(output_folder, base_folder_name)
        else:
            base_path = base_folder_name
        
        if not os.path.exists(base_path):
            os.makedirs(base_path)
            print(f"Created base folder: {base_path}")
        
        # First, scrape the main gallery images
        main_rename_pattern = f"{base_folder_name}-Main (%)" if rename_pattern is None else rename_pattern.replace("Issue-X", "Main")
        print(f"\nScraping main gallery images")
        scrape8muses(url=url, output_folder=base_path, rename_pattern=main_rename_pattern)
        
        # Then, scrape any sub-galleries
        gallery_links = []
        for anchor in anchor_elements:
            href = anchor.get('href')
            if href and '/comics/album/' in href and '/comics/picture/' not in href:
                if not href.startswith('http'):
                    href = 'https://comics.8muses.com' + href
                gallery_links.append(href)
        
        print(f"Found {len(gallery_links)} sub-galleries")
        
        for issue_num, gallery_url in enumerate(gallery_links, start=1):
            issue_rename_pattern = f"{base_folder_name}-Issue{issue_num} (%)"
            print(f"\nScraping Issue {issue_num}: {gallery_url}")
            scrape8muses(url=gallery_url, output_folder=base_path, rename_pattern=issue_rename_pattern)
            time.sleep(1)
        
        return
    
    # If we found sub-gallery links, it's definitely a gallery list
    if is_gallery_list:
        # This is a gallery of galleries - create subfolders and scrape each
        print(f"Detected gallery listing (multiple galleries)")
        
        # Extract the last path component from the URL to create base folder
        url_path = url.rstrip('/').split('/')
        base_folder_name = url_path[-1]
        
        if output_folder:
            base_path = os.path.join(output_folder, base_folder_name)
        else:
            base_path = base_folder_name
        
        if not os.path.exists(base_path):
            os.makedirs(base_path)
            print(f"Created base folder: {base_path}")
        
        # Extract gallery links from anchors with /comics/album/ hrefs
        gallery_links = []
        for anchor in anchor_elements:
            href = anchor.get('href')
            if href and '/comics/album/' in href and '/comics/picture/' not in href:
                if not href.startswith('http'):
                    href = 'https://comics.8muses.com' + href
                gallery_links.append(href)
        
        print(f"Found {len(gallery_links)} sub-galleries")
        
        # Scrape each gallery directly into base folder with issue numbering in filenames
        for issue_num, gallery_url in enumerate(gallery_links, start=1):
            # Create rename pattern for this issue (files will be named with issue number)
            issue_rename_pattern = f"{base_folder_name}-Issue{issue_num} (%)" if rename_pattern is None else rename_pattern.replace("Issue-X", f"Issue{issue_num}")
            
            print(f"\nScraping Issue {issue_num}: {gallery_url}")
            scrape8muses(url=gallery_url, output_folder=base_path, rename_pattern=issue_rename_pattern)
            
            # Small delay between requests
            time.sleep(1)
    
    elif is_image_gallery:
        # This is a single image gallery - create folder and scrape it directly
        print(f"Detected single image gallery")
        
        # Extract the last path component from the URL to create base folder
        url_path = url.rstrip('/').split('/')
        base_folder_name = url_path[-1]
        
        if output_folder:
            base_path = os.path.join(output_folder, base_folder_name)
        else:
            base_path = base_folder_name
        
        if not os.path.exists(base_path):
            os.makedirs(base_path)
            print(f"Created folder: {base_path}")
        
        # Create rename pattern with automatic issue naming
        issue_rename_pattern = f"{base_folder_name}-Issue-01 (%)" if rename_pattern is None else rename_pattern
        
        scrape8muses(url=url, output_folder=base_path, rename_pattern=issue_rename_pattern)
    
    else:
        print(f"Could not determine gallery type at {url}")

def scrape8muses(file_path=None, url=None, output_folder=None, rename_pattern=None):
    # Ensure the output folder exists
    if output_folder and not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Load the HTML from file or URL
    if url:
        # Fetch HTML from URL
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            html_content = response.text
            print(f"Successfully fetched: {url}")
        except Exception as e:
            print(f"Error fetching URL {url}: {e}")
            return
    elif file_path:
        # Load from file
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                html_content = file.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return
    else:
        print("Error: Either file_path or url must be provided")
        return
    
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find all anchor elements with class "c-tile t-hover"
    anchor_elements = soup.find_all('a', class_='c-tile t-hover')
    total_images = len(anchor_elements)
    print(f"Found {total_images} anchor elements with class 'c-tile t-hover'.")

    failed_downloads = []

    for index, anchor in enumerate(anchor_elements, start=1):
        # Find the img element inside the anchor (more flexible approach)
        img = anchor.find('img')
        if img:
            # Try to get src from img tag (fallback to data-src if needed)
            img_url = img.get('src') or img.get('data-src')
            if img_url:
                # Modify the URL: replace /th/ with /fl/ and prepend the base URL
                high_res_url = 'https://comics.8muses.com' + img_url.replace('/th/', '/fl/')

                # Display the current progress
                print(f"{index}/{total_images}: Processing {high_res_url}")

                # Extract the filename from the URL or use rename pattern
                if rename_pattern:
                    # Get file extension from the URL
                    original_filename = os.path.basename(high_res_url)
                    file_ext = os.path.splitext(original_filename)[1]
                    # Replace % with the index number
                    img_filename = rename_pattern.replace('%', str(index)) + file_ext
                else:
                    img_filename = os.path.basename(high_res_url)

                # Check if the file already exists (skip if not using rename pattern)
                img_path = os.path.join(output_folder, img_filename)
                if not rename_pattern and os.path.exists(img_path):
                    print(f"File already exists, skipping: {img_path}")
                    continue

                # Attempt to download the high-resolution image
                try:
                    response = requests.get(high_res_url, stream=True)
                    if response.status_code == 200:
                        with open(img_path, 'wb') as f:
                            for chunk in response.iter_content(1024):
                                f.write(chunk)
                        print(f"Downloaded image: {img_filename}")
                    else:
                        print(f"Failed to download image: {high_res_url} (Status code: {response.status_code})")
                        failed_downloads.append(high_res_url)
                except Exception as e:
                    print(f"Error downloading {high_res_url}: {e}")
                    failed_downloads.append(high_res_url)
            else:
                print(f"{index}/{total_images}: No valid src attribute found for img element in anchor")
        else:
            print(f"{index}/{total_images}: No img.lazyloaded element found in anchor")

    # Log failed downloads
    if failed_downloads:
        print(f"Failed to download the following images:")
        for failed_url in failed_downloads:
            print(f"- {failed_url}")


def main():
    parser = argparse.ArgumentParser(description='Scrape images from HTML files or URLs')
    parser.add_argument('-rename', type=str, help='Rename pattern for downloaded files (use %% as placeholder for number). Example: -rename "file%%" or -rename "output %%"')
    parser.add_argument('-method', type=str, default='scrape8muses', help='Scraping method to use (default: scrape8muses)')
    parser.add_argument('-file', type=str, help='Path to HTML file (use either -file or -url)')
    parser.add_argument('-url', type=str, help='URL to scrape (use either -file or -url)')
    parser.add_argument('-output', type=str, default='8muses', help='Output folder for images (default: 8muses)')
    parser.add_argument('-recursive', action='store_true', help='Enable recursive scraping for gallery listings (auto-detects single gallery vs gallery list)')
    
    args = parser.parse_args()
    
    # Check that either file or url is provided
    if not args.file and not args.url:
        # Set default file if neither is provided
        args.file = 'e:/Forge/express/fap.html'
    
    if args.method == 'scrape8muses':
        # Use recursive function if URL is provided (auto-detects structure)
        if args.url:
            scrape8muses_recursive(url=args.url, output_folder=args.output, rename_pattern=args.rename)
        else:
            scrape8muses(file_path=args.file, output_folder=args.output, rename_pattern=args.rename)
    elif args.method == 'scrape_fapellosu':
        scrape_fapellosu(file_path=args.file, output_folder=args.output)
    else:
        print(f"Unknown method: {args.method}")
        sys.exit(1)

if __name__ == '__main__':
    main()