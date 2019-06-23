# coding: utf-8
# Date      : 2019-04-28
# PROJECT   : credit
# File      : spiders.py
from aiocrawler import BaseSettings, Spider, Request, Response
from urllib.parse import quote_plus
from items import CreditItem


class CreditSpider(Spider):
    name = "credit"

    def __init__(self, settings: BaseSettings):
        Spider.__init__(self, settings)

    def make_request(self, word):
        params = {
            'index': 0,
            'keyword': quote_plus(word)
        }
        url = 'https://www.creditchina.gov.cn/xinyongxinxi/index.html'
        return Request(url, params=params, callback=self.parse, meta={'keyword': word})

    def parse(self, response):
        page_count = 5
        for page in range(1, page_count + 1):
            params = {
                'keyword': quote_plus(response.meta.get('keyword', '')),
                'templateId': '',
                'page': page,
                'pageSize': '10'
            }
            url = 'https://www.creditchina.gov.cn/api/credit_info_search'
            yield Request(url, params=params,
                          callback=self.get_detail,
                          format_type='json',
                          cookies=response.cookies)

    def get_detail(self, response: Response):
        if response.json:
            for com in response.json.get('data', {}).get('results', []):
                url = 'https://www.creditchina.gov.cn/api/credit_info_detail?encryStr={}'.format(com['encryStr'])
                item = CreditItem()
                item['encry_str'] = com['encryStr']
                yield Request(url, callback=self.get_detail2, format_type='json', meta={'item': item})

    def get_detail2(self, response: Response):
        item = response.meta['item']
        item['name'] = response.json['result']['entName']
        item['legal_person'] = response.json['result']['legalPerson']
        item['status'] = response.json['result']['entstatus']
        item['credit_code'] = response.json['result']['creditCode']
        item['reg_no'] = response.json['result']['regno']
        item['ent_type'] = response.json['result']['enttype']
        item['dom'] = response.json['result']['dom']
        item['date'] = response.json['result']['esdate']
        item['reg_org'] = response.json['result']['regorg']
        item['good_count'] = response.json['result']['goodCount']
        item['bad_count'] = response.json['result']['badCount']

        yield item
