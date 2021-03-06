from enum import Enum
import http
import pprint
import socket
import requests
from bs4 import BeautifulSoup
import threading
import time
import urllib3
from collections import defaultdict
from dateutil.parser import parse
from bs4.element import NavigableString
import re
import datetime

__author__ = 'Pawel'

#constant holding date regexes
REGEX = []

#tries to "cast" a string into an integer from [1 to 12] representing months
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

#class that holds day,month,year.
class DateData:
    def __init__(self):
        self.day = None
        self.month = None
        self.year = None

#helper class to create date regexes
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
            ret = DateData()
            for i in range(0, 3):
                if self._order[i] == 'D':
                    ret.day = int(n.groups(1)[i])
                if self._order[i] == 'M':
                    ret.month = MonthToInt(n.groups(1)[i])
                if self._order[i] == 'Y':
                    ret.year = int(n.groups(1)[i])
            return ret
        return None

def CheckDate(str):
    for r in REGEX:
        n = r.check(str)
        if n is not None:
            return n

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

# NARwhalData
# contains information for a single database
#
# NAR_summary_url
# - link to url on NAR website
# - Default: "" (empty string)
# NAR_title
# - database title on NAR website
# - Default: "" (empty string)
# NAR_subtitle
# - database subtitle on NAR website
# - Default: "" (empty string)
# NAR_href
# - actual link to database found on NAR website
# - Default: "" (empty string)
# category
# - category found on NAR website
# - Default: "" (empty string)
# subcategory
# - subcategory found on NAR website
# - Default: "" (empty string)
# status
# - GOOD, BAD or UNKNOWN
# - GOOD if response was between [200,300)
# - BAD if response was anything else
# - UNKNOWN is there was no response at all (e.g. timeout)
# - Default: "UNKNOWN" (string)
# response
# - HTTP response from database website
# - Default: -1
# update_day
# - estimated last updated day
# - Default: -1
# update_month
# - estimated last updated month
# - Default: -1
# update_year
# - estimated last updated year
# - Default: -1
# firstYear
# - estimated year of first article
# - Default: -1
# lastYear
# - estimated year of last article
# - Default: -1
class NARwhalData:
    def __init__(self):
        self.NAR_summary_url = ""
        self.NAR_title = ""
        self.NAR_subtitle = ""
        self.NAR_href = ""
        self.category = ""
        self.subcategory = ""
        self.status = "UNKNOWN"
        self.response = -1
        self.update_day = -1
        self.update_month = -1
        self.update_year = -1
        self.firstYear = -1
        self.lastYear = -1

    #displays object fields in a simple way
    def display(self):
        print("NAR_summary_url", self.NAR_summary_url)
        print("NAR_title", self.NAR_title)
        print("NAR_subtitle", self.NAR_subtitle)
        print("NAR_href", self.NAR_href)
        print("category", self.category)
        print("subcategory", self.subcategory)
        print("status", self.status)
        print("response", self.response)
        print("updated D/M/Y: ", end="")
        if self.update_day != -1:
            print(self.update_day, ".", end="", sep="")
        else:
            print("??.", end="")
        if self.update_month != -1:
            print(self.update_month, ".", end="", sep="")
        else:
            print("??.", end="")
        if self.update_year != -1:
            print(self.update_year)
        else:
            print("????")
        if self.firstYear != -1:
            print("first article year:", self.firstYear)
        if self.lastYear != -1:
            print("last article year:", self.lastYear)

#used for filtering results
class RemoveCondition(Enum):
    NO_CATEGORY = 0
    NO_SUBCATEGORY = 1
    NO_TITLE = 2
    NO_SUBTITLE = 3
    BAD_STATUS = 4
    UNKNOWN_STATUS = 5
    BAD_OR_UNKNOWN_STATUS = 6
    RESPONSE_NOT_SUCCESS = 7
    NO_UPDATE_DAY = 8
    NO_UPDATE_MONTH = 9
    NO_UPDATE_YEAR = 10
    NO_ARTICLE_YEAR = 11
    NO_UPDATE_DAY_AND_NO_MONTH_AND_NO_YEAR = 12
    NO_UPDATE_DATA_AT_ALL = 13

class NARwhalResults:
    def __init__(self, data):
        self._data = data

    #filters data results by category name. Keeps categories with provided name
    def filterByCategory(self, categoryName):
        self._data[:] = [x for x in self._data if x.category==categoryName]
        return self

    #filters data results by subcategory name. Keeps subcategories with provided name
    def filterBySubcategory(self, subcategoryName):
        self._data[:] = [x for x in self._data if x.subcategoryName==subcategoryName]
        return self

    #displays all NARwhalData in this object
    def display(self):
        for i in self._data:
            i.display()

    #returns a copy of NARwhalData objects in this object
    def getData(self):
        return list(self._data)

    #orders by first article, ascending
    def orderByFirstArticleASC(self):
        self._data[:] = sorted(self._data, key=lambda data: data.firstYear)
        return self

    #orders by first article, descending
    def orderByFirstArticleDESC(self):
        self._data[:] = sorted(self._data, key=lambda data: data.firstYear, reverse=True)
        return self

    #orders by last article, ascending
    def orderByLastArticleASC(self):
        self._data[:] = sorted(self._data, key=lambda data: data.lastYear)
        return self

    #orders by last article, descending
    def orderByLastArticleDESC(self):
        self._data[:] = sorted(self._data, key=lambda data: data.lastYear, reverse=True)
        return self

    #removes data from this object by given condition
    #filter
    # - RemoveCondition enum
    def removeIf(self, filter):
        if filter == RemoveCondition.NO_CATEGORY:
            self._data[:] = [x for x in self._data if x.category!='']
        if filter == RemoveCondition.NO_SUBCATEGORY:
            self._data[:] = [x for x in self._data if x.subcategory!='']
        if filter == RemoveCondition.NO_TITLE:
            self._data[:] = [x for x in self._data if x.NAR_title!='']
        if filter == RemoveCondition.NO_SUBTITLE:
            self._data[:] = [x for x in self._data if x.NAR_subtitle!='']
        if filter == RemoveCondition.BAD_STATUS:
            self._data[:] = [x for x in self._data if x.status!="BAD"]
        if filter == RemoveCondition.UNKNOWN_STATUS:
            self._data[:] = [x for x in self._data if x.status!="UNKNOWN"]
        if filter == RemoveCondition.BAD_OR_UNKNOWN_STATUS:
            self._data[:] = [x for x in self._data if x.status!="BAD"]
            self._data[:] = [x for x in self._data if x.status!="UNKNOWN"]
        if filter == RemoveCondition.RESPONSE_NOT_SUCCESS:
            self._data[:] = [x for x in self._data if x.response>=200]
            self._data[:] = [x for x in self._data if x.response<300]
        if filter == RemoveCondition.NO_UPDATE_DAY:
            self._data[:] = [x for x in self._data if x.update_day!=-1]
        if filter == RemoveCondition.NO_UPDATE_MONTH:
            self._data[:] = [x for x in self._data if x.update_month!=-1]
        if filter == RemoveCondition.NO_UPDATE_YEAR:
            self._data[:] = [x for x in self._data if x.update_year!=-1]
        if filter == RemoveCondition.NO_ARTICLE_YEAR:
            self._data[:] = [x for x in self._data if x.firstYear!=-1]
            self._data[:] = [x for x in self._data if x.lastYear!=-1]
        if filter == RemoveCondition.NO_UPDATE_DAY_AND_NO_MONTH_AND_NO_YEAR:
            self._data[:] = [x for x in self._data if x.update_day!=-1]
            self._data[:] = [x for x in self._data if x.update_month!=-1]
            self._data[:] = [x for x in self._data if x.update_year!=-1]
        if filter == RemoveCondition.NO_UPDATE_DATA_AT_ALL:
            self._data[:] = [x for x in self._data if x.update_day!=-1 and x.update_month!=-1 and x.update_year!=-1]
        return self

    #counts statuses, prints them and returns a dictonary
    def count_status(self):
        result = {"GOOD":0, "BAD":0, "UNKNOWN":0}
        for i in self._data:
            result[i.status] += 1
        return result

    #counts statuses, prints them and returns a dictonary grouped by categories and subcategories
    def count_statusSummary(self):
        result = {}
        for i in self._data:
            if i.category not in result:
                result[i.category] = {}
            if i.subcategory not in result[i.category]:
                result[i.category][i.subcategory] = {}
            if "GOOD" not in result[i.category][i.subcategory]:
                result[i.category][i.subcategory]["GOOD"]=0
            if "BAD" not in result[i.category][i.subcategory]:
                result[i.category][i.subcategory]["BAD"]=0
            if "UNKNOWN" not in result[i.category][i.subcategory]:
                result[i.category][i.subcategory]["UNKNOWN"]=0
            result[i.category][i.subcategory][i.status] += 1
        return result


class NARwhal:
    DOMAIN_LINK = "http://www.oxfordjournals.org"
    SEARCH_ROOT_LINK = "http://www.oxfordjournals.org/nar/database/cap/"
    CATEGORY_PREFIX = "/nar/database/cat/"
    SUBCATEGORY_PREFIX = "/nar/database/subcat/"
    SUMMARY_PREFIX = "/nar/database/summary/"

    # NARwhal
    # loadFromNARwebsite or load
    # must be called directly after creating this object
    def __init__(self):
        pass

    # Loads data from NAR website
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
    def loadFromNARwebsite(self, retryCount=5, retrySleep=5, singleRequestTimeout=60, limit=-1, skip=0):
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


    # Loads pregenerated data from a file instead of fetching results again
    # filename
    # - will try to load data from the file instead of visiting links again
    # - assumes file format is correct
    def load(self, fileName):
        self.data = []
        N = int(sum(1 for line in open(fileName))/14)
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
                nextData.update_day = int((f.readline().strip()))
                nextData.update_month = int((f.readline().strip()))
                nextData.update_year = int((f.readline().strip()))
                nextData.firstYear = int((f.readline().strip()))
                nextData.lastYear = int((f.readline().strip()))
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
                        dbData.status = "GOOD"
                    else:
                        dbData.status = "BAD"

                    soup_main = BeautifulSoup(page.text, 'html.parser')
                    text = [i for i in soup_main.recursiveChildGenerator() if type(i) == NavigableString]
                    currentYear = datetime.datetime.now().year
                    yearRange = range(1900, currentYear+1)
                    for t in text:
                        for y in yearRange:
                            if str(y) in t:
                                if dbData.lastYear==-1 or dbData.lastYear<y:
                                    dbData.lastYear=y
                                if dbData.firstYear==-1 or dbData.firstYear>y:
                                    dbData.firstYear=y
                        if "last updated" in t:
                            result = CheckDate(t)
                            if result is not None:
                                if result.day is not None:
                                    dbData.update_day = result.day
                                if result.month is not None:
                                    dbData.update_month = result.month
                                if result.year is not None:
                                    dbData.update_year = result.year
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
        print("GOOD:   \t", statusDict["GOOD"])
        print("BAD:    \t", statusDict["BAD"])
        print("UNKNOWN:\t", statusDict["UNKNOWN"])

    # stores results in a text file
    # fileName
    # - name of file to save the data
    def save(self, fileName):
        file = open(fileName, 'w')
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
            file.write(str(i.update_day))
            file.write("\n")
            file.write(str(i.update_month))
            file.write("\n")
            file.write(str(i.update_year))
            file.write("\n")
            file.write(str(i.firstYear))
            file.write("\n")
            file.write(str(i.lastYear))
            file.write("\n")
        file.close()

    # creates a new object of results that can be filtered
    def results(self):
        return NARwhalResults(self.data)

    # shows all results in a primitive form
    def display(self):
        for i in self.data:
            i.display()

def main():
    #Fetches data from NAR website and database websites and stores results in a file
    #Following 3 lines can be commented out after fetching data, loading data from file is a lot faster
    #It can take about 5-10 minutes to fetch results from NAR website.
    #narv = NARwhal()
    #narv.loadFromNARwebsite(retryCount=2, retrySleep=5, singleRequestTimeout=15, limit=-1, skip=0,)
    #narv.save("data.txt")

    #Loads data from a file.
    narv = NARwhal()
    narv.load("data.txt")

    #returns a copy of results, leaving data in narv unchanged
    r = narv.results()
    #returns the number of GOOD, BAD and UNKNOWN databases.
    pprint.pprint(r.count_status())

    #optional data filtering, changes the original array
    r.removeIf(RemoveCondition.BAD_OR_UNKNOWN_STATUS)
    #this can be chained
    r.removeIf(RemoveCondition.NO_UPDATE_DATA_AT_ALL).removeIf(RemoveCondition.NO_ARTICLE_YEAR)

    #optional sorting
    r.orderByFirstArticleASC()
    #sorting again will overwrite any previous sorting
    r.orderByFirstArticleDESC()
    r.orderByLastArticleDESC()
    r.orderByLastArticleASC()

    #displays results in a simple way
    r.display()

    #returns a copy of an array containing NARwhalData objects.
    r.getData()

    #returns the number of GOOD, BAD and UNKNOWN databases after filtering
    pprint.pprint(r.count_status())

    #summary of statuses, in a dict object. Also provides information about categories and subcategories.
    pprint.pprint(r.count_statusSummary())

main()