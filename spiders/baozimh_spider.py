#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###############################################################################
# Author: zioer
# mail: next4nextjob@gmail.com
# Created Time: 2020年09月06日 星期日 13时47分36秒
# Brief: 包子漫画的漫画爬虫
###############################################################################

import os
import re
import sys
import time
import requests
from lxml import etree
from concurrent.futures import ThreadPoolExecutor
from requests.exceptions import RequestException

# 常量和配置
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36'
HEADERS = {
    'user-agent': UA,
    'origin': 'https://m.godamh.com',
    'referer': 'https://m.godamh.com/',
}
DEFAULT_SOCKS = 'socks5://127.0.0.1:1084'
DATA_PATH = '/docs/ebooks/comics/'
BREAK_PREFIX = './list/godamh.break.'
MAX_WORKERS = 20

# 可通过参数传递的变量
proxies = {
    'http': DEFAULT_SOCKS,
    'https': DEFAULT_SOCKS,
}
start_urls = [
    # 'https://hipmh.com/manga/doupocangqiongzhidazhuzai-dazhouhuyu',
    'https://hipmh.com/manga/doupocangqiong-zhiyinmankerenxiang',
    'https://hipmh.com/manga/guimiezhiren-wusanghushiqing',
    'https://hipmh.com/manga/wudonggankun-shenman',
    'https://hipmh.com/manga/yaoshenji-taxuedongman',
    'https://hipmh.com/manga/yuanzun-weitianchuanmei',
    # 'https://hipmh.com/manga/douluodalu2jueshitangmen-tangjiasanshao',
    'https://hipmh.com/manga/douluodaluiijueshitangmen-shenmanjun',
    'https://hipmh.com/manga/douluodalu3longwangchuanshuo-shenman'
    'https://hipmh.com/manga/douluodalu4zhongjidouluo-shenman',
    'https://hipmh.com/manga/wuliandianfeng-pikapi',
    'https://hipmh.com/manga/doupocangqiong-zhiyinmankerenxiang',
]

def retry_on_exception(retries=10, delay=3):
    """重试装饰器，处理异常时自动重试"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except RequestException as e:
                    print(f"Request failed: {e}. Retrying ({attempt + 1}/{retries})...")
                    time.sleep(delay)
            print(f"尝试失败! func:{func},args={args},kw={kwargs}")
            return None
        return wrapper
    return decorator

@retry_on_exception()
def get_resp(url):
    return requests.get(url, headers=HEADERS, proxies=proxies)

def main(start_urls):
    for url in start_urls:
        md5_hash = re.sub(r'[\/:*?"<>|]', '_', url)
        breakfile = BREAK_PREFIX + md5_hash + '.list'
        break_list = read_break(breakfile)
        ch_list = get_chapter_list(url, break_list)
        get_image_list(ch_list, breakfile)

def get_chapter_list(main_url, break_list):
    """获取章节URL列表"""
    resp = get_resp(main_url)
    if not resp or resp.status_code != 200:
        print(f"Error: 获取章节列表失败 - {resp.status_code if resp else 'No Response'}")
        return []
    
    resp.encoding = 'utf-8'
    tree = etree.HTML(resp.text)
    mid = tree.xpath('//div[@id="mangachapters"]/@data-mid')[0].strip()
    mid_title = tree.xpath('//*[@id="info"]/div[1]/div[1]/div[1]/h1/text()')[0].strip()

    api_chapters = f'https://api-get.mgsearcher.com/api/manga/get?mid={mid}&mode=all'
    resp1 = get_resp(api_chapters)
    if not resp1 or resp1.status_code != 200:
        print(f"Error: 获取章节列表API访问失败 - {resp1.status_code if resp1 else 'No Response'}")
        return []

    json_data = resp1.json()
    if not json_data.get("data"):
        print(f"Error: 章节API获取结果无效: {json_data}")
        return []

    chapters = json_data["data"]["chapters"]
    if not chapters:
        print("Error: 无任何章节信息")
        return []

    return [{
        'mid': mid,
        'title': mid_title,
        'ch_title': ch["attributes"]["title"],
        'ch_id': ch["id"]
    } for ch in chapters if ch["id"] not in break_list]

def get_image_list(ch_list, breakfile):
    """根据章节URL列表获取Image列表"""
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for ch in ch_list:
            ch_url = f'https://api-get.mgsearcher.com/api/chapter/getinfo?m={ch["mid"]}&c={ch["ch_id"]}'
            executor.submit(download_one_chapter, ch_url, ch['title'], ch['ch_title'], breakfile)

def download_one_chapter(ch_url, main_name, ch_name, breakfile):
    """下载一章节图片, 用于并发"""
    resp = get_resp(ch_url)
    if not resp:
        return

    json_data = resp.json()
    img_list = [image["url"] for image in json_data["data"]["info"]["images"]]
    download_images(img_list, main_name, ch_name, breakfile)
    write_break(breakfile, ch_url)

def download_images(img_list, main_name, ch_name, breakfile):
    """根据图片URL下载图片"""
    for img_url in img_list:
        img_url = img_url_trim(img_url)
        filename = create_filename(main_name, ch_name, img_url)
        if not filename or os.path.exists(filename):
            continue

        part_filename = filename + '.part'
        resp = get_resp(img_url)
        if resp:
            save_image(resp, part_filename)
            os.rename(part_filename, filename)
            write_break(breakfile, img_url)
        else:
            print(f"Failed to download image: {img_url}")

def img_url_trim(url):
    """去除URL中的双引号并添加协议前缀"""
    url = url.strip('"')
    return url if url.startswith('http') else 'http:' + url

def create_filename(main_name, ch_name, img_url):
    """生成文件路径和文件名"""
    match = re.search(r'(?i)http[s]?://.*?/(\w*?\.(?:jpg|png|jpeg|gif|webp))', img_url)
    if not match:
        print(f"Invalid image URL: {img_url}")
        return None

    name = match.group(1)
    write_path = os.path.join(DATA_PATH, main_name, ch_name.replace(' ', ''))
    if not os.path.exists(write_path):
        os.makedirs(write_path, 0o755)
    return os.path.join(write_path, name)

def save_image(resp, filename):
    """保存图片到文件"""
    with open(filename, 'wb') as f:
        f.write(resp.content)
        f.flush()

def write_break(breakfile, line):
    """记录下载列表，用于中断后继续恢复下载"""
    with open(breakfile, 'a') as f:
        f.write(line + '\n')

def read_break(breakfile):
    """获取下载记录"""
    if not os.path.exists(breakfile):
        return []
    with open(breakfile, 'r') as f:
        return [line.strip() for line in f]

if __name__ == '__main__':
    main(start_urls)
