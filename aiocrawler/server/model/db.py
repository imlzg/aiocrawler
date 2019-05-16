from pathlib import Path
from peewee import SqliteDatabase

current_path = Path(__file__).parent.parent
data_dir = (current_path/"data")
data_dir.mkdir(exist_ok=True)

db = SqliteDatabase(str(data_dir/"user.db"))
