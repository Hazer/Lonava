#!/usr/bin/env python
import feedparser
from BeautifulSoup import BeautifulSoup
import psycopg2
import psycopg2.extras
import urlnorm
import random
import time
import datetime
from indextank_client import ApiClient
import socket

class LonFeed(object):
    """
    LonStories are the object for posts.
    """
    def __init__(self):
        self.freq = -1;
        self.feedid = 0;
        self.lasttime = 0;
        self.url = "";
        self.feedclass = 0;
        self.usr = 0;
        self.channel = 0;
        self.feedname = " ";    
    def FromFeedID(self,feedid):
        db = psycopg2.connect("dbname='lonava' user='YOURUSER' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute ("select * from feeds where feedid = %s;",[feedid])
        row = cur.fetchone()
        self.FromDBRow(row)
        db.close()

    def FromDBRow(self,row):
        self.freq = row['freq']
        self.url = urlnorm.normalize(str(row['url']))
        self.feedid = row['feedid']
        self.lasttime = row['lasttime']
        self.feedclass = row['feedclass']
        self.channel = row['channel']
        if row['feedname'] is None:
            if self.feedclass == 1: #Reddit
                tempname = row['url']
                tempname = tempname[tempname.find('eddit.com') -1:tempname.find('.rss')]
                tempname = tempname[0:35]   
                self.feedname = tempname
            else:
                self.feedname = feedparser.parse('http://reddit.com/.rss').title[:20]
            cur.execute("update feeds set feedname = %s where feedid = %s",[self.feedname,self.feedid])
        else:
            self.feedname = row['feedname']
        if row['usr'] is None:
            cur.execute("insert into usrs (name,password,email) values (%s,%s,%s) returning usrid;",[self.feedname,random.getrandbits(10),'support@lonava.com'])
            self.usr = cur.fetchone()['usrid']
            cur.execute("update feeds set usr = %s where feedid = %s",[self.usr,self.feedid])
            db.commit()
        else:
            self.usr = row['usr']
            if row['channel'] is None:
                    cur.execute("insert into channels (name,postable) values (%s,%s) returning chanid",[self.feedname,False])
                    self.channel = cur.fetchone()['chanid']
                    cur.execute("update feeds set channel = %s where feedid = %s",[self.channel,self.feedid])
                    db.commit()
            else:
                    self.channel = row['channel']       
        
    
def extractExtLinks(html):
    soup = BeautifulSoup(html)
    anchors = soup.findAll('a')
    links = []
    for a in anchors:
        if str(a).find('reddit') < 1:
                links.append(a['href'])
    return links

# timeout in seconds
timeout = 10
socket.setdefaulttimeout(timeout)
if 1==1:
    feedparser.USER_AGENT = "LonBot-Reddit/1.0 +http://Lonava.com/"
    db = psycopg2.connect("dbname='lonava' user='YOURUSER' host='localhost' password='YOURPASS'")
    cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("select * from feeds where feedclass = 1") # Reddit Feed
    feedlist = cur.fetchall()

    init = datetime.datetime.now()
    waituntil = datetime.datetime.now()

    for row in feedlist:
        feed =  LonFeed()
        feed.FromDBRow(row)
        while datetime.datetime.now() <  waituntil:
                print "Sleeping to be polite.." + str(datetime.datetime.now())
                time.sleep(.5)
        waituntil = datetime.datetime.now() + datetime.timedelta(0,4)   
        print feed.feedname.encode('ascii','ignore')

        allentries = feedparser.parse(feed.url)
        for entry in allentries.entries:
            print entry.title.encode('ascii','ignore')
            title = entry.title
            outwardlinks = extractExtLinks(entry.summary)
            if len(outwardlinks) > 0:
                # no (self) links, please
                print str(outwardlinks[0])
                link = urlnorm.normalize(str(outwardlinks[0]))  # There should only be one. If there is more, take the first.
                cur.execute("select count(*) as count from stories where url = %s and location = %s",[link,feed.channel])
                count = cur.fetchone()['count']
                if count < 1: 
                    #New Story, for this chan.
                    #But is it new for all of Lonava?
                    cur.execute("select commentgroup from stories where url = %s",[link])
                    existing = cur.fetchall();
                    if len(existing) > 0:
                        commentgroupid = existing[0]['commentgroup']
                    else:
                        commentgroupid = 0;
                        
                    cur.execute("insert into stories (usr,title,url,text,name,location,channame) values (%s,%s,%s,%s,%s,%s,(select name from channels where chanid = %s )) returning storyid;",[feed.usr,entry.title,link,'Via: ' + entry.link, feed.feedname, feed.channel,feed.channel])
                    storyid = cur.fetchone()['storyid']
                    if commentgroupid == 0:
                        cur.execute("insert into commentgroups(url) values (%s) returning commentgroupid;",[link]);
                        commentgroupid = cur.fetchone()['commentgroupid']

                    #now, commentgroupid is set, either way. 
                    cur.execute("update stories set commentgroup = %s where storyid = %s;",[commentgroupid,storyid]);

                    #EVERYONE posts into ALL-STORIES. EVERYTHING goes there! ;)
                    cur.execute("insert into stories (usr,title,url,text,name,location,commentgroup,channame) values (%s,%s,%s,%s,%s,0,%s,(select name from channels where chanid = 0 )) returning storyid;",[feed.usr,entry.title,link,'Via: ' + entry.link, feed.feedname, commentgroupid])
                    api = ApiClient('http://:rXVEdV8N2clyZ4@8hdj3.api.indextank.com')
                    index = api.get_index('Pages')
                    index.add_document(storyid, { 'text': title , 'link': link})


            db.commit()
