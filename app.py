# -*- coding: utf-8 -*-
import streamlit as st

import cleansing

st.set_page_config(page_title="ファイルクレンジング", page_icon="🧹", layout="wide")

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
    st.download_button(
        "📥 クレンジング済 Excel をダウンロード",
        data=excel_buf,
        file_name=f"{base}_cleaned.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

st.divider()
st.caption(
    "⚠️ アップロードされたファイルはサーバーのメモリ上で処理され、保存されません。"
    "ただし無料の公開サービスのため、本番の機微な個人情報のアップロードは避けてください。"
)
