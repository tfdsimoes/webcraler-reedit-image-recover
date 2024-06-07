import os
import psutil
import requests
import re
import sys
import threading

from datetime import datetime
from bs4 import BeautifulSoup

regex_date = r"\d{4}-\d{2}-\d{2}"
date_format_argument = "%Y-%m-%d"
date_format_post = "%Y-%m-%dT%H:%M:%S.%f%z"
base_url = "https://www.reddit.com"
community_url = base_url + "/r/SpanishMeme/"

default_images_to_recover = 70
total_images_to_recover = None
filter_date_posts = None

max_number_threads = psutil.cpu_count()

path_images_directory = "images"
total_images = 0
posts = []
total_images_lock = threading.Lock()
process_type = None


def process_date_from_post(post):
    post_date_str = post["created-timestamp"]
    post_date = datetime.strptime(post_date_str, date_format_post)
    post_date = post_date.replace(tzinfo=None)
    return post_date

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

    with open("images/" + str(counter) + ".jpg", "wb") as image_file:
        image_file.write(image_content)


def recover_posts_by_date():
    page = retrieve_page(community_url)
    while True:
        soup = BeautifulSoup(page.text, "html.parser")
        posts.extend(soup.find_all("shreddit-post"))

        post_date = process_date_from_post(posts[len(posts) - 1])

        if post_date < filter_date_posts:
            break

        page = load_more_posts(soup)


def recover_posts_by_total_images():
    page = retrieve_page(community_url)
    while len(posts) < total_images_to_recover:
        soup = BeautifulSoup(page.text, "html.parser")
        posts.extend(soup.find_all("shreddit-post"))
        page = load_more_posts(soup)


def load_more_posts(soup):
    faceplate_partial_load_posts = soup.select("[id^=\"partial-more-posts\"]")
    src_value = faceplate_partial_load_posts[0].get("src")
    load_more_url = base_url + src_value
    print(f"Next url to load: {load_more_url}")
    return retrieve_page(load_more_url)


def process_posts():
    global total_images

    while posts:
        if process_type == "total" and total_images >= total_images_to_recover:
            break

        with total_images_lock:
            number_image = total_images
            total_images = total_images + 1

        post = posts.pop()
        post_date = process_date_from_post(post)
        if process_type == "date" and post_date < filter_date_posts:
            break

        if process_type == "total":
            print(f"Processing image with process {number_image}")
        elif process_type == "date":
            print(f"Processing image with date {post_date}")

        download_image(post['content-href'], number_image)


# Check if it will process by date or total images
if len(sys.argv) >= 2:
    start_argument = sys.argv[1]
    if start_argument.isdigit():
        print(f"Recovering {start_argument} images")
        total_images_to_recover = int(start_argument)
        recover_posts_by_total_images()
        process_type = "total"
    elif re.fullmatch(regex_date, start_argument):
        print(f"Recovering images from {start_argument}")
        filter_date_posts = datetime.strptime(start_argument, date_format_argument)
        recover_posts_by_date()
        process_type = "date"
else:
    print(f"Recovering {default_images_to_recover} images by default")
    total_images_to_recover = default_images_to_recover
    recover_posts_by_total_images()
    process_type = "total"

# Clean the directory to store the images
prepare_directory_images(path_images_directory)

# Reverse list to process the most recent first
posts.reverse()
threads = []

for i in range(max_number_threads):
    thread = threading.Thread(target=process_posts)
    thread.start()
    threads.append(thread)

for thread in threads:
    thread.join()
