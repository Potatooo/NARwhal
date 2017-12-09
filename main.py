import http
import socket
import requests
from bs4 import BeautifulSoup
import threading
import time
import urllib3

__author__ = 'Pawel'

class NARwhalData:
    def __init__(self):
        self.NAR_summary_url = ""
        self.NAR_title = ""
        self.NAR_subtitle = ""
        self.NAR_href = ""

class NARwhal:
    DOMAIN_LINK = "http://www.oxfordjournals.org"
    SEARCH_ROOT_LINK = "http://www.oxfordjournals.org/nar/database/cap/"
    CATEGORY_PREFIX = "/nar/database/cat/"
    SUBCATEGORY_PREFIX = "/nar/database/subcat/"
    SUMMARY_PREFIX = "/nar/database/summary/"

    def __init__(self, retryCount=5, retrySleep=5, singleRequestTimeout=60, limit=-1):
        self.retryCount = retryCount
        self.retrySleep = retrySleep
        self.singleRequestTimeout = singleRequestTimeout
        self.limit = limit

        self.visited = set()
        self.cat_subcat_links = set()
        self.summary_links = set()

        self.count = 0

        self.data = []
        self._populate()
        self._visitSummaries()

    def _isVisited(self, url):
        return url in self.visited

    def _visitUrl(self, url):
        self.visited.add(url)
        page = requests.get(url)
        soup = BeautifulSoup(page.text.encode('utf-8').decode('ascii', 'ignore'), 'html.parser')
        return soup

    def _populate(self):
        start = time.time()

        soup_main = self._visitUrl(self.SEARCH_ROOT_LINK)
        for link in soup_main.find_all('a'):
            href = link.get('href')
            if(href.startswith(self.SUMMARY_PREFIX)):
                self.summary_links.add(self.DOMAIN_LINK + href)
                if(len(self.summary_links) >= self.limit and self.limit >= 0):
                    break

        print("Time:", time.time() - start)

    def _extractData(self, url, pageText):
        nextData = NARwhalData()

        soup_main = BeautifulSoup(pageText, 'html.parser')

        element_title = soup_main.find('h1', {'class': 'summary'})

        element_paper = soup_main.find('div', {"id": "paper"})
        soup_bodytext = BeautifulSoup(str(element_paper), 'html.parser')
        elements_bodytext = soup_bodytext.find_all('div', {'class': 'bodytext'})[:2]

        soup_other_line = BeautifulSoup(str(elements_bodytext[1]), 'html.parser')
        other_link = soup_other_line.find('a').get('href')

        nextData.NAR_summary_url = url
        nextData.NAR_title = element_title.getText()
        nextData.NAR_subtitle = elements_bodytext[0].getText()[2:-2]
        nextData.NAR_href = other_link

        return nextData

    def _visitSummaries(self):
        start = time.time()

        self.count = 0
        countLock = threading.Lock()

        def fetch_summary(url):
            triesLeft = self.retryCount
            while(triesLeft > 0):
                try:
                    page = requests.get(url, timeout=self.singleRequestTimeout)
                    nextData = self._extractData(url, page.text.encode('utf-8').decode('ascii', 'ignore'))
                    try:
                        countLock.acquire()
                        self.data.append(nextData)
                    finally:
                        countLock.release()
                except (ConnectionError, ConnectionResetError, urllib3.exceptions.ProtocolError, requests.exceptions.ConnectionError, requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout, requests.exceptions.ChunkedEncodingError, requests.exceptions.ChunkedEncodingError, socket.timeout, http.client.IncompleteRead) as e:
                    pass
                except (TypeError, AttributeError) as e:
                    # 419, 1323
                    pass
                else:
                    try:
                        countLock.acquire()
                        self.count += 1
                    finally:
                        countLock.release()
                    break
                triesLeft -= 1
                time.sleep(self.retrySleep)

        threads = [threading.Thread(target=fetch_summary, args=(url,)) for url in self.summary_links]
        [thread.start() for thread in threads]
        [thread.join() for thread in threads]


        for i in self.data:
            print(i.NAR_summary_url, i.NAR_title, i.NAR_subtitle, i.NAR_href)
        print("Elapsed Time: %s" % (time.time() - start))
        print("Count:", self.count)


def main():
    narv = NARwhal(retryCount=5, retrySleep=5, singleRequestTimeout=60, limit=21)

main()

