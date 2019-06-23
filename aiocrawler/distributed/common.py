from hashlib import sha1
from datetime import datetime
from pathlib import Path
from typing import Union, Iterable

DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'


def scan(project_dir: Union[str, Path] = None, spider_name: str = 'spiders'):
    """
    :param project_dir:
    :param spider_name:
    :return:
    """
    projects = {}
    project_dir = Path(project_dir) if project_dir else Path('projects')
    spider_data = project_dir.glob('**/{}.py'.format(spider_name))
    for spider_file in spider_data:
        project_name = spider_file.parent.name
        project = {'files': {}, 'name': project_name, 'path': str(spider_file.parent)}

        stat = spider_file.stat()
        project['created_at'] = datetime.fromtimestamp(stat.st_ctime).strftime(DATETIME_FORMAT)
        project['updated_at'] = datetime.fromtimestamp(stat.st_mtime).strftime(DATETIME_FORMAT)

        files = spider_file.parent.glob('*.py')
        for file in files:
            project['files'][file.stem] = hash_file(file)

        project['hash'] = hash_strings(project['files'])

        projects[project_name] = project

    return projects


class ProjectScanner(object):
    def __init__(self, project_dir: Union[str, Path], spider_name: str = 'spiders'):
        self.project_dir = Path(project_dir) if project_dir else Path('projects')
        self.spider_name = spider_name
        self.projects = {}
        self.updated_at = {}
        self.scan()

    def scan(self):
        changed = {}
        for spider_file in self.project_dir.glob('**/{}.py'.format(self.spider_name)):
            project_name = spider_file.parent.name
            stat = spider_file.stat()
            if project_name not in self.projects:
                self.updated_at[project_name] = {}
                self.projects[project_name] = {'files': {}, 'name': project_name, 'path': str(spider_file.parent)}

                self.projects[project_name]['created_at'] = datetime.fromtimestamp(
                    stat.st_ctime).strftime(DATETIME_FORMAT)
                self.projects[project_name]['updated_at'] = datetime.fromtimestamp(
                    stat.st_mtime).strftime(DATETIME_FORMAT)

                for file in spider_file.parent.glob('*.py'):
                    self.projects[project_name]['files'][file.stem] = hash_file(file)
                    self.updated_at[project_name][file.stem] = file.stat().st_mtime

                self.projects[project_name]['hash'] = hash_strings(self.projects[project_name]['files'])
                self.projects[project_name] = self.projects[project_name]

                changed[project_name] = self.projects[project_name]
            else:
                updated_at = datetime.fromtimestamp(
                    stat.st_mtime).strftime(DATETIME_FORMAT)
                if self.projects[project_name]['updated_at'] != updated_at:
                    self.projects[project_name]['updated_at'] = updated_at
                    changed[project_name] = {'updated_at': updated_at}

                for file in spider_file.parent.glob('*.py'):
                    if file.stem not in self.updated_at[project_name] \
                            or file.stat().st_mtime != self.updated_at[project_name][file.stem]:

                        self.projects[project_name]['files'][file.stem] = hash_file(file)
                        self.projects[project_name]['hash'] = hash_strings(self.projects[project_name]['files'])

                        if project_name not in changed:
                            changed[project_name] = {'files': {}}
                        changed[project_name]['files'][file.stem] = self.projects[project_name]['files'][file.stem]
                        changed[project_name]['hash'] = self.projects[project_name]['hash']

                        self.updated_at[project_name][file.stem] = file.stat().st_mtime
        return changed


def hash_file(file: Union[str, Path], block_size=65536):
    """
    :param file:
    :param block_size:
    :return: the file sha1 hex digest
    """
    hash_data = sha1()
    file = Path(file)
    with file.open('rb') as fb:
        for block in iter(lambda: fb.read(block_size), b""):
            hash_data.update(block)

    return hash_data.hexdigest()


def hash_strings(strings: Iterable[str]):
    hash_data = sha1()
    for str_one in strings:
        hash_data.update(str_one.encode())

    return hash_data.hexdigest()
