# coding: utf-8
# Date      : 2019/4/25
# Author    : kylin
# PROJECT   : credit
# File      : parsel_test
#              ┏┓   ┏┓
#            ┏┛┻━━━┛┻┓
#            ┃   ☃   ┃
#            ┃ ┳┛ ┗┳ ┃
#            ┃   ┻   ┃
#            ┗━┓   ┏━┛
#              ┃   ┗━━━┓
#              ┃神兽保佑┣┓
#              ┃永无BUG!┏┛
#              ┗┓┓┏━┳┓┏┛
#               ┃┫┫  ┃┫┫
#               ┗┻┛  ┗┻┛
from parsel import selector


with open('1.html', 'r', encoding='utf-8') as f:
    content = f.read()

html = selector.Selector(text=content)
urls = html.xpath('//div[@class="right_column"]//li')
for url in urls:
    print(url.xpath('b/text()').get())
    print(url.xpath('span//text()').get())
