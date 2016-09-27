import urllib.request, sys, queue, threading, time, os
from html.parser import HTMLParser


def get_source(url):
    with urllib.request.urlopen(url) as url:
        html = url.read()
        return html

def saver():
    global pics_downloaded
    global changed_file_name
    global same_file_length
    file_name_check = True
    i = q.get()
    if "=" in i:
        i = urllib.request.url2pathname(i)
        i = i.split("=")[-1]
    if "http" not in i:
        i = "http://" + i
    with urllib.request.urlopen(i) as img:
        file_name = img.info()["Content-Disposition"]
        if file_name == None:
            o = urllib.request.url2pathname(i)
            file_name = o.split("/")[-1]
            file_name = file_name + ".jpg"
        else:
            file_name = file_name.split('"')[1]
            file_name = urllib.request.url2pathname(file_name)

        while True:
            if not os.path.exists(file_name):
                print("Downloading: %s" % (i))
                imglink = open(file_name, "wb")
                imglink.write(img.read())
                imglink.close()
                pics_downloaded += 1
                break
            else:
                nonlocal_img = img.info()["Content-Length"]
                with open(file_name, "rb") as f:
                    local_img = len(f.read())
                    f.close()
                if int(nonlocal_img) != int(local_img):
                    file_name = file_name.split(".jpg")[0]
                    file_name = file_name + "I" + ".jpg"
                    if not os.path.exists(file_name):
                        changed_file_name += 1
                else:
                    same_file_length += 1
                    break
    if q.qsize() > 0:
        thread_starter()
    elif threading.active_count() <= 2 and q.qsize() <= 0:
        msg_total = (
        " Scraper found %s picture%s." %
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
        msg_total if total_found > 0 else "Scraper could not find any pictures.",
        msg_dl if pics_downloaded > 0 else "",
        msg_length if same_file_length > 0 else "",
        ))

def thread_starter():
    t = threading.Thread(target=saver)
    t.start()

link_listg = []
class PicLinks(HTMLParser):
    def handle_starttag(self, tag, attrs):
        # Tistory
        if tag == "img":
            for name, value in attrs:
                if name == "src" and "tistory.com" in value:
                    l = value.replace("image", "original")
                    if l not in link_listg:
                        link_listg.append(l)
        # Imgur
        if tag == "a":
            for name, value in attrs:
                if ".jpg" in value:
                    l = value.replace("//", "")
                    link_listg.append(l)

url = sys.argv[1].replace(" ", "")
number_of_threads = 12
number_of_pages = []
multiple_pages = False
changed_file_name = 0
same_file_length = 0
pics_downloaded = 0

for opt in sys.argv[1:]:
    if opt == "-help":
        print(
        "   Download a specific tistory page\n"
        "   >tty http://idol-grapher.tistory.com/140\n\n"
        "-p\n"
        "   Download pictures from multiple pages\n"
        "   >tty http://idol-grapher.tistory.com/ -p 140-150\n"
        "-t\n"
        "   Specify number of simultaneous downloads (default is 12)\n"
        "   >tty http://idol-grapher.tistory.com/140 -t 4\n"
        )
        sys.exit()
    elif opt == "-p":
        multiple_pages = True
        p_num = sys.argv[sys.argv.index("-p") + 1]
        first_num = p_num.split("-")[0]
        last_num = p_num.split("-")[1]
        total_num = int(last_num) - int(first_num)
        for x in range(total_num + 1):
            number_of_pages.append(x + int(first_num))
    elif opt == "-t":
        t_num = sys.argv[sys.argv.index("-t") + 1]
        if t_num.isdigit() and int(t_num) > 0 and int(t_num) < 31:
            number_of_threads = t_num
        else:
            print(
            "Threads(-t) needs to be a number in between 1-30\n\n"
            "   >tty http://jjtaeng.tistory.com/244 -t 3\n"
            )
            sys.exit()

if multiple_pages == True:
    print("Fetching source for:")
    if url[-1] != "/":
        url = url + "/"
    for page in number_of_pages:
        multi_url = url + str(page)
        print(multi_url)
        html = get_source(multi_url)
        PicLinks().feed(html.decode("utf-8"))
else:
    print("Fetching page source...")
    html = get_source(url)
    PicLinks().feed(html.decode("utf-8"))

link_list = link_listg
q = queue.Queue()
for x in link_list:
    q.put(x)
if int(number_of_threads) > q.qsize():
    number_of_threads = q.qsize()
total_found = q.qsize()
print("\nStarting download:")
for x in range(int(number_of_threads)):
    thread_starter()
