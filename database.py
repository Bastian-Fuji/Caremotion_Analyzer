import os
import boto3
from sqlalchemy import create_engine, Column, Integer, String, Float, MetaData, Table
from sqlalchemy.orm import sessionmaker

# Amazon S3認証
s3 = boto3.client(
    's3',
    aws_access_key_id=st.secrets["s3"]["aws_access_key_id"],
    aws_secret_access_key=st.secrets["s3"]["aws_secret_access_key"]
)
BUCKET_NAME = st.secrets["s3"]["bucket_name"]

# 保存ディレクトリの設定
SAVE_DIR = "uploaded_files"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

# S3にファイルをアップロードする関数
def upload_file_to_s3(local_path, bucket_name, s3_path):
    s3.upload_file(local_path, bucket_name, s3_path)
    return f"s3://{bucket_name}/{s3_path}"

# データベースディレクトリの設定
DB_DIR = "CareMotionAnalyzer/DB"
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

# データベースファイルをS3にアップロード
s3_db_path = upload_file_to_s3(DATABASE_PATH, BUCKET_NAME, 'uploaded_data.db')
