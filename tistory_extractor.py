#!/usr/bin/env python

import urllib.parse
import logging
import re


class Extractor:
    """extractor for Tistory"""
    regex = {
        'title_meta': re.compile('<meta.+?>'),
        'title_doublequotes': re.compile('content="(.+?)"'),
        'title_singlequotes': re.compile("content='(.+?)'"),
        'title_fallback': re.compile('<title>(.+?)</title>'),
        'imgtag': re.compile('<img.+?>'),
        'imgurl': re.compile('src=["\'](.+?)["\']'),
        'filename': re.compile('data-filename=["\'](.+?)["\']'),
        'filename_fallback1': re.compile('filename=["\'](.+?)["\']'),
        'filename_fallback2': re.compile('file_name=["\'](.+?)["\']'),
    }

    def __init__(self, page_url, page_html, page_num):
        self.logger = logging.getLogger('Tistory Extractor')
        self.page_url = urllib.parse.urlparse(page_url)
        self.html = page_html.decode('utf-8', 'replace')
        self.title = self.find_title()
        self.page_num = page_num
        self.links = []

        self.find_links()

    def find_title(self):
        """
        tries to find title
        returns String or NoneType
        """
        self.logger.debug('find_title()')
        date = None
        for meta in self.regex["title_meta"].finditer(self.html):
            if "og:title" in meta[0]:
                # checks first for contents="*" then contents='*' if doublequotes doesn't exist
                date = self.regex['title_doublequotes'].search(meta[0])

                if not date:
                    date = self.regex['title_singlequotes'].search(meta[0])

                if date:
                    break

        if not date:
            date = self.regex['title_fallback'].search(self.html)

        if date:
            date = date[1]
            self.logger.debug('title: %s', date)
        else:
            self.logger.debug('no title')

        return date

    def find_links(self):
        """find urls"""
        self.logger.debug('find_links()')
        for imgtag in self.regex['imgtag'].finditer(self.html):
            reg_url = self.regex['imgurl'].search(imgtag[0])

            if reg_url:
                url_components = self.format_components(reg_url[1])

                if self.exclude(url_components):
                    continue

                url_info = {'url': url_components.geturl(),
                            'title': self.title,
                            'page': self.page_num,
                            'filename': self.find_filename(imgtag[0])}

                if url_info not in self.links:
                    self.add_item(url_info)

    def exclude(self, components):
        """a bunch of filter checks"""
        if len(components.path) < 2:
            self.logger.debug('components.path is less than two removing: %s', components.geturl())
            return True

        if "/skin/" in components.path:
            self.logger.debug('found /skin/ in: %s', components.geturl())
            return True

        if "/tistory_admin/" in components.path:
            self.logger.debug('found /tistory_admin/ in: %s', components.geturl())
            return True

        return False

    def find_filename(self, tag):
        """
        looks for filename inside same <img> tag as url
        returns String or NoneType
        """
        self.logger.debug('find_filename()')
        filename = self.regex['filename'].search(tag)

        if not filename:
            filename = self.regex['filename_fallback1'].search(tag)

        if not filename:
            filename = self.regex['filename_fallback2'].search(tag)

        if filename:
            filename = filename[1]
            self.logger.debug('found filename: %s', filename)

        return filename

    def add_item(self, item):
        """add item to download queue"""
        self.logger.debug('add_item()')
        self.logger.debug('adding %s', item)
        self.links.append(item.copy())

    def get_links(self):
        """returns queue of links extractor found"""
        self.logger.debug('get_queue')
        return self.links

    def format_components(self, url):
        """format image hosting url quirks"""
        if url.startswith('"') and url.endswith('"'):
            url = url.strip('"')

        components = urllib.parse.urlparse(url)

        if "fname=" in components.path and "tistory" in components.netloc:
            url = urllib.request.url2pathname(components.geturl())
            url = url.split("fname=")[-1]
            components = urllib.parse.urlparse(url)

        if not components.scheme:
            components = components._replace(scheme='http')
        if not components.netloc:
            components = components._replace(netloc=self.page_url.netloc)

        if "cfile/tistory" in components.path:
            if "daumcdn" in components.netloc:
                components = components._replace(query='original')
            else:
                new_path = components.path.replace('/image/', '/original/')
                components = components._replace(path=new_path)

        return components


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s')

    u = 'https://jjoggomi.tistory.com/803'
    import urllib.request
    r = urllib.request.urlopen(u)
    extractor = Extractor(u, r, "")
