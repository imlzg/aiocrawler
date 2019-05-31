from peewee import (Model,
                    CharField,
                    IntegerField,
                    DateTimeField,
                    BooleanField,
                    FloatField,
                    ForeignKeyField)
from peewee import JOIN
from aiocrawler.distributed.server.model.db import db


class RequestMethodModel(Model):
    session_id = CharField(max_length=40, primary_key=True, unique=True)
    method = CharField(max_length=8, default='GET')
    method_count = IntegerField(default=0)

    class Meta:
        table_name = 'task_request_method'
        database = db


class ResponseStatusModel(Model):
    session_id = CharField(max_length=40, primary_key=True, unique=True)
    status = CharField(max_length=8, default='200')
    status_count = IntegerField(default=0)

    class Meta:
        table_name = 'task_response_status'
        database = db


class ItemCountModel(Model):
    session_id = CharField(max_length=40, primary_key=True, unique=True)
    item_name = CharField(max_length=16)
    item_count = IntegerField(default=0)

    class Meta:
        table_name = 'task_item_count'
        database = db


class TaskModel(Model):
    session_id = CharField(max_length=40, primary_key=True, unique=True)
    uuid = CharField(max_length=40, unique=True)
    spider_name = CharField(max_length=32, null=True)
    running = BooleanField(default=False)
    start_time = DateTimeField(null=True)
    done_startup_tasks = BooleanField(default=False)
    done_cleanup_tasks = BooleanField(default=False)

    word_received_count = IntegerField(default=0)
    item_count = ForeignKeyField(ItemCountModel, backref='item_count', null=True)

    request_count = IntegerField(default=0)
    request_method = ForeignKeyField(RequestMethodModel, backref='request_method', null=True)

    response_received_count = IntegerField(default=0)
    response_status = ForeignKeyField(ResponseStatusModel, backref='response_status', null=True)
    response_bytes = FloatField(default=0.0)

    exception_count = IntegerField(default=0)
    finish_reason = CharField(max_length=128, default='Finished')
    finish_time = DateTimeField(null=True)

    class Meta:
        table_name = 'task'
        database = db


class TaskDatabase(object):
    def __init__(self):
        if not TaskModel.table_exists():
            TaskModel.create_table()
        if not RequestMethodModel.table_exists():
            RequestMethodModel.create_table()
        if not ResponseStatusModel.table_exists():
            ResponseStatusModel.create_table()
        if not ItemCountModel.table_exists():
            ItemCountModel.create_table()

    @staticmethod
    def replace(uuid: str, session_id: str, data: dict):
        if 'request_method_count' in data:
            method, count = data.pop('request_method_count').items()
            RequestMethodModel.replace({RequestMethodModel.session_id: session_id,
                                        RequestMethodModel.method: method,
                                        RequestMethodModel.count: count}).execute()

        if 'response_status_count' in data:
            status, count = data.pop('response_status_count').items()
            ResponseStatusModel.replace({ResponseStatusModel.session_id: session_id,
                                         ResponseStatusModel.status: status,
                                         ResponseStatusModel.count: count}).execute()

        if 'item_count' in data:
            item_name, count = data.pop('item_count').items()
            ItemCountModel.replace({ItemCountModel.session_id: session_id,
                                    ItemCountModel.item_name: item_name,
                                    ItemCountModel.count: count}).execute()
        data['session_id'] = session_id
        data['uuid'] = uuid
        TaskModel.replace(data).execute()

    @staticmethod
    def get_client_task(uuid: str):
        data = TaskModel.select(TaskModel, RequestMethodModel, ResponseStatusModel).join(
            RequestMethodModel, JOIN.LEFT_OUTER, on=(TaskModel.session_id == RequestMethodModel.session_id),
        ).join(
            ResponseStatusModel, on=(TaskModel.session_id == ResponseStatusModel.session_id)
        ).join(
            ItemCountModel, on=(TaskModel.session_id == ItemCountModel.session_id)
        ).where(TaskModel.uuid == uuid).execute()
        return data

    @staticmethod
    def get_task_count():
        count = TaskModel.select().count()
        return count

    @staticmethod
    def get_all_task():
        tasks = TaskModel.select()
        return tasks

    @staticmethod
    def get_active_task_count():
        count = TaskModel.select().where(TaskModel.running is True).count()
        return count

    @staticmethod
    def get_active_task():
        tasks = TaskModel.select().where(TaskModel.running is True)
        return tasks
