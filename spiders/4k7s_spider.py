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
    'user-agent': ua
}

socks = 'socks5://192.168.50.1:1080'
proxies = {
    'http': socks,
    'https': socks,
}

# 更新中的漫画，下载
start_urls = [
    {
        'name': 'doupocangqiong',
        'url': 'https://www.4k7s.com/info-40.html',
        'comment': '斗破苍穹'
    },
    {
        'name': 'dazhuzai',
        'url': 'https://www.4k7s.com/info-1810.html',
        'comment': '大主宰'
    },
    {
        'name': 'douluodalu',
        'url': 'https://www.4k7s.com/info-456.html',
        'comment': '斗罗大陆'
    },
    {
        'name': 'gelapunier',
        'url': 'https://www.4k7s.com/info-105.html',
        'comment': '格莱普尼尔'
    },
    {
        'name': 'wudongqiankun',
        'url': 'https://www.4k7s.com/info-1642.html',
        'comment': '武动乾坤'
    },
]

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
    breakprefix = './list/4k7s.break.'
    breakfile = ''
    global break_list
    while True:
        try:
            for item in start_urls:
                breakfile = breakprefix + item['name'] + '.list'
                # 加载下载记录列表
                break_list = read_break(breakfile)
                ch_list = get_chapter_list(item['url'])
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
    url_home = 'https://www.4k7s.com'
    resp = get_resp(main_url)
    # 解析章节列表
    tree = etree.HTML(resp.text)
    # 漫画名称
    mid_title = tree.xpath('//h1[@class="title"]/text()')[0].strip()
    a_list = tree.xpath('//ul[@id="chapterList"]/li/a')
    ch_list = []
    for a in a_list:
        ch_item = {}
        title = a.xpath('string(.)').strip().replace(' ', '')
        ch_url = url_home + a.xpath('./@href')[0]
        if ch_url in break_list:
            print(ch_url, 'already downloaded!')
            continue
        ch_item['title'] = mid_title
        ch_item['ch_title'] = title
        ch_item['ch_url'] = ch_url
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
    img_list = []
    proc_list = []
    lock = mp.RLock()
    for ch in ch_list:
        main_name = ch['title']
        ch_url = ch['ch_url']
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
    res = re.findall(r'chapter_list_all:\[(.*)\]', resp.text)
    img_list = list(map(img_url_trim, res[0].split(',')))
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
    data_path = '/data/Images/comics/4k7s/'
    for img_url in img_list:
        if img_url in break_list:
            print(img_url, 'already downloaded!')
            continue
        name = re.search(r'(?i)http://.*?/(\w*?\.(?:jpg|png|jpeg|gif))',
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
