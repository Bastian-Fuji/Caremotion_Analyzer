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

# S3にファイルをアップロードする関数
def upload_file_to_s3(local_path, s3_path=None):
    if s3_path is None:
        s3_path = os.path.basename(local_path)
    s3.upload_file(local_path, BUCKET_NAME, s3_path)
    return s3_path

# 保存ディレクトリの設定
SAVE_DIR = "uploaded_files"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

# データベースディレクトリの設定
DB_DIR = "CareMotionAnalyzer/DB"
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

# データベース設定
DATABASE_URL = f"sqlite:///{os.path.join(DB_DIR, 'uploaded_data.db')}"
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
