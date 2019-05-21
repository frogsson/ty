#!/usr/bin/env python

import logging
import argparse
import sys
import os

DIRNAME = os.path.dirname(__file__)
CONFIG_USER = os.path.join(DIRNAME, "config.py")
if os.path.exists(CONFIG_USER):
    import config as conf
else:
    import config_def as conf


class ArgSettings:
    """arg vals"""
    def __init__(self):
        self.logger = logging.getLogger('ArgSettings')
        self.url = ''
        self.threads = conf.threads
        self.organize = conf.organize
        self.pages = []
        self.title_filter = []
        self.debug = False

    def set_url(self, url):
        """sets url"""
        self.logger.debug('set_url()')
        self.url = url

    def get_url(self):
        """returns url"""
        return self.url

    def organize_true(self):
        """sets organize to true"""
        self.logger.debug('organize_true()')
        self.organize = True

    def organize_status(self):
        """returns organize bool"""
        self.logger.debug('organize_status()')
        return self.organize

    def gather_pages(self, nums):
        """gathers pages between numbers given"""
        self.logger.debug('gather_pages()')
        if nums[0] < nums[1]:
            fnum, snum = nums[0], nums[1]
        else:
            snum, fnum = nums[0], nums[1]

        for num in range(fnum, snum + 1):
            self.pages.append(num)

    def page_status(self):
        """return true if it there's multiple pages"""
        if self.pages:
            return True
        return False

    def get_pages(self):
        """returns list of pages"""
        self.logger.debug('get_pages()')
        return self.pages

    def set_threads(self, num):
        """sets number of threads"""
        self.logger.debug('set_threads()')
        self.threads = num

    def get_threads(self):
        """returns setting for number of threads"""
        self.logger.debug('get_threads()')
        return self.threads

    def set_filter(self, filter_words):
        """sets filter"""
        self.logger.debug('set_filter()')
        for word in filter_words.split("/"):
            self.title_filter.append(word)

    def get_title_filter(self):
        """returns list of words to include"""
        self.logger.debug('get_title_filter()')
        return self.title_filter

    def debug_true(self):
        """sets debug to true"""
        self.logger.debug('set_debug()')
        self.debug = True

    def debug_status(self):
        """returns debug status"""
        self.logger.debug('debug_status()')
        return self.debug


def create_parse_arguments():
    """adds arguments for parser"""
    pars = argparse.ArgumentParser(prog='ty')
    pars.add_argument('url',
                      help='takes an url')
    pars.add_argument('-o', '--organize',
                      action='store_true',
                      help='organize images in folders by date')
    pars.add_argument('-p', '--page',
                      metavar='n',
                      nargs=2,
                      type=int,
                      help='download page n to n')
    pars.add_argument('-t', '--threads',
                      metavar='n',
                      type=int,
                      help='number of simultaneous downloads (32 max)')
    pars.add_argument('-f', '--filter',
                      metavar='word',
                      type=str,
                      help='download [-p/--pages] containing word specified in filter (used with [-p/--page])')
    pars.add_argument('--debug',
                      action='store_true',
                      help='runs program in debug mode')

    return pars


def parse(argv):
    """parses arguments and returns class with values"""
    logger = logging.getLogger('parser')
    logger.debug('parsing %s', argv)

    opt = ArgSettings()

    parser = create_parse_arguments()
    args = parser.parse_args(argv)

    opt.set_url(args.url)

    if args.organize:
        logger.debug('found [-o/--organize]')
        opt.organize_true()

    if args.threads:
        logger.debug('found [-t/--threads] args: %s', args.threads)
        opt.set_threads(args.threads)

    if args.page:
        logger.debug('found [-p/--parse] args: %s', args.page)
        opt.gather_pages(args.page)

    if args.filter:
        logger.debug('found [-f/--filter] args: %s', args.filter)
        opt.set_filter(args.filter)

    if args.debug:
        logger.debug('found [--debug]')
        opt.debug_true()

    return opt


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG,
                        format='%(name)s: %(message)s')

    if len(sys.argv) > 1:
        logging.debug('args: %s', sys.argv)
        SETTINGS = parse(sys.argv[1:])
    else:
        logging.debug('args: %s', sys.argv)
        SETTINGS = parse('https://sparkles805.tistory.com/228 -o -p 1 5 -t 12 -f hello/world'.split())

    logging.debug("organize: %s", SETTINGS.organize_status())
    logging.debug("url: %s", SETTINGS.get_url())
    logging.debug("page: %s", SETTINGS.get_pages())
    logging.debug("threads: %s", SETTINGS.get_threads())
    logging.debug("filter: %s - status: %r",
                  SETTINGS.get_title_filter(),
                  SETTINGS.title_filter_status())
