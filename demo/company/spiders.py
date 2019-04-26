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
        self.__base_url = 'https://www.mingluji.com'

    def make_request(self, word):
        return Request(word, callback=self.parse)

    def parse(self, response):
        urls = response.selector.xpath('//div[@class="view-content"]//span[@class="field-content"]/a/@href').getall()
        for url in urls:
            yield Request(url=self.__base_url + url, callback=self.next_page, cookies=response.cookies)

    def next_page(self, response):
        item_list = response.selector.xpath('//div[@class="item-list"]//span[@class="field-content"]/a/@href').getall()
        for url in item_list:
            yield Request(self.__base_url + url, callback=self.get_detail, cookies=response.cookies)

        next_page = response.selector.xpath('//li[@class="pager-next last"]/a/@href').get()
        yield Request(self.__base_url + next_page, callback=self.get_detail, cookies=response.cookies)

    def get_detail(self, response):
        columns = response.selector.xpath('//div[@class="right_column"]//li')

        dict_map = {
            '企业名称': 'name',
            '公司法定代表人': 'legal_person',
            '省份': 'province',
            '成立日期': 'date',
            '注册资金': 'capital',
            '经营状态': 'status',
            '地区代码': 'region_code',
            '地址': 'address',
            '统一社会信用代码': 'credit_code',
            '联系电话': 'phone_number',
            '电子邮箱': 'email',
            '经营范围': 'scope'
        }
        tmp = {}
        for column in columns:
            key = column.xpath('b/text()').get()
            value = column.xpath('span//text()').get()
            tmp[key] = value

        item = CompanyItem()
        for cn_key, en_key in dict_map.items():
            item[en_key] = tmp.get(cn_key, None)

        yield item
