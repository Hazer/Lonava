#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.escape
import psycopg2
import psycopg2.extras
import bcrypt
import time
import datetime
import os
import markdown
import imghdr 
import urlnorm    #Modified url verification lib
import feedparser
import random
from indextank_client import ApiClient
import socket

from PIL import Image
from urlparse import urlparse
from tornado.options import define, options

import re
try: 
   from hashlib import md5 as md5_func
except ImportError:
   from md5 import new as md5_func
import NofollowExtension


define("port", default=80, help="run on the given port", type=int)


#Autolink from http://greaterdebater.com/blog/gabe/post/4
def autolink(html):
    # match all the urls
    # this returns a tuple with two groups
    # if the url is part of an existing link, the second element
    # in the tuple will be "> or </a>
    # if not, the second element will be an empty string
    urlre = re.compile("(\(?https?://[-A-Za-z0-9+&@#/%?=~_()|!:,.;]*[-A-Za-z0-9+&@#/%=~_()|])(\">|</a>)?")
    urls = urlre.findall(html)
    clean_urls = []

    # remove the duplicate matches
    # and replace urls with a link
    for url in urls:
        # ignore urls that are part of a link already
        if url[1]: continue
        c_url = url[0]
        # ignore parens if they enclose the entire url
        if c_url[0] == '(' and c_url[-1] == ')':
            c_url = c_url[1:-1]

        if c_url in clean_urls: continue # We've already linked this url

        clean_urls.append(c_url)
        # substitute only where the url is not already part of a
        # link element.
        html = re.sub("(?<!(=\"|\">))" + re.escape(c_url), 
                      "<a rel=\"nofollow\" href=\"" + c_url + "\">" + c_url + "</a>",
                      html)
    return html

# Github flavored Markdown, from http://gregbrown.co.nz/code/githib-flavoured-markdown-python-implementation/
def gfm(text):
    # Extract pre blocks.
    extractions = {}
    def pre_extraction_callback(matchobj):
        digest = md5(matchobj.group(0)).hexdigest()
        extractions[digest] = matchobj.group(0)
        return "{gfm-extraction-%s}" % digest
        pattern = re.compile(r'<pre>.*?</pre>', re.MULTILINE | re.DOTALL)
        text = re.sub(pattern, pre_extraction_callback, text)

    # Prevent foo_bar_baz from ending up with an italic word in the middle.
    def italic_callback(matchobj):
        s = matchobj.group(0)
        if list(s).count('_') >= 2:
            return s.replace('_', '\_')
        return s
        text = re.sub(r'^(?! {4}|\t)\w+_\w+_\w[\w_]*', italic_callback, text)

    # In very clear cases, let newlines become <br /> tags.
    def newline_callback(matchobj):
        if len(matchobj.group(1)) == 1:
            return matchobj.group(0).rstrip() + '  \n'
        else:
            return matchobj.group(0)
        pattern = re.compile(r'^[\w\<][^\n]*(\n+)', re.MULTILINE)
        text = re.sub(pattern, newline_callback, text)

    # Insert pre block extractions.
    def pre_insert_callback(matchobj):
        return '\n\n' + extractions[matchobj.group(1)]
        text = re.sub(r'{gfm-extraction-([0-9a-f]{32})\}', pre_insert_callback, text)

    return text



class BaseHandler(tornado.web.RequestHandler):
    def getvars(self):
        self.uid = self.get_secure_cookie("usrid")
        if self.uid is None:
            self.uid = "0"
        
        self.name = self.get_secure_cookie("name")
        self.ustatus = self.get_secure_cookie("ustatus")
        if self.ustatus is None:
            self.ustatus = "0"

        return long(self.uid)
           

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
        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute ("select * from feeds where feedid = %s;",[feedid])
        row = cur.fetchone()
        print str(row)
        self.FromDBRow(row)
        db.close()

    def FromDBRow(self,row):
        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
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
            cur.execute("insert into channels (name,postable,chanclass) values (%s,False,3) returning chanid",[self.feedname])
            self.channel = cur.fetchone()['chanid']
            cur.execute("update feeds set channel = %s where feedid = %s",[self.channel,self.feedid])
            db.commit()
        else:
            self.channel = row['channel']       
        db.commit()

class LonReply(object):
    ## Could Reply and Post be merged? Yes. 
    ## But it would be more confusing what goes where.
    def __init__(self):
        self.usr = -1
        self.replytime = datetime.datetime.now()
        self.text = ""
        self.replyid = -1
        self.parent = -1
        self.commentgroup = -1  
        self.name = ""

    def FromReplyID(self,replyid):
        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'") 
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute ("select * from replies where replyid = %s;", [replyid])
        row = cur.fetchone()
        self.FromDBRow(row)
        db.close()

    def FromDBRow(self,row):
        self.replyid = row['replyid']
        self.usr = row['usr']
        self.replytime = row['replytime']
        self.text = row['text']
        self.parent = row['parent']
        self.commentgroup = row['commentgroup']
        self.name = row['name']
        self.score = row['score']
        self.lastedit = row['lastedit']
        self.imgurl = row['imgurl']
        self.pimgurl = row['pimgurl']

    def GetReplyIDs(self):
        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute ("select *,score - (select count(*) from replies where commentgroup = %s and parent = %s and replyid > r.replyid) as rank from replies as r where commentgroup = %s and parent = %s order by rank desc;", [self.commentgroup,self.replyid,self.commentgroup,self.replyid])

        self.replies = []
        rows = cur.fetchall()
        for row in rows:
            replies.append(row['replyid'])
        return replies


    def GetReplyRows(self):
        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute ("select *,score - (select count(*) from replies where commentgroup = %s and parent = %s and replyid > r.replyid) as rank from replies as r where commentgroup = %s and parent = %s order by rank desc;", [self.commentgroup,self.replyid,self.commentgroup,self.replyid])
        self.replies = []
        rows = cur.fetchall()
        return rows

    def GetHTML(self,caller):
        ## We don't need Markdown safemode, since we're encoding HTML before it is submitted.
        caller.getvars()
        retstr = caller.render_string('lonreply.html',ustatus=caller.ustatus,imgurl=self.imgurl,pimgurl=self.pimgurl,lastedit=self.lastedit,editago=FancyDateTimeDelta(self.lastedit).format(),viewer=caller.uid,usr=self.usr,score=self.score,name=self.name,replyid=self.replyid,replytime=self.replytime\
            ,timeago=FancyDateTimeDelta(self.replytime).format(),text=autolink(markdown.markdown(unicode(gfm(self.text),'utf8'),output_format='html4',extensions=['NofollowExtension'])))
        return retstr 
 
        
    def GetHTMLFamily(self,caller):
        #Take of yourself first
        replyrows = self.GetReplyRows()   #Don't do this in the if, so we can check len first
        if len(replyrows) > 0:
            cssclass = "commentbox"
        else:
            cssclass = " "

        retstr = "<ul class='grid_11 " + cssclass +"'><li>"
        retstr += self.GetHTML(caller)    
        if len(replyrows) > 0:
            for replyrow in replyrows:
                retstr += "<ul class='grid_11'><li>"
                reply = LonReply()
                reply.FromDBRow(replyrow)
                retstr += reply.GetHTMLFamily(caller) 
                    
                retstr += "</li></ul>"
        retstr += "</li></ul>"
        return retstr

class LonMsg(object):
    ## Could Reply and Post be merged? Yes.
    ## But it would be more confusing what goes where.
    def __init__(self):
        self.sendid = -1
        self.msgtime = datetime.datetime.now()
        self.text = ""
        self.title = ""
        self.recvid = -1
        self.msgid = -1

    def FromReplyID(self,msgid):
        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute ("select * from msgs where msgid = %s;", [msgid])
        row = cur.fetchone()
        self.FromDBRow(row)
        db.close()

    def FromDBRow(self,row):
        self.sendid = row['sendid']
        self.msgtime = row['msgtime']
        self.text = row['text']
        self.title = row['title']
        self.recvid= row['recvid']
        self.msgid = row['msgid']

    def GetHTML(self,caller):
        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute ("select name from usrs where usrid = %s;", [self.sendid])
        send_name = cur.fetchone()['name']

        ## We don't need Markdown safemode, since we're encoding HTML before it is submitted.
        retstr = caller.render_string('lonmsg.html',from_name=send_name,from_uid=self.sendid,title=self.title,msgtime=self.msgtime\
                                      ,timeago=FancyDateTimeDelta(self.msgtime).format(),text=autolink(markdown.markdown(unicode(gfm(self.text),'utf8'),output_format='html4',extensions=['NofollowExtension'])))
        return retstr


class LonStory(tornado.web.UIModule):
    """
    LonStories are the object for posts.
    """
    def __init__(self):
        self.usr = -1
        self.storytime = datetime.datetime.now()
        self.title = ""
        self.url = ""
        self.text = ""
        self.storyid = -1
        self.cachedreplycount = -1
        self.name = ""
        self.commentgroup = -1
        self.imgurl = ""
        self.pimgurl = ""
        self.channame = ""
        self.location = -1

    def FromStoryID(self,storyid):
        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute ("select * from storygroup where storyid = %s;", [storyid])
        row = cur.fetchone()
        self.FromDBRow(row)
        db.close()

    def FromDBRow(self,row):
        self.commentgroup = row['commentgroup']
        self.storyid = row['storyid']
        self.usr = row['usr']
        self.storytime = row['storytime']
        self.title = row['title']
        self.url = row['url']
        self.text = row['text']
        self.storyid = row['storyid']
        self.cachedreplycount = row['cachedreplycount']
        self.name = row['name']
        self.channame = row['channame']
        self.lastedit = row['lastedit']
        self.location = row['location']
        self.score = row['score']
        if self.url is None:
            self.urlstr = "self"
            self.url = "http://Lonava.com/stories/" + str(self.storyid)
        else:
            o = urlparse(self.url)
            self.urlstr = o.netloc
        try:
            self.imgurl = row['imgurl']
        except:
            self.imgurl = None
        try:
            self.pimgurl = row['pimgurl']
        except:
            self.pimgurl = None


    def GetReplyIDs(self):
        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute ("select *,score - (select count(*) from replies where commentgroup = %s and parent = 0 and replyid > r.replyid) as rank from replies as r where commentgroup = %s and parent = 0 order by rank desc;", [self.commentgroup,self.commentgroup])

        self.replies = []
        rows = cur.fetchall()
        for row in rows:
            replies.append(row['replyid'])
            
        self.cachedreplycount = len(replies)
        return replies


    def GetReplyRows(self):
        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute ("select *,score - (select count(*) from replies where commentgroup = %s and parent = 0 and replyid > r.replyid) as rank from replies as r where commentgroup = %s and parent = 0 order by rank desc;", [self.commentgroup,self.commentgroup])

        self.replies = []
        rows = cur.fetchall()
        self.cachedreplycount = len(rows)
        return rows
    
    def GetHTML(self,caller):
        caller.getvars()
        retstr = caller.render_string('lonstory.html',ustatus=caller.ustatus,location=self.location,channame=self.channame,editago=FancyDateTimeDelta(self.lastedit).format(),lastedit=self.lastedit,viewer=caller.uid,pimgurl=self.pimgurl,imgurl=self.imgurl,userid=self.usr,storyid=self.storyid,score=self.score,name=self.name,cachedreplycount=self.cachedreplycount,url=self.url,urlstr=self.urlstr,title=self.title,storytime=self.storytime,\
                                      timeago=FancyDateTimeDelta(self.storytime).format(),text=autolink(markdown.markdown(unicode(gfm(self.text),'utf8'),output_format='html4',extensions=['NofollowExtension'])))
        return retstr

    def GetHTMLTitle(self,caller):
        caller.getvars()
        retstr = caller.render_string('lonstory-title.html',location=self.location,channame=self.channame,viewer=caller.uid,imgurl=self.imgurl,userid=self.usr,score=self.score,name=self.name,cachedreplycount=self.cachedreplycount,url=self.url,urlstr=self.urlstr,storyid=self.storyid,title=self.title,storytime=self.storytime\
                                      ,timeago=FancyDateTimeDelta(self.storytime).format()) 
        return retstr


    
class FancyDateTimeDelta(object):
    """
    Format the date / time difference between the supplied date and
    the current time using approximate measurement boundaries
    """

    def __init__(self, dt):
        now = datetime.datetime.now()
        delta = now - dt
        self.year = delta.days / 365
        self.month = delta.days / 30 - (12 * self.year)
        if self.year > 0:
            self.day = 0
        else: 
            self.day = delta.days % 30
        self.hour = delta.seconds / 3600
        self.minute = delta.seconds / 60 - (60 * self.hour)
        self.second = delta.seconds - ( self.hour * 3600) - (60 * self.minute) 
        self.millisecond = delta.microseconds / 1000

    def format(self):
        #Round down. People don't want the exact time.
        #For exact time, reverse array.
        fmt = ""
        for period in ['millisecond','second','minute','hour','day','month','year']:
            value = getattr(self, period)
            if value:
                if value > 1:
                    period += "s"

                fmt = str(value) + " " + period
        return fmt + " ago"
    

class PageHandler(BaseHandler):
    def get(self,page = 1):
        self.getvars()

        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        client_usrid = tornado.escape.xhtml_escape(self.uid)
        cur.execute ("select postsperpage,newmail from usrs where usrid = %s",[self.uid])
        usrstuff = cur.fetchone()
        ppp = usrstuff['postsperpage']
        newmail = usrstuff['newmail']

        self.write(self.render_string('header.html',newmail=newmail,title=' ',uid=self.uid,user=self.name,ustatus=self.ustatus))

        cur.execute("create temporary table mystories (like stories);")
        cur.execute("alter table mystories add column ord bigserial;")
        cur.execute("alter table mystories add column  cachedreplycount bigint;")
        stop = long(ppp) * long(page)
        start = (long(ppp) * long(page)) - long(ppp)
        cur.execute("insert into mystories(channame,lastedit,pimgurl,imgurl,usr,storytime,title,url,text,name,score,commentgroup,storyid,location,cachedreplycount) select channame,lastedit,pimgurl,imgurl,usr,storytime,title,url,text,name,score,commentgroup,storyid,location,cachedreplycount from storygroup where location in (select subbedchan from usrsubs where usr = %s) order by storyid asc; ",[str(self.uid)])
        cur.execute("select * from (select distinct on (commentgroup) * from (select *, ( (select case when sign(score) = -1 then 2 ^ score else 1 + score end ) + (cachedreplycount / 10))  / (1.1 + (select count(*) from mystories) - ord) as rank from mystories order by rank) as foo) as bar order by rank desc limit (%s) offset (%s);",[ppp,start])        
        rows = cur.fetchall()

        self.write("""<ul class="grid_11"> """)
        for storyrow in rows:
            story = LonStory()
            story.FromDBRow(storyrow)
            self.write(story.GetHTMLTitle(self))

        cur.execute("drop table mystories")
        db.close()
        self.write("<nav><li class='pagenext single_wrap'>")
        self.write("view more: ")
        if long(page) > 1:
            self.write("<a href='/page/" + str(long(page) - 1) +"'>Page " + str(long(page) - 1) + "</a>")
            self.write("&nbsp | &nbsp" )
        self.write("<a href='/page/" + str(long(page) + 1) +"'>Page " + str(long(page) + 1) + "</a>") 
        self.write("</li></nav>")
        self.write("""</ul>""")
        self.write(self.render_string('footer.html',topchans=retrChans(self.uid,True).topchans,ustatus=self.ustatus,uid=self.uid))

class NewHandler(BaseHandler):
    def get(self,page = 1):
        self.getvars()

        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        client_usrid = tornado.escape.xhtml_escape(self.uid)
        cur.execute ("select postsperpage,newmail from usrs where usrid = %s",[self.uid])
        usrstuff = cur.fetchone()
        ppp = usrstuff['postsperpage']
        newmail = usrstuff['newmail']
        stop = long(ppp) * long(page)
        start = (long(ppp) * long(page)) - long(ppp)

        self.write(self.render_string('header.html',newmail=newmail,title='Your Newest Stories',uid=self.uid,user=self.name,ustatus=self.ustatus))
        self.write("""<li>
    <div class="clear"></div>
    <div class="single_wrap">
        <div class="padder">

                   <h2>Showing the newest stories from the channels you are are subscribed to: </h2><br>
                   For <i>all</i> new stories, check out the <a href="http://lonava.com/channel/0"> "Every Story"</a> channel.

        </div>
        </div>
        </li>""")

        cur.execute("create temporary table mystories (like stories);")
        cur.execute("alter table mystories add column ord bigserial;")
        cur.execute("alter table mystories add column  cachedreplycount bigint;")
        cur.execute("insert into mystories(channame,lastedit,pimgurl,imgurl,usr,storytime,title,url,text,name,score,commentgroup,storyid,location,cachedreplycount) select channame,lastedit,pimgurl,imgurl,usr,storytime,title,url,text,name,score,commentgroup,storyid,location,cachedreplycount from storygroup where location in (select subbedchan from usrsubs where usr = %s) order by storyid asc;",[str(self.uid)])
        cur.execute("select * from (select distinct on (commentgroup) * from (select *,  ( (select case when sign(score) = -1 then 2 ^ score else 1 + score end ) + (cachedreplycount / 10))  / (1.1 + (select count(*) from mystories) - ord) as rank from mystories) as foo) as bar order by storyid desc limit (%s) offset (%s);",[ppp,start])

        rows = cur.fetchall()
        for storyrow in rows:
            story = LonStory()
            story.FromDBRow(storyrow)
            self.write(story.GetHTMLTitle(self))


        cur.execute("drop table mystories")
        db.close()
        self.write("<nav><li class='pagenext single_wrap'>")
        self.write("view more: ")
        if long(page) > 1:
            self.write("<a href='/newest/" + str(long(page) - 1) +"'>Page " + str(long(page) - 1) + "</a>")
            self.write("&nbsp | &nbsp" )
        self.write("<a href='/newest/" + str(long(page) + 1) +"'>Page " + str(long(page) + 1) + "</a>")
        self.write("</li></nav>")
        self.write("""</ul>""")

        self.write(self.render_string('footer.html',topchans=retrChans(self.uid,True).topchans,ustatus=self.ustatus,uid=self.uid))

class UserPostsHandler(BaseHandler):
    def get(self,client_userid):
        self.getvars()

        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        client_usrid = tornado.escape.xhtml_escape(self.uid)
        cur.execute ("select postsperpage,newmail from usrs where usrid = %s",[self.uid])
        usrstuff = cur.fetchone()
        ppp = usrstuff['postsperpage']
        newmail = usrstuff['newmail']

        self.write(self.render_string('header.html',newmail=newmail,title=' ',uid=self.uid,user=self.name,ustatus=self.ustatus))

        ## Score + log10(comments)  / 1 + (stories above you.)

        cur.execute ("select * from (select distinct on (commentgroup) * from storygroup where usr = %s ) as foo order by storyid desc limit %s;",[client_userid,ppp])

        rows = cur.fetchall()
        for storyrow in rows:
            story = LonStory()
            story.FromDBRow(storyrow)
            self.write(story.GetHTMLTitle(self))

        db.close()
        self.write(self.render_string('footer.html',topchans=retrChans(self.uid,True).topchans,ustatus=self.ustatus,uid=self.uid))

class ChanPostsHandler(BaseHandler):
        def get(self,client_chanid,page = 1):
            self.getvars()

            db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
            cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
            client_usrid = tornado.escape.xhtml_escape(self.uid)
            cur.execute ("select postsperpage,newmail from usrs where usrid = %s",[self.uid])
            usrstuff = cur.fetchone()
            ppp = usrstuff['postsperpage']
            newmail = usrstuff['newmail']

            cur.execute ("select name from channels where chanid = %s",[client_chanid]);
            channame = cur.fetchone()['name']
            stop = long(ppp) * long(page)
            start = (long(ppp) * long(page)) - long(ppp)
            self.write(self.render_string('header.html',newmail=newmail,title=channame,uid=self.uid,user=self.name,ustatus=self.ustatus))
            self.write(self.render_string('showingstories.html',channame=channame))
            cur.execute ("select * from (select distinct on (commentgroup) * from storygroup where location = %s ) as foo order by storyid desc limit (%s) offset (%s);",[client_chanid,ppp,start])

            rows = cur.fetchall()
            if len(rows) < 1:    
                self.write("""
                            <li> 
                           <div class="clear"></div> 
                           <div class="single_wrap"> 
                           <div class="padder"> 
                           
                           There doesn't appear to be any stories in this channel yet. If this is an Channel from an RSS feed, it may take up to half an hour for the feed to enter the rotation. If this is a Discussion Channel, <a href='http://lonava.com/submit'>Submit Something</a>! ;)
                            </div> 
                           </div> 
                           </li> """)
            for storyrow in rows:
                story = LonStory()
                story.FromDBRow(storyrow)
                self.write(story.GetHTMLTitle(self))

            db.close()
            self.write("<nav><li class='pagenext single_wrap'>")
            self.write("view more: ")
            if long(page) > 1:
                self.write("<a href='/chan/" + tornado.escape.xhtml_escape(client_chanid) + "/" + str(long(page) - 1) +"'>Page " + str(long(page) - 1) + "</a>")
                self.write("&nbsp | &nbsp" )
            self.write("<a href='/chan/" +  tornado.escape.xhtml_escape(client_chanid) + "/" + str(long(page) + 1) +"'>Page " + str(long(page) + 1) + "</a>")
            self.write("</li></nav>")
            self.write("""</ul>""")

            self.write(self.render_string('footer.html',topchans=retrChans(self.uid,True).topchans,ustatus=self.ustatus,uid=self.uid))

class NewChanHandler(BaseHandler):
    def get(self):
        self.getvars() 

        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute ("select postsperpage,newmail from usrs where usrid = %s",[self.uid])
 
        usrstuff = cur.fetchone()
        print "usrid: " + self.uid  
        ppp = usrstuff['postsperpage']
        newmail = usrstuff['newmail']

        self.write(self.render_string('header.html',newmail=newmail,title='Create New Channel',uid=self.uid,user=self.name,ustatus=self.ustatus))
        self.write(self.render_string('newchanform.html',uid=self.uid,user=self.name,ustatus=self.ustatus))

        db.close()
        self.write(self.render_string('footer.html',topchans=retrChans(self.uid,True).topchans,ustatus=self.ustatus,uid=self.uid))


    def post(self):
        if (self.getvars() == 0):
            return -1
        if (self.ustatus < 1):
            return -1
        
        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            client_channame =  unicode(tornado.escape.xhtml_escape(self.get_argument("channame")),'utf8')  
        except:
            client_channame = None

        try:
            client_newurl =  unicode(tornado.escape.xhtml_escape(self.get_argument("newurl")),'utf8')
        except:
            client_newurl = None

        if client_newurl == None and client_channame == None:
            self.write("I'm sorry, the submitted information had neither a Feed Name, nor a Feed URL.")
            return -1
        
        if client_newurl is not None:
            url = urlnorm.normalize(str(client_newurl))              
            cur.execute("select * from feeds where url = %s",[url])
            existing = cur.fetchone()

            if existing is None:
                #The feed is new
                cur.execute("insert into feeds(url,feedclass) values (%s,3) returning feedid",[url])
                feedid = cur.fetchone()['feedid']
                db.commit()
                feed =  LonFeed()
                feed.FromFeedID(feedid)


                cur.execute("insert into usrsubs(usr,subbedchan) values (%s,%s)",[self.uid,str(feed.channel)])
                db.commit()
                db.close()
                self.redirect("http://lonava.com/channel/" + str(feed.channel))

            else:
                #Chan already exists
                feed = LonFeed()
                feed.FromFeedID(existing['feedid'])
                loc = feed.channel
                cur.execute("insert into usrsubs(usr,subbedchan) values (%s,%s)",[self.uid,str(loc)])
                self.redirect("http://lonava.com/channel/" + str(loc))

        if client_channame is not None:
            cur.execute("insert into channels (name,createdby,postable) values (%s,%s,True) returning chanid",[str(client_channame),self.uid])
            chan = cur.fetchone()['chanid']
            cur.execute("insert into usrsubs(usr,subbedchan) values (%s,%s)",[self.uid,str(chan)])
            db.commit()
            db.close()
                                    
            self.redirect("http://lonava.com/channel/" + str(chan))


class MyMsgHandler(BaseHandler):
    def get(self):
        if (self.getvars() == 0):
            return -1

        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute ("select postsperpage,newmail from usrs where usrid = %s",[self.uid])
 
        usrstuff = cur.fetchone()
        print "usrid: " + self.uid  
        ppp = usrstuff['postsperpage']
        newmail = usrstuff['newmail']

        self.write(self.render_string('header.html',newmail=newmail,title='My Messages',uid=self.uid,user=self.name,ustatus=self.ustatus))

        ## Score + log10(comments)  / 1 + (stories above you.)

        cur.execute ("select * from msgs where recvid = %s order by msgid desc limit %s;",[self.uid,ppp])
        rows = cur.fetchall()
        for msgrow in rows:
            msg = LonMsg()
            msg.FromDBRow(msgrow)
            self.write(msg.GetHTML(self))

        cur.execute ("update usrs set newmail = 0 where usrid = %s;",[self.uid])
        db.commit()
        db.close()
        self.write(self.render_string('footer.html',topchans=retrChans(self.uid,True).topchans,ustatus=self.ustatus,uid=self.uid))

class UserCommentsHandler(BaseHandler):
    def get(self,client_userid):
        self.getvars()

        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        client_usrid = tornado.escape.xhtml_escape(self.uid)
        cur.execute ("select postsperpage,newmail from usrs where usrid = %s",[self.uid])
        usrstuff = cur.fetchone()
        ppp = usrstuff['postsperpage']
        newmail = usrstuff['newmail']

        self.write(self.render_string('header.html',newmail=newmail,title=' ',uid=self.uid,user=self.name,ustatus=self.ustatus))

        ## Score + log10(comments)  / 1 + (stories above you.)

        cur.execute ("select * from replies where usr = %s order by replyid desc limit %s",[client_userid,ppp])
        rows = cur.fetchall()
        for reply in rows:
            rep = LonReply()
            rep.FromDBRow(reply)
            self.write(rep.GetHTML(self))

        db.close()
        self.write(self.render_string('footer.html',topchans=retrChans(self.uid,True).topchans,ustatus=self.ustatus,uid=self.uid))

class StoryHandler(BaseHandler):
    def get(self, story_id):
        self.getvars()
        print "uid = " + self.uid
        story = LonStory()
        story.FromStoryID(story_id)
        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute ("select postsperpage,newmail from usrs where usrid = %s",[self.uid])
        usrstuff = cur.fetchone()
        ppp = usrstuff['postsperpage']
        newmail = usrstuff['newmail']

        self.write(self.render_string('header.html',newmail=newmail,title=story.title,uid=self.uid,user=self.name,ustatus=self.ustatus)) 
        self.write(story.GetHTML(self))
        self.write(self.render_string('replyform.html',edit=0,commentgroup=story.commentgroup,uid=self.uid,storyid=story_id,parent=0,ustatus=self.ustatus))  
        self.write("<ul class='grid_11'>")
        for replyrow in story.GetReplyRows():
            reply = LonReply()
            reply.FromDBRow(replyrow)
            self.write (reply.GetHTMLFamily(self))
        self.write("</ul>")
        db.close()
        self.write(self.render_string('footer.html',topchans=retrChans(self.uid,True).topchans,ustatus=self.ustatus,uid=self.uid))

    def post(self,storyid):
        if (self.getvars() == 0):
            return -1
        if long(self.ustatus) < 1:
            self.write("I'm sorry, only Verified users may post replies. You may Verify your account at <a href='https://lonava.com/verify/'" + self.uid + "'>the verification page</a>.")
            return -1

        try:
            client_parent =  tornado.escape.xhtml_escape(self.get_argument("parent"))
        except:
            client_parent = None
        try:
            client_text =  unicode(tornado.escape.xhtml_escape(self.get_argument("text")),'utf8')
            if client_text == unicode(''):
                client_text = " "
        except:
            client_text = " "
    
        client_usrid = tornado.escape.xhtml_escape(self.uid)
        try:
            print "Trying Img"
            client_img_path =  unicode(tornado.escape.xhtml_escape(self.get_argument("image.path")),'utf8')
            print client_img_path
            imagetype = imghdr.what(client_img_path)
            acceptable_images = ['gif','jpeg','jpg','png','bmp']
            if imagetype in acceptable_images:
                print "Acceptable image"
                fs_path = client_img_path + '.' + imagetype
                os.rename(client_img_path,fs_path)
                imgurl = '/static/' + fs_path[fs_path.rindex('uploads')::]
                pimgurl = '/static/thumb-' + fs_path[fs_path.rindex('uploads')::]

                print "Ugly."
                print imgurl
                print pimgurl
                pfs_path = fs_path[:fs_path.rindex('uploads'):] + 'thumb-' + fs_path[fs_path.rindex('uploads')::]

                #Open it in Python to check it out
                im =  Image.open(fs_path)
                print "Boo."
                img_width, img_height = im.size
                print "fooo"
                if ((img_width > 150) or (img_height > 150)):
                    print "deboo"
                    im.thumbnail((150, 150), Image.ANTIALIAS)
                    print "ffoo"

                    im.save(pfs_path)
                    print "loo"
                else:
                    print "ooo"
                    pimgurl = imgurl
                    print "bar"

            else:
                self.write("I'm sorry, but we can't recognize that image type.")
                self.imgurl = None
                self.pimgurl = None
                print "unrecognizable image"

        except:
            client_img_path =  None
            img_path = None
            imgurl = None
            pimgurl = None

        print (str(client_text).__len__())
        if (str(client_text).__len__() < 5 ):
            if (imgurl is None):
                self.write(self.render_string('header.html',newmail=0,title="Error in Posting",uid=self.uid,user=self.name,ustatus=self.ustatus))
                self.write("All posts must contain some text, or an image.")
                return -1

        if (client_parent is None) or (client_usrid is None):
            self.write(self.render_string('header.html',newmail=0,title="Error in Posting",uid=self.uid,user=self.name,ustatus=self.ustatus))
            self.write("Technical error. Missing parent or usrid.")
            return -1

        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("select commentgroup from stories where storyid = %s",[storyid]);
        commentgroup = cur.fetchone()['commentgroup']
        cur.execute("insert into replies (commentgroup,usr,parent,text,name) values (%s,%s,%s,%s,%s) returning replyid;",[commentgroup,client_usrid,client_parent,client_text,self.name])
        replyid = cur.fetchone()['replyid']
        if pimgurl is not None:
            cur.execute("update replies set imgurl = %s, pimgurl = %s where replyid = %s",[imgurl,pimgurl,replyid])

        cur.execute("update commentgroups set cachedreplycount = ( select count(*) from replies where commentgroup = %s) where commentgroupid = %s;",[commentgroup,commentgroup])
        db.commit()
        self.redirect("/stories/" + storyid)
        db.close()

class VoteStoryHandler(BaseHandler):
    def post(self):
        if (self.getvars() == 0):
            return -1

        client_story =  tornado.escape.xhtml_escape(self.get_argument("storyid"))
        client_voteval =  tornado.escape.xhtml_escape(self.get_argument("val"))
        print "Vote recvd for " + str(client_story) + " from " + str(self.uid)

        value = int(client_voteval)
        if ((value != 1) and (value != -1) and (value != 0)): # You can add or subtract 1. Not more.
            return -1
        
    

        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute("delete from storyvotes where story = %s and usr = %s",[client_story,self.uid])
        #Only one vote per story per user. If they submit a second one, drop the first.

        cur.execute("insert into storyvotes(usr,story,pointchange) values (%s,%s,%s);",[self.uid, client_story, value])
        cur.execute("update stories set score = (select sum(pointchange) from storyvotes where story = %s) where storyid = %s;",[client_story,client_story])


        #set cookie with hidden story votes
        cur.execute('select * from storyvotes where usr = %s order by storyvoteid desc limit 100;',[self.uid])
        rows = cur.fetchall()
        cookiearry = "["
        for row in rows:
            cookiearry = cookiearry + '"' + "storyid||" + str(row['story']) + "||" + str(row['pointchange']) + '",'

        #set cookie for replies
        cur.execute('select * from replyvotes where usr = %s order by replyvoteid desc limit 100;',[self.uid])
        rows = cur.fetchall()
        for row in rows:
            cookiearry = cookiearry + '"' + "replyid||" + str(row['reply']) + "||" + str(row['pointchange']) + '",'

        cookiearry = cookiearry + '"storyid||0||1"]'
        self.set_cookie("hidden-post-votes",cookiearry)

        db.commit() 
        db.close()

class VoteReplyHandler(BaseHandler):
    def post(self):
        print "ReplyingVote"
        if (self.getvars() == 0):
            return -1

        client_reply =  tornado.escape.xhtml_escape(self.get_argument("replyid"))
        client_voteval =  tornado.escape.xhtml_escape(self.get_argument("val"))
        print client_reply
        print client_voteval

        value = int(client_voteval)
        if ((value != 1) and (value != -1) and (value != 0)): # You can add or subtract 1. Not more.
            # You can add or subtract 1. Not more.
            return -1
        print value
        print client_voteval
        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute("delete from replyvotes where reply = %s and usr = %s",[client_reply,self.uid])
        #Only one reply vote per user. If they submit a second one, drop the first.

        cur.execute("insert into replyvotes (usr,reply,pointchange) values (%s,%s,%s);",[self.uid, client_reply, value])
        cur.execute("update replies set score = (select sum(pointchange) from replyvotes where reply = %s) where replyid = %s;",[client_reply,client_reply])

        #set cookie with hidden post votes
        cur.execute('select * from storyvotes where usr = %s order by storyvoteid desc limit 100;',[self.uid])
        rows = cur.fetchall()
        cookiearry = "["
        for row in rows:
            cookiearry = cookiearry + '"' + "storyid||" + str(row['story']) + "||" + str(row['pointchange']) + '",' 
        
        #set cookie for replies
        cur.execute('select * from replyvotes where usr = %s order by replyvoteid desc limit 100;',[self.uid])
        rows = cur.fetchall()
        for row in rows:
            cookiearry = cookiearry + '"' + "replyid||" + str(row['reply']) + "||" + str(row['pointchange']) + '",'
        cookiearry = cookiearry + '"storyid||0||1"]'
        self.set_cookie("hidden-post-votes",cookiearry)

        db.commit()
        db.close()

class RepostHandler(BaseHandler):
    def get(self,storyid):
        self.getvars()
        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        client_usrid = tornado.escape.xhtml_escape(self.uid)
        cur.execute ("select postsperpage,newmail from usrs where usrid = %s",[self.uid])
        usrstuff = cur.fetchone()
        ppp = usrstuff['postsperpage']
        newmail = usrstuff['newmail']

        self.write(self.render_string('header.html',newmail=newmail,title="repost",uid=self.uid,user=self.name,ustatus=self.ustatus))
        self.write(self.render_string('repostform.html',storyid=storyid))
        self.write(self.render_string('footer.html',topchans=retrChans(self.uid,True).topchans,ustatus=self.ustatus,uid=self.uid))


    def post(self,storyid):
        if self.getvars() == 0:
            return -1
        if long(self.ustatus) < 1:
            return -1
        try:
            client_chanlist=  self.get_argument("chanlist")
            chanlist = tornado.escape.json_decode(client_chanlist)
        except:
            self.write("You must select at least one channel to repost to.")
            return -1


        if (len(chanlist) > 5):
            self.write("Sorry. You can only post to a maximum of 5 channels.")
            return -1

        if (len(chanlist) < 1):
            self.write("Sorry. You must post to at least 1 channel.")
            return -1

        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("select subbedchan from usrsubs where usr = %s",[str(self.uid)])
        allowedchans = cur.fetchall()
        for a in range(len(allowedchans)):
            allowedchans[a] = str(allowedchans[a][0])


        for i in range(len(chanlist)):
            print long(chanlist[i])
            if (str(chanlist[i]) in allowedchans):
                # ONLY POST IN ALLOWED CHANNELS, Even if they fake an ID        
                print "-" + chanlist[i] + "-"
                cur.execute("insert into stories(channame,lastedit,pimgurl,imgurl,usr,storytime,title,url,text,name,commentgroup,location,score) (select channame,lastedit,pimgurl,imgurl,usr,storytime,title,url,text,name,commentgroup,location,0 as score from stories where storyid = %s) returning storyid;",[storyid])
                newstoryid = cur.fetchone()['storyid']
                cur.execute("update stories set channame = (select name from channels where chanid = %s), location = %s where storyid = %s",[chanlist[i],chanlist[i],newstoryid])
                db.commit()
                self.redirect("http://lonava.com/stories/" + str(newstoryid))
            else:
                print "Not allowing chan" + str(chanlist[i])
        db.close()


class EditStoryHandler(BaseHandler):
    def retrHTMLDivs(self,clist):
        content = ""
        for product in clist:
            divclass = 'channel'
            if (product[1] == 1):
                divclass += ' clicked'
                content += "<div class='" + divclass + "' channelnum='" + str(product[1]) + "'>" +  product[2] + "     (" + str(product[0]) + " subscribers) </div>";
        return content

    def get(self,storyid):
        self.getvars()
        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute ("select postsperpage,newmail from usrs where usrid = %s",[self.uid])
        usrstuff = cur.fetchone()
        ppp = usrstuff['postsperpage']
        newmail = usrstuff['newmail']
        self.write(self.render_string('header.html',title='Submit',newmail=newmail,uid=self.uid,user=self.name,ustatus=self.ustatus))
        story = LonStory()
        story.FromStoryID(storyid)

        clist = retrChans(self.uid,False).chanlist
        self.write(self.render_string('editsubmitform.html',edit=storyid,defaulttext=story.text,defaulttitle=story.title,defaulturl=story.url,retrHTMLDivs=self.retrHTMLDivs,clist=clist))
        db.close()
        self.write(self.render_string('footer.html',topchans=retrChans(self.uid,True).topchans,ustatus=self.ustatus,uid=self.uid))

    def post(self,storyid):
        if (self.getvars() == 0):
            return -1

        self.write(self.render_string('header.html',title='Submit',newmail=0,uid=self.uid,user=self.name,ustatus=self.ustatus))
        try:
            client_title =  unicode(tornado.escape.xhtml_escape(self.get_argument("title")),'utf8')
        except:
            self.write("Sorry. All posts must have a title.")
            return -1


        try:
            client_text =  unicode(tornado.escape.xhtml_escape(self.get_argument("text")),'ascii',errors='ignore')
        except:
            client_text = ' ' #I'm using a space, rather than None, so we don't need to error-check for null

        try:
            client_url =  unicode(tornado.escape.xhtml_escape(self.get_argument("url")),'utf8')
        except:
            client_url =  None

        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute ("select usr from stories where storyid = %s;",[storyid])
        origposter = cur.fetchone()['usr']
        if (str(origposter) != str(self.uid)):
            self.write('Only the original Poster can edit a post.')
            return -1

        #Get list of all posts to alter 
        cur.execute("update stories set title = %s,text= %s, url=%s, lastedit=now() where commentgroup = (select commentgroup where storyid = %s) and usr = %s",[client_title,client_text,client_url,storyid,self.uid])
        db.commit()
        db.close()
        self.redirect("/stories/" + str(storyid))
    


class SubmitHandler(BaseHandler):
    def retrHTMLDivs(self,clist):
        content = ""
        for product in clist:
            divclass = 'channel'
            if (product[1] == 1):
                divclass += ' clicked'

            content += "<div class='" + divclass + "' channelnum='" + str(product[1]) + "'>" +  product[2] + "     (" + str(product[0]) + " subscribers) </div>";

        return content
    
    def get(self):
        self.getvars()
        if long(self.ustatus) < 1:
            self.write(self.render_string('header.html',title='Submit',newmail=False,uid=self.uid,user=self.name,ustatus=self.ustatus))
            self.write("I'm sorry, only Verified users may post replies. You may Verify your account at <a href='https://lonava.com/verify/'" + self.uid + "'>the verification page</a>.")
            return -1

        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute ("select postsperpage,newmail from usrs where usrid = %s",[self.uid])
        usrstuff = cur.fetchone()
        ppp = usrstuff['postsperpage']
        newmail = usrstuff['newmail']

        self.write(self.render_string('header.html',title='Submit',newmail=newmail,uid=self.uid,user=self.name,ustatus=self.ustatus))
        clist = retrChans(self.uid,False).chanlist
        self.write(self.render_string('submitform.html',retrHTMLDivs=self.retrHTMLDivs,clist=clist))
        db.close()
        self.write(self.render_string('footer.html',topchans=retrChans(self.uid,True).topchans,ustatus=self.ustatus,uid=self.uid))

    def post(self):
        if (self.getvars() == 0):
            return -1

        if (self.ustatus) < 1:
            self.write("I'm sorry, only Verified users may post replies. You may Verify your account at <a href='https://lonava.com/verify/'" + self.uid + "'>the verification page</a>.")
            return -1

        self.write(self.render_string('header.html',title='Submit',newmail=0,uid=self.uid,user=self.name,ustatus=self.ustatus))
        try:
            client_title =  unicode(tornado.escape.xhtml_escape(self.get_argument("title")),'utf8')
        except:
            self.write("Sorry. All posts must have a title.")
            return -1


        try:
            client_text =  unicode(tornado.escape.xhtml_escape(self.get_argument("text")),'utf8')
        except:
            client_text = ' ' #I'm using a space, rather than None, so we don't need to error-check for null

        try:
            client_url =  unicode(tornado.escape.xhtml_escape(self.get_argument("url")),'utf8')
            if client_url.__len__() > 1:
                client_url = urlnorm.normalize(str(client_url))
            else:
                client_url = None

        except:
            client_url =  None

        try:
                client_edit =  long(tornado.escape.xhtml_escape(self.get_argument("edit")))
        except:
                client_edit =  None

    
        try:
            client_img_path =  unicode(tornado.escape.xhtml_escape(self.get_argument("image.path")),'utf8')
            imagetype = imghdr.what(client_img_path)
            acceptable_images = ['gif','jpeg','jpg','png','bmp']
            if imagetype in acceptable_images:
                print "Image included."
                fs_path = client_img_path + '.' + imagetype
                os.rename(client_img_path,fs_path)
                imgurl = '/static/' + fs_path[fs_path.rindex('uploads')::]
                pimgurl = '/static/thumb-' + fs_path[fs_path.rindex('uploads')::]
                pfs_path = fs_path[:fs_path.rindex('uploads'):] + 'thumb-' + fs_path[fs_path.rindex('uploads')::]

                #Open it in Python to check it out
                im =  Image.open(fs_path)
                img_width, img_height = im.size
                if ((img_width > 600) or (img_height > 600)):
                    im.thumbnail((600, 600), Image.ANTIALIAS)
                    im.save(pfs_path, "JPEG")
                else:
                    pimgurl = imgurl
    
            else:
                self.write("I'm sorry, but we can't recognize that image type.")
                self.imgurl = None
                self.pimgurl = None
                return -1
    
        except:
            print "No Image."
            client_img_path =  None
            img_path = None
            imgurl = None
            pimgurl = None


        client_chanlist=  self.get_argument("chanlist")
        chanlist = tornado.escape.json_decode(client_chanlist)
   
        if (len(chanlist) > 5):
            self.write("Sorry. You can only post to a maximum of 5 channels.")
            return -1

        if (len(chanlist) < 1):
            self.write("Sorry. You must post to at least 1 channel.")
            return -1

        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
       
        #Let's make sure you're allowed to post to this chan
        cur.execute("select subbedchan from usrsubs where usr = %s",[str(self.uid)])
        allowedchans = cur.fetchall()
        for a in range(len(allowedchans)):
            #Convert into StringList for later compare
            allowedchans[a] = str(allowedchans[a][0])

        cur.execute("select commentgroup from stories where url = %s",['client_url'])
        existing = cur.fetchall();
        if len(existing) > 0:
            commentgroupid = existing['commentgroup']
        else:   
            commentgroupid = 0;

        print "Submission in-progress"

        for i in range(len(chanlist)):
            print long(chanlist[i])
            if (str(chanlist[i]) in allowedchans):
                # ONLY POST IN ALLOWED CHANNELS, Even if they fake an ID        
                cur.execute("insert into stories (usr,title,url,text,name,location,imgurl,pimgurl,channame) values (%s,%s,%s,%s,%s,%s,%s,%s,(select name from channels where chanid = %s )  ) returning storyid;",[self.uid,client_title,client_url,client_text,self.name,chanlist[i],imgurl,pimgurl,chanlist[i]])
                storyid = cur.fetchone()['storyid']
                if (commentgroupid == 0):
                    #This means this is the first story under this URL
                    cur.execute("insert into commentgroups(url) values (%s) returning commentgroupid;",[client_url]);
                    commentgroupid = cur.fetchone()['commentgroupid']

                #now, commentgroupid is set, either way. 
                cur.execute("update stories set commentgroup = %s where storyid = %s;",[commentgroupid,storyid]);

            else:
                print "Not allowing chan" + str(chanlist[i])

        #EVERYONE posts into ALL-STORIES. EVERYTHING goes there! ;)
        cur.execute("insert into stories (usr,title,url,text,name,location,commentgroup,channame) values (%s,%s,%s,%s,%s,0,%s,(select name from channels where chanid = 0 )) returning storyid;",[self.uid,client_title,client_url,client_text,self.name,commentgroupid])
        storyid = cur.fetchone()['storyid']

        api = ApiClient('http://:rXVEdV8N2clyZ4@8hdj3.api.indextank.com')
        index = api.get_index('Pages')
	##Kill Indextank. Not used for more people
        ##index.add_document(str(storyid), { 'text': str(client_text), 'title': str(client_title), 'author': str(self.name), 'link': str(client_url) })

        db.commit()
        self.redirect("/stories/" + str(storyid))
    
        db.close()

class MsgHandler(BaseHandler):
    def get(self,client_recip):
        self.getvars()
        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute ("select postsperpage,newmail from usrs where usrid = %s",[self.uid])
        usrstuff = cur.fetchone()
        ppp = usrstuff['postsperpage']
        newmail = usrstuff['newmail']

        self.write(self.render_string('header.html',newmail=newmail,title='Send Lonava Message',uid=self.uid,user=self.name,ustatus=self.ustatus))

        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("select name from usrs where usrid = %s",[client_recip])
        recip_name=cur.fetchone()['name']
        self.write(self.render_string('sendmsgform.html',uid=self.uid,name=recip_name,recvid=client_recip))
        db.close()
        self.write(self.render_string('footer.html',topchans=retrChans(self.uid,True).topchans,ustatus=self.ustatus,uid=self.uid))

    def post(self,client_recv):
        if (self.getvars() == 0):
            return -1

        self.write(self.render_string('header.html',title='Send Lonava Message',newmail=0,uid=self.uid,user=self.name,ustatus=self.ustatus))
        try:
            client_title =  unicode(tornado.escape.xhtml_escape(self.get_argument("title")),'utf8')
        except:
            self.write("Sorry. All messages must have a title.")
            return -1

        try:
            client_text =  unicode(tornado.escape.xhtml_escape(self.get_argument("text")),'utf8')
        except:
            client_text = ' ' #I'm using a space, rather than None, so we don't need to error-check for null

        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute('insert into msgs (sendid,recvid,title,text) values (%s,%s,%s,%s)',[self.uid,client_recv,client_title,client_text])
        cur.execute("update usrs set newmail = newmail + 1 where usrid = %s",[client_recv]);
        db.commit()
        self.redirect("/")

        db.close()


class UserHandler(BaseHandler):
    def get(self,client_user):
        self.getvars()

        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("select * from usrs where usrid = %s",[client_user])
        userrow = cur.fetchone()


        cur.execute("select sum(pointchange) from storyvotes as a right join usrs as b on a.usr = b.usrid where usrid = %s",[client_user])
        storykarma =cur.fetchone()['sum'] 
        cur.execute("select sum(pointchange) from replyvotes as a right join usrs as b on a.usr = b.usrid where usrid = %s",[client_user])
        commentkarma = cur.fetchone()['sum']
        cur.execute("select aboutme,imgurl,pimgurl from usrs where usrid = %s",[client_user]);
        destusrstuff = cur.fetchone()
        if destusrstuff['aboutme'] is not None:
            rawme = destusrstuff['aboutme']
        else:
            rawme = " " 
        aboutme = autolink(markdown.markdown(unicode(gfm(rawme),'utf8')))
        imgurl = destusrstuff['imgurl']
        pimgurl= destusrstuff['pimgurl']


        cur.execute ("select postsperpage,newmail from usrs where usrid = %s",[self.uid])
        usrstuff = cur.fetchone()
        ppp = usrstuff['postsperpage']
        newmail = usrstuff['newmail']
        

        if (self.uid == client_user):
            isme = True
        else:
            isme = False

        self.write(self.render_string('header.html',newmail=newmail,title=userrow['name'] + ' Information',uid=self.uid,user=self.name,ustatus=self.ustatus))
        self.write(self.render_string('userpage.html',imgurl=imgurl,pimgurl=pimgurl,aboutme=aboutme,ustatus=self.ustatus,isme=isme,storykarma=storykarma,commentkarma=commentkarma,client_user=client_user,name=userrow['name'],url=userrow['url'],timeago=FancyDateTimeDelta(userrow['regtime']).format(),regtime=userrow['regtime'],state=userrow['state'],zipcode=userrow['zip'],hometown=userrow['hometown']))
        self.write(self.render_string('userform.html',userid=self.uid,aboutme=rawme,isme=isme))
        self.write(self.render_string('footer.html',topchans=retrChans(self.uid,True).topchans,ustatus=self.ustatus,uid=self.uid)) 
        db.close()
        


    def post(self,userid):
        if (self.getvars() == 0):
            return -1

        self.write(self.render_string('header.html',title='Submit',newmail=0,uid=self.uid,user=self.name,ustatus=self.ustatus))

        try:
            client_text =  unicode(tornado.escape.xhtml_escape(self.get_argument("text")),'utf8')
        except:
            client_text = " "

        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)

        if (str(userid) != str(self.uid)):
            self.write('You can only edit your own profile.')
            return -1

        try:
            client_img_path =  unicode(tornado.escape.xhtml_escape(self.get_argument("image.path")),'utf8')
            imagetype = imghdr.what(client_img_path)
            acceptable_images = ['gif','jpeg','jpg','png','bmp']
            if imagetype in acceptable_images:
                print "Image included."
                fs_path = client_img_path + '.' + imagetype
                os.rename(client_img_path,fs_path)
                imgurl = '/static/' + fs_path[fs_path.rindex('uploads')::]
                pimgurl = '/static/thumb-' + fs_path[fs_path.rindex('uploads')::]
                pfs_path = fs_path[:fs_path.rindex('uploads'):] + 'thumb-' + fs_path[fs_path.rindex('uploads')::]
                tfs_path = fs_path[:fs_path.rindex('uploads'):] + 'usrpics/' +   str(self.uid)  + '.png'
                #Open it in Python to check it out
                im =  Image.open(fs_path)
                img_width, img_height = im.size
                if ((img_width > 600) or (img_height > 600)):
                    im.thumbnail((600, 600), Image.ANTIALIAS)
                    im.save(pfs_path, "JPEG")
                else:
                    pimgurl = imgurl

                #Now save small preview person
                im.thumbnail((40,40), Image.ANTIALIAS)
                im.save(tfs_path, "PNG")
                                                        
    
            else:
                self.write("I'm sorry, but we can't recognize that image type.")
                self.imgurl = None
                self.pimgurl = None
                return -1
    
        except:
            print "No Image."
            client_img_path =  None
            img_path = None
            imgurl = None
            pimgurl = None
        if imgurl is not None:
            cur.execute("update usrs set aboutme = %s,imgurl = %s,pimgurl = %s where usrid = %s",[str(client_text),imgurl,pimgurl,long(self.uid)])
        else:
            cur.execute("update usrs set aboutme = %s where usrid = %s",[str(client_text),long(self.uid)])
        db.commit()
        self.redirect("/user/" + str(self.uid))
        db.close()




class SubscribeHandler(BaseHandler):
    def retrHTMLDivs(self,usrid):

        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)


        cur.execute("select count(subbedchan) as count,chanid,name,postable from usrsubs inner join channels on subbedchan = chanid where chanid in (select subbedchan from usrsubs where usr = %s) group by chanid,name,postable order by count desc",[usrid]);
        sublist = cur.fetchall()

        content = ""
        subbedlist = []


        #GET THE ALREADY SUBBED CHANS
        for a in sublist:
            subbedlist.append(a['chanid'])


        cur.execute("select * from chanclasses;")
        chanclasses = cur.fetchall()
        for cclass in chanclasses:
            content += """<ul class="grid_6">
            <li>
            <div class="clear"></div>
            <div class="single_wrap cclass">
            <div class="padder">
            <h2>""" + cclass['classname'] + "</h2>"

            cur.execute("select count(subbedchan) as count,chanid,name,chanclass from usrsubs right join channels on subbedchan = chanid where chanclass = %s group by chanid,name,chanclass order by count desc;",[cclass['chanclass']])
            chanlist = cur.fetchall()
            for chan in chanlist:
                if chan['chanid'] in subbedlist:
                    divclass = "clicked"
                else:
                    divclass = " "

                content += "<div class='channel " + divclass + "' channelnum='" + str(chan['chanid']) + "'> <p class = 'chan'> " + chan['name'] +  "     (" + str(chan['count']) + " subscribers) </p></div>";

            content += """</div>
            </div>
            </li>
            </ul>"""

        return content

    def get(self):
        if (self.getvars() == 0):
            return -1

        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute ("select postsperpage,newmail from usrs where usrid = %s",[self.uid])
        usrstuff = cur.fetchone()
        ppp = usrstuff['postsperpage']
        newmail = usrstuff['newmail']

        self.write(self.render_string('header.html',newmail=newmail,title='Modify Channel Subscriptions',uid=self.uid,user=self.name,ustatus=self.ustatus))


        self.write(self.render_string('subscribe.html',retrHTMLDivs=self.retrHTMLDivs,uid=self.uid))
        db.close()
        self.write(self.render_string('footer.html',topchans=retrChans(self.uid,True).topchans,ustatus=self.ustatus,uid=self.uid))

    def post(self):
        if (self.getvars() == 0):
            return -1
        
        client_chanlist= self.get_argument("chanlist")
        chanlist = tornado.escape.json_decode(client_chanlist)
        print chanlist
        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("delete from usrsubs where usr = %s",[self.uid])    
        for i in range(len(chanlist)):
            print "Subscribing to " + str(i) + " : " + str(chanlist[i])
            cur.execute("insert into usrsubs (usr,subbedchan) values (%s,%s)",[self.uid,str(chanlist[i])])
            
        db.commit()
        self.redirect("/")

        db.close()

class SearchHandler(BaseHandler):
    def get(self, client_search = ""):
        self.getvars()

        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")

        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute ("select postsperpage,newmail from usrs where usrid = %s",[self.uid])
        usrstuff = cur.fetchone()
        ppp = usrstuff['postsperpage']
        newmail = usrstuff['newmail']

        self.write(self.render_string('header.html',newmail=newmail,title='Add Comment',uid=self.uid,user=self.name,ustatus=self.ustatus))
        if client_search is None:
            client_search = unicode(tornado.escape.xhtml_escape(self.get_argument("search")),'utf8')
        if client_search is None:
            self.write("Invalid Search.")
            return -1

            

        api = ApiClient('http://:rXVEdV8N2clyZ4@8hdj3.api.indextank.com')
        index = api.get_index('Pages')
        index.add_function(0, "pow(relevance,8) * boost(1) * (-age)")
        print client_search
        sresults = index.search(client_search, scoring_function=0)

        count = 0
        for result in sresults['results']:
            if count < ppp:
                story = LonStory()
                story.FromStoryID(long(result['docid']))
                self.write(story.GetHTMLTitle(self))
            count += 1

        db.close()
        self.write(self.render_string('footer.html',topchans=retrChans(self.uid,True).topchans,ustatus=self.ustatus,uid=self.uid))


class SHandler(BaseHandler):
    def post(self):
        client_search = unicode(tornado.escape.xhtml_escape(self.get_argument("search")),'utf8')
        if client_search is None:
            self.write("Invalid Search.")
            return -1
        self.redirect("http://lonava.com/search/" + client_search)

class NotFoundHandler(BaseHandler):
    def get(self,foo):
        self.getvars()
        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        client_usrid = tornado.escape.xhtml_escape(self.uid)
        cur.execute ("select postsperpage,newmail from usrs where usrid = %s",[self.uid])
        usrstuff = cur.fetchone()
        ppp = usrstuff['postsperpage']
        newmail = usrstuff['newmail']
        db.close()
        self.write(self.render_string('header.html',newmail=newmail,title='404',uid=self.uid,user=self.name,ustatus=self.ustatus))
        self.write(self.render_string('404.html'))
        self.write(self.render_string('footer.html',topchans=retrChans(self.uid,True).topchans,ustatus=self.ustatus,uid=self.uid))


class SaveHandler(BaseHandler):
    def get(self,storyid):
        if (self.getvars() == 0):
            return -1

        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("insert into savedstories (usr,savedstory) values (%s,%s)",[self.uid,storyid])
        db.commit()
        db.close()
        self.redirect("/stories/" + str(storyid))

class UserSavedHandler(BaseHandler):
   def get(self):
        self.getvars()

        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        client_usrid = tornado.escape.xhtml_escape(self.uid)
        cur.execute ("select postsperpage,newmail from usrs where usrid = %s",[self.uid])
        usrstuff = cur.fetchone()
        ppp = usrstuff['postsperpage']
        newmail = usrstuff['newmail']

        self.write(self.render_string('header.html',newmail=newmail,title='Saved Stories',uid=self.uid,user=self.name,ustatus=self.ustatus))

        cur.execute ("select * from savedstories where usr = %s limit %s;",[self.uid,ppp])
        rows = cur.fetchall()
        for storyrow in rows:
            storyid = storyrow['savedstory']
            story = LonStory()
            story.FromStoryID(storyid)
            self.write(story.GetHTMLTitle(self))
    
        db.close()
        self.write(self.render_string('footer.html',topchans=retrChans(self.uid,True).topchans,ustatus=self.ustatus,uid=self.uid))

class ReplyHandler(BaseHandler):
    def get(self, reply_id):
        self.getvars()

        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")

        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute ("select postsperpage,newmail from usrs where usrid = %s",[self.uid])
        usrstuff = cur.fetchone()
        ppp = usrstuff['postsperpage']
        newmail = usrstuff['newmail']

        self.write(self.render_string('header.html',newmail=newmail,title='Add Comment',uid=self.uid,user=self.name,ustatus=self.ustatus))
        reply = LonReply()
        reply.FromReplyID(reply_id)

        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("select * from stories where commentgroup = %s;",[reply.commentgroup])
        storyid = cur.fetchone()['storyid'] 

        self.write("<ul class='grid_11'><li>")
        self.write(reply.GetHTML(self))
        self.write("</li></ul")

        self.write(self.render_string('replyform.html',storyid=storyid,uid=self.uid,commentgroup=reply.commentgroup,parent=reply_id,ustatus=self.ustatus))

        db.close()
        self.write(self.render_string('footer.html',topchans=retrChans(self.uid,True).topchans,ustatus=self.ustatus,uid=self.uid))

class EditReplyHandler(BaseHandler):
    def get(self, reply_id):
        self.getvars()

        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")

        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute ("select postsperpage,newmail from usrs where usrid = %s",[self.uid])
        usrstuff = cur.fetchone()
        ppp = usrstuff['postsperpage']
        newmail = usrstuff['newmail']

        self.write(self.render_string('header.html',newmail=newmail,title='Add Comment',uid=self.uid,user=self.name,ustatus=self.ustatus))
        reply = LonReply()
        reply.FromReplyID(reply_id)

        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("select * from stories where commentgroup = %s;",[reply.commentgroup])
        storyid = cur.fetchone()['storyid']

        self.write(reply.GetHTML(self))
        self.write(self.render_string('editreplyform.html',replyid=reply.replyid,defaulttext=reply.text,edit=reply_id,storyid=storyid,uid=self.uid,commentgroup=reply.commentgroup,parent=reply_id))
        db.close()
        self.write(self.render_string('footer.html',topchans=retrChans(self.uid,True).topchans,ustatus=self.ustatus,uid=self.uid))


    def post(self,replyid):
        if (self.getvars() == 0):
            return -1

        self.write(self.render_string('header.html',title='Submit',newmail=0,uid=self.uid,user=self.name,ustatus=self.ustatus))

        try:
            client_text =  unicode(tornado.escape.xhtml_escape(self.get_argument("text")),'utf8')
        except:
            self.write("You cannot edit a post to be empty.")
            return -1

        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute ("select usr from replies where replyid = %s;",[replyid])
        origposter = cur.fetchone()['usr']
        if (str(origposter) != str(self.uid)):
            self.write('Only the original Poster can edit a reply.')
            return -1

        cur.execute("update replies set text = %s, lastedit = now() where replyid = %s",[client_text,replyid])
        cur.execute("select * from stories where commentgroup = (select commentgroup from replies where replyid = %s)",[replyid])
        storyid = cur.fetchone()['storyid']
        db.commit()
        self.redirect("/stories/" + str(storyid))
        db.close()


class LoginHandler(BaseHandler):
    def get(self):
        self.getvars()
        self.write(self.render_string('header.html',newmail=0,title='Login',uid=self.uid,user=self.name,ustatus=self.ustatus))
        self.write(self.render_string('loginform.html'))
        self.write(self.render_string('footer.html',topchans=retrChans(self.uid,True).topchans,ustatus=self.ustatus,uid=self.uid))

    def post(self):
        self.getvars()
        client_email =  unicode(tornado.escape.xhtml_escape(self.get_argument("email")),'utf8')
        client_pass =  unicode(tornado.escape.xhtml_escape(self.get_argument("pass")),'utf8')
        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("select usrid,password from usrs where upper(email) = upper(%s);",[client_email])
        row = cur.fetchone()
        try:
            if bcrypt.hashpw(client_pass, row['password']) != row['password']:
                lookup = False
                print "Fail"
            else:
                lookup = True
                print "Login Successful."
        except:
            self.write(self.render_string('header.html',newmail=0,title='Login\
                                          Difficulty',uid=self.uid,user=self.name,ustatus=self.ustatus))
            self.write("I'm sorry, we don't have that email/password combo on file.")
            return -1

        if lookup == False:
            self.write(self.render_string('header.html',newmail=0,title='Login Difficulty',uid=self.uid,user=self.name,ustatus=self.ustatus))
            self.write("I'm sorry, we don't have that email/password combo on file.")
            return -1
        else:
            usrid = str(row['usrid'])
            self.write("Match for user " + usrid )
            self.set_secure_cookie("usrid", usrid)
            self.uid = usrid;
            print usrid
            cur.execute('select status,name FROM usrs WHERE usrid = %s;', [usrid]) 
            row = cur.fetchone()
            self.set_secure_cookie("name", row['name'])
            self.set_secure_cookie("ustatus", str(row['status']))
            self.name = row['name']
            self.ustatus = row['status'] 

            #set cookie with hidden story votes
            cur.execute('select * from storyvotes where usr = %s order by storyvoteid desc limit 100;',[self.uid])
            rows = cur.fetchall()
            cookiearry = "["
            for row in rows:
                cookiearry = cookiearry + '"' + "storyid||" + str(row['story']) + "||" + str(row['pointchange']) + '",'

            #set cookie for replies
            cur.execute('select * from replyvotes where usr = %s order by replyvoteid desc limit 100;',[self.uid])
            rows = cur.fetchall()
            for row in rows:
                cookiearry = cookiearry + '"' + "replyid||" + str(row['reply']) + "||" + str(row['pointchange']) + '",'
                
            cookiearry = cookiearry + '"storyid||0||1"]'
            print cookiearry
    
            self.set_cookie("hidden-post-votes",cookiearry)
            self.redirect("/")

        db.close()

class VerifyHandler(BaseHandler):
    def get(self,user = -1):
        self.getvars()  
        if user == -1:
                user = self.uid
        self.redirect("https://lonava.com/verify/" + user)

class LogoutHandler(BaseHandler):
    def get(self):
        self.write(self.render_string('header.html',newmail=0,title='Logout',uid='0',user='Unregistered User',ustatus=0)) 
        self.clear_cookie("user")
        self.clear_cookie("usrid")
        self.clear_cookie("name")
        self.clear_cookie("ustatus")
        self.clear_cookie("hidden-post-votes")
        self.write(self.render_string('nowloggedout.html'))
        self.write(self.render_string('footer.html',topchans=retrChans(0,True).topchans,ustatus=0,uid=0))

class retrChans(object):
    def __init__(self,usrid,showAll):
        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        if (usrid == -1 ):
            #Ret for all users
            cur.execute("select count(subbedchan) as count,chanid,name,chanclass from usrsubs right join channels on subbedchan = chanid group by chanid,name order by count desc;")
        else:
            if showAll == False:        
                cur.execute("select count(subbedchan) as count,chanid,name,postable from usrsubs inner join channels on subbedchan = chanid where chanid in (select subbedchan from usrsubs where usr = %s) and postable = 'True' group by chanid,name,postable order by count desc",[usrid]);
            else:
                cur.execute("select count(subbedchan) as count,chanid,name,postable from usrsubs inner join channels on subbedchan = chanid where chanid in (select subbedchan from usrsubs where usr = %s) group by chanid,name,postable order by count desc",[usrid]);

        self.chanlist = cur.fetchall()  
        count = 0
        topchans = ""
        for chan in self.chanlist:
            if count < 10:
                topchans += "<a href=http://lonava.com/channel/" + str(chan['chanid']) + ">" + chan['name']+" (" + str(chan['count']) + ")</a><br>"
        self.topchans = topchans

        db.close()
    
class JSONChannelListHandler(BaseHandler):
    def get(self):
        rows = retrChans(-1,True).chanlist
        jsonrep = tornado.escape.json_encode(rows)
        self.write(jsonrep)


class myJSONChannelListHandler(BaseHandler):
    def get(self):
        self.getvars()
        rows = retrChans(self.uid,False).chanlist
        jsonrep = tornado.escape.json_encode(rows)
        self.write(jsonrep)

class RegisterHandler(BaseHandler):
    def get(self):
        self.getvars()
        self.write(self.render_string('header.html',newmail=0,title='Register for an account',uid=self.uid,user=self.name,ustatus=self.ustatus))
        self.write(self.render_string('registerform.html'))
        self.write(self.render_string('footer.html',topchans=retrChans(self.uid,True).topchans,ustatus=self.ustatus,uid=self.uid))
    def post(self):
        self.getvars()
        self.write(self.render_string('header.html',newmail=0,title='Register for an account',uid=self.uid,user=self.name,ustatus=self.ustatus))
        client_newuser =  unicode(tornado.escape.xhtml_escape(self.get_argument("name")),'utf8')
        client_newpass =  unicode(tornado.escape.xhtml_escape(self.get_argument("pass")),'utf8')
        client_newpass2 =  unicode(tornado.escape.xhtml_escape(self.get_argument("pass2")),'utf8')
        client_newemail = unicode(tornado.escape.xhtml_escape(self.get_argument("email")),'utf8')

        if client_newpass != client_newpass2:
            self.write("I'm sorry, your passwords don't match.") 
            return

        db = psycopg2.connect("dbname='lonava' user='youruser' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        #Make sure this email is unused
        cur.execute("select count(*) as count from usrs where upper(email) = upper(%s);",[client_newemail])
        count = cur.fetchone()['count']

        if count != 0:
            self.write("I'm sorry, this email address has already been used.")  
            return
        else:
            hashed = bcrypt.hashpw(client_newpass, bcrypt.gensalt())
            cur.execute("insert into usrs (name,password,email) values (%s,%s,%s) returning usrid;",[client_newuser,hashed,client_newemail])
            ## Copy in Default Channels
            newid = cur.fetchone()[0]
    
            #defaultchans = ({"usr":str(newid), "chan":"1"})    
            cur.execute("select subbedchan from usrsubs where usr = 0")
            rows = cur.fetchall()
            for row in rows:
                cur.execute("insert into usrsubs(usr,subbedchan) values (%s,%s)",[newid,row['subbedchan']])
            self.write("User# " + str(newid) + " Created. You are now logged in. <br><a href='/' class='ul'>Return to main page</a>.")  
    
            #Go Ahead and Log you in by default

            usrid = str(newid)
            self.set_secure_cookie("usrid", usrid)
            cur.execute('select name FROM usrs WHERE usrid = %s;', [usrid])
            row = cur.fetchone()
            self.set_secure_cookie("name", row['name'])
            self.name = row['name']

            #set cookie with hidden story votes
            cur.execute('select * from storyvotes where usr = %s order by storyvoteid desc limit 100;',[self.uid])
            rows = cur.fetchall()
            cookiearry = "["
            for row in rows:
                cookiearry = cookiearry + '"' + "storyid||" + str(row['story']) + "||" + str(row['pointchange']) + '",'

            #set cookie for replies
            cur.execute('select * from replyvotes where usr = %s order by replyvoteid desc limit 100;',[self.uid])
            rows = cur.fetchall()
            for row in rows:
                cookiearry = cookiearry + '"' + "replyid||" + str(row['reply']) + "||" + str(row['pointchange']) + '",'

            cookiearry = cookiearry + '"storyid||0||1"]'

            self.set_cookie("hidden-post-votes",cookiearry)
            self.redirect("/")



            db.commit() 
            db.close()
            self.redirect("/")





def main():
    tornado.options.parse_command_line()
    # timeout in seconds
    timeout = 10
    socket.setdefaulttimeout(timeout)

    settings = {
        "static_path": os.path.join(os.path.dirname(__file__), "static"),
        "cookie_secret": "9b90a85cfe46cad5ec136ee44a3fa332",
        "login_url": "/login",
        "xsrf_cookies": True,
    }
    application = tornado.web.Application([
        (r"/" ,PageHandler),
        (r"/login", LoginHandler),
        (r"/logout", LogoutHandler),
        (r"/register", RegisterHandler),
        (r"/submit", SubmitHandler),
        (r"/poststory", SubmitHandler),
        (r"/stories/([0-9]+)", StoryHandler),
        (r"/reply/([0-9]+)", ReplyHandler),
        (r"/votestory", VoteStoryHandler),
        (r"/votereply", VoteReplyHandler),
        (r"/getchannels", JSONChannelListHandler),
        (r"/getmychannels", myJSONChannelListHandler),
        (r"/subscribe", SubscribeHandler),
        (r"/new", NewHandler),
        (r"/newest/([0-9]+)", NewHandler),
        (r"/user/([0-9]+)", UserHandler),
        (r"/getusrposts/([0-9]+)", UserPostsHandler),
        (r"/channel/([0-9]+)", ChanPostsHandler),
        (r"/chan/([0-9]+)/([0-9]+)", ChanPostsHandler),
        (r"/getusrcomments/([0-9]+)", UserCommentsHandler),
        (r"/getusrsaved", UserSavedHandler),
        (r"/msg/([0-9]+)", MsgHandler),
        (r"/mymsg", MyMsgHandler),
        (r"/save/([0-9]+)", SaveHandler),
        (r"/editstory/([0-9]+)", EditStoryHandler),
        (r"/editreply/([0-9]+)", EditReplyHandler),
        (r"/postreply/([0-9]+)", StoryHandler),
        (r"/postuser/([0-9]+)", UserHandler),
        (r"/page/([0-9]+)", PageHandler),
        (r"/verify/([0-9]+)", VerifyHandler),
        (r"/newchan", NewChanHandler),
        (r"/repost/([0-9]+)", RepostHandler),
        (r"/search/([^/]+)", SearchHandler),
        (r"/s", SHandler),
        (r"/(.*)", NotFoundHandler),


    ], **settings)
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
