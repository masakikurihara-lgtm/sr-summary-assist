import streamlit as st
import pandas as pd
from io import StringIO
import datetime
from dateutil.relativedelta import relativedelta # 支払月計算のために追加


# --- ページ設定 ---
# 最初に実行することで、レイアウトをwideに設定
st.set_page_config(layout="wide", page_title="SHOWROOMライバーデータ整理ツール")


# --- 定数（URL） ---
# ライブKPIデータ（配信有無確認用）のベースURL
KPI_DATA_BASE_URL = "https://mksoul-pro.com/showroom/csv/{year}-{month:02d}_all_all.csv"
# 管理ライバーのルームID一覧URL
LIVER_LIST_URL = "https://mksoul-pro.com/showroom/file/m-liver-list.csv"
# ルーム名一覧URL (今回追加)
ROOM_LIST_URL = "https://mksoul-pro.com/showroom/file/room_list.csv"


## データの準備・読み込み関数
@st.cache_data
def load_data(url, name="データ"):
    """URLからCSVを読み込み、DataFrameとして返す"""
    try:
        df = pd.read_csv(url)
        # st.success(f"{name}を読み込みました。件数: {len(df)}")
        return df
    except Exception as e:
        st.error(f"{name}の読み込みに失敗しました: {url}\nエラー: {e}")
        return None

@st.cache_data
def get_processed_months():
    """
    プルダウンに表示する処理月リストを生成する。
    （例：今月から過去数ヶ月分）
    """
    today = datetime.date.today()
    
    # 処理月は「配信月」を指すため、今日の日付から1ヶ月前を基準にする
    current_date = today - relativedelta(months=1)
    
    processed_months = []

    for i in range(12): # 過去12ヶ月分を生成
        
        # 表示用のフォーマット 'YYYY年MM月分'
        display_str = f"{current_date.year}年{current_date.month:02d}月分"
        # データ取得用のフォーマット 'YYYY-MM'
        value_str = f"{current_date.year}-{current_date.month:02d}"
        
        processed_months.append((display_str, value_str))
        
        # 1ヶ月前に戻る
        current_date = current_date - relativedelta(months=1)
            
    return processed_months

## メインアプリケーション
def main():
    st.title("🎤 SHOWROOMライバーデータ整理ツール (配信有無チェック)")

    # 1. 処理月の選択とスタートボタン
    st.header("1. 処理月の選択と実行")
    
    # 処理月リストを生成 [(表示名, 値), ...]
    month_options = get_processed_months()
    # 選択肢の表示名リスト
    display_options = [opt[0] for opt in month_options]
    # 選択肢の値リスト (YYYY-MM形式)
    value_options = [opt[1] for opt in month_options]
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        # プルダウンでの選択
        selected_display_month = st.selectbox(
            "処理する**配信月**を選択してください:",
            options=display_options,
            index=0 # デフォルトは最新月
        )
        
    # 選択された表示名から、対応する値 (YYYY-MM) を取得
    try:
        selected_index = display_options.index(selected_display_month)
        selected_value_month = value_options[selected_index]
        year, month = map(int, selected_value_month.split('-'))
        
        # 配信月 (YYYY/MM) のフォーマット
        delivery_month_str = f"{year}/{month:02d}"

        # 支払月 (配信月 + 2ヶ月) の計算とフォーマット (YYYY/MM)
        # datetimeオブジェクトに変換して計算
        delivery_date = datetime.date(year, month, 1)
        payment_date = delivery_date + relativedelta(months=2)
        payment_month_str = f"{payment_date.year}/{payment_date.month:02d}"
        
    except:
        st.warning("有効な処理月が選択されていません。")
        return
    
    with col2:
        st.markdown(f"選択された配信月: **{selected_display_month}** (データ出力形式: {delivery_month_str})")
        st.markdown(f"想定される支払月: **{payment_month_str}**")
        
        # 処理開始ボタン
        if st.button("🚀 データ処理を開始する", type="primary"):
            process_data(year, month, delivery_month_str, payment_month_str)
        else:
            st.info("処理を開始するには上記のボタンを押してください。")


# データ処理のメインロジック (ボタンが押されたときのみ実行)
def process_data(year, month, delivery_month_str, payment_month_str):
    
    with st.spinner("データを読み込み、配信有無をチェックしています..."):
        
        # 2. データの読み込み
        
        # 2.1. 管理ライバーリストの読み込み (ルームID一覧)
        st.subheader("管理ライバーリストの読み込み")
        liver_df = load_data(LIVER_LIST_URL, "管理ライバーリスト")
        if liver_df is None: return
        liver_ids = liver_df.iloc[:, 0].astype(str).tolist()
        st.success(f"管理ライバーのルームIDリストを読み込みました。件数: **{len(liver_ids)}**")
        
        # 2.2. ルーム名リストの読み込みとマッピング
        st.subheader("ルーム名リストの読み込みとマッピング")
        room_list_df = load_data(ROOM_LIST_URL, "ルーム名リスト")
        if room_list_df is None: return
        
        # 1列目: ルームID, 2列目: ルーム名と仮定してマッピング辞書を作成
        if room_list_df.shape[1] >= 2:
            # 1列目をキー(ルームID)、2列目を値(ルーム名)として辞書を作成
            room_name_map = room_list_df.iloc[:, [0, 1]].set_index(room_list_df.columns[0]).iloc[:, 0].to_dict()
            st.success(f"ルーム名マッピングを作成しました。マッピング件数: **{len(room_name_map)}**")
        else:
            st.error("ルーム名リストCSVに必要な列（1列目:ID, 2列目:ルーム名）が見つかりません。")
            return
            
        # 2.3. KPIデータ（配信有無）の読み込み
        st.subheader(f"{year}年{month:02d}月分のKPIデータの読み込み")
        kpi_url = KPI_DATA_BASE_URL.format(year=year, month=month)
        kpi_df = load_data(kpi_url, f"{year}年{month:02d}月分のKPIデータ")
        if kpi_df is None: return

        if kpi_df.shape[1] > 1:
            # 2列目のデータを取得し、Setに変換して高速な存在チェックを可能にする
            kpi_room_ids = set(kpi_df.iloc[:, 1].astype(str).tolist())
            st.success(f"配信があったルーム件数: **{len(kpi_room_ids)}**")
        else:
            st.error("KPIデータCSVに配信ルームID（2列目）が見つかりません。")
            return

        # 3. 配信有無の突き合わせと結果生成
        st.header("3. 配信有無の結果生成")
        
        results = []
        
        # 管理ライバーのルームID一覧の順序通りにチェック
        for room_id in liver_ids:
            # ルーム名取得 (見つからない場合は「不明」とする)
            room_name = room_name_map.get(room_id, "ルーム名不明")

            # 配信有無のチェック
            has_stream = "有り" if room_id in kpi_room_ids else "なし"
                
            # 結果を辞書としてリストに追加
            results.append({
                "ルームID": room_id,
                "ルーム名": room_name,
                "配信有無": has_stream,
                "配信月": delivery_month_str,
                "支払月": payment_month_str
            })

        # 結果リストをDataFrameに変換
        results_df = pd.DataFrame(results)

    st.success("✅ 全てのデータ処理が完了しました！")

    # 4. 結果の表示とCSVダウンロード
    st.header("4. 結果リスト")
    
    st.dataframe(results_df, use_container_width=True) # wideレイアウトに合わせて表示
    
    st.subheader("CSVダウンロード")
    
    # DataFrameをCSV形式に変換
    # Excelで文字化けしないよう'utf-8-sig'を使用
    csv = results_df.to_csv(index=False, encoding='utf-8-sig') 
    
    # ダウンロードボタンの設置
    st.download_button(
        label="📥 結果をCSVダウンロード",
        data=csv,
        file_name=f'showroom_liver_stream_check_{year}{month:02d}.csv',
        mime='text/csv',
    )
    
    st.markdown("---")
    st.info("💡 **次のステップについて**\n\nここまでの実装で、①から④の修正を全てクリアしました。次は、**ルーム売上分配額**などの売上関連データを追加し、最終目標の項目を完成させるフェーズに進みましょう。")


if __name__ == "__main__":
    main()