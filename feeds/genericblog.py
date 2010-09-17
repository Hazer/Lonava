#!/usr/bin/env python
import feedparser
from BeautifulSoup import BeautifulSoup
import psycopg2
import psycopg2.extras
import urlnorm
import random
import time
import datetime
from time import mktime
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
        self.lastupdated = datetime.datetime.now()

    def FromFeedID(self,feedid):
        db = psycopg2.connect("dbname='lonava' user='YOURUSER' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute ("select * from feeds where feedid = %s;",[feedid])
        row = cur.fetchone()
        self.FromDBRow(row)
        db.close()

    def FromDBRow(self,row):
        db = psycopg2.connect("dbname='lonava' user='YOURUSER' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)

        self.freq = row['freq']
        self.url = urlnorm.normalize(str(row['url']))
        self.feedid = row['feedid']
        self.lasttime = row['lasttime']
        self.feedclass = row['feedclass']
        self.channel = row['channel']
        if row['feedname'] is None:
            if self.feedclass == 1:
                tempname = row['url']
                tempname = tempname[tempname.find('eddit.com') -1:tempname.find('.rss')]
                tempname = tempname[0:35]   
                self.feedname = tempname
            else:
                try:
                    self.feedname = feedparser.parse(self.url).feed.title[:35]
                except:
                    self.feedname = self.url
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
        if row['lastupdated'] is None:
            fe = feedparser.parse(self.url)
            if hasattr(fe, 'updated'):
                upd = datetime.datetime.fromtimestamp(mktime(fe.updated))
                print "Fixed time"
            else: 
                upd = datetime.datetime.now() - datetime.timedelta(days=365)
            if upd is not None:
                updated = upd
                cur.execute("update feeds set lastupdated = %s where feedid = %s",[updated,self.feedid])
                self.lastupdated = updated
                print "using parsed value"
            else:
                self.lastupdated = datetime.datetime.now() - datetime.timedelta(days=365)
        else:
            lastupdated = row['lastupdated']
            self.lastupdated = lastupdated 
            print "Using DB value"

        db.commit()

def extractExtLinks(html,omit):
    soup = BeautifulSoup(html)
    anchors = soup.findAll('a')
    links = []
    for a in anchors:
        if str(a).find(omit) < 1:
            links.append(a['href'])
            return links



# timeout in seconds
timeout = 10
socket.setdefaulttimeout(timeout)
if 1==1:
    feedparser.USER_AGENT = "LonBot/1.0 +http://Lonava.com/"
    db = psycopg2.connect("dbname='lonava' user='YOURUSER' host='localhost' password='YOURPASS'")
    cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("select * from feeds where feedclass = 3") # 'regular' feed
    feedlist = cur.fetchall()
    init = datetime.datetime.now()
    waituntil = datetime.datetime.now()


    for row in feedlist:
        print "------"

        feed =  LonFeed()
        feed.FromDBRow(row)
        print("Loaded.")
        lastrun = feed.lasttime
        nextrun = lastrun + datetime.timedelta(0,feed.freq)
        print("Lastrun" + str(lastrun))
        print("Nextrun" + str(nextrun))
        print("Now is " + str( datetime.datetime.now()))
        if datetime.datetime.now() >= nextrun:

            print(feed.feedname.encode('ascii','ignore'))
            allentries = feedparser.parse(feed.url)
            #Get the Last Updated time from feed.
            if hasattr(allentries, 'updated'):
                upd = datetime.datetime.fromtimestamp(mktime(allentries.updated)) 
            else:
                upd = datetime.datetime.now()
                print "Malformed Feed."


            delta = upd - feed.lastupdated
            if delta.seconds > 60: 
                print "Last    Update value:  " + str(feed.lastupdated)
                print "Current Update value:  " + str(upd)

                for entry in allentries.entries:
                    print(entry.title.encode('ascii','ignore'))
                    title = entry.title
                    link = urlnorm.normalize(str(entry.link))
                    print entry.keys()

                    if hasattr(entry,'id') is True:
                        id = entry.id
                        print "Link has an ID"
                    else:
                        id = entry.link
                        print "Link has no ID"
                    cur.execute("select count(*) as count from stories where (url = %s or id_from_feed = %s) and location = %s",[link,str(id),feed.channel])
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

                        cur.execute("insert into stories (usr,title,url,text,name,location,channame,id_from_feed) values (%s,%s,%s,%s,%s,%s,(select name from channels where chanid = %s ),%s) returning storyid;",[feed.usr,entry.title,link,' ', feed.feedname, feed.channel,feed.channel,str(id)])
                        storyid = cur.fetchone()['storyid']
                        if commentgroupid == 0:
                            cur.execute("insert into commentgroups(url) values (%s) returning commentgroupid;",[link]);
                            commentgroupid = cur.fetchone()['commentgroupid']

                        #now, commentgroupid is set, either way. 
                        cur.execute("update stories set commentgroup = %s where storyid = %s;",[commentgroupid,storyid]);

                        #EVERYONE posts into ALL-STORIES. EVERYTHING goes there! ;)
                        cur.execute("insert into stories (usr,title,url,text,name,location,commentgroup,channame,id_from_feed) values \
                          (%s,%s,%s,%s,%s,0,%s,(select name from channels where chanid = 0),%s) returning storyid;",[feed.usr,entry.title,link,' ', feed.feedname, commentgroupid,str(id)])

                        api = ApiClient('http://:rXVEdV8N2clyZ4@8hdj3.api.indextank.com')
                        index = api.get_index('Pages')
                        index.add_document(storyid, { 'text': title , 'link': link})
                        print "Added " + str(storyid) + " to index"
                    cur.execute("update feeds set lasttime = now() where feedid = %s",[feed.feedid])
                    db.commit()
            else:
                print "Delta is " + str(delta.seconds)
             
    print("***********************************************************************************")
    print("************************************RESTARTING LIST********************************")
    db.close()

