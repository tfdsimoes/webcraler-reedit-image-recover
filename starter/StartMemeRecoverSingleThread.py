import os
import requests
from bs4 import BeautifulSoup


def retrieve_page(page_url):
    response = requests.get(page_url)

    if response.status_code != 200:
        print(f"Failed to retrieve the page. Status code: {response.status_code}")

    return response


def download_image(image_url, counter):
    image_content = requests.get(image_url).content

    with open('images/' + str(counter) + '.jpg', 'wb') as image_file:
        image_file.write(image_content)


def process_posts(posts_to_process, total_processed):
    for post in posts_to_process:
        print(f"Processing image:  {total_processed}")
        download_image(post['content-href'], total_processed)
        total_processed = total_processed + 1

    return total_processed


def prepare_directory_images(images_directory):
    if os.path.exists(images_directory):
        files = os.listdir(images_directory)

        for file_name in files:
            file_path = os.path.join(images_directory, file_name)
            os.remove(file_path)
    else:
        os.makedirs(images_directory, exist_ok=True)


# Global variables
base_url = 'https://www.reddit.com'
community_url = base_url + '/r/SpanishMeme/'
total_images = 0
total_images_to_recover = 40
path_images_directory = 'images'

prepare_directory_images(path_images_directory)

# Load initial page
page = retrieve_page(community_url)

while total_images < total_images_to_recover:
    soup = BeautifulSoup(page.text, 'html.parser')
    posts = soup.find_all('shreddit-post')

    total_images = process_posts(posts, total_images)

    faceplate_partial_load_posts = soup.select('[id^="partial-more-posts"]')
    src_value = faceplate_partial_load_posts[0].get('src')
    load_more_url = base_url + src_value

    print(f"Next url to load: {load_more_url}")
    page = retrieve_page(load_more_url)
