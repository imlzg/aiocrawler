# coding: utf-8
# Date      : 2019-04-28
# PROJECT   : credit
# File      : items.py
from aiocrawler import Item, Field


class CreditItem(Item):
    """
    you can define your Item like this, just like scrapy Item:
    name = Field()
    website = Field()
    """
    item_name = "credit"

    encry_str = Field()
    name = Field()
    legal_person = Field()
    reg_no = Field()
    status = Field()
    credit_code = Field()
    ent_type = Field()
    dom = Field()
    date = Field()
    reg_org = Field()
    good_count = Field()
    bad_count = Field()
