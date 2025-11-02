import streamlit as st
import pandas as pd
from io import StringIO
import datetime

# --- 定数（URL） ---
# ライブKPIデータ（配信有無確認用）のベースURL
KPI_DATA_BASE_URL = "https://mksoul-pro.com/showroom/csv/{year}-{month:02d}_all_all.csv"
# 管理ライバーのルームID一覧URL
LIVER_LIST_URL = "https://mksoul-pro.com/showroom/file/m-liver-list.csv"


## データの準備・読み込み関数
@st.cache_data
def load_data(url):
    """URLからCSVを読み込み、DataFrameとして返す"""
    try:
        df = pd.read_csv(url)
        return df
    except Exception as e:
        st.error(f"データの読み込みに失敗しました: {url}\nエラー: {e}")
        return None

@st.cache_data
def get_processed_months():
    """
    プルダウンに表示する処理月リストを生成する。
    （例：今月から過去数ヶ月分）
    """
    today = datetime.date.today()
    # 直近の月（例：11月なら10月分、12月なら11月分）から過去12ヶ月分をリストアップ
    # 処理月は「配信月」を指すため、今日の日付から1ヶ月前を基準にする
    processed_months = []
    
    # 基準となる月 (例: 11月であれば、10月分から開始)
    current_year = today.year
    current_month = today.month - 1
    if current_month == 0: # 1月の場合、前年の12月
        current_month = 12
        current_year -= 1

    for i in range(12): # 過去12ヶ月分を生成
        
        # 表示用のフォーマット 'YYYY年MM月分'
        display_str = f"{current_year}年{current_month:02d}月分"
        # データ取得用のフォーマット 'YYYY-MM'
        value_str = f"{current_year}-{current_month:02d}"
        
        processed_months.append((display_str, value_str))
        
        # 1ヶ月前に戻る
        current_month -= 1
        if current_month == 0:
            current_month = 12
            current_year -= 1
            
    return processed_months

## メインアプリケーション
def main():
    st.title("🎤 SHOWROOMライバーデータ整理ツール (配信有無チェック)")

    # 1. 処理月の選択
    st.header("1. 処理月の選択")
    
    # 処理月リストを生成 [(表示名, 値), ...]
    month_options = get_processed_months()
    # 選択肢の表示名リスト
    display_options = [opt[0] for opt in month_options]
    # 選択肢の値リスト (YYYY-MM形式)
    value_options = [opt[1] for opt in month_options]
    
    # プルダウンでの選択
    selected_display_month = st.selectbox(
        "処理する**配信月**を選択してください（配信有無を確認する月）:",
        options=display_options,
        index=0 # デフォルトは最新月
    )

    # 選択された表示名から、対応する値 (YYYY-MM) を取得
    try:
        selected_index = display_options.index(selected_display_month)
        selected_value_month = value_options[selected_index]
        year, month = map(int, selected_value_month.split('-'))
    except:
        st.warning("有効な処理月が選択されていません。")
        return

    st.info(f"選択された配信月: **{selected_display_month}**")

    st.header("2. データの読み込みと配信有無のチェック")
    
    # 2.1. 管理ライバーリストの読み込み
    st.subheader("管理ライバーリストの読み込み")
    liver_df = load_data(LIVER_LIST_URL)
    if liver_df is None:
        return
        
    # ルームID一覧（1列目）を取得
    # データの構造に依存しますが、ここでは1列目がルームIDと仮定し、列名を 'RoomID' とします。
    # 実際のCSVの構造に合わせて列名を調整してください。
    if liver_df.shape[1] > 0:
        # 1列目のデータを取得（iloc[:, 0]）
        liver_ids = liver_df.iloc[:, 0].astype(str).tolist()
        st.success(f"管理ライバーのルームIDリストを読み込みました。件数: **{len(liver_ids)}**")
        # st.dataframe(liver_df.head()) # デバッグ用
    else:
        st.error("管理ライバーリストCSVにデータがありません。")
        return
        
    # 2.2. KPIデータ（配信有無）の読み込み
    st.subheader(f"{year}年{month:02d}月分のKPIデータの読み込み")
    kpi_url = KPI_DATA_BASE_URL.format(year=year, month=month)
    kpi_df = load_data(kpi_url)
    
    if kpi_df is None:
        st.warning(f"{year}年{month:02d}月分のKPIデータが見つからないか、読み込めませんでした。")
        return

    # 配信があったルームID一覧（2列目）を取得
    # データの構造に依存しますが、ここでは2列目がルームIDと仮定し、列名を 'KPI_RoomID' とします。
    if kpi_df.shape[1] > 1:
        # 2列目のデータを取得（iloc[:, 1]）
        kpi_room_ids = set(kpi_df.iloc[:, 1].astype(str).tolist())
        st.success(f"{year}年{month:02d}月分のKPIデータを読み込みました。配信があったルーム件数: **{len(kpi_room_ids)}**")
        # st.dataframe(kpi_df.head()) # デバッグ用
    else:
        st.error("KPIデータCSVに配信ルームID（2列目）が見つかりません。")
        return

    # 2.3. 配信有無の突き合わせ
    st.subheader("配信有無の結果生成")
    
    # 結果格納用のリスト
    results = []
    
    # 管理ライバーのルームID一覧の順序通りにチェック
    for room_id in liver_ids:
        # KPIデータにルームIDが存在するかチェック
        if room_id in kpi_room_ids:
            has_stream = "有り"
        else:
            has_stream = "なし"
            
        # 結果を辞書としてリストに追加
        results.append({
            "ルームID": room_id,
            "配信月": selected_display_month,
            "配信有無": has_stream
        })

    # 結果リストをDataFrameに変換
    results_df = pd.DataFrame(results)

    st.success("配信有無のチェックが完了しました。")

    # 3. 結果の表示とCSVダウンロード
    st.header("3. 結果リスト")
    
    st.dataframe(results_df)

    # 3.1. CSVダウンロード機能
    st.subheader("CSVダウンロード")
    
    # DataFrameをCSV形式に変換
    csv = results_df.to_csv(index=False, encoding='utf-8-sig') # Excelで文字化けしないよう'utf-8-sig'
    
    # ダウンロードボタンの設置
    st.download_button(
        label="📥 結果をCSVダウンロード",
        data=csv,
        file_name=f'showroom_liver_stream_check_{selected_value_month}.csv',
        mime='text/csv',
    )
    
    st.markdown("---")
    st.info("💡 **次のステップについて**\n\nここまでの実装で、①の要件はクリアしました。次は、**ルーム売上分配額**などの売上関連データを取得・計算し、最終的な目標の項目を完成させるフェーズに進みましょう。")


if __name__ == "__main__":
    main()