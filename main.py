#!/usr/bin/env python

import urllib.request
import urllib.parse
import threading
import logging
import queue
import sys
import os
import argparser
import tistory_extractor as tistory


SPECIAL_CHARS = r'!\"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
CONTENT_TYPES = ["image/jpeg", "image/png", "image/gif, image/webp"]
IMG_EXTS = ['jpg', 'jpeg', 'png', 'gif', 'webp']
LOCK = threading.Lock()


class E:
    imgs_downloaded = 0
    already_found = 0
    error_links = []


def run(args):
    pic_q = queue.Queue()

    settings = argparser.parse(args[1:])
    E.title_filter_words = settings.get_title_filter()
    E.debug = settings.debug_status()
    E.organize = settings.organize_status()

    E.url = settings.get_url()
    E.urlparse = urllib.parse.urlparse(E.url)

    if E.debug:
        logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(name)s: %(message)s')

    logging.debug('%s', E.url)

    # Parse pages for images
    if settings.page_status():
        if not E.url.endswith("/"):
            E.url = E.url + "/"
        page_q = queue.Queue()
        for page in settings.get_pages():
            page_q.put(page)
        print("Fetching source for:")
        start_threads(work_page, [page_q, pic_q], settings.get_threads())
    else:
        print("Fetching page source...")
        html = fetch(E.url)
        if html:
            parse_page(E.url, html, '', pic_q)
        else:
            sys.exit()
    total_img_found = pic_q.qsize()

    # Starts the download
    print("\nStarting download:")
    start_threads(download, [pic_q], settings.get_threads())

    # Final report
    print("\nDone!")
    print("Found:", total_img_found)
    if E.imgs_downloaded > 0:
        print("Saved:", E.imgs_downloaded)
    if E.already_found > 0:
        print("Already saved:", E.already_found)

    if E.error_links:
        print('Errors: %s' % len(E.error_links))
    if E.error_links:
        print("\nCould not download:")
        for url in E.error_links:
            print(url)


def start_threads(target, q, t):
    img_threads = [threading.Thread(target=target, args=q) for i in range(t)]
    for thread in img_threads:
        thread.start()
    for thread in img_threads:
        thread.join()


def download(pic_q):
    while pic_q.qsize() > 0:
        data = pic_q.get()
        url = data["url"]
        title = data["title"]
        page = " -page /{}".format(data["page"]) if data["page"] is not None else ""

        # fetch image content, returns None if error
        img_content = fetch(url, page=page)

        if img_content is None:
            continue

        img_info = img_content.info()

        print(url)
        with LOCK:
            img_path = get_img_path(url, title, img_info, filename=data['filename'])
            if E.debug:
                continue
            if img_path is not None:
                with open(img_path, 'wb') as f:
                    f.write(img_content.read())
                E.imgs_downloaded += 1
            else:
                E.already_found += 1


def get_img_path(url, folder_name, img_info, filename):
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
        filename = url.split('/')[-1]
        filename = filename.strip('/')

    if '.' in filename and filename.rsplit('.', 1)[1] not in IMG_EXTS:
        extension = "." + img_info["Content-Type"].split("/")[1]
        extension = extension.replace("jpeg", "jpg")
        filename = filename + extension
    elif '.' not in filename:
        extension = "." + img_info["Content-Type"].split("/")[1]
        extension = extension.replace("jpeg", "jpg")
        filename = filename + extension

    filename = filename.strip()

    if E.organize:
        if folder_name is None:
            folder_name = "Untitled"
        for char in SPECIAL_CHARS:
            folder_name = folder_name.replace(char, "")
        folder_name = folder_name.strip()
        img_path = os.path.join(folder_name, filename)
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
    else:
        img_path = filename.strip()

    for _ in range(999):
        if not os.path.exists(img_path):
            return img_path

        if int(img_info["Content-Length"]) != int(len(open(img_path, "rb").read())):
            number = filename[filename.rfind("(") + 1:filename.rfind(")")]
            if number.isdigit() and filename[filename.rfind(")") + 1:].lower() in IMG_EXTS:
                file_number = int(number) + 1
                filename = filename.rsplit("(", 1)[0].strip()
            else:
                file_number = 2
                filename = filename.rsplit(".", 1)[0]
            filename = filename.strip() + " (" + str(file_number) + ")" + extension
            if E.organize:
                img_path = os.path.join(
                    folder_name.strip(), filename.strip())
            else:
                img_path = filename.strip()
        else:
            return None


def fetch(url, page=""):
    """sends a http get request and returns html content"""
    logger = logging.getLogger('fetch')
    logger.debug('fetching: %s', url)
    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent',
                       'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_4) \
                       AppleWebKit/601.5.17 (KHTML, like Gecko) Version/9.1 Safari/601.5.17')
        req = urllib.request.urlopen(req)
        logger.debug('returning request [HTTP status code: %s]', req.getcode())
        return req
    except Exception as err:
        logger.debug('Error: %s', err)
        print('Error: %s' % err)
        with LOCK:
            E.error_links.append(url + str(page))
        return None


def work_page(page_q, pic_q):
    while page_q.qsize() > 0:
        page_num = page_q.get()
        url = E.url + str(page_num)
        print(url)
        html = fetch(url)
        if html is not None:
            parse_page(url, html, page_num, pic_q)


def parse_page(page_url, page_html, page_number, pic_q):
    page = tistory.Extractor(page_url, page_html, page_number)
    for link in page.get_links():
        pic_q.put(link)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s')

    if len(sys.argv) > 1:
        ARG = sys.argv
    else:
        ARG = 'ty https://ohcori.tistory.com/321 --debug -o -t 1 -f hello/world'.split()

    run(ARG)
