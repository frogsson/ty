from bs4 import BeautifulSoup
import urllib.request # replace with request
import urllib.parse # might replace with request
import threading 
import queue
import time
import http # not sure what this is for yet
import json # might replace with request
import sys
import os


def main(args):
    # Collects argument data -- might change this with argparse module
    ArgData.url = args[1]
    ArgData.url = format_url(ArgData.url)
    #get_data(ArgData.url, True) # checks if url is valid - fix this later
    argument_flags(args)

    # Collects image links from given arguments
    if ArgData.multiple_pages:
        multiple_pages()
    else:
        single_page()

    Error.total_img_found = URLData.q.qsize()

    lock = threading.Lock()
    # Starts the download
    print("\nStarting download:")
    while True:
        img_threads = [
                threading.Thread(target=DL, daemon=True)
                for i in range(int(ArgData.number_of_threads))
                ]
        for thread in img_threads:
            thread.start()
            time.sleep(0.1)
        for thread in img_threads:
            thread.join()

        # retry slow mode
        if len(Error.retry_error) > 0:
            ArgData.number_of_threads = 1
            Error.retry_error.clear()
        else:
            break # breaks if done


    #final report


class ArgData:
    organize = False
    multiple_pages = False
    number_of_threads = 6
    lock = threading.Lock()

# page_error - pages did not load
# img_error - images could not load or was skipped
# url_error - could not open following URLS
# content_type_error - Following urls were not a jpg, png or gif format and did not save

class Error:                # shared thread variables
    tota_img_found = 0      # not an error but I'll put it here for now for final report
    imgs_downloaded = 0

    HTTP404_error = []
    img_error = []     # img_error on old tty
    url_error = []
    retry_error = []
    value_error = []

    already_found = 0

def DL():
    while URLData.q.qsize() > 0:
        data = URLData.q.get()
        #print(data)
        url = data["url"]
        page = " - page " + data["page"] if data["page"] != None else ""

        # corrects the url for some cases
        # might improve with urllib.parse
        url = special_case_of_tistory_formatting(url) 

        # returns image headers in a dictionary, or None if error
        img_info = fetch_img_variables(url, data, page) 
        if img_info is None:
            continue

        # filter out files under 10kb
        # will skip file if it can't find content-length
        # it should always find it, so if it can't something is wrong
        if (img_info["Content-Length"].isdigit() and
            int(img_info["Content-Length"]) < 10000):
            Error.total_img_found -= 1
            continue
        elif img_info["Content-Length"] is None:
            print("Could not find Content-Length header for: ", url)
            Error.img_error.append("%s%s" % (url, page))
            continue

        #filters out non jpg/gif/png
        types = ["image/jpeg", "image/png", "image/gif"]
        if img_info["Content-Type"] not in types:
            content_type_error.append("%s%s" % (url, page))
            continue

        print(url)
        mem_file = get_data(url)
        with ArgData.lock:
            img_path = get_img_path(url, img_info)
            if img_path != None:
                print("saving:", img_path)
                img_file = open(img_path, "wb")
                img_file.write(mem_file)
                img_file.close()
                Error.imgs_downloaded += 1
            else:
                print("it's none")
                Error.already_found += 1

def get_img_path(url, img_info):
    s_types = [".jpg", ".jpeg", ".png", ".gif"]
    file_name = img_info["Content-Disposition"]
    if file_name == None:
        file_name = url.split("/")[-1]
        for s_type in s_types:
            if file_name.endswith(s_type):
                file_name = file_name.rsplit["."][0]
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
    if ArgData.organize:
        if data["date"] == "":
            data["data"] = "Untitled"
        no_good_chars = '\/:*?"<>|.'
        folder_name = data["date"]
        for char in no_good_chars:
            folder_name = folder_name.replace(char, "")
            file_name = file_name.replace(char, "")
        img_path = os.path.join(folder_name.strip(), file_name.strip())
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
    else:
        img_path = file_name.strip()

    for _ in range(999):
        if not os.path.exists(img_path):
            return img_path
        else:
            if int(img_info["Content-Length"]) != int(len(open(img_path, "rb").read())):
                number = file_name[file_name.rfind("(")+1:file_name.rfind(")")]
                if number.isdigit and file_name[file_name.rfind(")")+1:].lower() in s_types:
                    file_number = int(number) + 1
                    file_name = file_name.rsplit("(", 1)[0].strip()
                else:
                    file_number = 2
                    file_name = file_name.rsplit(".", 1)[0]
                file_name = file_name.strip() + " (" + str(file_number) + ")" + extension
                if ArgData.organize:
                    img_path = os.path.join(folder_name.strip(), file_name.strip())
                else:
                    img_path = file_name.strip()
            else:
                return None



def fetch_img_variables(url, data, page):
    try:
        img = urllib.request.urlopen(url)
        img_info = img.info()
    except urllib.error.HTTPError:
        print(url, "HTTP Error 404: Not Found")
        Error.img_error.append("%s%s" % (url, page))
    except urllib.error.URLError:
        url_error.append(url)
    except:
        if data["retry"] == True:
            data["retry"] = False
            URLData.q.put(data)
        else:
            Error.retry_error.append(data)
    else:
        return img_info

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

def special_case_of_tistory_formatting(url):
    if "=" in url and "tistory.com" in url:
        url = urllib.request.url2pathname(url)
        url = url.split("=")[-1]
        return url
    else:
        return url

def get_data(url):
    try:
        r = urllib.request.urlopen(url)
    except urllib.error.HTTPError:
        print(url, "HTTP Error 404: Not Found")
        Error.HTTP404_error.append(url)
    except ValueError as url_error:
        print(url_error)
        Error.value_error.append(url)
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
    
def parse_html(html, page_number):
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
            data["page"] = page_number
            URLData.q.put(data.copy())

def work_page(page_q):
    while page_q.qsize() > 0:
        page_number = page_q.get()
        url = ArgData.url + str(page_number)
        print(url)
        html = get_data(url)
        if html != None:
            parse_html(html, page_number)

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
    print("Fetching page source...")
    html = get_data(ArgData.url)
    page_number = ArgData.url.rsplit("/", 1)[1]
    if not page_number.isdigit():
        page_number = None
    if html != None:
        parse_html(html, page_number)

main(sys.argv)
