from peewee import PrimaryKeyField, CharField, DateTimeField, Model
from aiocrawler.distributed.server.model.db import db


class ProjectModel(Model):
    project_id = PrimaryKeyField()
    project_name = CharField(max_length=64, unique=True)
    created_at = DateTimeField()
    updated_at = DateTimeField()
    uploader = CharField(max_length=32)
    project_hash = CharField(max_length=40)

    class Meta:
        table_name = 'project'
        database = db


class ProjectDatabase(object):
    def __init__(self):
        if not ProjectModel.table_exists():
            ProjectModel.create_table()

    @staticmethod
    def new_project(project_name: str, created_at: str, updated_at: str, uploader: str, project_hash: str):
        ProjectModel.insert({
            ProjectModel.project_name: project_name,
            ProjectModel.created_at: created_at,
            ProjectModel.updated_at: updated_at,
            ProjectModel.uploader: uploader,
            ProjectModel.project_hash: project_hash
        }).execute()

    @staticmethod
    def update_project_hash(project_name: str, project_hash: str):
        ProjectModel.update({
            ProjectModel.project_hash: project_hash
        }).where(ProjectModel.project_name == project_name).execute()
