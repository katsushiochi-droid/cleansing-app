# -*- coding: utf-8 -*-
import streamlit as st

import cleansing

try:
    import gdrive

    _GDRIVE_IMPORT_OK = True
except Exception:
    _GDRIVE_IMPORT_OK = False

st.set_page_config(page_title="ファイルクレンジング", page_icon="🧹", layout="wide")

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _oauth_conf():
    if not _GDRIVE_IMPORT_OK:
        return None
    try:
        conf = st.secrets["google_oauth"]
    except Exception:
        return None
    if "client_id" not in conf or "client_secret" not in conf:
        return None
    # Secrets のキーは redirect_uri(単数)/ redirect_uris(複数)のどちらでも受け付ける。
    redirect_uri = gdrive.pick_redirect_uri(conf)
    if not redirect_uri:
        return None
    return {
        "client_id": conf["client_id"],
        "client_secret": conf["client_secret"],
        "redirect_uri": redirect_uri,
    }


# 注: OAuth の往復でページが全リロードされ、Streamlit の session_state はリセットされる。
# そのため state(CSRF対策トークン)を session_state で保持・照合できない。社内・信頼できる
# 範囲での利用を前提とし、機微な本番データのアップロードは避けること(README 参照)。
def _handle_oauth_callback(conf):
    params = st.query_params
    if "code" in params and "gdrive_creds" not in st.session_state:
        code = params["code"]
        try:
            flow = gdrive.build_flow(conf)
            creds = gdrive.exchange_code(flow, code)
            st.session_state["gdrive_creds"] = gdrive.creds_to_dict(creds)
        except Exception as e:
            st.session_state["gdrive_error"] = (
                f"Google 連携に失敗しました。もう一度「Google で接続」を押してください: {e}"
            )
        st.query_params.clear()
        st.rerun()


conf = _oauth_conf()
if conf is not None:
    _handle_oauth_callback(conf)

with st.sidebar:
    st.header("Google ドライブ連携")
    if conf is None:
        st.caption("Google ドライブ連携は未設定です(ローカルダウンロードのみ利用できます)。")
    elif "gdrive_creds" in st.session_state:
        st.success("✅ Google ドライブ接続済み")
        if st.button("切断"):
            st.session_state.pop("gdrive_creds", None)
            st.rerun()
    else:
        if st.session_state.get("gdrive_error"):
            st.error(st.session_state.pop("gdrive_error"))
        flow = gdrive.build_flow(conf)
        auth_url, _ = gdrive.get_authorization_url(flow)
        st.link_button("🔗 Google で接続", auth_url)
        st.caption("接続するとページが再読み込みされます。接続後にファイルをアップロードしてください。")

st.title("🧹 ファイルクレンジング")
st.caption(
    "顧客データの CSV / Excel をアップロードすると、表記ゆれを正規化し、"
    "品質チェック結果を付けて整形済み Excel をダウンロードできます。"
)

uploaded = st.file_uploader(
    "CSV または Excel(.xlsx)をドラッグ&ドロップ、または選択してください",
    type=["csv", "xlsx", "xls"],
)

if uploaded is not None:
    try:
        df = cleansing.read_input(uploaded, uploaded.name)
    except Exception as e:
        st.error(f"ファイルを読み込めませんでした: {e}")
        st.stop()

    if len(df) == 0:
        st.warning("データ行が見つかりませんでした。")
        st.stop()

    try:
        result = cleansing.cleanse(df)
    except Exception as e:
        st.error(f"クレンジング処理中にエラーが発生しました: {e}")
        st.stop()

    if result.missing_columns:
        st.warning(
            "次の想定列が見つかりませんでした(該当列の処理はスキップしました): "
            + ", ".join(result.missing_columns)
        )

    s = dict(zip(result.summary_df["項目"], result.summary_df["値"]))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("入力行数", int(s.get("入力行数", 0)))
    c2.metric("クレンジング済行数", int(s.get("クレンジング済 行数(完全重複除外後)", 0)))
    c3.metric("完全重複で除外", int(s.get("完全重複により除外した行数", 0)))
    c4.metric("要確認行数", int(s.get("要確認(個別対応が必要)行数", 0)))

    st.subheader("クレンジング済データ(プレビュー)")
    st.dataframe(result.clean_df, use_container_width=True)

    st.subheader("問題種別ごとの件数")
    if len(result.report_df) == 0:
        st.success("品質上の問題は検出されませんでした。")
    else:
        st.dataframe(result.report_df, use_container_width=True)

    excel_buf = cleansing.build_excel(result)
    base = uploaded.name.rsplit(".", 1)[0]
    filename = f"{base}_cleaned.xlsx"

    st.subheader("保存")
    st.download_button(
        "📥 この端末にダウンロード",
        data=excel_buf,
        file_name=filename,
        mime=XLSX_MIME,
    )

    if conf is not None and "gdrive_creds" in st.session_state:
        if st.button("☁️ Google ドライブに保存"):
            try:
                creds = gdrive.dict_to_creds(st.session_state["gdrive_creds"])
                service = gdrive.build_drive_service(creds)
                excel_buf.seek(0)
                info = gdrive.upload_excel(service, excel_buf, filename)
                st.session_state["gdrive_creds"] = gdrive.creds_to_dict(creds)
                if info.get("link"):
                    st.success(f"Google ドライブに保存しました: [{filename}]({info['link']})")
                else:
                    st.success(f"Google ドライブに保存しました: {filename}")
            except Exception as e:
                st.error(f"Google ドライブへの保存に失敗しました: {e}")
    elif conf is not None:
        st.caption("左の「Google で接続」で連携すると、ここから Google ドライブにも保存できます。")

st.divider()
st.caption(
    "⚠️ アップロードされたファイルはサーバーのメモリ上で処理され、保存されません。"
    "ただし無料の公開サービスのため、本番の機微な個人情報のアップロードは避けてください。"
)
