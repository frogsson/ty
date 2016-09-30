import urllib.request, sys, queue, threading, time, os, http
from html.parser import HTMLParser


def get_source(url):
    try:
        with urllib.request.urlopen(url) as u:
            html = u.read()
            return html
    except urllib.error.HTTPError:
        print("HTTP Error 404: Not Found:", url)
        page_error.append(url)

def saver():
    global pics_downloaded
    global same_file_length
    while q.qsize() > 0:
        data = q.get()
        i = data["url"]
        if "=" in i:
            i = urllib.request.url2pathname(i)
            i = i.split("=")[-1]
        if "http" not in i:
            i = "http://" + i
        try:
            img = urllib.request.urlopen(i)
        except urllib.error.HTTPError:
            print("HTTP Error 404: Not Found:", i)
            img_error.append("%s - page %s" % (i, data["page"]))
        else:
            if img.info()["Content-Type"] == "image/gif":
                break
            file_name = img.info()["Content-Disposition"]
            if file_name == None:
                o = urllib.request.url2pathname(i)
                file_name = o.split("/")[-1]
                if img.info()["Content-Type"] == "image/jpeg":
                    file_name = file_name + ".jpg"
                elif img.info()["Content-Type"] == "image/png":
                    file_name = file_name + ".png"
            else:
                file_name = file_name.split('"')[1]
                file_name = urllib.request.url2pathname(file_name)
            if data["date"] == None:
                data["date"] = "No Title"
            if organize == True:
                no_good_letters = '\/:*?"<>|'
                folder_name = data["date"]
                for char in no_good_letters:
                    folder_name = folder_name.replace(char, "")
                img_path = os.path.join(folder_name, file_name)
                if not os.path.exists(folder_name):
                    os.makedirs(folder_name)
            else:
                img_path = file_name
            while True:
                if not os.path.exists(img_path):
                    print("%s" % (i))
                    try:
                        temp_file = img.read()
                    except http.client.IncompleteRead:
                        if data["retry"] == True:
                            data["retry"] = False
                            q.put(data)
                        else:
                            retry_error.append(data)
                    else:
                        img_link = open(img_path, "wb")
                        img_link.write(temp_file)
                        img_link.close()
                        pics_downloaded += 1
                    break
                else:
                    nonlocal_img = img.info()["Content-Length"]
                    with open(img_path, "rb") as f:
                        local_img = len(f.read())
                        f.close()
                    if int(nonlocal_img) != int(local_img):
                        if img.info()["Content-Type"] == "image/jpeg":
                            file_name = file_name.split(".jpg")[0]
                            file_name = file_name + "I" + ".jpg"
                        elif img.info()["Content-Type"] == "image/png":
                            file_name = file_name.split(".png")[0]
                            file_name = file_name + "I" + ".png"
                    else:
                        same_file_length += 1
                        break

class PicLinks(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.title_check = False
        self.title = ""
        self.title_dict = {}
        self.parsed_list = []

    def handle_starttag(self, tag, attrs):
        # Tistory
        if tag == "meta":
            for name, value in attrs:
                if value == "og:title":
                    self.title_check = True

                if name == "content" and self.title_check == True:
                    self.title = value
                    self.title_check = False

        if tag == "img":
            for name, value in attrs:
                if name == "src" and "tistory.com" in value:
                    l = value.replace("image", "original")
                    self.title_dict["date"] = self.title
                    self.title_dict["url"] = l
                    self.title_dict["retry"] = True
                    if self.title_dict not in self.parsed_list:
                        self.parsed_list.append(self.title_dict.copy())

url = sys.argv[1].replace(" ", "")
number_of_threads = 12
number_of_pages = []
multiple_pages = False
organize = False
same_file_length = 0
pics_downloaded = 0
img_error = []
page_error = []
retry_error = []
q = queue.Queue()
page_q = queue.Queue()
link_list = []

for opt in sys.argv[1:]:
    if opt == "-help":
        print(
        "   Download images from a specific tistory page\n"
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
        "   Specify number of simultaneous downloads (default is 12)\n"
        "   >tty http://idol-grapher.tistory.com/140 -t 12\n\n"
        "-o\n"
        "   Organize images by title (might not work, it's unpredictable)\n"
        "   >tty http://idol-grapher.tistory.com/140 -o\n\n"
        )
        sys.exit()
    elif opt == "-p":
        multiple_pages = True
        p_num = sys.argv[sys.argv.index("-p") + 1]
        digit_check = p_num.replace(",", " ")
        digit_check = digit_check.replace("-", " ").split(" ")
        for digit in digit_check:
            if not digit.isdigit():
                print(
                "   -p can only accept digits\n"
                "   >tty http://idol-grapher.tistory.com/ -p 1,2,5-10"
                )
                sys.exit()

        p_num = p_num.split(",")
        for num in p_num:
            if "-" in num:
                first_num = num.split("-")[0]
                second_num = num.split("-")[1]
                total_num = int(second_num) - int(first_num)
                for new_num in range(total_num + 1):
                    number_of_pages.append(new_num + int(first_num))
            else:
                number_of_pages.append(num)

    elif opt == "-t":
        t_num = sys.argv[sys.argv.index("-t") + 1]
        if t_num.isdigit() and int(t_num) > 0 and int(t_num) < 61:
            number_of_threads = t_num
        else:
            print(
            "   Threads(-t) needs to be a number in between 1-60\n\n"
            "   >tty http://jjtaeng.tistory.com/244 -t 3\n"
            )
            sys.exit()
    elif opt == "-o" or opt == "-organize":
        organize = True

def work_page():
    while page_q.qsize() > 0:
        page_nmbr = page_q.get()
        multi_url = str(url) + str(page_nmbr)
        print("%s" % multi_url)
        html = get_source(multi_url)
        if html != None:
            parser = PicLinks()
            parser.feed(html.decode("utf-8"))
            for x in parser.parsed_list:
                x["page"] = page_nmbr
                link_list.append(x)

if multiple_pages == True:
    number_of_pages.sort(key=int)
    print("Fetching source for:")
    if url[-1] != "/":
        url = url + "/"
    for page in number_of_pages:
        page_q.put(page)

    page_threads = [threading.Thread(target=work_page, daemon=True) for i in range(4)]
    for thread in page_threads:
        thread.start()
        time.sleep(0.2) #LookupError:unknown encoding:idna | error I get without this
    for thread in page_threads:
        thread.join()
else:
    print("Fetching page source...")
    html = get_source(url)
    if html != None:
        parser = PicLinks()
        parser.feed(html.decode("utf-8"))
        for x in parser.parsed_list:
            x["page"] = url.split("/")[-1]
            link_list.append(x)
    else:
        sys.exit()
for x in link_list:
    q.put(x)
if int(number_of_threads) > q.qsize():
    number_of_threads = q.qsize()
total_found = q.qsize()
print("\nStarting download:")

img_threads = [threading.Thread(target=saver, daemon=True) for i in range(int(number_of_threads))]
for thread in img_threads:
    thread.start()
    time.sleep(0.1)
for thread in img_threads:
    thread.join()

if len(retry_error) > 0:
    print("\nInterrupted downloads:")
    for x in retry_error:
        print(x["url"])
    while 1:
        yes_no = input("%s download%s %s interrupted, do you want to try download %s again? Y/n\n" %
        (len(retry_error),
        "s" if len(retry_error) > 1 else "",
        "were" if len(retry_error) > 1 else "was",
        "them" if len(retry_error) > 1 else "it"
        ))
        if yes_no.lower() == "y" or yes_no.lower() == "yes" or yes_no == "":
            for x in retry_error:
                q.put(x)
            break
        elif yes_no.lower() == "n" or yes_no.lower() == "no":
            for x in retry_error:
                y = "%s - page %s" % (x["url"], x["page"])
                img_error.append(y)
            break
        else:
            print("Not a valid input.\n")

    if q.qsize() > 0:
        print("\nStarting download:")
        backup_thread = threading.Thread(target=saver, daemon=True)
        backup_thread.start()
        backup_thread.join()

msg_total = (
" Scraper found %s image%s." %
(total_found,
"s" if total_found > 1 else "",
))
msg_dl = (
" %s saved%s" %
(pics_downloaded,
"." if same_file_length <= 0 else ",",
))
msg_length = (
" %s already existed and did not save." %
(same_file_length,
))
print("Done!%s%s%s" % (
msg_total if total_found > 0 else " Scraper could not find any images.",
msg_dl if pics_downloaded > 0 else "",
msg_length if same_file_length > 0 else "",
))
if len(page_error) > 0:
    print(
    "\n%s page%s did not load." % (
    len(page_error),
    "s" if len(page_error) > 1 else "",
    ))
    for x in page_error:
        print(x)
if len(img_error) > 0:
    print(
    "\n%s image%s did not load." % (
    len(img_error),
    "s" if len(img_error) > 1 else "",
    ))
    for x in img_error:
        print(x)
