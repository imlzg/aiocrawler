from hashlib import sha1
from pathlib import Path
from typing import Union

DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'


def scan(project_dir: Union[str, Path] = None, spider_name: str = 'spiders'):
    """
    :param project_dir:
    :param spider_name:
    :return:
    """
    projects = []
    project_dir = Path(project_dir) if project_dir else Path('projects')
    spider_data = project_dir.glob('**/{}.py'.format(spider_name))
    for idx, spider_file in enumerate(spider_data):
        project = {'id': idx, 'name': spider_file.parent.name, 'files': {}}

        stat = spider_file.stat()
        project['created_at'] = stat.st_ctime
        project['updated_at'] = stat.st_mtime
        files = spider_file.parent.glob('*.py')
        for file in files:
            project['files'][file.name] = sha1_file(file)
        projects.append(project)

    return projects


def sha1_file(file: Union[str, Path], block_size=65536):
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
