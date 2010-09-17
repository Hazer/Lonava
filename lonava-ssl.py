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
from sdk import *
from xml.dom import minidom
import urllib2
import urllib
import sys
from PIL import Image
from urlparse import urlparse
from tornado.options import define, options

import re
try: 
   from hashlib import md5 as md5_func
except ImportError:
   from md5 import new as md5_func
import NofollowExtension


define("port", default=400, help="run on the given port", type=int)

class payment:
    def __init__(self):
            self.credit_card = {
            'amt' : '0.00'
            }
    def loadup(self,ccn):
        self.credit_card = ccn


    def do_authorization(self):
        sale = do_direct_payment('Authorization', **self.credit_card)
        try:
            details = get_transaction_details(sale.TRANSACTIONID)
        except:
            print "I'm sorry, I could not authorize that Credit Card number and address"

        if [ details.success == 1 ]:
                print "Credit Card Authorized successfully"

        else:
                print "There was an error authorize your Credit Card number and address"

        return details.success

    def do_sale(self):
       sale = do_direct_payment('Sale', **self.credit_card)
       try:
           details = get_transaction_details(sale.TRANSACTIONID)
       except:
           print "I'm sorry, I could not process that Credit Card number and address"

       if [ details.success == 1 ]:
           #CCN Processed
           print "Credit Card Processed successfully" 

       else:
           print "There was an error processing your Credit Card number and address"

       return details.success



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


class VerifyHandler(BaseHandler):
    def get(self,client_user):
        self.getvars()

        db = psycopg2.connect("dbname='lonava' user='YOURUSER' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        #        client_usrid = tornado.escape.xhtml_escape(self.uid)
        cur.execute ("select postsperpage,newmail from usrs where usrid = %s",[self.uid])
        usrstuff = cur.fetchone()
        ppp = usrstuff['postsperpage']
        newmail = usrstuff['newmail']

        self.write(self.render_string('header.html',newmail=False,title=' ',uid=self.uid,user=self.name,ustatus=self.ustatus))
        self.write(self.render_string('ccn.html',ustatus=self.ustatus,uid=self.uid))
        self.write(self.render_string('footer.html',topchans=retrChans(self.uid,True).topchans,ustatus=self.ustatus,uid=self.uid))
        db.commit()
        db.close()
        
    def post(self,storyid):
        self.getvars()
        self.write(self.render_string('header.html',newmail=False,title=' ',uid=self.uid,user=self.name,ustatus=self.ustatus))

        try:
            cc_first_name =  tornado.escape.xhtml_escape(self.get_argument("credit_card[first_name]"))
            cc_last_name =   tornado.escape.xhtml_escape(self.get_argument("credit_card[last_name]"))

            cc_address1 = tornado.escape.xhtml_escape(self.get_argument("credit_card[address-1]"))
            try:
                cc_address2 = tornado.escape.xhtml_escape(self.get_argument("credit_card[address-2]"))
            except:
                cc_address2 = " "
            cc_city= tornado.escape.xhtml_escape(self.get_argument("credit_card[city]"))
            cc_state= tornado.escape.xhtml_escape(self.get_argument("credit_card[state]"))
            cc_zip = tornado.escape.xhtml_escape(self.get_argument("credit_card[zip]"))


            cc_type     =   tornado.escape.xhtml_escape(self.get_argument("credit_card[card_type]"))
            cc_number     =   tornado.escape.xhtml_escape(self.get_argument("credit_card[number]"))
            cc_cvv     =   tornado.escape.xhtml_escape(self.get_argument("credit_card[verification_value]"))
            cc_month     =   tornado.escape.xhtml_escape(self.get_argument("credit_card[month]"))
            cc_year =   tornado.escape.xhtml_escape(self.get_argument("credit_card[year]"))
        except:
            print "Not all of the information on the previous page was filled in. Please try again."
            return -1

        sub_card = {
            'amt': '1.05',
            'creditcardtype': cc_type,
            'acct': cc_number,
            'expdate': cc_month + cc_year,
            'cvv2': cc_cvv,
            'firstname': cc_first_name,
            'lastname': cc_last_name,
            'street': cc_address1,
            'city': cc_city,
            'state': cc_state,
            'zip': cc_zip,
            'countrycode': 'US',
            'currencycode': 'USD',
        }
        payme = payment()
        payme.loadup(sub_card)
        try:
            success = payme.do_authorization()
        except:
            self.write("There was an error authorizing payment from your credit card; It came back as declined from the Credit Card Processor. Can you make sure all fields are correct, including address?")
            return -1
        if success != 1:
            self.write("There was an error authorizing payment from your credit card. Please make sure that all fields are correct, including address")
        else:

            wsusername = ['1','2']
            wspassword = ['1','2']
            wsusername[0] = ""     #PROD
            wspassword[0] = ""

            wsusername[1] = ""    #Sandbox
            wspassword[1] = ""


            sandbox = 0  # 1 for sandbox 0 for PROD
            qstring = "<query><user>" + wsusername[sandbox] +"</user><pass>" + wspassword[sandbox] + "</pass><function>age</function><output-type>4.3</output-type>"
            qstring += "<client-side>"
            qstring += "<first_name>" + cc_first_name + "</first_name>"
            qstring += "<last_name>" + cc_last_name + "</last_name>"
            qstring += "</client-side>"
            qstring += "<fn>" + cc_first_name + "</fn>"
            qstring += "<ln>" + cc_last_name+ "</ln>"
            qstring += "<bill>"
            qstring += "<addr>" + cc_address1 + "," + cc_address2 + "</addr>"
            qstring += "<city>" + cc_city + "</city>"
            qstring += "<state>" + cc_state + "</state>"
            qstring += "<zip>" + cc_zip + "</zip>"
            qstring += "</bill>"
            qstring += "</query>"

            params = urllib.urlencode({
            'query': qstring
            })

            namespace = "http://idresponse.com/idr"
            url = urllib2.urlopen('https://idresponse.com:6650/gateway.php',params)

            dom = minidom.parse(url)

            nodes = []
            for node in dom.getElementsByTagNameNS(namespace,'idr-message'):
                status_node = node.getElementsByTagName('status')
                message_mode = node.getElementsByTagName('message')

            verify_error = status_node[0].firstChild.nodeValue
            print "Lookup Error: " + str(verify_error)
            #verify_error of 0 is success
            #verify_error of 1 is failure.
            if long(verify_error) == 0:        
                #GREAT! Card authed, You match. ACTUALLY charge the card.
                print "Ready to update db."
                salesuccess = payme.do_sale()
                print salesuccess
                if salesuccess == 1:
                    db = psycopg2.connect("dbname='lonava' user='YOURUSER' host='localhost' password='YOURPASS'")
                    cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
                    cur.execute ("update usrs set name = %s,status = 1 where usrid = %s;", [cc_first_name + " " + cc_last_name,self.uid])
                    cur.execute ("select * from usrs where usrid = %s",[self.uid])
                    row = cur.fetchone()
                    name = row['name']
                    self.write("""<ul class="grid_11">
                               <li>
                               <div class="clear"></div>
                               <div class="single_wrap">
                               <div class="padder"><p>User """ + self.uid + ", Named " + cc_first_name + " " + cc_last_name + """ has been verified. <br> Your account has been set to Verified, and you are free to post! Enjoy!</p> </div>
                               </div>
                               </li>
                               </ul>""")
                    self.set_secure_cookie("name", cc_first_name + " " + cc_last_name)
                    self.set_secure_cookie("ustatus","1")
                    self.name = row['name']
                    self.ustatus = row['status']

                    db.commit()
                    db.close()
                else:
                    self.write("Your address did validate successfully, but the authorization charge on your credit card was declined.")
                    self.write("Please verify the card information, and try again.")

            if long(verify_error) == 1:
                self.write("<p>I'm sorry to say it, but it looks like I can't verify you right now. <br>")
                self.write("While your Credit Card is valid, I'm not able to find a match on your identity.<br>")
                self.write("There's a few things that could cause this, that we can check-")
                self.write("<ul><li>Please be sure that you have included all relevent information, such as apartment number.<br>")
                self.write("<li> If you have not been paying bills at this address, it may impossible to verify you automatically. Please email <a href='mailto:support@lonava.com'>support@lonava.com</a> and we'll try to work something out.</li>")
                self.write("</ul>")
                self.write("Your card has not been charged; There was an authorization charge placed to test to see if the card was valid, but your bank will let it expire normally. No money has changed hands.<br>")
                self.write("<br>")

        self.write(self.render_string('footer.html',topchans=retrChans(self.uid,True).topchans,ustatus=self.ustatus,uid=self.uid))


class MainHandler(BaseHandler):
    def get(self):
        self.redirect("http://lonava.com")

class ThanksHandler(BaseHandler):
        def get(self):
            self.getvars()
            self.write(self.render_string('header.html',newmail=False,title=' ',uid=self.uid,user=self.name,ustatus=self.ustatus))
            self.write(self.render_string('thanks.html',newmail=False,title=' ',uid=self.uid,user=self.name,ustatus=self.ustatus))
            self.write(self.render_string('footer.html',topchans=retrChans(self.uid,True).topchans,ustatus=self.ustatus,uid=self.uid))

class retrChans(object):
    def __init__(self,usrid,showAll):
        db = psycopg2.connect("dbname='lonava' user='YOURUSER' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        if (usrid == -1 ):
            #Ret for all users
            cur.execute("select count(subbedchan) as count,chanid,name from usrsubs right join channels on subbedchan = chanid group by chanid,name order by count desc;")
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
    

def main():
    tornado.options.parse_command_line()
    settings = {
        "static_path": os.path.join(os.path.dirname(__file__), "static"),
        "cookie_secret": "9b90a85cfe46cad5ec136ee44a3fa332",
        "login_url": "/login",
        "xsrf_cookies": False,
    }
    application = tornado.web.Application([
        (r"/verify/([0-9]+)", VerifyHandler),
        (r"/", MainHandler),
        (r"/thanks", ThanksHandler),
    ], **settings)
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
