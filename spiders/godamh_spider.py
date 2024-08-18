#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###############################################################################
# Author: zioer
# mail: next4nextjob@gmail.com
# Created Time: 2020年09月06日 星期日 13时47分36秒
# Brief: 漫画爬虫
###############################################################################
import requests
from lxml import etree
import re
import os
import sys
import time
import traceback
import multiprocessing as mp


ua = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36'

headers = {
    'user-agent': ua,
    'origin': 'https://m.godamh.com',
    'referer': 'https://m.godamh.com/',
}

default_socks = 'socks5://127.0.0.1:1080'

# TODO: socks 参数通过参数设置，如果每设置则使用默认 default_socks #
# socks

proxies = {
    'http': socks,
    'https': socks,
}

# 更新中的漫画列表参数，通过参数传递
start_urls = []

# 图片存储路径
data_path = './comics/'

# 记录下载完成的URL,没什么用 #
downloaded_urls = [
    {
        'name': 'yaoshenji',
        'url': 'https://www.4k7s.com/info-690.html',
        'zh_name': '妖神记'
    },
]

break_list = []


def get_resp(url):
    while True:
        try:
            resp = requests.get(url, headers=headers, proxies=proxies)
            break
        except Exception as e:
            print('request : url:', url, 'exception: ', str(e))
        time.sleep(3)
    return resp


def main(start_urls):
    breakprefix = './list/godamh.break.'
    breakfile = ''
    global break_list
    while True:
        try:
            for url in start_urls:
                md5_hash = re.sub(r'[\/:*?"<>|]', '_', url)
                breakfile = breakprefix + md5_hash + '.list'
                # 加载下载记录列表
                break_list = read_break(breakfile)
                ch_list = get_chapter_list(url)
                get_image_list(ch_list, breakfile)
            break
        except Exception as e:
            print(e)
            traceback.print_exc()
        time.sleep(3)
    return


def get_chapter_list(main_url):
    '''获取章节URL列表'''
    global break_list
    resp = get_resp(main_url)
    if resp.status_code != 200:
        print("Error: 获取章节列表失败:" + resp.status_code)
        return []
    
    # 确保使用正确的编码
    resp.encoding = 'utf-8'
    # 解析章节列表
    tree = etree.HTML(resp.text)
    # 漫画名称
    mid = tree.xpath('//div[@id="mangachapters"]/@data-mid')[0].strip()
    mid_title = tree.xpath('//*[@id="info"]/div[1]/div[1]/div[1]/h1/text()')[0].strip()

    api_chapters = 'https://api-get.mgsearcher.com/api/manga/get?mid='+mid+'&mode=all'
    resp1 = get_resp(api_chapters)
    if resp1.status_code != 200:
        print("Error: 获取章节列表API访问失败:" + resp1.status_code)
        return []
    resp1.encoding = 'utf-8'
    json_data = resp1.json()
    if json_data["data"] == None:
        print("Error: 章节API获取结果无效:" + json_data)
        return []
    chapters = json_data["data"]["chapters"]
    if len(chapters) == 0:
        print("Error: 无任何章节信息")
        return []
    
    ch_list = []
    for ch in chapters:
        ch_item = {}
        ch_id = ch["id"]
        attr = ch["attributes"]
        title = attr["title"]
        
        if ch_id in break_list:
            print(ch_id, title, '已经下载了!忽略本章节请求！')
            continue
        ch_item['mid'] = mid
        ch_item['title'] = mid_title
        ch_item['ch_title'] = title
        ch_item['ch_id'] = ch_id
        ch_list.append(ch_item)
    return ch_list


def img_url_trim(item):
    url = item.strip('"')
    if not url.startswith('http'):
        url = 'http:' + url
    return url


def get_image_list(ch_list, breakfile, maxp=20):
    '''根据章节URL列表获取Image列表'''
    ctx = mp.get_context('fork')
    proc_list = []
    lock = mp.RLock()
    for ch in ch_list:
        main_name = ch['title']
        ch_url = 'https://api-get.mgsearcher.com/api/chapter/getinfo?m='+ch['mid']+'&c='+ ch['ch_id']
        ch_name = ch['ch_title']
        p = ctx.Process(target=download_one_chapter, args=(lock, ch_url, main_name, ch_name, breakfile))
        p.start()
        proc_list.append(p)
        if len(proc_list) == maxp:
            for p in proc_list:
                p.join()
            proc_list = []
    for p in proc_list:
        p.join()
    return True


def download_one_chapter(lock, ch_url, main_name, ch_name, breakfile):
    '''下载一章节图片, 用于并发'''
    resp = get_resp(ch_url)
    json_data = resp.json()
    img_list = [image["url"] for image in json_data["data"]["info"]["images"]]
    download_image(lock, img_list, main_name, ch_name, breakfile)
    write_break(lock, breakfile, ch_url)


def write_break(lock, breakfile, line):
    '''
    记录下载列表，用于中断后继续恢复下载
    '''
    lock.acquire()
    print('DEBUG: write :', breakfile, ' ,content: ', line)
    with open(breakfile, 'a') as f:
        f.write(line + '\n')
    lock.release()
    return


def read_break(breakfile):
    '''
    获取下载记录
    '''
    write_path = os.path.dirname(breakfile)
    if not os.path.exists(write_path):
        os.makedirs(write_path, 0o755)  # 递归创建子目录
    print(breakfile)
    if not os.path.exists(breakfile):
        return []
    with open(breakfile, 'r') as f:
        data = f.readlines()
    return [i.replace('\n', '') for i in data]


def download_image(lock, img_list, main_name, ch_name, breakfile):
    '''根据图片URL下载图片'''
    global break_list
    for img_url in img_list:
        if img_url in break_list:
            print(img_url, 'already downloaded!')
            continue
        name = re.search(r'(?i)http[s]?://.*?/(\w*?\.(?:jpg|png|jpeg|gif|webp))',
                         img_url)
        if name is None:
            print(img_url)
            continue
        name = name.group(1)
        write_path = data_path + main_name + '/' + ch_name.replace(' ', '') + '/'
        filename = write_path + name
        if not os.path.exists(write_path):
            print('递归创建目录:', write_path)
            os.makedirs(write_path, 0o755)  # 递归创建子目录
        if os.path.exists(filename):
            print(filename, ' 文件已经下载过了')
            # return "已下载过"
            continue
        resp = get_resp(img_url)
        with open(filename, 'wb') as f:
            f.write(resp.content)
            f.flush()
        write_break(lock, breakfile, img_url)


if __name__ == '__main__':
    main(start_urls)
