#!/usr/bin/env python

import urllib.request
import urllib.parse
import threading
import logging
import queue
import sys
import os
import tistory_extractor as tistory
import httpbin
import argparser



# issue: if multiple pages have the same url saved to same directory they'll be marked as "already saved"
# hash check duplicate files instead of checking name and file size
# fix title_filter

CONTENT_TYPES = ["image/jpeg", "image/png", "image/gif, image/webp"]
IMG_EXTS = ['jpg', 'jpeg', 'png', 'gif', 'webp']
LOCK = threading.Lock()
DOWNLOADED = 0
EXISTING = 0


def run(args):
    global SETTINGS
    SETTINGS = argparser.parse(args[1:])

    if SETTINGS.debug_status():
        logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s')

    logging.debug('%s', SETTINGS.get_url())

    pic_q = queue.Queue()

    # Parse pages for images
    if SETTINGS.multiplepages():
        page_q = queue.Queue()
        for page in SETTINGS.get_pages():
            page_q.put(page)
        logging.info("Fetching source for:")
        start_threads(parse_multiple_pages, [page_q, pic_q], SETTINGS.get_threads())
    else:
        logging.info("Fetching page source...")
        html = httpbin.Fetch(SETTINGS.get_url()).body()
        if html:
            parse_page(SETTINGS.get_url(), pic_q)
        else:
             sys.exit()
    total_img_found = pic_q.qsize()

    # Starts the download
    logging.info("\nStarting download:")
    start_threads(download, [pic_q], SETTINGS.get_threads())

    # Final report
    logging.info("\nDone!")
    logging.info(f"Found: {total_img_found}")
    if DOWNLOADED > 0:
        logging.info(f"Saved: {DOWNLOADED}")
    if EXISTING > 0:
        logging.info(f"Already saved: {EXISTING}")

    if httpbin.Fetch.errors:
        logging.info("\nCould not download:")
        for url in httpbin.Fetch.errors:
            logging.info(url)


def start_threads(target, q, t):
    img_threads = [threading.Thread(target=target, args=q) for i in range(t)]
    for thread in img_threads:
        thread.start()
    for thread in img_threads:
        thread.join()


def download(pic_q):
    global DOWNLOADED
    global EXISTING

    while pic_q.qsize() > 0:
        data = pic_q.get()
        url = data["url"]
        title = data["title"]

        content = httpbin.Fetch(url)
        if not content:
            continue

        logging.info(url)
        with LOCK:
            img_path = get_img_path(url, title, content.info(), filename=data['filename'])
            if SETTINGS.debug:
                continue
            if img_path:
                try:
                    with open(img_path, 'wb') as f:
                        f.write(content.body())
                except Exception as err:
                    logging.info('Error: %s', err)

                DOWNLOADED += 1
            else:
                EXISTING += 1


def get_img_path(url, title, img_info, filename):
    if img_info['Content-Disposition'] and not filename:
        # filename fallback 1
        filename = img_info['Content-Disposition']
        if "filename*=UTF-8" in filename:
            filename = filename.split("filename*=UTF-8''")[1]
            filename = filename.rsplit(".", 1)[0]
        else:
            filename = filename.split('"')[1]
        filename = urllib.request.url2pathname(filename)

    if not filename:
        # filename fallback 2
        filename = url.rsplit('/', 1)[1]
        filename = filename.strip('/')

    if not filename:
        # filename fallback 3
        filename = 'image'

    filename = filename.strip()
    extension = "." + img_info["Content-Type"].split("/")[1]
    extension = extension.replace("jpeg", "jpg")

    if '.' in filename and filename.rsplit('.', 1)[1] not in IMG_EXTS:
        # if filename randomly has a dot in its name
        filename = filename + extension
    elif '.' not in filename:
        # no filename has no extension
        filename = filename + extension

    img_path = get_path(title, filename)

    for _ in range(999):
        if not os.path.exists(img_path):
            return img_path

        if int(img_info["Content-Length"]) != int(len(open(img_path, "rb").read())):
            number = filename[filename.rfind("(") + 1:filename.rfind(")")]

            if number.isdigit() and filename.rsplit(".", 1)[1].lower() in IMG_EXTS:
                file_number = int(number) + 1
                filename = filename.rsplit("(", 1)[0].strip()
            else:
                file_number = 2
                filename = filename.rsplit(".", 1)[0]

            filename = f"{filename} ({file_number}){extension}"

            img_path = get_path(title, filename)
        else:
            return None


def get_path(title, file):
    path = ''
    if SETTINGS.directory:
        path = SETTINGS.directory

    if SETTINGS.organize:
        path = os.path.join(path, title.strip())
        if not os.path.exists(path):
            os.makedirs(path)

    path = os.path.join(path, file)
    return path


def parse_multiple_pages(page_q, pic_q):
    while page_q.qsize() > 0:
        page_num = page_q.get()
        url = "{}{}".format(SETTINGS.get_url(), page_num)
        parse_page(url, pic_q, page_num)


def parse_page(url, pic_q, page_num=''):
    logging.info(url)
    html = httpbin.Fetch(url).body()
    if html:
        page = tistory.Extractor(url, html)
        for link in page.get_links():
            pic_q.put(link)


if __name__ == "__main__":
    ARGS = 'ty https://ohcori.tistory.com/ --debug -p 301 305 -o -t 2 -f hello/world'.split()
    run(ARGS)
