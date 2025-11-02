import streamlit as st
import pandas as pd
from io import StringIO
import datetime
from dateutil.relativedelta import relativedelta


# --- ページ設定 ---
st.set_page_config(layout="wide", page_title="SHOWROOMライバーデータ整理ツール")


# --- 定数（URL） ---
KPI_DATA_BASE_URL = "https://mksoul-pro.com/showroom/csv/{year}-{month:02d}_all_all.csv"
LIVER_LIST_URL = "https://mksoul-pro.com/showroom/file/m-liver-list.csv"
ROOM_LIST_URL = "https://mksoul-pro.com/showroom/file/room_list.csv"


## データの準備・読み込み関数
@st.cache_data
def load_data(url, name="データ"):
    """URLからCSVを読み込み、DataFrameとして返す（ヘッダーあり前提）"""
    try:
        # ヘッダー行ありのCSVとして読み込む
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
        
        # 2. データの読み込み
        
        # 2.1. 管理ライバーリストの読み込み (m-liver-list.csv)
        st.subheader("管理ライバーリストの読み込み")
        liver_df = load_data(LIVER_LIST_URL, "管理ライバーリスト")
        if liver_df is None: return
        
        # 1列目 (.iloc[:, 0]) のルームIDを取得し、文字列に変換
        if liver_df.shape[1] > 0:
            liver_ids = liver_df.iloc[:, 0].astype(str).str.strip().tolist()
            st.success(f"管理ライバーのルームIDリスト（1列目）を読み込みました。件数: **{len(liver_ids)}**")
        else:
            st.error("管理ライバーリストCSVにデータがありません。")
            return
        
        # 2.2. ルーム名リストの読み込みとマッピング (room_list.csv)
        st.subheader("ルーム名リストの読み込みとマッピング")
        room_list_df = load_data(ROOM_LIST_URL, "ルーム名リスト")
        if room_list_df is None: return
        
        # === 最終確定：1列目ID（キー）と2列目ルーム名（値）でマッピング ===
        if room_list_df.shape[1] >= 2:
            
            # 1列目 (ID) を文字列に変換し、インデックスとして設定
            room_list_df.iloc[:, 0] = room_list_df.iloc[:, 0].astype(str).str.strip()
            
            # 2列目 (ルーム名) のデータを値として取得
            # 1列目をキー(ID)、2列目(インデックス1)を値(ルーム名)として辞書を作成
            # 他の列を一切参照せず、2列目の値をそのまま使用します。
            room_name_map = room_list_df.set_index(room_list_df.columns[0]).iloc[:, 1].astype(str).str.strip().to_dict()
            st.success(f"ルーム名マッピングを作成しました。マッピング件数: **{len(room_name_map)}** (**2列目のルーム名のみを使用**)")
        else:
            st.error("ルーム名リストCSVに必要な列（1列目:ID, 2列目:ルーム名）が見つかりません。処理を中断します。")
            return
            
        # 2.3. KPIデータ（配信有無）の読み込み (YYYY-MM_all_all.csv)
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
            # 2列目のルーム名を取得
            room_name = room_name_map.get(room_id, "ルーム名不明") 
            has_stream = "有り" if room_id in kpi_room_ids else "なし"
                
            results.append({
                "ルームID": room_id,
                "ルーム名": room_name,
                "配信有無": has_stream,
                "配信月": delivery_month_str,
                "支払月": payment_month_str
            })

        results_df = pd.DataFrame(results)

    st.success("✅ 全てのデータ処理が完了しました！")

    # 4. 結果の表示とCSVダウンロード
    st.header("4. 結果リスト")
    
    st.dataframe(results_df, use_container_width=True) 
    
    st.subheader("CSVダウンロード")
    
    csv = results_df.to_csv(index=False, encoding='utf-8-sig') 
    
    st.download_button(
        label="📥 結果をCSVダウンロード",
        data=csv,
        file_name=f'showroom_liver_stream_check_{year}{month:02d}.csv',
        mime='text/csv',
    )
    
    st.markdown("---")
    st.info("💡 **次のステップについて**\n\nこの修正で、ルーム名（2列目）の紐づけが正しく行われていることをご確認ください。次は**売上データ**を取り込み、残りの目標項目を完成させましょう。")


if __name__ == "__main__":
    main()