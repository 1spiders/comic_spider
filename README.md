# 漫画爬虫工具
![](https://visitor-badge.glitch.me/badge?page_id=learnhard-cn.comics_spider)

支持功能：
1. 根据配置URL地址，自动爬取章节漫画图片(解析JS数据获取ImageURL)
2. 下载历史记录功能，记录曾经下载过的地址，可重复执行来下载更新的章节漫画内容.

## 如何使用
> 此工具需要使用`Python3`环境

依赖安装: `pip3 install -r requirements.txt`

具体安装的时间就看自己的网络速度哦。如果安装`Pyppeteer`时第一次运行时会自动下载`chromium`浏览器, 可能会比较慢或下载失败。自己了解下科学上网吧。


## 关于`pyppeteer`运行失败问题说明

### 1.可能`chromium`安装失败
Linux用户的验证方法:
1. 检查`~/.local/share/pyppeteer/local-chromium/`目录下是否有`Chromium`浏览器版本号的目录(例如:588429)
2. 如果没有，那就说明浏览器下载失败了，手工下载命令(安装pyppeteer会自带安装):`pyppeteer-install`
3. 如果有就执行`~/.local/share/pyppeteer/local-chromium/588429/chrome-linux/chrome` 浏览器命令，看是否可以运行成功，报什么错误就`Google`搜索.通常会因为缺少依赖库而无法运行。

## 说明
由于网站的图片格式多种多样(尺寸不规则)以及图片破损等等问题，在下载后可能有很多漫画图片无法查看是正常的(因为其网站就是如此)。


![](comics.png)

---

