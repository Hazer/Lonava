#!/usr/bin/python
import time
import datetime
import psycopg2
import psycopg2.extras
import os

db = psycopg2.connect("dbname='lonava' user='lonuser' host='localhost' password='YOURPASS'")
cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
print "Generating Count"
cur.execute  ("select count(*) as count from (select distinct on (commentgroup) * from storygroup ) as bar")
totalrows = cur.fetchone()['count']
print "There are " + str(totalrows) + " stories in Lonava."
looppasses = 1 + (totalrows / 40000)
print "A total of " + str(looppasses) + " story sitemaps"
date1  = datetime.datetime.now().isoformat()
datenow = date1[0:date1.find(".")] + "+00:00"
print datenow


startat = 0 
sitemapindex = open('/usr/local/lonava/static/sitemap_index.xml', 'w')
sitemapindex.write("""<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9 http://www.sitemaps.org/schemas/sitemap/0.9/siteindex.xsd" xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<sitemap>
<loc>http://lonava.com/static/sitemap-0.xml</loc>
<lastmod>""" + datenow + """</lastmod>
</sitemap>
""")

 
for i in range(looppasses):
    sitemap_path = "/usr/local/lonava/static/sitemap-" + str(i + 1) + ".xml"
    sitemap = open(sitemap_path, 'w')   
    sitemapindex.write("<sitemap>")
    sitemapindex.write("<loc>http://lonava.com/static/sitemap-" + str(i + 1) + ".xml</loc>\n")
    sitemapindex.write("<lastmod>" + datenow +  "</lastmod>\n")
    sitemapindex.write("</sitemap>\n")
    cur.execute("create temporary table mystories (like stories);")
    cur.execute("alter table mystories add column ord bigserial;")
    cur.execute("alter table mystories add column  cachedreplycount bigint;")
    cur.execute("insert into mystories(lastedit,pimgurl,imgurl,usr,storytime,title,url,text,name,score,commentgroup,storyid,location,cachedreplycount) select lastedit,pimgurl,imgurl,usr,storytime,title,url,text,name,score,commentgroup,storyid,location,cachedreplycount from storygroup where location in (select subbedchan from usrsubs) order by storyid asc;",)
    cur.execute("select * from (select distinct on (commentgroup) * from (select *,(1.0 + score + (cachedreplycount / 10)) / (1.0 + (select count(*) from mystories) - ord) as rank from mystories) as foo) as bar order by storyid asc  offset %s limit %s;",[startat,39999])


    sitemap.write("""<?xml version="1.0" encoding="UTF-8"?>\n""")
    sitemap.write("""<urlset xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9 http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd" xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n""")
    print "Starting file " + str(i) + "; startat = " + str(startat) + " ; endat " + str(startat + 39999)
    startat = startat + 40000
    rows = cur.fetchall()
    cur.execute("drop table mystories")
    print "Writing " + str(len(rows)) + " rows to " + sitemap_path
    for row in rows:
        url = 'http://lonava.com/stories/' + str(row['storyid'])
        date = row['storytime'] + datetime.timedelta(days=2)
        datestr = date.isoformat()
        datecur = datestr[0:datestr.find(".")] + "+00:00"
        sitemap.write("<url>\n")
        sitemap.write("<loc>" + url + "</loc>\n")
        sitemap.write("<lastmod>" + datecur + "</lastmod>\n")
        sitemap.write("<changefreq> monthly </changefreq>\n")   
        sitemap.write("<priority> .5 </priority>\n")
        sitemap.write("</url>\n")
    sitemap.write("</urlset>\n")
    sitemap.close()

#### DONE WITH STORIES, now do USERS

cur.execute  ("select count(*) from usrs as count")
totalrows = cur.fetchone()['count']
print "There are " + str(totalrows) + " usrs of Lonava."
looppasses = 1 + (totalrows / 40000)
print "A total of " + str(looppasses) + " usr sitemaps"
date1  = datetime.datetime.now().isoformat()
datenow = date1[0:date1.find(".")] + "+00:00"
i = 0
startat = 0
for i in range(looppasses):
    sitemap_path = "/usr/local/lonava/static/sitemap-usr-" + str(i + 1) + ".xml"
    sitemap = open(sitemap_path, 'w')
    sitemapindex.write("<sitemap>")
    sitemapindex.write("<loc>http://lonava.com/static/sitemap-usr-" + str(i + 1) + ".xml</loc>\n")
    sitemapindex.write("<lastmod>" + datenow +  "</lastmod>\n")
    sitemapindex.write("</sitemap>\n")
    cur.execute ("select * from usrs limit %s offset %s",[startat + 39999,startat])


    sitemap.write("""<?xml version="1.0" encoding="UTF-8"?>\n""")
    sitemap.write("""<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n""")

    startat = startat + 40000
    rows = cur.fetchall()
    for row in rows:
        url = 'http://lonava.com/user/' + str(row['usrid'])
        date = row['regtime'] + datetime.timedelta(days=2)
        datestr = date.isoformat()
        datecur = datestr[0:datestr.find(".")] + "+00:00"
        sitemap.write("<url>\n")
        sitemap.write("<loc>" + url + "</loc>\n")
        sitemap.write("<lastmod>" + datecur + "</lastmod>\n")
        sitemap.write("<changefreq> monthly </changefreq>\n")
        sitemap.write("<priority> .6 </priority>\n")
        sitemap.write("</url>\n")
    sitemap.write("</urlset>\n")
    sitemap.close()

sitemapindex.write("</sitemapindex>\n")
sitemapindex.close()
print "Notifying Bing"
cmd = 'curl http://www.bing.com/webmaster/ping.aspx?siteMap=http://lonava.com/static/sitemap_index.xml > /dev/null'
os.system(cmd)
print "Notifying Google"
cmd = 'curl http://www.google.com/webmasters/sitemaps/ping?sitemap=http://lonava.com/static/sitemap_index.xml > /dev/null'
os.system(cmd)
