# -*- coding: utf-8 -*-

import os
import sys
import requests
import xmltodict
from six.moves import queue as Queue
from threading import Thread
import re
import json

reload(sys)  
sys.setdefaultencoding('utf8')  

# 设置请求超时时间
TIMEOUT = 10

# 尝试次数
RETRY = 5

# 分页请求的起始点
START = 0

# 每页请求个数
MEDIA_NUM = 50

# 并发线程数
THREADS = 10

# 是否下载图片
IS_DOWNLOAD_IMG=True

#是否下载视频
IS_DOWNLOAD_VIDEO=True

# 网页下载器，使用Threading模块创建线程，直接从threading.Thread继承，然后重写__init__方法和run方法
class DownloadWorker(Thread):
    def __init__(self, queue, proxies=None):
        Thread.__init__(self)
        self.queue = queue
        self.proxies = proxies

    #线程创建后直接运行run函数
    def run(self):
        while True:
            # 从任务队列中获取一条任务
            medium_type, post, target_folder = self.queue.get()
            # 将该任务含有的三个信息传入download
            self.download(medium_type, post, target_folder)
            self.queue.task_done()

    def download(self, medium_type, post, target_folder):
        try:
            # 获取具体资源的url
            medium_url = self._handle_medium_url(medium_type, post)
            if medium_url is not None:
                self._download(medium_type, medium_url, target_folder)
        except TypeError:
            pass

    def _handle_medium_url(self, medium_type, post):
        try:
            if medium_type == "photo":
                # 处理第一张图片
                return post["photo-url"][0]["#text"]

            if medium_type == "video":
                video_player = post["video-player"][1]["#text"]
                hd_pattern = re.compile(r'.*"hdUrl":("([^\s,]*)"|false),')
                hd_match = hd_pattern.match(video_player)
                try:
                    if hd_match is not None and hd_match.group(1) != 'false':
                        return hd_match.group(2).replace('\\', '')
                except IndexError:
                    pass
                pattern = re.compile(r'.*src="(\S*)" ', re.DOTALL)
                match = pattern.match(video_player)
                if match is not None:
                    try:
                        return match.group(1)
                    except IndexError:
                        return None
        except:
            raise TypeError("找不到正确的下载URL "
                            "请到邮箱"
                            "1228868719@qq.com"
                            "提交错误信息:\n\n"
                            "%s" % post)

    def _download(self, medium_type, medium_url, target_folder):
        medium_name = medium_url.split("/")[-1].split("?")[0]
        if medium_type == "video":
            if not medium_name.startswith("tumblr"):
                medium_name = "_".join([medium_url.split("/")[-2], medium_name])
            medium_name += ".mp4"

        # 构造存储文件的路径
        file_path = os.path.join(target_folder, medium_name)
        if not os.path.isfile(file_path):
            print("Downloading %s from %s.\n" % (medium_name, medium_url))
            retry_times = 0
            while retry_times < RETRY:
                try:
                    # 用requests发送get请求获取数据流，分片获取文件数据写入磁盘
                    resp = requests.get(medium_url, stream=True, proxies=self.proxies, timeout=TIMEOUT)
                    with open(file_path, 'wb') as fp:
                        for chunk in resp.iter_content(chunk_size=1024):
                            fp.write(chunk)
                    break
                except:
                    # try again
                    pass
                retry_times += 1
            else:
                try:
                    os.remove(file_path)
                except OSError:
                    pass
                print("Failed to retrieve %s from %s.\n" % (medium_type, medium_url))

# 调度器
class CrawlerScheduler(object):

    def __init__(self, sites, proxies=None):
        self.sites = sites
        self.proxies = proxies
        self.queue = Queue.Queue()
        self.scheduling()
      

    def scheduling(self):
        # 创建工作线程
        for x in range(THREADS):
            worker = DownloadWorker(self.queue, proxies=self.proxies)
            # 设置daemon属性，保证主线程在任何情况下可以退出
            worker.daemon = True
            # 启动线程
            worker.start()

        for site in self.sites:
            if IS_DOWNLOAD_IMG:
                self.download_photos(site)
            if IS_DOWNLOAD_VIDEO:
                self.download_videos(site)
        

    def download_videos(self, site):
        self._download_media(site, "video", START)
        # 等待queue处理完一个用户的所有请求任务项
        self.queue.join()
        print("视频下载完成 %s" % site)

    def download_photos(self, site):
        self._download_media(site, "photo", START)
         # 等待queue处理完一个用户的所有请求任务项
        self.queue.join()
        print("图片下载完成 %s" % site)
    def _download_media(self, site, medium_type, start):
        # 创建存储目录
        current_folder = os.getcwd()
        # 构造目标文件夹路径
        target_folder = os.path.join(current_folder, site)
        if not os.path.isdir(target_folder):
            # 创建一级目录
            os.mkdir(target_folder)

        base_url = "http://{0}.tumblr.com/api/read?type={1}&num={2}&start={3}"
        start = START
        while True:
            # MEDIA_NUM每页请求数，start分页请求起始点
            media_url = base_url.format(site, medium_type, MEDIA_NUM, start)
            response = requests.get(media_url, proxies=self.proxies)
            # response.content返回bytes型二进制数据，*.text返回headers中编码解析的数据
            # xmltodict.parse反序列化xml数据到data对象
            data = xmltodict.parse(response.content)
            try:
                posts = data["tumblr"]["posts"]["post"]
                for post in posts:
                    # select the largest resolution
                    # usually in the first element
                    self.queue.put((medium_type, post, target_folder))
                start += MEDIA_NUM
            except KeyError:
                break

# 提示用户使用
def usage():
    print(u"未找到sites.txt文件，请创建.\n"
          u"请在文件中指定Tumblr站点名，并以逗号分割，不要有空格.\n"
          u"保存文件并重试.\n\n"
          u"例子: site1,site2\n\n"
          u"或者直接使用命令行参数指定站点\n"
          u"例子: python tumblr-photo-video-ripper.py site1,site2")

# 提示代理配置error
def illegal_json():
    print(u"文件proxies.json格式非法.\n"
          u"请参照示例文件'proxies_sample1.json'和'proxies_sample2.json'.\n"
          u"然后去 http://jsonlint.com/ 进行验证.")


if __name__ == "__main__":
    sites = None

    proxies = None
    if os.path.exists("./proxies.json"):
        ## 读文件
        with open("./proxies.json", "r") as pj:
            try:
                # 解析json数据
                proxies = json.load(pj)
                if proxies is not None and len(proxies) > 0:
                    print("You are using proxies.\n%s" % proxies)
            except:
                illegal_json()
                # 退出程序引发SystemExit异常
                sys.exit(1)

    # sys.argv命令行的参数列表            
    if len(sys.argv) < 2:
        #校验sites配置文件
        filename = "sites.txt"
        if os.path.exists(filename):
            with open(filename, "r") as fn:
                # 字符串处理
                sites = fn.read().rstrip().lstrip().split(",")
        else:
            usage()
            sys.exit(1)
    else:
        sites = sys.argv[1].split(",")

    if len(sites) == 0 or sites[0] == "":
        usage()
        sys.exit(1)

    CrawlerScheduler(sites, proxies=proxies)
