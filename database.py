import os
from sqlalchemy import create_engine, Column, Integer, String, Float, MetaData, Table
from sqlalchemy.orm import sessionmaker
import boto3
import streamlit as st

# Amazon S3設定
s3 = boto3.client(
    's3',
    aws_access_key_id=st.secrets["s3"]["aws_access_key_id"],
    aws_secret_access_key=st.secrets["s3"]["aws_secret_access_key"],
    region_name=st.secrets["s3"]["region"]
)
BUCKET_NAME = st.secrets["s3"]["bucket_name"]
DB_S3_PATH = 'DB/uploaded_data.db'

# S3からファイルをダウンロードする関数
def download_file_from_s3(s3_path, local_path):
    s3.download_file(BUCKET_NAME, s3_path, local_path)

# S3にファイルをアップロードする関数
def upload_file_to_s3(local_path, s3_path=None):
    if s3_path is None:
        s3_path = os.path.join('DB', os.path.basename(local_path))
    s3.upload_file(local_path, BUCKET_NAME, s3_path)
    return s3_path

# データベースディレクトリの設定
DB_DIR = "DB"
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

DATABASE_PATH = os.path.join(DB_DIR, 'uploaded_data.db')

# S3からデータベースファイルをダウンロード
if not os.path.exists(DATABASE_PATH):
    try:
        download_file_from_s3(DB_S3_PATH, DATABASE_PATH)
    except Exception as e:
        print(f"S3からデータベースファイルをダウンロードできませんでした: {e}")

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

# アプリケーションの終了時にデータベースをアップロード
import atexit

def at_exit():
    session.commit()  # データベースセッションのコミット
    upload_file_to_s3(DATABASE_PATH, DB_S3_PATH)  # パスを明示的に指定

atexit.register(at_exit)
