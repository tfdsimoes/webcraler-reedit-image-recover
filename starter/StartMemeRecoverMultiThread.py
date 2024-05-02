import os
import psutil
import requests
import re
import sys
import threading

from bs4 import BeautifulSoup

base_url = 'https://www.reddit.com'
community_url = base_url + '/r/SpanishMeme/'

default_images_to_recover = 70
total_images_to_recover = None
last_time_run = None

max_number_processor_images = psutil.cpu_count()

path_images_directory = 'images'
total_images = 0
posts = []
total_images_lock = threading.Lock()


def prepare_directory_images(images_directory):
    if os.path.exists(images_directory):
        files = os.listdir(images_directory)

        for file_name in files:
            file_path = os.path.join(images_directory, file_name)
            os.remove(file_path)
    else:
        os.makedirs(images_directory, exist_ok=True)


def retrieve_page(page_url):
    response = requests.get(page_url)

    if response.status_code != 200:
        print(f"Failed to retrieve the page. Status code: {response.status_code}")

    return response


def download_image(image_url, counter):
    image_content = requests.get(image_url).content

    with open('images/' + str(counter) + '.jpg', 'wb') as image_file:
        image_file.write(image_content)


def recover_posts_by_date():
    page = retrieve_page(community_url)
    while True:
        soup = BeautifulSoup(page.text, 'html.parser')
        posts.extend(soup.find_all('shreddit-post'))

        post_date = posts[len(posts) - 1]['created-timestamp']

        if post_date < last_time_run:
            break

        page = load_more_posts(soup)


def recover_posts_by_total_images():
    page = retrieve_page(community_url)
    while len(posts) < total_images_to_recover:
        soup = BeautifulSoup(page.text, 'html.parser')
        posts.extend(soup.find_all('shreddit-post'))

        page = load_more_posts(soup)


def load_more_posts(soup):
    faceplate_partial_load_posts = soup.select('[id^="partial-more-posts"]')
    src_value = faceplate_partial_load_posts[0].get('src')
    load_more_url = base_url + src_value
    print(f"Next url to load: {load_more_url}")
    return retrieve_page(load_more_url)


def process_posts():
    global total_images

    while posts:
        with total_images_lock:
            number_process = total_images
            total_images = total_images + 1

        print(f"Processing image with process {number_process}")
        download_image(posts.pop()['content-href'], number_process)


# Check if it will process by date or total images
if len(sys.argv) >= 2:
    start_argument = sys.argv[1]
    regex_date = r'\d{4}-\d{2}-\d{2}'
    if start_argument.isdigit():
        print(f"Recovering {start_argument} images")
        total_images_to_recover = int(start_argument)
        recover_posts_by_total_images()
    elif re.fullmatch(regex_date, start_argument):
        print(f"Recovering images from {start_argument}")
        last_time_run = start_argument
        recover_posts_by_date()
else:
    print(f"Recovering {default_images_to_recover} images by default")
    total_images_to_recover = default_images_to_recover
    recover_posts_by_total_images()

# Clean the directory to store the images
prepare_directory_images(path_images_directory)

# Reverse list to process the most recent first
posts.reverse()
threads = []

for i in range(max_number_processor_images):
    thread = threading.Thread(target=process_posts)
    thread.start()
    threads.append(thread)

for thread in threads:
    thread.join()
