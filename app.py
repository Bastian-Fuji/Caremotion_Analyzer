import streamlit as st
import os
import json
from datetime import datetime
from bvh_parser import BVHParser
from database import session, uploads_table, SAVE_DIR, upload_file_to_s3, BUCKET_NAME
import numpy as np
import pandas as pd
from streamlit_option_menu import option_menu
import matplotlib.pyplot as plt
import japanize_matplotlib
import io

# サイドバーにメニューを追加
with st.sidebar:
    selected = option_menu(
        menu_title=None,  # メニュータイトル
        options=["メインページ", "ダッシュボード", "動作比較"],  # メニューオプション
        icons=["house", "bar-chart", "arrows-move"],  # メニューアイコン
        menu_icon="cast",  # メニューアイコン
        default_index=0,  # デフォルト選択
    )

# セッション状態の初期化
if 'gender' not in st.session_state:
    st.session_state.gender = "選択してください"
if 'age' not in st.session_state:  # 年齢の初期化
    st.session_state.age = 40
if 'height' not in st.session_state:
    st.session_state.height = 170
if 'weight' not in st.session_state:
    st.session_state.weight = 60
if 'experience' not in st.session_state:
    st.session_state.experience = 5
if 'care_action' not in st.session_state:
    st.session_state.care_action = "選択してください"
if 'uploaded_file' not in st.session_state:
    st.session_state.uploaded_file = None
if 'lifting_index' not in st.session_state:
    st.session_state.lifting_index = None
if 'bvh_path' not in st.session_state:
    st.session_state.bvh_path = None
if 'submitted' not in st.session_state:
    st.session_state.submitted = False

if selected == "メインページ":
    st.title("動作分析")

    st.markdown("""
        <style>
        .stButton button {
            background-color: #4CAF50;
            color: white;
            padding: 14px 20px;
            margin: 8px 0;
            border: none;
            cursor: pointer;
            width: 100%;
            opacity: 0.9;
        }
        .stButton button:hover {
            opacity: 1;
        }
        .stSelectbox label, .stNumberInput label {
            font-weight: bold;
            margin-bottom: 5px;
        }
        .stSelectbox, .stNumberInput, .stFileUploader {
            margin-bottom: 20px;
        }
        </style>
    """, unsafe_allow_html=True)

    # 性別選択
    st.session_state.gender = st.selectbox(
        "性別",
        ["選択してください", "男性", "女性", "ノンバイナリー", "答えたくない", "その他"],
        index=["選択してください", "男性", "女性", "ノンバイナリー", "答えたくない", "その他"].index(st.session_state.gender)
    )

    # 年齢入力
    age = st.number_input("年齢 (歳)", min_value=0, value=st.session_state.age)  # 年齢入力欄の追加

    # 身長入力
    height = st.number_input("身長 (cm)", min_value=0, value=st.session_state.height)

    # 体重入力
    weight = st.number_input("体重 (kg)", min_value=0, value=st.session_state.weight)

    # 介護士歴入力
    experience = st.number_input("介護士歴 (年)", min_value=0, value=st.session_state.experience)

    # 介護動作選択
    care_action = st.selectbox(
        "介護動作",
        ["選択してください", "移乗介助", "その他"],
        index=["選択してください", "移乗介助", "その他"].index(st.session_state.care_action)
    )

    # BVHファイルアップロード
    uploaded_file = st.file_uploader("BVHファイルをアップロード", type=["bvh"])
    if uploaded_file is not None:
        st.session_state.uploaded_file = uploaded_file

    # NIOSH Lifting Equationの評価関数
    def calculate_niosh_lifting_index(start_height, end_height, weight, asymmetry_angle):
        # 定数
        LC = 23  # Load Constant (kg)
        HM = 1.5  # 20(cm)用
        VM = 1 - (0.0075 * abs(start_height - 75))  # Vertical Multiplier
        DM = 0.82 + (4.5 / 1000 * abs(start_height - end_height))  # Distance Multiplier
        FM = 1  # (Times)
        AM = 1 - (asymmetry_angle * 0.0032)  # Asymmetry Multiplier
        CM = 1  # Coupling Multiplier (assumed)

        RWL = LC * HM * VM * DM * FM * AM * CM  # Recommended Weight Limit
        LI = weight / RWL  # Lifting Index

        return LI

    if st.button("送信"):
        if st.session_state.gender == "選択してください":
            st.error("性別を選択してください")
        elif care_action == "選択してください":
            st.error("介護動作を選択してください")
        elif not st.session_state.uploaded_file:
            st.error("BVHファイルをアップロードしてください")
        else:
            try:
                # 現在のタイムスタンプを取得
                timestamp = datetime.now().strftime("%Y%m%d%H%MS")

                # ファイル名を生成
                bvh_filename = f"{timestamp}_{st.session_state.uploaded_file.name}"

                # BVHファイルに保存
                bvh_path = os.path.join(SAVE_DIR, bvh_filename)
                with open(bvh_path, "wb") as f:
                    f.write(st.session_state.uploaded_file.getbuffer())

                # BVHファイルをS3にアップロード
                s3_bvh_path = upload_file_to_s3(bvh_path, BUCKET_NAME, bvh_filename)

                # BVHデータを解析
                bvh_parser = BVHParser(bvh_path)
                bvh_parser.parse()

                # 持ち上げ開始位置と終了位置の取得
                root_node = bvh_parser.get_root()
                frame_data = bvh_parser.frames
                
                # ここでは腰の位置を取得することを仮定
                # "root"ノードが存在することを前提にしています
                hips_node = root_node  # rootノードが腰の位置を示していると仮定

                # 全フレームの腰の位置を取得
                hip_positions = np.array([frame[:3] for frame in hips_node.channel_values])
                hip_rotations = np.array([frame[3:6] for frame in hips_node.channel_values])  # 追加：腰の回転角を取得
                
                # 最も低い位置と最も高い位置を取得
                start_position = hip_positions[np.argmin(hip_positions[:, 1])]
                end_position = hip_positions[np.argmax(hip_positions[:, 1])]
                
                start_height = start_position[1]
                end_height = end_position[1]

                # 非対称角度の計算（腰の回転角の2分の1）
                max_rotation = np.max(hip_rotations, axis=0)
                asymmetry_angle = max_rotation[1]  # Y軸の回転角度を使用
                
                # 重さの取得
                weight_lifted = 25  # 入力された体重を使用

                # NIOSH Lifting Equationの評価
                lifting_index = calculate_niosh_lifting_index(start_height, end_height, weight_lifted, asymmetry_angle)

                st.session_state.lifting_index = lifting_index
                st.session_state.bvh_path = bvh_path
                st.session_state.submitted = True

                st.success(f"データが保存されました: {s3_bvh_path}")

                st.write(f"NIOSH Lifting Index: {lifting_index:.2f}")

                # データベースに保存
                session.execute(
                    uploads_table.insert().values(
                        gender=st.session_state.gender,
                        age=age,  # 年齢を追加
                        height=height,
                        weight=weight,
                        experience=experience,
                        care_action=care_action,
                        niosh_index=lifting_index,
                        bvh_filename=s3_bvh_path,
                    )
                )
                session.commit()

                # セッションステートを更新
                st.session_state.age = age
                st.session_state.height = height
                st.session_state.weight = weight
                st.session_state.experience = experience
                st.session_state.care_action = care_action

                # 自分のNIOSH Indexの位置を表示
                query = session.query(uploads_table).all()
                columns = ["id", "gender", "age", "height", "weight", "experience", "care_action", "niosh_index", "bvh_filename"]
                data = [{column: getattr(record, column) for column in columns} for record in query]
                df = pd.DataFrame(data)
                if not df.empty:
                    percentile = (df['niosh_index'] < lifting_index).mean() * 100
                    st.write(f"あなたのNIOSH Indexは全体の上位{percentile:.2f}%です。")
                else:
                    st.write("データが不足しています。")

                # BVHデータをJavaScript用に変換
                def node_to_dict(node):
                    return {
                        "name": node.name,
                        "offset": node.offset.tolist(),
                        "channels": node.channels,
                        "channel_values": node.channel_values,
                        "children": [node_to_dict(child) for child in node.children]
                    }

                bvh_data = {
                    "root": node_to_dict(root_node),
                    "frames": bvh_parser.frames,
                    "frame_time": bvh_parser.frame_time
                }

                bvh_json = json.dumps(bvh_data)

                # HTMLテンプレートの読み込み
                with open('template.html', 'r') as file:
                    html_template = file.read()

                # JavaScriptでBVHをビジュアライズするHTMLテンプレートにデータを埋め込む
                html_template = html_template.replace('{{bvh_json}}', bvh_json)
                
                st.components.v1.html(html_template, height=600)
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")

elif selected == "ダッシュボード":
    st.title("データ分布ダッシュボード")

    # NIOSH Indexの説明を追加
    with st.expander("NIOSH Lifting Index とは？"):
        st.write("""
        NIOSH Lifting Index（NIOSHリフティングインデックス）は、作業者が持ち上げる重量が作業者の能力に対して適切かどうかを評価するための指標です。指数が1以下であれば安全な持ち上げとされ、1を超えると持ち上げ作業がリスクを伴うと判断されます。指数は以下のような要素を考慮して計算されます：
        - 持ち上げる物の重量
        - 持ち上げる高さ
        - 作業の対称性（体の回転角度）
        - 持ち上げる距離
        これらの要素を組み合わせて計算されたNIOSH Lifting Indexにより、持ち上げ作業のリスク評価が行われます。
        """)

    # データの取得
    def load_data():
        query = session.query(uploads_table).all()
        columns = ["id", "gender", "age", "height", "weight", "experience", "care_action", "niosh_index", "bvh_filename"]
        data = [{column: getattr(record, column) for column in columns} for record in query]
        return pd.DataFrame(data)

    df = load_data()

    # NIOSH Indexの計算状態を確認
    st.subheader("あなたのNIOSH Lifting Index")
    if st.session_state.submitted:
        st.write(f"あなたのNIOSH Lifting Indexは {st.session_state.lifting_index:.2f} です。")
    else:
        st.write("あなたのNIOSH Lifting Indexはまだ計算されていません。")

    if not df.empty:
        # NIOSH Indexの分布
        st.subheader("年齢ごとのNIOSH Indexの分布")
        age_groups = st.slider("年齢グループの範囲を選択してください", 0, 100, (20, 50), 1)

        # 指定された年齢範囲でデータをフィルタリング
        filtered_df = df[(df['age'] >= age_groups[0]) & (df['age'] <= age_groups[1])]
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # 横軸を年齢、縦軸をNIOSH Indexに設定して散布図をプロット
        ax.scatter(filtered_df['age'], filtered_df['niosh_index'], alpha=0.6, edgecolors='w', linewidth=0.5)
        ax.set_title(f"年齢{age_groups[0]}歳から{age_groups[1]}歳のNIOSH Indexの分布", fontsize=16)
        ax.set_xlabel("年齢", fontsize=14)
        ax.set_ylabel("NIOSH Index", fontsize=14)
        ax.grid(True)
        st.pyplot(fig)

        # 自分のNIOSH Indexの位置
        if st.session_state.submitted:
            percentile = (df['niosh_index'] < st.session_state.lifting_index).mean() * 100
            st.info(f"あなたのNIOSH Indexは全体の上位{percentile:.2f}%です。")

        # 性別ごとのNIOSH Indexの平均
        st.subheader("性別ごとのNIOSH Indexの分布")
        fig, ax = plt.subplots(figsize=(10, 6))
        df.boxplot(column='niosh_index', by='gender', ax=ax, grid=False, patch_artist=True)
        ax.set_title('性別ごとのNIOSH Indexの分布', fontsize=16)
        ax.set_xlabel('性別', fontsize=14)
        ax.set_ylabel('NIOSH Index', fontsize=14)
        plt.suptitle('')  # デフォルトのタイトルを削除
        st.pyplot(fig)

        # 経験年数とNIOSH Indexの関係
        st.subheader("経験年数とNIOSH Indexの関係")
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.scatter(df['experience'], df['niosh_index'], alpha=0.6, edgecolors='w', linewidth=0.5)
        ax.set_title('経験年数とNIOSH Indexの関係', fontsize=16)
        ax.set_xlabel('経験年数 (年)', fontsize=14)
        ax.set_ylabel('NIOSH Index', fontsize=14)
        ax.grid(True)
        st.pyplot(fig)

        # 体重とNIOSH Indexの関係
        st.subheader("体重とNIOSH Indexの関係")
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.scatter(df['weight'], df['niosh_index'], alpha=0.6, edgecolors='w', linewidth=0.5)
        ax.set_title('体重とNIOSH Indexの関係', fontsize=16)
        ax.set_xlabel('体重 (kg)', fontsize=14)
        ax.set_ylabel('NIOSH Index', fontsize=14)
        ax.grid(True)
        st.pyplot(fig)

        # 介護動作別のNIOSH Indexの分布
        st.subheader("介護動作別のNIOSH Indexの分布")
        fig, ax = plt.subplots(figsize=(10, 6))
        df.boxplot(column='niosh_index', by='care_action', ax=ax, grid=False, patch_artist=True)
        ax.set_title('介護動作別のNIOSH Indexの分布', fontsize=16)
        ax.set_xlabel('介護動作', fontsize=14)
        ax.set_ylabel('NIOSH Index', fontsize=14)
        plt.suptitle('')  # デフォルトのタイトルを削除
        st.pyplot(fig)

        # NIOSH Indexの平均および標準偏差
        st.subheader("NIOSH Indexの平均および標準偏差")
        mean_index = df['niosh_index'].mean()
        std_index = df['niosh_index'].std()
        st.write(f"NIOSH Indexの平均値: {mean_index:.2f}")
        st.write(f"NIOSH Indexの標準偏差: {std_index:.2f}")

        # 相関分析
        st.subheader("相関分析")
        numeric_df = df.drop(columns=['id']).select_dtypes(include=[np.number])  # 数値データのみ選択（id 列を除外）
        corr_matrix = numeric_df.corr()
        fig, ax = plt.subplots(figsize=(10, 6))
        cax = ax.matshow(corr_matrix, cmap='coolwarm')
        fig.colorbar(cax)
        ticks = np.arange(0, len(corr_matrix.columns), 1)
        ax.set_xticks(ticks)
        ax.set_yticks(ticks)
        ax.set_xticklabels(corr_matrix.columns, rotation=45, ha="left")
        ax.set_yticklabels(corr_matrix.columns)
        st.pyplot(fig)

        # CSVとしてデータをダウンロード
        st.subheader("データのダウンロード")
        csv_buffer = io.StringIO()
        df.drop(columns=["bvh_filename"]).to_csv(csv_buffer, index=False, encoding='utf-8')
        csv_data = csv_buffer.getvalue().encode('utf-8-sig')
        st.download_button(
            label="データをCSVとしてダウンロード",
            data=csv_data,
            file_name='niosh_index_data.csv',
            mime='text/csv',
        )

        # データの詳細表示
        st.subheader("データの詳細表示")
        st.dataframe(df.drop(columns=["bvh_filename", "id"]))
    else:
        st.warning("データが不足しています。")

elif selected == "動作比較":
    st.title("動作比較")

    # データの取得
    def load_data():
        query = session.query(uploads_table).all()
        columns = ["id", "gender", "age", "height", "weight", "experience", "care_action", "niosh_index", "bvh_filename"]
        data = [{column: getattr(record, column) for column in columns} for record in query]
        return pd.DataFrame(data)

    df = load_data()

    if not df.empty:
        st.subheader("動作IDを選択してください")

        # 動作ID選択肢をカスタマイズ
        df['display_name'] = df.apply(lambda row: f"{row['id']} : (介護士歴{row['experience']}年, NIOSH Index {row['niosh_index']:.2f})", axis=1)
        selected_display_name = st.selectbox("動作ID", df['display_name'].values)

        if selected_display_name:
            selected_id = int(selected_display_name.split(' : ')[0])
            selected_record = df[df['id'] == selected_id].iloc[0]
            bvh_filename = selected_record['bvh_filename']
            bvh_path = os.path.join(SAVE_DIR, bvh_filename)

            # 選択されたIDの詳細情報を表示
            st.write("### 選択された動作の詳細")
            st.write(f"**ID:** {selected_record['id']}")
            st.write(f"**性別:** {selected_record['gender']}")
            st.write(f"**年齢:** {selected_record['age']}歳")
            st.write(f"**身長:** {selected_record['height']}cm")
            st.write(f"**体重:** {selected_record['weight']}kg")
            st.write(f"**介護士歴:** {selected_record['experience']}年")
            st.write(f"**介護動作:** {selected_record['care_action']}")
            st.write(f"**NIOSH Index:** {selected_record['niosh_index']:.2f}")

            try:
                bvh_parser = BVHParser(bvh_path)
                bvh_parser.parse()

                # BVHデータをJavaScript用に変換
                def node_to_dict(node):
                    return {
                        "name": node.name,
                        "offset": node.offset.tolist(),
                        "channels": node.channels,
                        "channel_values": node.channel_values,
                        "children": [node_to_dict(child) for child in node.children]
                    }

                root_node = bvh_parser.get_root()
                bvh_data = {
                    "root": node_to_dict(root_node),
                    "frames": bvh_parser.frames,
                    "frame_time": bvh_parser.frame_time
                }

                bvh_json = json.dumps(bvh_data)

                # HTMLテンプレートの読み込み
                with open('template.html', 'r') as file:
                    html_template = file.read()

                # JavaScriptでBVHをビジュアライズするHTMLテンプレートにデータを埋め込む
                html_template = html_template.replace('{{bvh_json}}', bvh_json)
                
                st.components.v1.html(html_template, height=600)
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
    else:
        st.warning("データが不足しています。")
