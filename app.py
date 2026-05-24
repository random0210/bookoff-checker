import streamlit as st
import pandas as pd
import os
import re

# 1. ページの設定（タイトルやレイアウト）
st.set_page_config(page_title="任天堂中古ゲーム 相場検索システム", layout="wide")

st.title("🎮 任天堂中古ゲームソフト 相場検索システム")
st.caption("ブックオフオンラインのデータからリアルタイム（収集時点）の相場を分析します")

# 🔄 古いバグデータを強制クリアするためのボタンを設置
if st.button("🔄 アプリのデータを最新の状態に更新（キャッシュクリア）"):
    st.cache_data.clear()
    st.success("古いデータをクリアしました！画面をリロードしてください。")

# 2. CSVデータの読み込み処理
csv_file = "bookoff_all_games.csv"

if not os.path.exists(csv_file):
    st.error(f"❌ データファイル（{csv_file}）が見つかりません。先に `crawler.py` を実行してデータを収集してください。")
else:
    @st.cache_data
    def load_data():
        df = pd.read_csv(csv_file)
        
        # 🔥 超強力版：最初の「¥」から始まる塊だけを狙い撃ちするロジック
        def clean_price(x):
            try:
                if pd.isna(x): return None
                s = str(x).strip()
                
                # 正規表現で「¥」の直後にある数字とカンマの塊（最初の金額）だけを抽出
                # 例: "¥4,510定価より..." -> "4,510" だけを取り出す
                match = re.search(r'¥([\d,]+)', s)
                if match:
                    digits = match.group(1).replace(',', '')
                    return int(digits)
                
                # 万が一 ¥ がない場合は、最初の「定価より」や「円」の前を切り出す（予備）
                first_part = re.split(r'定価より|\(|円', s)[0]
                digits = "".join([c for c in first_part if c.isdigit()])
                return int(digits) if digits else None
            except:
                return None
        
        # 計算用の数値を「価格_数値」列として追加
        df['価格_数値'] = df['価格'].apply(clean_price)
        return df

    df = load_data()

    # 3. サイドバーの検索・フィルター機能
    st.sidebar.header("🔍 検索フィルター")
    
    # 機種での絞り込み
    hardware_list = ["すべて"] + list(df["機種"].unique())
    selected_hardware = st.sidebar.selectbox("機種を選択", hardware_list)
    
    # タイトルのキーワード検索
    search_keyword = st.sidebar.text_input("ゲームタイトルで検索 (部分一致)")

    # 4. データのフィルタリング
    filtered_df = df.copy()
    if selected_hardware != "すべて":
        filtered_df = filtered_df[filtered_df["機種"] == selected_hardware]
    
    if search_keyword:
        filtered_df = filtered_df[filtered_df["ゲームタイトル"].str.contains(search_keyword, case=False, na=False)]

    # 5. 相場情報のダッシュボード表示
    st.subheader("📊 検索結果の相場統計")
    
    # 有効な価格データがあるものだけで統計を計算
    valid_prices = filtered_df['価格_数値'].dropna()
    
    if not valid_prices.empty:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("該当件数", f"{len(filtered_df)} 件")
        with col2:
            st.metric("最安値", f"¥{int(valid_prices.min()):,} -")
        with col3:
            st.metric("最高値", f"¥{int(valid_prices.max()):,} -")
        with col4:
            st.metric("平均相場", f"¥{int(valid_prices.mean()):,} -")
    else:
        st.warning("該当する価格データがないか、検索結果が0件です。")

    st.markdown("---")

    # 6. データ一覧の表示
    st.subheader("📋 該当ソフト一覧")
    
    if not filtered_df.empty:
        display_df = filtered_df[["機種", "ゲームタイトル", "価格", "詳細URL"]]
        
        st.dataframe(
            display_df,
            column_config={
                "詳細URL": st.column_config.LinkColumn("ブックオフ商品リンク")
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("条件に一致するゲームソフトがありません。別のキーワードをお試しください。")