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
coms = html.xpath('//ul[@class="cony_div"]//a')
for com in coms:
    url = com.xpath('@href').get()
    name = com.xpath('b[contains(text(), "公司")]/text()').get()
