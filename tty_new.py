from bs4 import BeautifulSoup
import urllib.request # replace with request
import urllib.parse # might replace with request
import queue
import threading import time
import http # not sure what this is for yet
import json # might replace with request
import sys
import os


def main(args):
    ArgData.url = args[1]
    ArgData.url = format_url(ArgData.url)
    #get_source(ArgData.url, True) # url check
    #ArgData.url = "http://sinbru.tistory.com/36"
    argument_flags(args)
    if ArgData.multiple_pages:
        multiple_pages()
    else:
        single_page()
    print(URLData.q.qsize())
    while URLData.q.qsize() > 0:
        i = URLData.q.get()
        print(i)

class ArgData:
    organize = False
    multiple_pages = False
    number_of_threads = 6

class error:
    page_http = 0

def help_message():
    print(
        "-\n"
        "   Download images from a tistory page\n"
        "   >tty http://idol-grapher.tistory.com/140\n\n"
        "-p\n"
        "   Download images from multiple pages\n\n"
        "   To download images from page 140 to 150\n"
        "   >tty http://idol-grapher.tistory.com/ -p 140-150\n\n"
        "   To download images from page 1, 2 and 3\n"
        "   >tty http://idol-grapher.tistory.com/ -p 1,2,3\n\n"
        "   To download images from page 1, 2, 3, 5 to 10 and 20 to 25\n"
        "   >tty http://idol-grapher.tistory.com/ -p 1,2,3,5-10,20-25\n\n"
        "-t\n"
        "   Number of simultaneous downloads (default is 6 and max is 32)\n"
        "   >tty http://idol-grapher.tistory.com/140 -t 6\n\n"
        "-o\n"
        "   Organize images by title (may not always work)\n"
        "   >tty http://idol-grapher.tistory.com/140 -o\n"
        )
    sys.exit()

def error_message(error):
    print(error)
    print("\n>tty --help (for help and more options)")
    sys.exit()

def format_url(url):
    if url.startswith("http://www."):
        url = "http://" + url[11:]
    elif url.startswith("www."):
        url = url[4:]
        url = "http://" + url
    return url      # http://idol-grapher.tistory.com/

def get_source(url, valid_url_check):
    try:
        r = urllib.request.urlopen(url)
    except urllib.error.HTTPError:
        print(url, "HTTP Error 404: Not Found")
        error.page_http += 1
    except ValueError as url_error:
        if valid_url_check:
            error_message(url_error)
        else:
            print(url_error)
    else:
        if valid_url_check:
            r.close()
            return None
        else:
            html = r.read()
            r.close()
            return html

def parse_pages(p_digits):
    ArgData.multiple_pages = True
    ArgData.number_of_pages = []

    digit_check = p_digits.replace(",", " ")
    digit_check = digit_check.replace("-", " ").split(" ")
    for digit in digit_check:
        if not digit.isdigit():
            digit_error = "-p can only accept numbers\n" \
                          ">tty http://idol-grapher.tistory.com/ -p 1,2,3-10"
            error_message(digit_error)

    p_digits = p_digits.split(",")
    for digit in p_digits:
        if "-" in digit:
            first_digit = digit.split("-")[0]
            second_digit = digit.split("-")[1]
            total_digit = int(second_digit) - int(first_digit)
            for new_digit in range(total_digit + 1):
                ArgData.number_of_pages.append(new_digit + int(first_digit))
        else:
            ArgData.number_of_pages.append(int(digit))

def argument_flags(args):
    for opt in args:
        if opt == "-h" or opt == "--help":
            help_message()
        elif opt == "-p" or opt == "--pages":
            try:
                parse_pages(args[args.index("-p") + 1])
            except IndexError:
                page_error = "-p needs an argument\n" \
                             ">tty http://idol-grapher.tistory.com/ -p 1-5"
                error_message(page_error)
        elif opt == "-t" or opt == "--threads":
            try:
                thread_num = args[args.index("-t") + 1]
            except IndexError:
                thread_num_error = "-t needs an argument\n" \
                                   ">tty http://idol-grapher.tistory.com/244 -t 6"
                error_message(thread_num_error)
            if (thread_num.isdigit() and 
                int(thread_num) > 0 and
                int(thread_num) < 33):
                ArgData.number_of_threads = int(thread_num)
            else:
                thread_num_error = "-t needs a number in between 1-32\n" \
                                   ">tty http://idol-grapher.tistory.com/244 -t 6"
                error_message(thread_num_error)
        elif opt == "-o" or opt == "--organize":
            ArgData.organize = True

class URLData:
    q = queue.Queue()
    
def parse_html(html):
    data = {}
    soup = BeautifulSoup(html, "html.parser")
    try:
        date = soup.find(property="og:title").get("content")
    except AttributeError:
        date = soup.title.string
    for tag in soup.find_all("img"):
        url = tag.get("src")
        if "tistory.com" in url:
            url = url.replace("image", "original")
        if "daumcdn.net" not in url:
            data["date"] = date
            data["retry"] = True
            data["url"] = url
            URLData.q.put(data.copy())

def work_page(page_q):
    while page_q.qsize() > 0:
        page_number = page_q.get()
        url = ArgData.url + str(page_number)
        print(url)
        time.sleep(1)
        html = get_source(url, False)
        if html != None:
            parse_html(html)

def multiple_pages():
    page_q = queue.Queue()
    ArgData.number_of_pages.sort(key=int)
    print("Fetching source for:")
    for page in ArgData.number_of_pages:
        page_q.put(page)
    ArgData.number_of_pages.clear()
    page_t = [threading.Thread(target=work_page, args=(page_q,), daemon=True) for i in range(4)]
    for thread in page_t:
        thread.start()
        time.sleep(0.1)
    for thread in page_t:
        thread.join()
            
def single_page():
    html = get_source(ArgData.url, False)
    if html != None:
        parse_html(html)

main(sys.argv)
