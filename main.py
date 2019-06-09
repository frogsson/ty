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
import httpbin


SPECIAL_CHARS = r'!\"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
CONTENT_TYPES = ["image/jpeg", "image/png", "image/gif, image/webp"]
IMG_EXTS = ['jpg', 'jpeg', 'png', 'gif', 'webp']
LOCK = threading.Lock()

# issue: if multiple pages have the same url saved to same directory they'll be marked as "already saved"
# TODO add directory to img_path
# TODO


class E:
    imgs_downloaded = 0
    already_found = 0


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
        html = httpbin.Fetch(E.url).body()
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

    if httpbin.Fetch.errors:
        print("\nCould not download:")
        for url in httpbin.Fetch.errors:
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
        # page = " -page /{}".format(data["page"]) if data["page"] is not None else ""

        content = httpbin.Fetch(url)

        if content is None:
            continue

        print(url)
        with LOCK:
            img_path = get_img_path(url, title, content.info(), filename=data['filename'])
            if E.debug:
                continue
            if img_path is not None:
                with open(img_path, 'wb') as f:
                    f.write(content.body())
                E.imgs_downloaded += 1
            else:
                E.already_found += 1


def get_img_path(url, folder, img_info, filename):
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

    if E.organize:
        if folder is None:
            folder = "Untitled"
        for char in SPECIAL_CHARS:
            folder = folder.replace(char, "")
        folder = folder.strip()
        img_path = os.path.join(folder, filename)
        if not os.path.exists(folder):
            os.makedirs(folder)
    else:
        img_path = filename.strip()

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
            # filename = filename.strip() + " (" + str(file_number) + ")" + extension
            filename = "{} ({}){}".format(filename, file_number, extension)
            if E.organize:
                img_path = os.path.join(
                    folder.strip(), filename)
            else:
                img_path = filename
        else:
            return None


# def test(folder, file):
#     if E.organize:
#         if folder is None:
#             folder = "Untitled"
#         for char in SPECIAL_CHARS:
#             folder = folder.replace(char, "")
#         folder = folder.strip()
#         img_path = os.path.join(folder, filename)
#         if not os.path.exists(folder):
#             os.makedirs(folder)
#     else:
#         img_path = filename.strip()
# 


def work_page(page_q, pic_q):
    while page_q.qsize() > 0:
        page_num = page_q.get()
        url = E.url + str(page_num)
        print(url)
        html = httpbin.Fetch(url).body()
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
