import os
import time
import requests
import random
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
            # Remove `.md` from the URL to get the high-resolution version
            high_res_url = img_url.replace('.md', '')

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


scrape_fapellosu(
    file_path='d:/Forge/express/sample.html',  # Path to the HTML file
    output_folder='name_images'                # Folder to save the images
)

 