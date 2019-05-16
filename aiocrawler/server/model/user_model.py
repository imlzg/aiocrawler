# coding: utf-8
import rsa
from datetime import datetime
from peewee import Model
from peewee import PrimaryKeyField, CharField, IntegerField, DateTimeField
from aiocrawler.server.model.db import db


class UserModel(Model):
    user_id = PrimaryKeyField()
    username = CharField(max_length=64, unique=True)
    password = CharField(max_length=64)
    permission = IntegerField(default=0)
    created_at = DateTimeField()

    class Meta:
        database = db
        table_name = "user"


class RsaModel(Model):
    public_key = CharField(max_length=256)

    class Meta:
        database = db
        table_name = 'rsa'


class RsaDatabase(object):
    def __init__(self):
        if not RsaModel.table_exists():
            RsaModel.create_table()

    @staticmethod
    def get_public_key():
        data = RsaModel.get_or_none()
        if data:
            pub = data.public_key
        else:
            pub, _ = rsa.newkeys(1024)
            pub = pub.save_pkcs1()
            RsaModel.insert({
                RsaModel.public_key: pub
            }).execute()
        return pub


class UserDatabase(object):
    def __init__(self):
        if not UserModel.table_exists():
            UserModel.create_table()

    @staticmethod
    def create_user(username: str, sha1_password: str, permission: int = 10):
        UserModel.insert({
            UserModel.username: username,
            UserModel.password: sha1_password,
            UserModel.permission: permission,
            UserModel.created_at: datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }).execute()

    @staticmethod
    def is_user_exists():
        data = UserModel.select()
        if len(data):
            return True

        return False

    @staticmethod
    def has_user(username: str, sha1_password: str):
        user = UserModel.get_or_none(UserModel.username == username,
                                     UserModel.password == sha1_password)
        return user

    @staticmethod
    def get_user_info(username: str) -> UserModel:
        user = UserModel.get_or_none(UserModel.username == username)
        return user
