import os
from sqlalchemy import create_engine, Column, Integer, String, Float, MetaData, Table
from sqlalchemy.orm import sessionmaker

# 保存ディレクトリの設定
SAVE_DIR = "BVH"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

# データベースディレクトリの設定
DB_DIR = "DB"
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

DATABASE_PATH = os.path.join(DB_DIR, 'uploaded_data.db')

# データベース設定
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
engine = create_engine(DATABASE_URL)

metadata = MetaData()

# テーブルの定義
uploads_table = Table(
    "uploads",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("gender", String),
    Column("age", Integer),
    Column("height", Float),
    Column("weight", Float),
    Column("experience", Integer),
    Column("care_action", String),
    Column("niosh_index", Float),
    Column("bvh_filename", String)
)

# テーブルを作成
metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()
