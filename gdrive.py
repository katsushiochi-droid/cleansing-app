# -*- coding: utf-8 -*-
"""Google ドライブ保存(per-user OAuth)。Streamlit 非依存のロジック。"""
import datetime as dt
import os

os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def pick_redirect_uri(conf):
    """secrets の redirect_uri(単数の文字列)または redirect_uris(文字列/配列)の
    どちらでも受け付け、単一のリダイレクトURI文字列を返す。無ければ None。"""
    redirect = conf.get("redirect_uri")
    if not redirect:
        ru = conf.get("redirect_uris")
        if isinstance(ru, (list, tuple)):
            redirect = ru[0] if ru else None
        else:
            redirect = ru
    return redirect or None


def _client_config(oauth_conf):
    return {
        "web": {
            "client_id": oauth_conf["client_id"],
            "client_secret": oauth_conf["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": [oauth_conf["redirect_uri"]],
        }
    }


def build_flow(oauth_conf, state=None):
    # PKCE(code_verifier/code_challenge)は無効化する。
    # 認可URL生成時の Flow と token 交換時の Flow は別インスタンスで、間でページが
    # 全リロードされ session_state が消えるため、code_verifier を引き継げない。
    # 本アプリは client_secret を持つ機密(web)クライアントのため、client_secret により
    # token 交換が保証され、PKCE がなくても標準の Web アプリ OAuth フローとして成立する。
    flow = Flow.from_client_config(
        _client_config(oauth_conf),
        scopes=SCOPES,
        state=state,
        autogenerate_code_verifier=False,
    )
    flow.redirect_uri = oauth_conf["redirect_uri"]
    return flow


def get_authorization_url(flow):
    url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return url, state


def exchange_code(flow, code):
    flow.fetch_token(code=code)
    return flow.credentials


def build_drive_service(credentials):
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def upload_excel(service, buf, filename):
    buf.seek(0)
    media = MediaIoBaseUpload(buf, mimetype=XLSX_MIME, resumable=False)
    created = (
        service.files()
        .create(body={"name": filename}, media_body=media, fields="id,webViewLink")
        .execute()
    )
    return {"id": created.get("id"), "link": created.get("webViewLink")}


def creds_to_dict(credentials):
    return {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
        "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
    }


def dict_to_creds(d):
    return Credentials(
        token=d.get("token"),
        refresh_token=d.get("refresh_token"),
        token_uri=d.get("token_uri"),
        client_id=d.get("client_id"),
        client_secret=d.get("client_secret"),
        scopes=d.get("scopes"),
        expiry=dt.datetime.fromisoformat(d["expiry"]) if d.get("expiry") else None,
    )
