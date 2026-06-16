# -*- coding: utf-8 -*-
"""表示専用ヘルパー(クリーン＆プロのUI)。処理ロジックは持たない。

CSS とヘッダーHTMLは固定文字列のみを st.markdown(unsafe_allow_html=True) で
注入する。ユーザー入力を HTML に埋め込まないこと(インジェクション防止)。
CSS は装飾専用で、将来 Streamlit のセレクタが変わって外れても機能は壊れず
素のスタイルに戻るだけ(グレースフルデグレード)。
"""
import streamlit as st

# アクセント色など。config.toml のテーマと揃える。
_NAVY = "#1B3A5B"
_NAVY_2 = "#274C77"

CUSTOM_CSS = """
<style>
/* 本文の余白を少し広げる */
.block-container { padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1080px; }

/* メトリクスをカード風に */
[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #E8EEF4;
    border-radius: 10px;
    padding: 14px 16px;
    box-shadow: 0 1px 3px rgba(27, 58, 91, 0.06);
}

/* ボタンを統一(角丸・余白・太字) */
.stButton > button, .stDownloadButton > button, .stLinkButton > a {
    border-radius: 8px;
    padding: 0.5rem 1.1rem;
    font-weight: 600;
}

/* 見出し(st.subheader)の上に少し余白 */
h2, h3 { margin-top: 0.6rem; }
</style>
"""


def header_html(title, subtitle):
    """ネイビー帯の見出しブロックのHTMLを返す純関数(固定文言用)。"""
    return (
        '<div style="background: linear-gradient(135deg, {navy}, {navy2});'
        ' border-radius: 14px; padding: 22px 26px; margin-bottom: 18px;">'
        '<div style="color:#FFFFFF; font-size:1.7rem; font-weight:700;">'
        "\U0001f9f9 {title}</div>"
        '<div style="color:#D6E0EC; font-size:0.95rem; margin-top:6px;">'
        "{subtitle}</div>"
        "</div>"
    ).format(navy=_NAVY, navy2=_NAVY_2, title=title, subtitle=subtitle)


def inject_css():
    """カスタムCSSを一度だけ注入する。"""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_header(title, subtitle):
    """ネイビー帯の見出しブロックを描画する。"""
    st.markdown(header_html(title, subtitle), unsafe_allow_html=True)
