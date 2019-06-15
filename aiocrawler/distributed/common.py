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
    project_hashes = set()
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
        project_hashes.add(project['hash'])

        projects[project_name] = project

    return projects, project_hashes


def scan_project_dir(project_dir: Union[str, Path] = None, spider_name: str = 'spiders'):
    """
    :param project_dir:
    :param spider_name:
    """
    project_dir = Path(project_dir) if project_dir else Path('projects')
    spider_data = project_dir.glob('**/{}.py'.format(spider_name))
    return {
        spider_file.parent for spider_file in spider_data
    }


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
