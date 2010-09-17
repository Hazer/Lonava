import urlnorm    #Modified url verification lib
import feedparser
import datetime
import time

#feed = "http://feeds.feedburner.com/blogspot/MKuf"
feed = "http://online.wsj.com/article/SB10001424052748703447004575449490162986822.html?mod=rss_Technology"
url = urlnorm.normalize(str(feed))
print feed
print url
