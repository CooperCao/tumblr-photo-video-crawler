# tumblr-photo-video-crawler #

## 项目说明
本文利用Python2.7爬取了Tumblr博客空间的图片及视频。以用户zerohd4869的[Tumblr博客](https://zerohd4869.tumblr.com)为示例，借助Chrome的DevTools工具解析页面，基于HTTP框架Requests下，通过Tumblr API获得XML资源数据，使用Queue和Threading等技术实现该博客空间资源的多线程并发下载。具体介绍及使用方法可在本人[CSDN博客](http://blog.csdn.net/weixin_37325825/article/details/73769937)查看。

## 项目依赖
os, sys, requests, xmltodict, six.moves, threading, re, json

## 项目运行
```
$ pip install -r requirements.txt
$ python tumblr-photo-video-crawler.py
```

