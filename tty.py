import urllib.request
import urllib.parse
import threading
import queue
import time
import sys
import os
import re


class E:
    number_of_threads = 6
    number_of_pages = []
    title_filter_words = []
    multiple_pages = False
    title_filter = False
    organize = False
    testing = False

    title = re.compile('content="(.+?)"')
    title1 = re.compile('<meta.+?>')
    title2 = re.compile('<title>(.+?)</title>')

    imgtag = re.compile('<img.+?>')
    imgurl = re.compile('src="(.+?)"')

    pic_q = queue.Queue()
    page_q = queue.Queue()
    lock = threading.Lock()

    imgs_downloaded = 0
    total_img_found = 0
    already_found = 0

    HTTP_error = []
    retry_error = []
    url_error = []


def main(args):  # python tty.py www.tistory.ilovegfriend.com/231
    if len(args) < 2:
        print("No arguments given")
        print("\n>tty --help (for help and more options)")
        input("\nPress Enter to continue")
        sys.exit()

    # Parses argument flags -- might change with argparse module
    argument_flags(args)
    E.url = format_url(args[1])
    E.netloc = urllib.parse.urlparse(E.url).netloc

    if E.testing:
        print("\n{}".format(E.url))

    # Parse pages for images
    if E.multiple_pages:
        if not E.url.endswith("/"):
            E.url = E.url + "/"
        E.number_of_pages.sort(key=int)
        for page in E.number_of_pages:
            E.page_q.put(page)
        print("Fetching source for:")
        E.number_of_pages.clear()
        start_threads(number_of_threads, work_page)
    else:
        print("Fetching page source...")
        html = fetch(E.url)
        page_number = E.url.rsplit("/", 1)[1]
        if not page_number.isdigit():
            page_number = None
        if html is not None:
            parse_page(html, page_number)
        else:
            sys.exit()
    E.total_img_found = E.pic_q.qsize()

    # Starts the download
    lock = threading.Lock()
    print("\nStarting download:")
    start_threads(E.number_of_threads, DL)

    # Retry in slow mode if there was any timeout errors
    if len(E.retry_error) > 0:
        print(
            "\n{} image{} {} interrupted, retrying in slow mode:".format(
                len(
                    E.retry_error), "s" if len(
                    E.retry_error) > 1 else "", "was" if len(
                    E.retry_error) < 2 else "were"))
        for x in E.retry_error:
            E.pic_q.put(x)
        start_threads(1, DL)

    # Final report
    total_error = len(E.HTTP_error) + len(E.url_error)
    print("\nDone!")
    print("Found:", E.total_img_found)
    if E.imgs_downloaded > 0:
        print("Saved:", E.imgs_downloaded)
    if E.already_found > 0:
        print("Already saved:", E.already_found)

    if total_error > 0:
        print("Errors:", total_error)
    if len(E.HTTP_error) > 0:
        print("\nHTTP error:")
        [print(url) for url in E.HTTP_error]
    if len(E.url_error) > 0:
        print("\nCould not open:")
        [print(url) for url in E.url_error]


def start_threads(number_of_threads, _target):
    img_threads = [threading.Thread(target=_target, daemon=True)
                   for i in range(int(number_of_threads))]
    for thread in img_threads:
        thread.start()
        time.sleep(0.1)
    for thread in img_threads:
        thread.join()


def DL():
    while E.pic_q.qsize() > 0:
        data = E.pic_q.get()
        url = data["url"]
        date = data["date"]
        page = " -page /{}".format(data["page"]
                                   ) if data["page"] is not None else ""

        # Corrects the url for some cases
        url = special_case_of_tistory_formatting(url)

        # Returns image headers in a dictionary, or None if error
        img_info = fetch(url, retry=data["retry"], img_headers=True, page=page)
        if img_info is None:
            continue
        elif "_TimeoutError_" == img_info:
            data["retry"] = False
            E.retry_error.append(data)
            continue

        # Filter out files under 10kb
        if (img_info["Content-Length"].isdigit() and
                int(img_info["Content-Length"]) < 10000):
            E.total_img_found -= 1
            continue

        # Filter out non jpg/gif/png
        types = ["image/jpeg", "image/png", "image/gif"]
        if img_info["Content-Type"] not in types:
            E.total_img_found -= 1
            continue

        print(url)
        mem_file = fetch(url, retry=data["retry"], page=page)
        if mem_file is None:
            continue
        elif "_TimeoutError_" == mem_file:
            data["retry"] = False
            E.retry_error.append(data)
            continue

        with E.lock:
            img_path = get_img_path(url, date, img_info)
            if E.testing:
                continue
            if img_path is not None:
                img_file = open(img_path, "wb")
                img_file.write(mem_file)
                img_file.close()
                E.imgs_downloaded += 1
            else:
                E.already_found += 1


def get_img_path(url, date, img_info):
    s_types = [".jpg", ".jpeg", ".png", ".gif"]
    file_name = img_info["Content-Disposition"]
    if file_name is None:
        file_name = url.split("/")[-1]
        for s_type in s_types:
            if file_name.endswith(s_type):
                file_name = file_name.rsplit(".", 1)[0]
    else:
        if "filename*=UTF-8" in file_name:
            file_name = file_name.split("filename*=UTF-8''")[1]
            file_name = file_name.rsplit(".", 1)[0]
        else:
            file_name = file_name.split('"')[1]
        file_name = urllib.request.url2pathname(file_name)
    extension = "." + img_info["Content-Type"].split("/")[1]
    extension = extension.replace("jpeg", "jpg")
    file_name = file_name + extension
    if E.organize:
        if date is None:
            date = "Untitled"
        no_good_chars = r'\/:*?"<>|.'
        folder_name = date
        for char in no_good_chars:
            folder_name = folder_name.replace(char, "")
        img_path = os.path.join(folder_name.strip(), file_name.strip())
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
    else:
        img_path = file_name.strip()

    for _ in range(999):
        if not os.path.exists(img_path):
            return img_path
        else:
            if int(img_info["Content-Length"]
                   ) != int(len(open(img_path, "rb").read())):
                number = file_name[file_name.rfind(
                    "(") + 1:file_name.rfind(")")]
                if number.isdigit and file_name[file_name.rfind(
                        ")") + 1:].lower() in s_types:
                    file_number = int(number) + 1
                    file_name = file_name.rsplit("(", 1)[0].strip()
                else:
                    file_number = 2
                    file_name = file_name.rsplit(".", 1)[0]
                file_name = file_name.strip() + " (" + str(file_number) + ")" + extension
                if E.organize:
                    img_path = os.path.join(
                        folder_name.strip(), file_name.strip())
                else:
                    img_path = file_name.strip()
            else:
                return None


def fetch(url, img_headers=False, retry=False, page=""):
    try:
        r = urllib.request.urlopen(url)
        if img_headers:
            return r.info()
        else:
            return r.read()
    except urllib.error.HTTPError as error:
        print(url, error)
        E.HTTP_error.append(url + str(page))
    except ValueError as error:  # missing http/https
        print(url, error)
        E.url_error.append(url + str(page))
    except Exception as error:
        print(url, error)
        if retry:
            return "_TimeoutError_"
        else:
            print(url, error)
            E.url_error.append(url + str(page))


def help_message():
    print(
        "usage: tty \"url\"\n"
        "    Download images from a tistory page\n"
        "    >tty http://idol-grapher.tistory.com/140\n\n"
        "optional:\n"
        "-p, --pages\n"
        "    Download images from multiple pages\n\n"
        "    Download images from page 140 to 150\n"
        "    >tty http://idol-grapher.tistory.com/ -p 140-150\n\n"
        "    Download images from page 1, 2 and 3\n"
        "    >tty http://idol-grapher.tistory.com/ -p 1,2,3\n\n"
        "    Download images from page 1, 2, 3, 5 to 10 and 20 to 25\n"
        "    >tty http://idol-grapher.tistory.com/ -p 1,2,3,5-10,20-25\n\n"
        "-t, --threads\n"
        "    Number of simultaneous downloads (32 max)\n"
        "    >tty http://idol-grapher.tistory.com/140 -t 12\n\n"
        "-o, --organize\n"
        "    Organize images by date\n"
        "    >tty http://idol-grapher.tistory.com/140 -o\n\n"
        "-f, --filter\n"
        "    Download images only from pages where the title contains one of the words you define, multiple words split by \"/\"\n"
        "    Download images from pages containing the words 여자친구 OR 소원 OR 은하 (translates to GFRIEND, SOWON, EUNHA)\n"
        "    >tty http://idol-grapher.tistory.com/ -p 20-160 -f 여자친구/소원/은하 (translates to GFRIEND/SOWON)\n\n"
        "    (Note: This only works alongside the -p argument, and most tistory pages use Korean titles so you\n"
        "    may have to translate)")
    sys.exit()


def error_message(error):
    print(error)
    print("\nFor help and more options:")
    print(">tty --help")
    sys.exit()


def format_url(url):
    if url.startswith('"') and url.endswith('"'):
        url = url.strip('"')
    if url.startswith("http://www."):
        url = "http://" + url[11:]
    elif url.startswith("www."):
        url = "http://" + url[4:]
    elif not url.startswith("http") and not url.startswith("https"):
        url = "http://" + url
    return url      # http://idol-grapher.tistory.com/


def special_case_of_tistory_formatting(url):
    if "fname=" in url and "tistory.com" in url:
        url = urllib.request.url2pathname(url)
        url = url.split("fname=")[-1]
    return url


def split_pages(p_digits):
    digit_check = p_digits.replace(",", " ")
    digit_check = digit_check.replace("-", " ").split(" ")
    for digit in digit_check:
        if not digit.isdigit():
            digit_error = "-p only accept numbers\n" \
                          ">tty http://idol-grapher.tistory.com/ -p 1,2,3-10"
            error_message(digit_error)
    p_digits = p_digits.split(",")
    for digit in p_digits:
        if "-" in digit:
            first_digit = digit.split("-")[0]
            second_digit = digit.split("-")[1]
            if int(second_digit) > int(first_digit):
                total_digit = int(second_digit) - int(first_digit)
            else:
                negative_error = "{}\n" \
                                 "Can't go from '{} to {}'\n" \
                                 ">tty http://idol-grapher.tistory.com/ -p 1-10".format(digit, first_digit, second_digit)
                error_message(negative_error)
            for new_digit in range(total_digit + 1):
                E.number_of_pages.append(new_digit + int(first_digit))
        else:
            E.number_of_pages.append(int(digit))


def argument_flags(args):
    for arg in args:
        if arg == "-f" or arg == "--filter":
            E.title_filter = True
            try:
                E.title_filter_words = args[args.index(
                    "-f" if "-f" in args else "--filter") + 1].split('/')
            except IndexError:
                thread_title_filter_error = "{} needs an argument\n\n" \
                                            "Example:\n" \
                                            ">tty http://idol-grapher.tistory.com/ -p 3-19 -f GFRIEND".format("-f" if "-f" in args else "--filter")
                error_message(thread_title_filter_error)
        if arg == "-h" or arg == "--help":
            help_message()
        if arg == "-p" or arg == "--pages":
            E.multiple_pages = True
            try:
                split_pages(
                    args[args.index("-p" if "-p" in args else "--pages") + 1])
            except IndexError:
                page_error = "{} needs an argument\n\n" \
                             ">tty http://idol-grapher.tistory.com/ -p 1-5".format("-p" if "-p" in args else "--pages")
                error_message(page_error)
        if arg == "-t" or arg == "--threads":
            try:
                thread_num = args[args.index(
                    "-t" if "-t" in args else "--threads") + 1]
            except IndexError:
                thread_num_error = "{} needs an argument\n\n" \
                                   ">tty http://idol-grapher.tistory.com/244 -t 6".format("-t" if "-t" in args else "--threads")
                error_message(thread_num_error)
            if (thread_num.isdigit() and
                int(thread_num) > 0 and
                    int(thread_num) < 33):
                E.number_of_threads = int(thread_num)
            else:
                thread_num_error = "-t needs a number in between 1-32\n" \
                                   ">tty http://idol-grapher.tistory.com/244 -t 6"
                error_message(thread_num_error)
        if arg == "-o" or arg == "--organize":
            E.organize = True
        if arg == "--test":
            E.testing = True


def parse_page(html, page_number):
    parse = False
    data = {}
    html = html.decode("utf-8")
    date = None

    for meta in E.title1.finditer(html):
        if "og:title" in meta[0]:
            try:  # make a better regex parser instead of this mess
                date = E.title.search(meta[0])[1]
            except BaseException:
                pass

    if date is None:
        date = E.title2.search(html)[1]

    if E.title_filter and date:
        for word in E.title_filter_words:
            if re.search('.*?{}.*?'.format(word), date, flags=re.IGNORECASE):
                parse = True
                break
    else:
        parse = True

    if parse:
        for img in E.imgtag.finditer(html):
            url = E.imgurl.search(img[0])

            # UGLY FILTER
            # filter_list = ["tistory_admin", "/skin/"]
            if url is None:
                continue
            url = url[1]
            if "/content/files/" in url:  # UGLY http://www.breath39.com/master/20
                url = "http://{}{}".format(E.netloc, url)
            if ("tistory_admin" in url
                    or urllib.parse.urlparse(url).netloc == ""
                    or "/skin/" in url):
                continue
            if "daumcdn" in url and not url.endswith("?original"):
                url = url + "?original"
            elif "tistory" in url:
                url = url.replace("/image/", "/original/")
            data["date"] = date
            data["url"] = url
            data["page"] = page_number
            data["retry"] = True
            E.pic_q.put(data.copy())


def work_page():
    while E.page_q.qsize() > 0:
        page_number = E.page_q.get()
        url = E.url + str(page_number)
        print(url)
        html = fetch(url)
        if html is not None:
            parse_page(html, page_number)


if __name__ == "__main__":
    main(sys.argv)
