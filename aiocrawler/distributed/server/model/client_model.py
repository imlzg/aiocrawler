# coding: utf-8
from datetime import datetime
from aiocrawler.distributed.server.utils import gen_token
from aiocrawler.distributed.server.model.db import db
from aiocrawler.distributed.server.utils import DATETIME_FORMAT
from peewee import Model, CharField, DateTimeField, PrimaryKeyField, IntegerField


class ClientModel(Model):
    client_id = PrimaryKeyField()
    uuid = CharField(max_length=40, unique=True)
    remote_ip = CharField(max_length=16)
    host = CharField(max_length=32)
    hostname = CharField(max_length=32)
    token = CharField(max_length=64, default=None, null=True)
    status = IntegerField(default=0)
    authorized_at = DateTimeField(null=True)
    connected_at = DateTimeField(null=True)

    class Meta:
        database = db
        table_name = 'client'


class BlacklistModel(Model):
    remote = CharField(max_length=16, unique=True)
    start_time = IntegerField()

    class Meta:
        database = db
        table_name = 'blacklist'


class ClientDatabase(object):
    def __init__(self):
        if not ClientModel.table_exists():
            ClientModel.create_table()

    @staticmethod
    def create_client(uuid: str, ip: str, host: str, hostname: str):
        ClientModel.replace({
            ClientModel.remote_ip: ip,
            ClientModel.host: host,
            ClientModel.hostname: hostname,
            ClientModel.uuid: uuid,
            ClientModel.connected_at: datetime.now().strftime(DATETIME_FORMAT),
        }).execute()

    @staticmethod
    def update(uuid: str):
        ClientModel.update({
            ClientModel.connected_at: datetime.now().strftime(DATETIME_FORMAT)
        }).where(ClientModel.uuid == uuid).execute()

    @staticmethod
    def get_client_info(uuid: str) -> ClientModel:
        client = ClientModel.get_or_none(ClientModel.uuid == uuid)
        return client

    @staticmethod
    def auth(client_id: str):
        client_id = int(client_id)
        client = ClientModel.get_or_none(ClientModel.client_id == client_id)
        if not client:
            return None

        if client.token:
            return client.token

        token = gen_token()
        ClientModel.update({
            ClientModel.token: token,
            ClientModel.authorized_at: datetime.now().strftime(DATETIME_FORMAT)
        }).where(ClientModel.client_id == client_id).execute()
        return token

    @staticmethod
    def clear_token(uuid: str):
        client = ClientModel.get_or_none(ClientModel.uuid == uuid)
        if not client:
            return False

        ClientModel.update({ClientModel.token: None}).where(ClientModel.uuid == uuid).execute()
        return True

    @staticmethod
    def verify(uuid: str, token: str):
        if uuid and token:
            client = ClientModel.get_or_none(ClientModel.uuid == uuid, ClientModel.token == token)
            if client:
                return True

        return False

    @staticmethod
    def set_status(uuid: str, status: int = 0):
        ClientModel.update({ClientModel.status: status}).where(ClientModel.uuid == uuid).execute()

    @staticmethod
    def get_unverified_client():
        data = ClientModel.select().where(ClientModel.token.is_null())
        return data

    @staticmethod
    def get_verified_client():
        data = ClientModel.select().where(ClientModel.token.is_null(False))
        return data

    @staticmethod
    def remove_client(client_id: str):
        try:
            ClientModel.delete().where(ClientModel.client_id == int(client_id)).execute()
        except Exception as e:
            return e
