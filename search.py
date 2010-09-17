#!/usr/bin/python
import time
import datetime
import psycopg2
import psycopg2.extras
import os
from indextank_client import ApiClient

api = ApiClient('http://:rXVEdV8N2clyZ4@8hdj3.api.indextank.com')
index = api.get_index('Pages')
index.add_function(0, "0 + 1")
sresults = index.search("Apple", scoring_function=0)
for result in sresults['results']:
    print "http://lonava.com/stories/" + result['docid']
