from sys import path
from hashlib import sha1
from pathlib import Path
from typing import Union
from importlib import import_module
from aiocrawler import Spider


SPIDER_DIR = Path() / 'spiders'
# SPIDER_DIR.mkdir(exist_ok=True)
if str(SPIDER_DIR) not in path:
    path.append(str(SPIDER_DIR))

DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'


def scan_spider(spider_filename: str = 'spiders', spider_dir: Union[str, Path] = None):
    """
    scan spiders
    :param spider_dir: spider dir
    :param spider_filename: spider filename

    """
    '''spiders:
        {package: {
            'spider_count': count,
            'spiders': {
                spider_name: spider_classname
            },
            'files': {
                filename: hash
            },
            'created_at': time,
            'updated_at': time
        }}
    '''
    spiders = {}

    spider_dir = Path(spider_dir) if spider_dir else SPIDER_DIR
    spider_module = spider_dir.glob('**/{}.py'.format(spider_filename))
    for m in spider_module:
        stat = m.lstat()
        package = '.'.join(m.parts[:-1])

        spiders[package] = {
            'spider_count': 0,
            'spiders': {},
            'files': {},
            'created_at': stat.st_ctime,
            'updated_at': stat.st_mtime
        }

        for file in m.parent.glob('*.py'):
            spiders[package]['files'][file.name] = sha1_file(file)

        ms = import_module(package + '.{}'.format(spider_filename))
        for m_name in vars(ms).keys():
            spider = getattr(ms, m_name)
            if isinstance(spider, type) and issubclass(spider, Spider):
                spider_name = vars(spider).get('name', None)
                if spider_name:
                    spiders[package]['spiders'][spider_name] = m_name
                    spiders[package]['spider_count'] += 1

    return spiders


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
