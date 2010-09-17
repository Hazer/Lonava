#!/usr/bin/python

import urllib, urllib2, sys
import simplejson as json
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
        
    

#janky declarations:
class Opener(urllib.FancyURLopener):
    version = 'LonBot-Digg/1.0 +http://Lonava.com/'

urlopen = Opener().open
appkey = '123'
#apisecret = ''


# timeout in seconds
timeout = 10
socket.setdefaulttimeout(timeout)

#getting digg containers and topics, 'cause digg is lazy
turl = 'http://services.digg.com/1.0/endpoint?method=container.getAll&type=json'
twebsite = urllib2.urlopen(turl)
twebsite_html = json.loads(twebsite.read())
twebsite.close()

containers = []
topics = []
z = 0


#Get List of current topics and containers
while z < len(twebsite_html[u'containers']):
   containers.append(twebsite_html[u'containers'][z][u'short_name'])
   x = 0
   while x < len(twebsite_html[u'containers'][z][u'topics']):
      topics.append(twebsite_html[u'containers'][z][u'topics'][x][u'short_name'])
      x=x+1
   z=z+1


db = psycopg2.connect("dbname='lonava' user='YOURUSER' host='localhost' password='YOURPASS'")
cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)

#Create a Channel for each topic
for topic in topics:
    kind = '&topic=%s' % topic

    #actually retrieve stuff
    # url = 'http://services.digg.com/1.0/endpoint?method=story.getPopular'  + kind + '&appkey=' + appkey + '+&type=json'
    url = 'http://services.digg.com/1.0/endpoint?method=story.getPopular'  + kind + '+&type=json'

    #Create channel and feed if it doesn't exist yet.
    cur.execute("select count(*) from feeds where feedclass = 4 and url = %s",[url])
    count = cur.fetchone()['count']
    if count < 1:
        #Create new Feed
        cur.execute("insert into feeds(url,feedclass,feedname,lasttime) values (%s,4,%s,now() - interval '60 minutes') returning feedid",[url,"Digg- " + topic])
    else:
        cur.execute("select feedid from feeds where feedclass = 4 and url = %s",[url])

    feedid = cur.fetchone()['feedid']
    db.commit()
    feed =  LonFeed()
    feed.FromFeedID(feedid)
    print "Loaded -" + str(topic) + "Chan " + str(feed.channel)
    lastrun = feed.lasttime
    nextrun = lastrun + datetime.timedelta(0,feed.freq)
    print("Lastrun" + str(lastrun))
    print("Nextrun" + str(nextrun))
    print("Now is " + str( datetime.datetime.now()))
    if datetime.datetime.now() >= nextrun:
        website = urllib2.urlopen(url)
        website_html = json.loads(website.read())
        website.close()

        a = 0

        while a < len(website_html[u'stories']):
            print str(a) + "/ " + str(len(website_html[u'stories']))
            digglink = website_html[u'stories'][a][u'href']
            title = website_html[u'stories'][a][u'title']
            link =  urlnorm.normalize(str(website_html[u'stories'][a][u'link']))
            print str(link)

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
            
                cur.execute("insert into stories (usr,title,url,text,name,location,channame) values (%s,%s,%s,%s,%s,%s,(select name from channels where chanid = %s )) returning storyid;",[feed.usr,title,link,'Via: ' + digglink, feed.feedname, feed.channel,feed.channel])
                storyid = cur.fetchone()['storyid']

                if commentgroupid == 0:
                    cur.execute("insert into commentgroups(url) values (%s) returning commentgroupid;",[link]);
                    commentgroupid = cur.fetchone()['commentgroupid']

                #now, commentgroupid is set, either way.
                cur.execute("update stories set commentgroup = %s where storyid = %s;",[commentgroupid,storyid]);
                #EVERYONE posts into ALL-STORIES. EVERYTHING goes there! ;)
                cur.execute("insert into stories (usr,title,url,text,name,location,commentgroup,channame) values (%s,%s,%s,%s,%s,0,%s,(select name from channels where chanid = 0 )) returning storyid;",[feed.usr,title,link,'Via: ' + digglink, feed.feedname, commentgroupid])
                api = ApiClient('http://:rXVEdV8N2clyZ4@8hdj3.api.indextank.com')
                index = api.get_index('Pages')
                index.add_document(storyid, { 'text': title , 'link': link})

            cur.execute("update feeds set lasttime = now() where feedid = %s",[feed.feedid])
            a += 1

        db.commit()

