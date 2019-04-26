# coding: utf-8
# Date      : 2019-04-25
# PROJECT   : company
# File      : spiders.py
from core.request import Request
from core.spider import Spider
from core.settings import BaseSettings
from demo.company.items import CompanyItem


class CompanySpider(Spider):
    def __init__(self, settings: BaseSettings):
        Spider.__init__(self, settings)

    def make_request(self, word):
        return Request(word, callback=self.parse)

    def parse(self, response):
        urls = response.selector.xpath('//div[@class="quer_div"]//td[@class="td_p"]/a/@href').getall()
        for url in urls:
            yield Request(url=url, callback=self.next_page)

    def next_page(self, response):
        coms = response.selector.xpath('//ul[@class="cony_div"]//a')
        for com in coms:
            name = com.xpath('b[contains(text(), "公司")]/text()').get()
            if name:
                item = CompanyItem()
                item['name'] = name
                yield item

        next_page = response.selector.xpath('//div[@class="page_list"]/a[contains(text(), "下一页")]/@href').get()
        if next_page:
            yield Request(next_page, callback=self.next_page)

        page_list = response.selector.xpath('//div[@class="page_list"]/a/@href').getall()
        if len(page_list):
            end = -2 if next_page else -1
            for page in page_list[:end]:
                yield Request(page, callback=self.next_page2, meta={'get_page_list': False})

    def next_page2(self, response):
        coms = response.selector.xpath('//ul[@class="cony_div"]//a')
        for com in coms:
            name = com.xpath('b[contains(text(), "公司")]/text()').get()
            if name:
                item = CompanyItem()
                item['name'] = name
                yield item
