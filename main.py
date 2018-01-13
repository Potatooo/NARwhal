import http
import socket
import requests
from bs4 import BeautifulSoup
import threading
import time
import urllib3
from enum import Enum
from collections import defaultdict
import re
from dateutil.parser import parse
from bs4.element import NavigableString
import re

__author__ = 'Pawel'

REGEX = []

def MonthToInt(str):
    i = 1
    for x in "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec".split("|"):
        if x == str:
            return i
        i += 1
    i = 1
    for x in "January|February|March|April|May|June|July|August|September|October|November|December".split("|"):
        if x == str:
            return i
        i += 1
    return int(str)

class DateData:
    def __init__(self):
        self.day = None
        self.month = None
        self.year = None

class RegexFormat():
    DAYS = []
    DAYS.append("(1|2|3|4|5|6|7|8|9|10|11|12|13|14|15|16|17|18|19|20|21|22|23|24|25|26|27|28|29|30|31)")
    MONTHS = []
    MONTHS.append("(1|2|3|4|5|6|7|8|9|10|11|12)")
    MONTHS.append("(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)")
    MONTHS.append("(January|February|March|April|May|June|July|August|September|October|November|December)")
    YEARS = []
    YEARS.append("(\d{4})")
    SEPERATORS = []
    SEPERATORS.append(" ")
    SEPERATORS.append(".")
    SEPERATORS.append("-")
    SEPERATORS.append("\/")

    def __init__(self):
        self.reg = ""
        self._order = ["", "", ""]
        self._size = 0

    def day(self, index):
        self.reg += RegexFormat.DAYS[index]
        self._order[self._size] = "D"
        self._size += 1
        return self

    def month(self, index):
        self.reg += RegexFormat.MONTHS[index]
        self._order[self._size] = "M"
        self._size += 1
        return self

    def year(self, index):
        self.reg += RegexFormat.YEARS[index]
        self._order[self._size] = "Y"
        self._size += 1
        return self

    def seperator(self, str):
        if str == "/":
            str = "\/"
        self.reg += str
        return self

    def check(self, str):
        n = re.search(self.reg, str)
        if n is not None:
            data = n.groups(1)
            print(str)
            print(data)
            ret = DateData()
            for i in range(0, 3):
                if self._order[i] == 'D':
                    ret.day = int(n.groups(1)[i])
                if self._order[i] == 'M':
                    ret.month = MonthToInt(n.groups(1)[i])
                if self._order[i] == 'Y':
                    ret.year = int(n.groups(1)[i])
            print(ret.day,ret.month,ret.year)
            print()
            return ret
        return None

def CheckDate(str):
    for r in REGEX:
        n = r.check(str)

REGEX.append(RegexFormat().month(0).seperator("/").day(0).seperator("/").year(0))
REGEX.append(RegexFormat().month(1).seperator("/").year(0))
REGEX.append(RegexFormat().year(0).seperator("-").month(0).seperator("-").day(0))
REGEX.append(RegexFormat().day(0).seperator(". ").month(1).seperator(" ").year(0))
REGEX.append(RegexFormat().month(1).seperator(".").day(0).seperator(".").year(0))
REGEX.append(RegexFormat().month(1).seperator(" ").day(0).seperator(", ").year(0))
REGEX.append(RegexFormat().month(2).seperator(" ").day(0).seperator(", ").year(0))
REGEX.append(RegexFormat().day(0).seperator(" ").month(2).seperator(", ").year(0))
REGEX.append(RegexFormat().month(2).seperator(" ").day(0).seperator(" ").year(0))
REGEX.append(RegexFormat().day(0).seperator(" ").month(2).seperator(" ").year(0))
REGEX.append(RegexFormat().month(2).seperator(" ").year(0))

def parseStrDate(dateString):
    try:
        dateTimeObj = parse(dateString)
        return dateTimeObj
    except:
        return None

class StatusCode(Enum):
    UNKNOWN = 1
    GOOD = 2
    BAD = 3

class NARwhalData:
    def __init__(self):
        self.NAR_summary_url = ""
        self.NAR_title = ""
        self.NAR_subtitle = ""
        self.NAR_href = ""
        self.status = StatusCode.UNKNOWN
        self.response = -1;

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

        self._visitDatabases()

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

        print("Fetched links to subpages.")
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
        print("Fetched links to databases.")
        print("Elapsed Time: %s" % (time.time() - start))
        print("Count:", self.count)

    def _visitDatabases(self):
        start = time.time()

        countLock = threading.Lock()

        self.done = 0
        self.total = self.count
        def fetch_database(dbData):
            triesLeft = self.retryCount
            while(triesLeft > 0):
                try:
                    page = requests.get(dbData.NAR_href, timeout=self.singleRequestTimeout)
                    dbData.response = page.status_code
                    self.done += 1
                    print(self.done/self.total*100, "%", sep="")
                    if page.status_code >= 200 and page.status_code < 300:
                        dbData.status = StatusCode.GOOD
                    else:
                        dbData.status = StatusCode.BAD

                    soup_main = BeautifulSoup(page.text, 'html.parser')
                    text = [i for i in soup_main.recursiveChildGenerator() if type(i) == NavigableString]
                    for t in text:
                        if "last updated" in t:
                            CheckDate(t)
                            print(t,"|",dbData.NAR_href)
                    break
                except (ConnectionError, ConnectionResetError, urllib3.exceptions.ProtocolError, requests.exceptions.ConnectionError, requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout, requests.exceptions.ChunkedEncodingError, requests.exceptions.InvalidSchema, requests.exceptions.ChunkedEncodingError, socket.timeout, http.client.IncompleteRead, requests.exceptions.ContentDecodingError) as e:
                    pass
                except UnicodeEncodeError:
                    break #unable to read website
                triesLeft -= 1
                time.sleep(self.retrySleep)

        threads = [threading.Thread(target=fetch_database, args=(db,)) for db in self.data]
        [thread.start() for thread in threads]
        [thread.join() for thread in threads]

        print("Fetched databases information.")
        print("Elapsed Time: %s" % (time.time() - start))

        statusDict = defaultdict(int)
        for db in self.data:
            statusDict[db.status] += 1

        print("STATUS:")
        print("GOOD:   \t", statusDict[StatusCode.GOOD])
        print("BAD:    \t", statusDict[StatusCode.BAD])
        print("UNKNOWN:\t", statusDict[StatusCode.UNKNOWN])

def main():
    narv = NARwhal(retryCount=2, retrySleep=5, singleRequestTimeout=15, limit=-1)
main()


# kompatybilnosc 2.7warto za 5pkt

