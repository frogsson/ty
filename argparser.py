#!/usr/bin/env python

import logging
import argparse
import sys
import os
import os.path

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
        self.directory = conf.directory
        self.threads = conf.threads
        self.organize = conf.organize
        self.pages = conf.pages
        self.title_filter = conf.title_filter
        self.debug = False

    def set_url(self, url):
        """sets url"""
        self.url = url

    def get_url(self):
        """returns url"""
        return self.url

    def organize_true(self):
        """sets organize to true"""
        self.logger.debug('organize set to true')
        self.organize = True

    def organize_status(self):
        """returns organize bool"""
        return self.organize

    def gather_pages(self, nums):
        """gathers pages between numbers given"""
        if not self.url.endswith("/"):
            self.url = self.url + "/"

        if nums[0] < nums[1]:
            fnum, snum = nums[0], nums[1]
        else:
            snum, fnum = nums[0], nums[1]

        for num in range(fnum, snum + 1):
            self.pages.append(num)
        self.logger.debug('pages: %s', self.pages)

    def multiplepages(self):
        """return true if it there's multiple pages"""
        if self.pages:
            return True
        return False

    def get_pages(self):
        """returns list of pages"""
        return self.pages

    def set_threads(self, num):
        """sets number of threads"""
        self.threads = num
        self.logger.debug('threads set to: %s', self.threads)

    def get_threads(self):
        """returns setting for number of threads"""
        return self.threads

    def set_filter(self, filter_words):
        """sets filter"""
        for word in filter_words.split("/"):
            self.title_filter.append(word)

    def get_title_filter(self):
        """returns list of words to include"""
        return self.title_filter

    def debug_true(self):
        """sets debug to true"""
        self.logger.debug('DEBUG MODE ON')
        self.debug = True

    def debug_status(self):
        """returns debug status"""
        return self.debug

    def set_dir(self, directory):
        """sets directory"""
        err = ''
        if not os.path.exists(directory):
            err = 'Error: could not find directory: `%s`' % directory
        elif not os.path.isdir(directory):
            err = 'Error: `%s` is not a directory' % directory

        if err:
            print(err)
            sys.exit()

        self.directory = directory

    def get_dir(self):
        """"returns directory"""
        return self.directory


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
                      help='download [-p/--pages] containing word specified in filter (used with [-o/--organize])')
    pars.add_argument('--debug',
                      action='store_true',
                      help='runs program in debug mode')
    pars.add_argument('dir',
                      nargs='?',
                      help='set target folder')

    return pars


def parse(argv):
    """parses arguments and returns class with values"""
    logger = logging.getLogger('parser')
    logger.debug('parsing %s', argv)

    settings = ArgSettings()

    parser = create_parse_arguments()
    args = parser.parse_args(argv)

    settings.set_url(args.url)

    if args.debug:
        logger.debug('found [--debug]')
        settings.debug_true()

    if args.organize:
        logger.debug('found [-o/--organize]')
        settings.organize_true()

    if args.threads:
        logger.debug('found [-t/--threads] args: %s', args.threads)
        settings.set_threads(args.threads)

    if args.page:
        logger.debug('found [-p/--parse] args: %s', args.page)
        settings.gather_pages(args.page)

    if args.filter:
        logger.debug('found [-f/--filter] args: %s', args.filter)
        settings.set_filter(args.filter)

    if args.dir:
        logger.debug('found [dir] args: %s', args.dir)
        settings.set_dir(args.dir)

    return settings


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG,
                        format='%(name)s: %(message)s')

    if len(sys.argv) > 1:
        logging.debug('args: %s', sys.argv)
        SETTINGS = parse(sys.argv[1:])
    else:
        logging.debug('args: %s', sys.argv)
        SETTINGS = parse('https://sparkles805.tistory.com/228 -o -p 1 5 -t 12 --debug -f hello/world'.split())

    logging.debug("organize: %s", SETTINGS.organize_status())
    logging.debug("url: %s", SETTINGS.get_url())
    logging.debug("page: %s", SETTINGS.get_pages())
    logging.debug("threads: %s", SETTINGS.get_threads())
    logging.debug("filter: %s", SETTINGS.get_title_filter())
    logging.debug("dir: %s", SETTINGS.directory)
