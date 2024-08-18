#!/usr/bin/env python3
# -*- coding: utf-8 -*-
################################################################################
# Author: zioer
# mail: xiaoyu0720@gmail.com
# Created Time: 2020年07月31日 星期五 12时44分32秒
# Brief:
################################################################################
import asyncio
from pyppeteer import launch
from pyppeteer import launcher
from lxml import etree
import re
import json
import html
import requests
import os

js_get = '() =>{return [MANGABZ_IMAGE_COUNT, MANGABZ_CID, MANGABZ_CID, MANGABZ_PAGEINDEX, MANGABZ_CID, COMIC_MID, MANGABZ_VIEWSIGN_DT, MANGABZ_VIEWSIGN]; }'

ua = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36'

headers = {
    'user-agent': ua
}
# socks = 'socks5://127.0.0.1:1084'
socks = 'socks5://192.168.50.187:1084'
proxies = {
    'http': socks,
    'https': socks,
}

# 字体cookies设置: 1-繁体, 2-简体,默认繁体
cookies = {'name': 'mangabz_lang', 'value': '2'}
breakprefix = './list/mangabz.break.'
breakfile = ''

# 完结列表
# 鬼灭之刃 - 'http://www.mangabz.com/73bz/',

# 更新中，下载
start_urlsbak = [
    {'name': 'dr_stone', 'url': 'https://www.mangabz.com/265bz/', 'comment': 'Dr.Stone 石头记'},
    {'name': 'dragonball_super', 'url': 'http://www.mangabz.com/610bz/', 'comment': '龙珠超'},
    {'name': 'only_spider', 'url': 'https://www.mangabz.com/134bz/', 'comment': '不过是蜘蛛什么的'},
    {'name': 'my_hero', 'url': 'https://www.mangabz.com/264bz/', 'comment': '我的英雄学院'},
    {'name': 'black_clover', 'url': 'https://www.mangabz.com/276bz/', 'comment': '黑色四叶草'},
    {'name': 'xugoutuili', 'url': 'https://www.mangabz.com/59bz/', 'comment': '虚构推理-城平京'},
    {'name': 'hzw', 'url': 'http://www.mangabz.com/139bz/', 'comment': '海贼王'},
    {'name': 'jj', 'url': 'https://www.mangabz.com/511bz/', 'comment': '进击的巨人'},
]

start_urls = [
    {'name': 'kenan', 'url': 'https://www.mangabz.com/249bz/', 'comment': '名侦探柯南'},
]

def get_resp(url):
    while True:
        try:
            resp = requests.get(url, headers=headers, proxies=proxies)
            break
        except Exception as e:
            print('request : url:', url, 'exception: ', str(e))
        time.sleep(3)
    return resp


async def main():
    while True:
        try:
            global breakprefix
            global breakfile
            for item in start_urls:
                breakfile = breakprefix + item['name'] + '.list'
                result = await do_fetch(item['url'])
            break
        except Exception as e:
            await asyncio.sleep(10)
            print(e)
    return result

async def do_fetch(main_url):
    # headless参数设为False，则变成有头模式
    proxy_server = "--proxy-server=" + socks
    browser = await launch(headless=True, args=['--disable-infobars', proxy_server])

    pages = await browser.pages()

    page1 = pages[0]
    # 设置页面视图大小
    await page1.setViewport(viewport={'width': 1280, 'height': 800})
    await page1.setUserAgent(ua)
    await page1.goto(main_url)
    await page1.setCookie(cookies)
    await page1.reload()
    page_text = await page1.content()
    # 解析章节列表
    tree = etree.HTML(page_text)
    # 漫画名称用于 MID替换中文
    mid_title = tree.xpath('//div[@class="detail-info"]/p[@class="detail-info-title"]//text()')[0].strip()
    a_list = tree.xpath('//div[@id="chapterlistload"]/a')
    ch_list = []
    for a in a_list:
        ch_item = {}
        title = a.xpath('string(.)').strip().replace(' ', '')
        ch_url = 'http://www.mangabz.com/' + a.xpath('./@href')[0]
        ch_item['title'] = mid_title
        ch_item['ch_title'] = title
        ch_item['ch_url'] = ch_url
        ch_list.append(ch_item)

    result = []
    item = {}
    break_list = read_break()
    for a in ch_list:
        item = {}
        cid_title = a['ch_title']
        ch_url = a['ch_url']
        if ch_url in break_list:
            print(f'URL已经下载过:{ch_url}')
            continue
        item['title'] = cid_title
        item['url'] = ch_url
        text_js1 = await get_chapter_url(page1, ch_url)
        page_count = text_js1[0]
        params = text_js1[1:]
        # for page_num in range(1, page_count+1):
        page_num = 1
        all_image_list = []
        while page_num <= page_count:
            params[2] = page_num
            print(params)
            # 获取Image链接地址
            js_url = 'http://www.mangabz.com/m{}/chapterimage.ashx?cid={}&page={}&key=&_cid={}&_mid={}&_dt={}&_sign={}'.format(*params)
            js_id = 'http://www.mangabz.com/m{}/chapterimage.ashx?cid={}&page={}&key=&_cid={}&_mid={}'.format(*params[:5])
            if js_id in break_list:
                print(f'URL已经下载过:{js_id}')
                page_num += 1
                continue
            image_list = await get_image_url(page1, js_url, params)
            print('-'*40)
            print(image_list)
            fn_list = []
            mid = '/' + str(params[4]) + '/'
            cid = '/' + str(params[0]) + '/'
            str_mid = '/' + mid_title + '/'
            str_cid = '/' + cid_title + '/'
            for img_url in image_list:
                # 图片链接示例: http://image.mangabz.com/1/610/45117/1_1319.jpg?cid=45117&key=93961abcd31ff00f2b28ffb4d208b5f5&uk=
                fn_re = re.search(r'(?i)http://image.*?.com/\w*?(/.*?(?:jpg|png|jpeg|gif))', img_url).group(1)
                # 将数字编号替换成中文标题
                filename = fn_re.replace(mid, str_mid).replace(cid, str_cid)
                fn_list.append(filename)
                ret_text = download_img(img_url, filename)
                print('-'*40)
                print(ret_text, filename, img_url)
            all_image_list += fn_list
            write_break(js_id)         # 记录下载过的JS请求地址ID
            img_len = len(image_list)  # 当数量大于1时，说明是多页同时获取到
            page_num += img_len
            await asyncio.sleep(2)
        print('-'*40)
        print(item)
        result.append(item.copy())
        item['image_list'] = all_image_list
        write_break(ch_url)
    await asyncio.sleep(3)
    await browser.close()
    return result

async def get_chapter_url(page, url, retry_max=5, sleep_sec=3):
    '''
    访问章节首页，执行`js_get`脚本
    获取章节基本参数信息，例如页数、key等信息
    MANGABZ_IMAGE_COUNT, MANGABZ_CID, MANGABZ_CID, MANGABZ_PAGEINDEX, MANGABZ_CID, COMIC_MID, MANGABZ_VIEWSIGN_DT, MANGABZ_VIEWSIGN
    [21, 17784, 17784, 1, 17784, 73, '2020-08-15 22:29:01', '5436a26bcbe7819868c2211545bc3e10']
    '''
    retry = 0
    while retry < retry_max:
        try:
            await page.goto(url)
            page_text1 = await page.content()
            js_info = re.search('<script type="text/javascript">\s*?(var isVip.*?)reseturl.*?</script>', page_text1)
            js_var1 = js_info.group(1)
            print('-'*40)
            print(js_var1)
            await page.evaluate(js_var1)
            text_js1 = await page.evaluate(js_get)
            print('-'*40)
            print(text_js1)
            break
        except Exception as e:
            print(e)
            retry += 1
            await asyncio.sleep(sleep_sec)
    if retry == retry_max:
        text_js1 = None
    return text_js1

async def get_image_url(page, url, params, retry_max=5, sleep_sec=3):
    retry = 0
    while retry < retry_max:
        try:
            await page.goto(url)
            page_text3 = await page.content()
            print('-'*40)
            print(url)
            print('-'*40)
            print(page_text3)

            js_eval1 = re.search(r'(eval\(.*\))', page_text3)
            js_eval2 = js_eval1.group(1)
            js_eval2 = html.unescape(js_eval2)
            print('-'*40)
            print(js_eval2)

            # 获取图片地址 #
            page_text2 = await page.evaluate(js_eval2)
            break
        except Exception as e:
            print(e)
            retry += 1
            await asyncio.sleep(sleep_sec)
    if retry == retry_max:
        page_text2 = None
    return page_text2


def write_break(line):
    '''
    记录下载列表，用于中断后继续恢复下载
    '''
    with open(breakfile, 'a') as f:
        f.write(line + '\n')


def read_break():
    '''
    获取下载记录
    '''
    write_path = os.path.dirname(breakfile)
    if not os.path.exists(write_path):
        os.makedirs(write_path, 0o755)  # 递归创建子目录
    if not os.path.exists(breakfile):
        return []
    with open(breakfile, 'r') as f:
        data = f.readlines()
    return [i.replace('\n', '') for i in data]


def download_img(url, name):
    '''
    下载图片文件：
    url : http://image.mangabz.com/1/73/17784/3_7694.png?cid=17784&key=32df64aa69b25d3b5dafafdb656d1ad6&uk=
    保存文件名: data_path + /漫画名/章节名称/3_7694.png
    '''
    data_path = '/data/Images/comics/mangabz/'
    write_path = data_path + '/' + os.path.dirname(name)
    filename = data_path + '/' + name
    if not os.path.exists(write_path):
        os.makedirs(write_path, 0o755)  # 递归创建子目录
    if os.path.exists(filename):
        return "已下载过"
    resp = get_resp(url)
    with open(filename, 'wb') as f:
        f.write(resp.content)
        f.flush()
    return "下载完成"


# 创建任务列表
tasks = []
# 创建任务对象
task1 = asyncio.ensure_future(main())
tasks.append(task1)

# 将任务列表放入事件循环中，挂起任务并运行
asyncio.get_event_loop().run_until_complete(asyncio.wait(tasks))
