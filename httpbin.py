import urllib.request
import logging


class Fetch:
    """wrapper for urllib.request with exceptions"""

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_4) \
                       AppleWebKit/601.5.17 (KHTML, like Gecko) Version/9.1 Safari/601.5.17'
    }
    errors = []

    def __init__(self, url):
        self.logger = logging.getLogger('Fetch')
        self.url = url
        self._info, self._body = self.urlopen()

    def __bool__(self):
        if self._info and self._body:
            return True
        return False

    def urlopen(self):
        try:
            req = urllib.request.Request(self.url, headers=self.headers)
            with urllib.request.urlopen(req) as req:
                body = req.read()
                info = req.info()
                self.logger.debug('returning request [HTTP status code: %s]', req.getcode())
            return info, body
        except Exception as err:
            err = "{} {}".format(self.url, err)
            print(err)
            self.errors.append(err)
            return None, None

    def body(self):
        return self._body

    def info(self):
        return self._info


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG,
                        format='%(name)s: %(message)s')
    test = Fetch("https://httpbin.org/get")
    logging.debug(test.info())
    logging.debug(test.body())
    logging.debug('errors: %s', Fetch.errors)
