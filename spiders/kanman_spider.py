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
import execjs


# 平台名称
platform = 'kanman'

ua = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36'

headers = {
    'user-agent': ua
}

socks = 'socks5://127.0.0.1:1084'
proxies = {
    'http': socks,
    'https': socks,
}

# 更新中的漫画，下载
start_urls = [
    {
        'name': 'doupocangqiong',
        'url': 'https://www.kanman.com/25934/',
        'comment': '斗破苍穹'
    },
    {
        'name': 'dazhuzai',
        'url': 'https://www.kanman.com/8687/',
        'comment': '斗破苍穹之大主宰'
    },
    {
        'name': 'jueshitangmen',
        'url': 'https://www.kanman.com/7119/',
        'comment': '绝世唐门'
    },
    {
        'name': 'douluodalu',
        'url': 'https://www.kanman.com/25933/',
        'comment': '斗罗大陆'
    },
    {
        'name': 'douluodalu3',
        'url': 'https://www.kanman.com/86080/',
        'comment': '斗罗大陆3龙王传说'
    },
    {
        'name': 'fengqicanglan',
        'url': 'https://www.kanman.com/9680/',
        'comment': '风气苍岚'
    },
    {
        'name': 'lingjianzun',
        'url': 'https://www.kanman.com/104685/',
        'comment': '灵剑尊'
    },
    {
        'name': 'wudongqiankun',
        'url': 'https://www.kanman.com/5324/',
        'comment': '武动乾坤'
    },
    {
        'name': 'shenyinwangzuo',
        'url': 'https://www.kanman.com/5323/',
        'comment': '神印王座'
    },
    {
        'name': 'wudijianyu',
        'url': 'https://www.kanman.com/108348/',
        'comment': '无敌剑域'
    },
]

# 记录下载完成的URL,没什么用 #
downloaded_urls = [
    {
        'name': 'doupocangqiong',
        'url': 'https://www.kanman.com/25934/',
        'comment': '斗破苍穹'
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
    breakprefix = f'./list/{platform}.break.'
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
    url_home = f'https://www.{platform}.com'
    resp = get_resp(main_url)
    # 解析章节列表
    tree = etree.HTML(resp.text)
    # 漫画名称
    mid_title = tree.xpath('//h1[@class="title"]/text()')[0].strip()
    a_list = tree.xpath('//ol[@id="j_chapter_list"]/li/a')
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
        print(ch)
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
    res = re.findall(r'<script>.*?window\.(comicInfo.*?)</script>', resp.text)
    js_var = 'var ' + res[0]
    myjs = execjs.compile(js_var)
    text_js1 = myjs.eval('comicInfo.current_chapter')
    ch_name = text_js1['chapter_name']
    chapter_id = text_js1['chapter_id']
    start_num = text_js1['start_num']
    end_num = text_js1['end_num']
    rule = text_js1['rule']
    prefix = 'https://mhpic.jumanhua.com'
    suffix = '-kmh.middle.webp'
    img_list = []
    for i in range(start_num, end_num+1):
        img_url = prefix + rule.replace(r'$$', str(i)) + suffix
        img_list.append(img_url)

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
    global platform
    data_path = f'/data/Images/comics/{platform}/'
    for img_url in img_list:
        if img_url in break_list:
            print(img_url, 'already downloaded!')
            continue
        name = re.search(r'(?i)https?://.*?/(\w*?\.(?:jpg|png|jpeg|gif))',
                         img_url)
        if name is None:
            print(f'ERROR: name is None:img_url: {img_url}')
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
