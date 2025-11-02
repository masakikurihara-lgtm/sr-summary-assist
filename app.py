import streamlit as st
import pandas as pd
from io import StringIO
import datetime
from dateutil.relativedelta import relativedelta


# --- ページ設定 ---
st.set_page_config(layout="wide", page_title="SHOWROOMライバーデータ整理ツール")


# --- 定数（URL） ---
KPI_DATA_BASE_URL = "https://mksoul-pro.com/showroom/csv/{year}-{month:02d}_all_all.csv"
# 管理ライバーリスト（1列目:ID, 2列目:ライバー愛称）
LIVER_LIST_URL = "https://mksoul-pro.com/showroom/file/m-liver-list.csv"
# ルーム名一覧（今回は使用しません）
ROOM_LIST_URL = "https://mksoul-pro.com/showroom/file/room_list.csv" 


## データの準備・読み込み関数
@st.cache_data
def load_data(url, name="データ"):
    """URLからCSVを読み込み、DataFrameとして返す（ヘッダーあり前提）"""
    try:
        df = pd.read_csv(url) 
        return df
    except Exception as e:
        st.error(f"{name}の読み込みに失敗しました: {url}\nエラー: {e}")
        return None

@st.cache_data
def get_processed_months():
    """プルダウンに表示する処理月リストを生成する"""
    today = datetime.date.today()
    current_date = today - relativedelta(months=1)
    processed_months = []

    for i in range(12): 
        display_str = f"{current_date.year}年{current_date.month:02d}月分"
        value_str = f"{current_date.year}-{current_date.month:02d}"
        processed_months.append((display_str, value_str))
        current_date = current_date - relativedelta(months=1)
            
    return processed_months

## メインアプリケーション
def main():
    st.title("🎤 SHOWROOMライバーデータ整理ツール (配信有無チェック)")

    st.header("1. 処理月の選択と実行")
    
    month_options = get_processed_months()
    display_options = [opt[0] for opt in month_options]
    value_options = [opt[1] for opt in month_options]
    
    selected_display_month = st.selectbox(
        "処理する**配信月**を選択してください:",
        options=display_options,
        index=0
    )
    
    try:
        selected_index = display_options.index(selected_display_month)
        selected_value_month = value_options[selected_index]
        year, month = map(int, selected_value_month.split('-'))
        
        delivery_month_str = f"{year}/{month:02d}"
        delivery_date = datetime.date(year, month, 1)
        payment_date = delivery_date + relativedelta(months=2)
        payment_month_str = f"{payment_date.year}/{payment_date.month:02d}"
        
    except:
        st.warning("有効な処理月が選択されていません。")
        return
    
    st.markdown("---")
    if st.button("🚀 データ処理を開始する", type="primary"):
        process_data(year, month, delivery_month_str, payment_month_str)
    else:
        st.info(f"選択された配信月: **{selected_display_month}**。処理を開始するには上記のボタンを押してください。")
    st.markdown("---")


# データ処理のメインロジック (ボタンが押されたときのみ実行)
def process_data(year, month, delivery_month_str, payment_month_str):
    
    with st.spinner("データを読み込み、配信有無をチェックしています..."):
        
        # 2. データの読み込みとマッピング
        
        # 2.1. 管理ライバーリストの読み込み (m-liver-list.csv)
        st.subheader("管理ライバーリストの読み込みと愛称マッピングの作成")
        liver_df = load_data(LIVER_LIST_URL, "管理ライバーリスト")
        if liver_df is None: return
        
        # 1列目 (ID) と 2列目 (ライバー愛称) の両方を使用
        if liver_df.shape[1] >= 2:
            
            # 1列目 (ID) をキーに、2列目 (ライバー愛称) を値として辞書を作成
            df_keys = liver_df.iloc[:, 0].astype(str).str.strip()
            df_values = liver_df.iloc[:, 1].astype(str).str.strip() 
            
            # ルームIDと愛称の辞書
            liver_alias_map = pd.Series(df_values.values, index=df_keys).to_dict()
            
            # IDリストも1列目から抽出
            liver_ids = df_keys.tolist()
            
            st.success(f"管理ライバーのルームIDリスト（1列目）と愛称（2列目）を読み込みました。件数: **{len(liver_ids)}**")
        else:
            st.error("管理ライバーリストCSVにデータ（1列目:ID, 2列目:愛称）が見つかりません。")
            return
        
        # 2.2. KPIデータ（配信有無）の読み込み (YYYY-MM_all_all.csv)
        st.subheader(f"{year}年{month:02d}月分のKPIデータの読み込み")
        kpi_url = KPI_DATA_BASE_URL.format(year=year, month=month)
        kpi_df = load_data(kpi_url, f"{year}年{month:02d}月分のKPIデータ")
        if kpi_df is None: return

        # 2列目（ルームID）のデータを取得し、Setに変換
        if kpi_df.shape[1] > 1:
            kpi_room_ids = set(kpi_df.iloc[:, 1].astype(str).str.strip().tolist())
            st.success(f"配信があったルーム件数: **{len(kpi_room_ids)}** (KPIデータは2列目のIDを使用)")
        else:
            st.error("KPIデータCSVに配信ルームID（2列目）が見つかりません。")
            return

        # 3. 配信有無の突き合わせと結果生成
        st.header("3. 配信有無の結果生成")
        
        results = []
        
        for room_id in liver_ids:
            # 2列目のライバー愛称を取得
            liver_alias = liver_alias_map.get(room_id, "愛称不明") 
            has_stream = "有り" if room_id in kpi_room_ids else "なし"
                
            results.append({
                "ルームID": room_id,
                "ルーム名": liver_alias, # ライバー愛称を「ルーム名」列として出力
                "配信有無": has_stream,
                "配信月": delivery_month_str,
                "支払月": payment_month_str
            })

        results_df = pd.DataFrame(results)

    st.success("✅ 全てのデータ処理が完了しました！")

    # 4. 結果の表示とCSVダウンロード
    st.header("4. 結果リスト")
    
    # 列名を変更して表示（CSV出力のヘッダーは「ルーム名」のまま維持）
    display_df = results_df.rename(columns={"ルーム名": "ライバー愛称"})
    st.dataframe(display_df, use_container_width=True) 
    
    st.subheader("CSVダウンロード")
    
    # CSV出力はヘッダー名「ルーム名」のままとします
    csv = results_df.to_csv(index=False, encoding='utf-8-sig') 
    
    st.download_button(
        label="📥 結果をCSVダウンロード",
        data=csv,
        file_name=f'showroom_liver_stream_check_{year}{month:02d}.csv',
        mime='text/csv',
    )
    
    st.markdown("---")
    st.info("💡 **次のステップについて**\n\nこの修正で、ルーム名が**ライバー愛称**（`m-liver-list.csv` の2列目）に置き換わりました。次は**売上データ**を取り込み、残りの目標項目を完成させましょう。")


if __name__ == "__main__":
    main()