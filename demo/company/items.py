# coding: utf-8
# Date      : 2019-04-25
# PROJECT   : company
# File      : items.py
from core.field import Field
from core.item import Item


class CompanyItem(Item):
    name = Field()
