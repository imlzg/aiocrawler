# coding: utf-8
# Date      : 2019-04-25
# PROJECT   : company
# File      : items.py
from core.field import Field
from core.item import Item


class CompanyItem(Item):
    name = Field()
    legal_person = Field()
    province = Field()
    date = Field()
    capital = Field()
    status = Field()
    region_code = Field()
    address = Field()
    credit_code = Field()
    phone_number = Field()
    email = Field()
    scope = Field()
