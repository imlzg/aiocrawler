# coding: utf-8
from pathlib import Path
from datetime import date
from typing import Union
from string import Template
import traceback
from aiocrawler.settings import BaseSettings


class SpiderTemplate(object):
    def __init__(self, project_name: str, output_dir: Union[Path, str] = ''):
        self.__templates_dir = Path(__file__).parent.parent/'templates'
        self.__logger = BaseSettings.LOGGER

        self.__project_name = project_name
        self.__output_dir = Path(output_dir)
        self.__project_dir = self.__output_dir/self.__project_name

    def gen_project(self):
        if self.__project_dir.is_dir():
            self.__logger.error('The target Project "{project_name}" already exists',
                                project_name=self.__project_name)
            return

        try:
            self.__project_dir.mkdir()
            self.__gen_spiders__()
            self.__gen_settings__()
            self.__gen_middlewares__()
            self.__gen_items__()
            self.__gen_run__()

            self.__logger.success('The Project "{project_name}" was created successfully.',
                                  project_name=self.__project_name)
        except Exception as e:
            files = self.__project_dir.glob('*')
            for file in files:
                file.unlink()
            self.__project_dir.rmdir()

            self.__logger.error(traceback.format_exc(limit=10))

    def gen(self, tmpl_name: str, sub_data: dict):
        tmpl_file = self.__templates_dir/tmpl_name
        output_name = Path(tmpl_name).stem + '.py'

        default_data = {
            'date': date.today(),
            'project_name': self.__project_name,
            'filename': output_name,
        }
        sub_data.update(default_data)

        if tmpl_file.is_file():
            with tmpl_file.open('r') as f:
                content = f.read()
            tmpl = Template(content).substitute(sub_data)

            output = Path(self.__project_dir)/output_name
            with output.open('w') as f:
                f.write(tmpl)

            self.__logger.success('Generated {filename}', filename=str(output))
        else:
            self.__logger.error('{template_name} does not exist', template_name=tmpl_name)

    def __gen_spiders__(self):
        tmpl_name = 'spiders.tmpl'
        sub_data = {
            'classname': self.__project_name.capitalize() + 'Spider',
            'name': self.__project_name.lower()
        }
        self.gen(tmpl_name=tmpl_name, sub_data=sub_data)

    def __gen_run__(self):
        tmpl_name = 'run.tmpl'
        sub_data = {
            'spider_name': self.__project_name.capitalize() + 'Spider',
            'settings_name': self.__project_name.capitalize() + 'Settings',
        }
        self.gen(tmpl_name=tmpl_name, sub_data=sub_data)

    def __gen_middlewares__(self):
        tmpl_name = 'middlewares.tmpl'
        sub_data = {
            'classname': self.__project_name.capitalize() + 'Middleware'
        }
        self.gen(tmpl_name=tmpl_name, sub_data=sub_data)

    def __gen_settings__(self):
        tmpl_name = 'settings.tmpl'
        sub_data = {
            'classname': self.__project_name.capitalize() + 'Settings',
            'middleware_name': self.__project_name.capitalize() + 'Middleware'
        }
        self.gen(tmpl_name=tmpl_name, sub_data=sub_data)

    def __gen_items__(self):
        tmpl_name = 'items.tmpl'
        sub_data = {
            'classname': self.__project_name.capitalize() + 'Item'
        }
        self.gen(tmpl_name=tmpl_name, sub_data=sub_data)
