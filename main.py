import http
from itertools import islice
import pprint
import socket
import requests
from bs4 import BeautifulSoup
import threading
import time
import urllib3
from enum import Enum
from collections import defaultdict
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
        self.category = ""
        self.subcategory = ""
        self.status = StatusCode.UNKNOWN
        self.response = -1

class NARwhalResults:
    def __init__(self, data):
        self._data = data

    def filterByCategory(self, categoryName):
        self._data[:] = [x for x in self._data if x.category==categoryName]

    def filterBySubcategory(self, subcategoryName):
        self._data[:] = [x for x in self._data if x.subcategoryName==subcategoryName]

    def count_statuses(self):
        result = {}
        for i in self._data:
            if i.category not in result:
                result[i.category] = {}
            if i.subcategory not in result[i.category]:
                result[i.category][i.subcategory] = {}
            if StatusCode.GOOD not in result[i.category][i.subcategory]:
                result[i.category][i.subcategory]["StatusCode.GOOD"]=0
            if StatusCode.BAD not in result[i.category][i.subcategory]:
                result[i.category][i.subcategory]["StatusCode.BAD"]=0
            if StatusCode.UNKNOWN not in result[i.category][i.subcategory]:
                result[i.category][i.subcategory]["StatusCode.UNKNOWN"]=0
            result[i.category][i.subcategory][i.status] += 1

        #for key_category in result:
        #    print("Category:" + key_category)
        #    for key_subcategory in result[key_category]:
        #        if key_subcategory != "":
        #            print("Subcategory:" + key_subcategory)
        #        for key_status in result[key_category][key_subcategory]:
        #            print(key_status, result[key_category][key_subcategory][key_status])
        pprint.pprint(result)
        return result


class NARwhal:
    DOMAIN_LINK = "http://www.oxfordjournals.org"
    SEARCH_ROOT_LINK = "http://www.oxfordjournals.org/nar/database/cap/"
    CATEGORY_PREFIX = "/nar/database/cat/"
    SUBCATEGORY_PREFIX = "/nar/database/subcat/"
    SUMMARY_PREFIX = "/nar/database/summary/"

    # NARwhal
    # retryCount=5
    # - maximum amount of tries a page should be visited after failed requests
    # retrySleep=5
    # - time between retries
    # singleRequestTimeout=60
    # - time after connection is if no response is received during that time
    # limit=-1
    # - maximum amount of databases to visit. -1 means no limit.
    # skip=0
    # - amount of links that should be skipped initially.
    # filename=""
    # - if not empty, will try to load data from the file instead of visiting links again
    def __init__(self, retryCount=5, retrySleep=5, singleRequestTimeout=60, limit=-1, skip=0, fileName=""):
        if fileName != "":
            self._load(fileName)
            return

        self.setting_retryCount = retryCount
        self.setting_retrySleep = retrySleep
        self.setting_singleRequestTimeout = singleRequestTimeout
        self.setting_limit = limit
        self._setting_skip = skip

        # set to check if a page has already been visited
        self._visited = set()
        # links to all NAR summaries
        self._summary_links = set()

        # number of summaries found, used to print out progress.
        self.count = 0

        self.data = []
        self._fetchSummaryLinks()
        self._visitSummaries()

        self._visitDatabases()

    # loads pregenerated data from a file instead of fetching results again
    def _load(self, fileName):
        self.data = []
        N = int(sum(1 for line in open(fileName))/9)
        with open(fileName, 'r') as f:

            for i in range(0, N):
                nextData = NARwhalData()
                (f.readline().strip())
                nextData.NAR_summary_url = (f.readline().strip())
                nextData.NAR_title = (f.readline().strip())
                nextData.NAR_subtitle = (f.readline().strip())
                nextData.NAR_href = (f.readline().strip())
                nextData.category = (f.readline().strip())
                nextData.subcategory = (f.readline().strip())
                nextData.status = (f.readline().strip())
                nextData.response = (f.readline().strip())
                self.data.append(nextData)

    # Checks set if URL has already been visited to prevent infinite looping.
    def _isVisited(self, url):
        return url in self._visited

    # Visits an URL and returns its contents.
    def _visitUrl(self, url):
        self._visited.add(url)
        page = requests.get(url)
        soup = BeautifulSoup(page.text.encode('utf-8').decode('ascii', 'ignore'), 'html.parser')
        return soup

    # Finds all summary links from NAR website and stores them.
    def _fetchSummaryLinks(self):
        start = time.time()

        soup_main = self._visitUrl(self.SEARCH_ROOT_LINK)
        for link in soup_main.find_all('a'):
            href = link.get('href')
            if(href.startswith(self.SUMMARY_PREFIX)):
                if self._setting_skip>0:
                    self._setting_skip -= 1
                    continue
                self._summary_links.add(self.DOMAIN_LINK + href)
                if(len(self._summary_links) >= self.setting_limit and self.setting_limit >= 0):
                    break

        print("Fetched links to subpages.")
        print("Time:", time.time() - start)

    # extracts data from a single summary on NAR website and fetches basic data from it
    def _extractData(self, url, pageText):
        nextData = NARwhalData()

        soup_main = BeautifulSoup(pageText, 'html.parser')

        element_title = soup_main.find('h1', {'class': 'summary'})

        element_paper = soup_main.find('div', {"id": "paper"})
        soup_bodytext = BeautifulSoup(str(element_paper), 'html.parser')
        elements_bodytext = soup_bodytext.find_all('div', {'class': 'bodytext'})[:2]

        soup_other_line = BeautifulSoup(str(elements_bodytext[1]), 'html.parser')
        other_link = soup_other_line.find('a').get('href')

        try:
            soup_category = BeautifulSoup(str(element_paper), 'html.parser').find('div', {'class': 'category'})
            soup_category2 = BeautifulSoup(str(soup_category), 'html.parser').find('a').getText()
            nextData.category = soup_category2
        except Exception as e:
            pass

        try:
            soup_subcategory = BeautifulSoup(str(element_paper), 'html.parser').find('div', {'class': 'subcategory'})
            soup_subcategory2 = BeautifulSoup(str(soup_subcategory), 'html.parser').find('a').getText()
            nextData.subcategory = soup_subcategory2
        except Exception as e:
            pass

        nextData.NAR_summary_url = url
        nextData.NAR_title = element_title.getText()
        nextData.NAR_subtitle = elements_bodytext[0].getText()[2:-2]
        nextData.NAR_href = other_link

        return nextData

    # visits all summaries that were found extracts data from them
    def _visitSummaries(self):
        start = time.time()

        self.count = 0
        countLock = threading.Lock()

        def fetch_summary(url):
            triesLeft = self.setting_retryCount
            while(triesLeft > 0):
                try:
                    page = requests.get(url, timeout=self.setting_singleRequestTimeout)
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
                time.sleep(self.setting_retrySleep)

        threads = [threading.Thread(target=fetch_summary, args=(url,)) for url in self._summary_links]
        [thread.start() for thread in threads]
        [thread.join() for thread in threads]


        for i in self.data:
            print(i.NAR_summary_url, i.NAR_title, i.NAR_subtitle, i.NAR_href)
        print("Fetched links to databases.")
        print("Elapsed Time: %s" % (time.time() - start))
        print("Count:", self.count)

    # visits all links to databases that were found on the NAR website
    def _visitDatabases(self):
        start = time.time()

        countLock = threading.Lock()

        self.done = 0
        self.total = self.count
        def fetch_database(dbData):
            triesLeft = self.setting_retryCount
            while(triesLeft > 0):
                try:
                    page = requests.get(dbData.NAR_href, timeout=self.setting_singleRequestTimeout)
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
                time.sleep(self.setting_retrySleep)

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

    # stores results in a text file
    def save(self):
        file = open('data.txt', 'w')
        for i in self.data:
            file.write("-----\n")
            file.write(i.NAR_summary_url)
            file.write("\n")
            file.write(i.NAR_title)
            file.write("\n")
            file.write(i.NAR_subtitle)
            file.write("\n")
            file.write(i.NAR_href)
            file.write("\n")
            file.write(i.category)
            file.write("\n")
            file.write(i.subcategory)
            file.write("\n")
            file.write(str(i.status))
            file.write("\n")
            file.write(str(i.response))
            file.write("\n")
        file.close()

    # creates a new object of results that can be filtered
    def results(self):
        return NARwhalResults(self.data)

    # shows all results in a primitive form
    def display(self):
        for i in self.data:
            print("NAR_summary_url", i.NAR_summary_url)
            print("NAR_title", i.NAR_title)
            print("NAR_subtitle", i.NAR_subtitle)
            print("NAR_href", i.NAR_href)
            print("category", i.category)
            print("subcategory", i.subcategory)
            print("status", i.status)
            print("response", i.response)

def main():
    narv = NARwhal(fileName="data.txt")
    narv.results().count_statuses()

    #narv = NARwhal(retryCount=2, retrySleep=5, singleRequestTimeout=15, limit=-1, skip=0, fileName="")
    #narv.save()

main()


# kompatybilnosc 2.7warto za 5pkt

