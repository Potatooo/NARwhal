# NARwhal
Python library to inefficiently check status of NAR websites!

Example usage:
```
    #Fetches data from NAR website and database websites and stores results in a file
    #Following 3 lines can be commented out after fetching data, loading data from file is a lot faster
    #It can take about 5-10 minutes to fetch results from NAR website.
    narv = NARwhal()
    narv.loadFromNARwebsite(retryCount=2, retrySleep=5, singleRequestTimeout=15, limit=-1, skip=0,)
    narv.save("data.txt")

    #Loads data from a file.
    narv = NARwhal()
    narv.load("data.txt")

    #returns a copy of results, leaving data in narv unchanged
    r = narv.results()
    #returns the number of GOOD, BAD and UNKNOWN databases.
    r.count_status()

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
    r.count_status()

    #summary of statuses, in a dict object. Also provides information about categories and subcategories.
    r.count_statusSummary()
```
