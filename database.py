import os
from sqlalchemy import create_engine, Column, Integer, String, Float, MetaData, Table
from sqlalchemy.orm import sessionmaker
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import streamlit as st

# Google Drive認証
def authenticate_gdrive():
    gauth = GoogleAuth()
    gauth.settings['client_config_backend'] = 'settings'
    gauth.settings['oauth_scope'] = ['https://www.googleapis.com/auth/drive']
    gauth.settings['client_config'] = {
        "client_id": st.secrets["google_drive"]["client_id"],
        "client_secret": st.secrets["google_drive"]["client_secret"],
        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "revoke_uri": "https://oauth2.googleapis.com/revoke"
    }
    gauth.credentials = {
        "refresh_token": st.secrets["google_drive"]["refresh_token"]
    }
    gauth.Authorize()
    return GoogleDrive(gauth)

drive = authenticate_gdrive()

# 保存ディレクトリの設定
SAVE_DIR = "uploaded_files"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

# データベースファイルのGoogle Driveアップロード
def upload_file_to_gdrive(local_path, gdrive_folder_id=None):
    file_name = os.path.basename(local_path)
    gfile = drive.CreateFile({'title': file_name, 'parents': [{'id': gdrive_folder_id}] if gdrive_folder_id else []})
    gfile.SetContentFile(local_path)
    gfile.Upload()
    return gfile['id']

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

# データベースファイルをGoogle Driveにアップロード
db_file_id = upload_file_to_gdrive(DATABASE_PATH)
