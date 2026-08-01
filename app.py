import streamlit as st
import pandas as pd
from io import StringIO
import datetime
from dateutil.relativedelta import relativedelta


# --- ページ設定 ---
# 【修正箇所】: st.set_set_page_config を st.set_page_config に修正
st.set_page_config(layout="wide", page_title="SHOWROOM 月初サマリー作成ツール")


# --- 定数（URL） ---
KPI_DATA_BASE_URL = "https://mksoul-pro.com/showroom/csv/{year}-{month:02d}_all_all.csv"
LIVER_LIST_URL = "https://mksoul-pro.com/showroom/file/m-liver-list.csv"
ROOM_LIST_URL = "https://mksoul-pro.com/showroom/file/room_list.csv"

# 【修正箇所】 固定ファイルURLから、処理月（{year}{month:02d}）を挿入する動的ベースURLへ変更

# ルーム売上分配額データURL
SALES_DATA_BASE_URL = "https://mksoul-pro.com/showroom/sales-app_v2/db/point_hist_with_mixed_rate_csv_donwload_for_room_{year}{month:02d}.csv"
# プレミアムライブ分配額データURL
PAID_LIVE_BASE_URL = "https://mksoul-pro.com/showroom/sales-app_v2/db/paid_live_hist_invoice_format_{year}{month:02d}.csv"
# タイムチャージ分配額データURL
TIME_CHARGE_BASE_URL = "https://mksoul-pro.com/showroom/sales-app_v2/db/show_rank_time_charge_hist_invoice_format_{year}{month:02d}.csv"


## データの準備・読み込み関数
# @st.cache_data は削除済み
def load_data(url, name="データ", header='infer'):
    """URLからCSVを読み込み、DataFrameとして返す（文字化け対策のためUTF-8, Shift-JISを試行）"""
    try:
        # **【文字化け対策】** まずは標準的な 'utf8' で試行
        df = pd.read_csv(url, header=header, encoding='utf8') 
        return df
    except UnicodeDecodeError:
        # UTF-8で失敗した場合、次に日本語でよく使われる 'shift-jis' を試行
        try:
            df = pd.read_csv(url, header=header, encoding='shift-jis') 
            return df
        except Exception as e:
            st.error(f"{name}の読み込み（Shift-JIS）に失敗しました: {url}\nエラー: {e}")
            return None
    except Exception as e:
        st.error(f"{name}の読み込みに失敗しました: {url}\nエラー: {e}")
        return None

# @st.cache_data は削除済み
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

# --- 【新規追加】チェックボックスのリセット関数 ---
def reset_checks():
    """
    処理月が変更された際にチェックボックスの状態をリセットする
    """
    st.session_state.check1 = False
    st.session_state.check2 = False
    st.session_state.check3 = False
    st.session_state.check4 = False


# --- 個別ランク判定関数 ---
def get_individual_rank(sales_amount_str):
    """
    ルーム売上分配額（文字列）から個別ランクを判定する
    """
    if sales_amount_str == "#N/A":
        return "#N/A"
    
    try:
        amount = float(sales_amount_str)
        
        if amount >= 900001:
            return "SSS"
        elif amount >= 450001:
            return "SS"
        elif amount >= 270001:
            return "S"
        elif amount >= 135001:
            return "A"
        elif amount >= 90001:
            return "B"
        elif amount >= 45001:
            return "C"
        elif amount >= 22501:
            return "D"
        elif amount >= 0:
            return "E"
        else:
            return "E" 
            
    except ValueError:
        return "#ERROR"

# --- MKランク判定関数 ---
def get_mk_rank(revenue):
    """
    全体分配額合計からMKランク（1〜11）を判定する
    """
    if revenue <= 175000:
        return 1
    elif revenue <= 350000:
        return 2
    elif revenue <= 525000:
        return 3
    elif revenue <= 700000:
        return 4
    elif revenue <= 875000:
        return 5
    elif revenue <= 1050000:
        return 6
    elif revenue <= 1225000:
        return 7
    elif revenue <= 1400000:
        return 8
    elif revenue <= 1575000:
        return 9
    elif revenue <= 1750000:
        return 10
    else:
        return 11
        
# --- ルーム売上支払想定額計算関数 ---
def calculate_payment_estimate(individual_rank, mk_rank, individual_revenue):
    """
    個別ランク、MKランク、個別分配額から支払想定額を計算する
    """
    if individual_revenue == "#N/A" or individual_rank == "#N/A":
        return "#N/A"

    try:
        individual_revenue = float(individual_revenue)
        # 個別ランクに応じた基本レートの辞書 (mk_rank 1, 3, 5, 7, 9, 11 のキーを使用)
        rank_rates = {
            'D': {1: 0.750, 3: 0.755, 5: 0.760, 7: 0.765, 9: 0.770, 11: 0.775},
            'E': {1: 0.725, 3: 0.730, 5: 0.735, 7: 0.740, 9: 0.745, 11: 0.750},
            'C': {1: 0.775, 3: 0.780, 5: 0.785, 7: 0.790, 9: 0.795, 11: 0.800},
            'B': {1: 0.800, 3: 0.805, 5: 0.810, 7: 0.815, 9: 0.820, 11: 0.825},
            'A': {1: 0.825, 3: 0.830, 5: 0.835, 7: 0.840, 9: 0.845, 11: 0.850},
            'S': {1: 0.850, 3: 0.855, 5: 0.860, 7: 0.865, 9: 0.870, 11: 0.875},
            'SS': {1: 0.875, 3: 0.880, 5: 0.885, 7: 0.890, 9: 0.895, 11: 0.900},
            'SSS': {1: 0.900, 3: 0.905, 5: 0.910, 7: 0.915, 9: 0.920, 11: 0.925},
        }

        # MKランクに応じてキーを決定 (1,2 -> 1, 3,4 -> 3, ...)
        if mk_rank in [1, 2]:
            key = 1
        elif mk_rank in [3, 4]:
            key = 3
        elif mk_rank in [5, 6]:
            key = 5
        elif mk_rank in [7, 8]:
            key = 7
        elif mk_rank in [9, 10]:
            key = 9
        elif mk_rank == 11:
            key = 11
        else:
            return "#ERROR_MK"

        # 適用レートの取得
        rate = rank_rates.get(individual_rank, {}).get(key)
        
        if rate is None:
            return "#ERROR_RANK"

        # 計算式の適用: ($individualRevenue * 1.08 * $rate) / 1.10 * 1.10
        # payment_estimate = (individual_revenue * 1.08 * rate) / 1.10 * 1.10
        payment_estimate = (individual_revenue * 1.07 * rate) / 1.10 * 1.10
        
        # 結果を小数点以下を四捨五入して整数に丸める
        return str(round(payment_estimate)) 

    except Exception:
        return "#ERROR_CALC"
        
# --- プレミアムライブ支払想定額計算関数 ---
def calculate_paid_live_payment_estimate(paid_live_amount_str):
    """
    プレミアムライブ分配額から支払想定額を計算する
    """
    # プレミアムライブ分配額がない場合はブランクを返す
    if paid_live_amount_str == "" or paid_live_amount_str == "#N/A":
        return ""

    try:
        # 分配額を数値に変換
        individual_revenue = float(paid_live_amount_str)
        
        # 計算式の適用: ($individualRevenue * 1.00 * 1.08 * 0.9) / 1.10 * 1.10
        # payment_estimate = (individual_revenue * 1.08 * 0.9) / 1.10 * 1.10
        payment_estimate = (individual_revenue * 1.07 * 0.9) / 1.10 * 1.10
        
        # 結果を小数点以下を四捨五入して整数に丸める
        return str(round(payment_estimate))

    except ValueError:
        return "#ERROR_CALC"

# --- タイムチャージ支払想定額計算関数 ---
def calculate_time_charge_payment_estimate(time_charge_amount_str):
    """
    タイムチャージ分配額から支払想定額を計算する
    """
    # タイムチャージ分配額がない場合はブランクを返す
    if time_charge_amount_str == "" or time_charge_amount_str == "#N/A":
        return ""

    try:
        # 分配額を数値に変換
        individual_revenue = float(time_charge_amount_str)
        
        # 計算式の適用: ($individualRevenue * 1.08 * 1.00) / 1.10 * 1.10
        # payment_estimate = (individual_revenue * 1.08 * 1.00) / 1.10 * 1.10
        payment_estimate = (individual_revenue * 1.07 * 1.00) / 1.10 * 1.10
        
        # 結果を小数点以下を四捨五入して整数に丸める
        return str(round(payment_estimate))

    except ValueError:
        return "#ERROR_CALC"

## メインアプリケーション
def main():
    #st.title("🎤 SHOWROOM 月初サマリー作成ツール")
    st.markdown(
        "<h1 style='font-size:28px; text-align:left; color:#1f2937;'>🎤 SHOWROOM 月初サマリー作成ツール</h1>",
        unsafe_allow_html=True
    )  
    st.markdown("<p style='text-align: left;'>⚠️ <b>注意</b>: このツールは、<b>Secretsに設定されたCookieが有効な間のみ</b>動作します。</p>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: left;'>⚠️ <b>注意</b>: インボイス制度経過措置第二フェーズ用に修正済み。（2026/07配信分対応後）</p>", unsafe_allow_html=True)
    st.markdown("---")

    #st.header("1. 処理月の選択と実行")
    st.markdown("#### 1. 処理月の選択と実行")
    
    # get_processed_monthsからキャッシュデコレータを削除したため、毎回最新のリストを取得
    month_options = get_processed_months()
    display_options = [opt[0] for opt in month_options]
    value_options = [opt[1] for opt in month_options]
    
    # 【修正 1/2】 on_changeコールバックに関数（reset_checks）を指定
    selected_display_month = st.selectbox(
        "処理する**配信月**を選択してください:",
        options=display_options,
        index=0,
        on_change=reset_checks # 処理月が変更されたらチェックをリセット
    )
    
    try:
        selected_index = display_options.index(selected_display_month)
        selected_value_month = value_options[selected_index]
        year, month = map(int, selected_value_month.split('-'))
        
        # 表示用の "2025年10月" の文字列を作成
        display_month_text = f"{year}年{month:02d}月"
        
        # ファイル名に使う "202510" の文字列を作成
        file_month_suffix = f"{year}{month:02d}"

        delivery_month_str = f"{year}/{month:02d}"
        payment_date = datetime.date(year, month, 1) + relativedelta(months=2)
        payment_month_str = f"{payment_date.year}/{payment_date.month:02d}"
        
    except:
        st.warning("有効な処理月が選択されていません。")
        return
    
    st.markdown("---")

    # --- データ更新チェック項目 ---
    st.markdown("#### 2. データ更新状況のチェック（処理開始の必須条件）")
    
    # チェックボックスの状態をセッションステートに保持（on_changeでリセットされる）
    if 'check1' not in st.session_state:
        st.session_state.check1 = False
    if 'check2' not in st.session_state:
        st.session_state.check2 = False
    if 'check3' not in st.session_state:
        st.session_state.check3 = False
    if 'check4' not in st.session_state:
        st.session_state.check4 = False

    # チェックボックスの表示
    st.markdown("以下のファイルが**最新の状態**であることを確認してください。")
    check1 = st.checkbox(f"① 管理ライバーリスト（`{LIVER_LIST_URL.split('/')[-1]}`）が最新状態か", key='check1')
    check2 = st.checkbox(f"② ルームリスト（`{ROOM_LIST_URL.split('/')[-1]}`）が最新状態か", key='check2')
    
    # KPIデータは `2025-10_all_all.csv` の形式で、選択された月がURLに含まれるため、ファイル名を表示。
    kpi_file_name = KPI_DATA_BASE_URL.format(year=year, month=month).split('/')[-1]
    check3 = st.checkbox(f"③ 処理月（{display_month_text}）のKPIデータ（`{kpi_file_name}`）が最新状態か", key='check3')
    
    # 複数の売上ファイルをまとめてチェック
    # 【修正箇所】 動的なファイル名を取得
    sales_file_names = [
        SALES_DATA_BASE_URL.format(year=year, month=month).split('/')[-1],
        PAID_LIVE_BASE_URL.format(year=year, month=month).split('/')[-1],
        TIME_CHARGE_BASE_URL.format(year=year, month=month).split('/')[-1]
    ]
    # チェック項目④のテキストから「分」を削除し、ファイル名を動的に表示
    check4 = st.checkbox(f"④ 処理月（{display_month_text}）の各種売上データが最新状態か (ファイル例: `{sales_file_names[0]}` 他)", key='check4')

    # 全てのチェックボックスがTrueであるかを確認
    all_checked = check1 and check2 and check3 and check4
    
    st.markdown("---")
    
    # ボタンの有効/無効を制御
    if st.button("🚀 データ処理を開始する", type="primary", disabled=not all_checked):
        # ボタンを押すたびに、process_data内からload_dataが実行され、常に最新データが取得されます。
        process_data(year, month, delivery_month_str, payment_month_str)
    elif not all_checked:
        st.warning("処理を開始するには、上記の**全てのデータチェック項目にチェック**を入れてください。")
    else:
        # 表示テキストから「分」を削除した display_month_text を使用
        st.info(f"選択された配信月: **{display_month_text}分**。処理を開始するには上記のボタンを押してください。")
    
    st.markdown("---")


# データ処理のメインロジック (ボタンが押されたときのみ実行)
def process_data(year, month, delivery_month_str, payment_month_str):
    
    with st.spinner("データを読み込み、配信有無と売上をチェックしています..."):
        
        # --- 2. データの読み込みとマッピング ---
        
        # 2.1. 管理ライバーリストの読み込み (m-liver-list.csv)
        st.markdown(f"##### 管理ライバーリストの読み込みと愛称マッピングの作成")
        liver_df = load_data(LIVER_LIST_URL, "管理ライバーリスト")
        if liver_df is None: return
        
        if liver_df.shape[1] >= 2:
            df_keys = liver_df.iloc[:, 0].astype(str).str.strip()
            df_values = liver_df.iloc[:, 1].astype(str).str.strip() 
            liver_alias_map = pd.Series(df_values.values, index=df_keys).to_dict()
            liver_ids = df_keys.tolist()
            st.success(f"管理ライバーのルームIDリスト（1列目）と愛称（2列目）を読み込みました。件数: **{len(liver_ids)}**")
        else:
            st.error("管理ライバーリストCSVにデータ（1列目:ID, 2列目:愛称）が見つかりません。")
            return
        
        # 2.2. KPIデータ（配信有無）の読み込み (YYYY-MM_all_all.csv)
        st.markdown(f"##### {year}年{month:02d}月分のKPIデータの読み込み")
        kpi_url = KPI_DATA_BASE_URL.format(year=year, month=month)
        kpi_df = load_data(kpi_url, f"{year}年{month:02d}月分のKPIデータ")
        if kpi_df is None: return

        if kpi_df.shape[1] > 1:
            kpi_room_ids = set(kpi_df.iloc[:, 1].astype(str).str.strip().tolist())
            st.success(f"配信があったルーム件数: **{len(kpi_room_ids)}** (KPIデータは2列目のIDを使用)")
        else:
            st.error("KPIデータCSVに配信ルームID（2列目）が見つかりません。")
            return
            
        # 2.3. ルームリストの読み込み (room_list.csv) - IDとアカウントIDの紐づけ用 
        st.markdown(f"##### ルームIDとアカウントIDの紐づけと管理対象判定リストの作成")
        room_list_df = load_data(ROOM_LIST_URL, "ルーム名リスト", header='infer')
        if room_list_df is None: return

        # 既存ロジック：アカウントIDとルームIDのマッピング作成
        account_id_to_room_id_map = {}
        if room_list_df.shape[1] >= 4:
            keys_series = room_list_df.iloc[:, 3].astype(str).str.strip()
            values_series = room_list_df.iloc[:, 0].astype(str).str.strip()
            account_id_to_room_id_map = pd.Series(values_series.values, index=keys_series).to_dict()
            st.success("ルームIDとアカウントIDのマッピングを作成しました。")
        else:
            st.error("ルーム名リストCSVにアカウントID（4列目）が見つかりません。売上分配額の紐づけをスキップします。")

        # ROOM_LIST_URLの1列目（ルームID）のセットを作成
        if room_list_df.shape[1] >= 1:
            room_list_ids = set(room_list_df.iloc[:, 0].astype(str).str.strip().tolist())
            st.success(f"room_list.csv のルームIDリストを読み込みました。件数: **{len(room_list_ids)}**")
        else:
            st.error("room_list.csvにルームID（1列目）が見つかりません。管理対象の判定をスキップします。")
            room_list_ids = set()

            
        # 2.4. ルーム売上分配額データの読み込み (point_hist_with_mixed_rate_csv_donwload_for_room_YYYYMM.csv)
        st.markdown(f"##### ルーム売上分配額データの読み込みとMKランク決定")
        # 【修正箇所】動的なURLを生成
        sales_url = SALES_DATA_BASE_URL.format(year=year, month=month)
        sales_df = load_data(sales_url, "売上分配額データ", header=None)
        if sales_df is None: return
        
        # 全体分配額合計の取得（1列目1行目）
        total_revenue = 0.0
        try:
            if sales_df.shape[0] > 0 and sales_df.shape[1] > 0:
                total_revenue = float(sales_df.iloc[0, 0])
                st.success(f"全体分配額合計（MKランク決定用）: **{round(total_revenue)}** 円")
            else:
                st.warning("売上分配額CSVが空のため、全体分配額合計は0として処理します。")
        except:
            st.error("売上分配額CSVの1列目1行目から全体分配額合計の取得に失敗しました。0として処理します。")
            
        # MKランクの決定
        mk_rank = get_mk_rank(total_revenue)
        st.info(f"計算されたMKランク: **{mk_rank}**")
        
        # 個別ルームの分配額マッピングの作成
        room_id_to_sales_map = {}
        if sales_df.shape[1] >= 2:
            sales_keys = sales_df.iloc[:, 1].astype(str).str.strip() # アカウントID (キー)
            sales_values = sales_df.iloc[:, 0].astype(str).str.strip() # 分配額 (値)
            
            # 1行目の全体分配額合計を除く
            # sales_values[1:].values と sales_keys[1:] で1行目をスキップ
            account_id_to_sales_map = pd.Series(sales_values[1:].values, index=sales_keys[1:]).to_dict()
            
            # ルームIDに紐づける
            for account_id, room_id in account_id_to_room_id_map.items():
                if account_id in account_id_to_sales_map:
                    room_id_to_sales_map[room_id] = account_id_to_sales_map[account_id]
        else:
            st.error("売上分配額CSVに分配額（1列目）またはアカウントID（2列目）が見つかりません。")
            account_id_to_sales_map = {}
        st.success(f"個別売上分配額データ（アカウントIDをキー）を読み込みました。件数: **{len(account_id_to_sales_map)}**")
        
        
        # 2.5. プレミアムライブ分配額データの読み込み (paid_live_hist_invoice_format_YYYYMM.csv)
        st.markdown(f"##### プレミアムライブ分配額データの読み込み")
        # 【修正箇所】動的なURLを生成
        paid_live_url = PAID_LIVE_BASE_URL.format(year=year, month=month)
        paid_live_df = load_data(paid_live_url, "プレミアムライブ分配額データ", header=None)
        
        room_id_to_paid_live_map = {}
        if paid_live_df is not None and paid_live_df.shape[1] >= 2:
            paid_live_keys = paid_live_df.iloc[:, 1].astype(str).str.strip() # アカウントID (キー)
            paid_live_values = paid_live_df.iloc[:, 0].astype(str).str.strip() # 分配額 (値)
            
            # 1行目からライバーデータ
            account_id_to_paid_live_map = pd.Series(paid_live_values.values, index=paid_live_keys).to_dict()

            # ルームIDに対する最終分配額マッピングを作成
            for account_id, room_id in account_id_to_room_id_map.items():
                if account_id in account_id_to_paid_live_map:
                    room_id_to_paid_live_map[room_id] = account_id_to_paid_live_map[account_id]
        st.success(f"プレミアムライブ分配額データ（アカウントIDをキー）を読み込みました。件数: **{len(account_id_to_paid_live_map)}**")
        
        # 2.6. タイムチャージ分配額データの読み込み (show_rank_time_charge_hist_invoice_format_YYYYMM.csv)
        st.markdown(f"##### タイムチャージ分配額データの読み込み")
        # 【修正箇所】動的なURLを生成
        time_charge_url = TIME_CHARGE_BASE_URL.format(year=year, month=month)
        time_charge_df = load_data(time_charge_url, "タイムチャージ分配額データ", header=None)
        
        room_id_to_time_charge_map = {}
        if time_charge_df is not None and time_charge_df.shape[1] >= 2:
            time_charge_keys = time_charge_df.iloc[:, 1].astype(str).str.strip() # アカウントID (キー)
            time_charge_values = time_charge_df.iloc[:, 0].astype(str).str.strip() # 分配額 (値)
            
            # 1行目からライバーデータ
            account_id_to_time_charge_map = pd.Series(time_charge_values.values, index=time_charge_keys).to_dict()

            # ルームIDに対する最終分配額マッピングを作成
            for account_id, room_id in account_id_to_room_id_map.items():
                if account_id in account_id_to_time_charge_map:
                    room_id_to_time_charge_map[room_id] = account_id_to_time_charge_map[account_id]
        st.success(f"タイムチャージ分配額データ（アカウントIDをキー）を読み込みました。件数: **{len(account_id_to_time_charge_map)}**")

        
        # 3. 配信有無と売上分配額の突き合わせと結果生成
        st.markdown("#### 3. 結果生成")
        
        results = []
        
        for room_id in liver_ids:
            liver_alias = liver_alias_map.get(room_id, "愛称不明") 
            
            # 管理対象判定
            # LIVER_LIST_URLに存在し、ROOM_LIST_URLに存在しない場合「外」
            is_managed = "外" if room_id not in room_list_ids else ""
            
            has_stream = "有り" if room_id in kpi_room_ids else "なし"
            
            # ルーム売上
            sales_amount = room_id_to_sales_map.get(room_id, "#N/A")
            individual_rank = get_individual_rank(sales_amount)
            payment_estimate = calculate_payment_estimate(individual_rank, mk_rank, sales_amount)
            
            # プレミアムライブ
            paid_live_amount = room_id_to_paid_live_map.get(room_id, "")
            paid_live_payment_estimate = calculate_paid_live_payment_estimate(paid_live_amount)
            
            # タイムチャージ
            time_charge_amount = room_id_to_time_charge_map.get(room_id, "")
            time_charge_payment_estimate = calculate_time_charge_payment_estimate(time_charge_amount)
                    
            results.append({
                "ルームID": room_id,
                "ルーム名": liver_alias, # <--- 一旦ここで「ルーム名」として定義
                "管理対象": is_managed,
                "配信有無": has_stream,
                "配信月": delivery_month_str,
                "支払月": payment_month_str,
                "R分配額": sales_amount, 
                "個別ランク": individual_rank,
                "R支払想定額": payment_estimate, 
                "PL分配額": paid_live_amount, 
                "PL支払想定額": paid_live_payment_estimate, 
                "TC支払想定額": time_charge_payment_estimate, 
            })

        results_df = pd.DataFrame(results)

        # 【修正箇所】CSVと画面表示で統一するため、「ルーム名」を「ライバー愛称」にここで変更
        results_df = results_df.rename(columns={"ルーム名": "ライバー愛称"})

        # 結果の列順序を明示的に指定
        column_order = [
            "ルームID",
            "ライバー愛称", # 修正: ルーム名 -> ライバー愛称
            "管理対象",
            "配信有無",
            "配信月",
            "支払月",
            "R分配額", 
            "個別ランク",
            "R支払想定額", 
            "PL分配額", 
            "PL支払想定額", 
            "TC支払想定額", 
        ]
        
        final_columns = [col for col in column_order if col in results_df.columns]
        results_df = results_df[final_columns]

        # Excelの日付自動変換対策（="2025/10" を含むデータ）を results_df に適用
        results_df_csv = results_df.copy()
        results_df_csv["配信月"] = results_df_csv["配信月"].astype(str).apply(lambda x: f'="{x}"')
        results_df_csv["支払月"] = results_df_csv["支払月"].astype(str).apply(lambda x: f'="{x}"')

        # 画面表示用データを作成し、Excel対策表記を解除
        display_df = results_df.copy()
        
    st.success("✅ 全てのデータ処理が完了しました！")

    # 4. 結果の表示とCSVダウンロード
    st.markdown("#### 4. 結果リスト")
    
    # 【修正箇所】列名変更がresults_dfに対して既に行われているため、ここでは不要な列名変更を削除し、
    # 既存のロジック（分配額などの列名はそのまま維持）を残す
    # display_dfはすでに「ライバー愛称」を持っている
    # display_df = display_df.rename(columns={...}) ブロック全体を削除し、必要な列だけを明示的にリネームする
    
    # 画面表示用のヘッダーとして表示されるDataFrameには、すでに「ライバー愛称」が設定されている
    
    # st.dataframeに hide_index=True を追加してインデックスを非表示にする
    st.dataframe(display_df, use_container_width=True, hide_index=True) 
    
    st.markdown(f"##### CSVダウンロード")

    # CSV出力はBOM付きUTF-8（Excel対応）
    # results_df_csvはすでに「ライバー愛称」の列名を持っている
    csv_bytes = results_df_csv.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')

    st.download_button(
        label="📥 結果をCSVダウンロード",
        data=csv_bytes,
        file_name=f'showroom_liver_sales_estimate_{year}{month:02d}.csv',
        mime='text/csv',
    )

    
    #st.markdown("---")


if __name__ == "__main__":
    main()
