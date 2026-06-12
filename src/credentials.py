"""
Credential loader — works for both local (.env) and Streamlit Cloud (st.secrets).
Import _get_client() and _get_sheet_id() from here everywhere.
"""

import os
import gspread
from pathlib import Path
from google.oauth2.service_account import Credentials

# Auto-load .env from the project root (works for both CLI and Streamlit)
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(dotenv_path=_env_path, override=False)
except ImportError:
    pass

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


_SHEET_ID = "1f9bBUB1DcDHJpiVKc_IOw2Y7GDa4uMsKqv_P9pWKLG8"

_SA_INFO = {
    "type": "service_account",
    "project_id": "gen-lang-client-0887627891",
    "private_key_id": "0de53993cae6a11701be36a51acb3c5c14679742",
    "private_key": (
        "-----BEGIN PRIVATE KEY-----\n"
        "MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQCrfxSHqnlPbUsB\n"
        "/yFYb3Ve2/QsvkNU5TQ2fx7GbWNSo1siUffXendrW66YPKqolEeeTT+jBXYO7S0j\n"
        "Ccyl0c7AR+7vt1MiysDPGd7YUIo4/2DaO1+zzld5ftAD8oY80Gh5Sjb+SzvbpJgW\n"
        "4jRKDFSg+ROuRTrVf7AY9Fx+OXOCBYC1tuke1ST5fEh4PtpvgU3Glgz4Oq8o1aHA\n"
        "ZSqoEVKJ+S6ke1PSLQcItnEPo5xP2PzTCftHgBv0xOIilcfrr3Z7zHn5bRaLCOoy\n"
        "wi5hDUt3ZHEv104ey6MFccxBMQacovOwIPnyyosIjMDn5azZCn1M2cjb5AwoH3N0\n"
        "x/8lOgblAgMBAAECggEAAuiXWQuvngS9Am4oyx6sz2yMkhux+aUfgxMZ2wSs7BBg\n"
        "Mc9RFEL79oKqDePtgwlsw4cM3r9vdqZYHyGB6ogJ6SHvL/qcetkUdw65xFJtXbUb\n"
        "F+hs4ZhMzH81mPOKikqAkxoKn7p36+w5Nh4lA+J8pvRCfLCo5EkTnAC89tkTl+9n\n"
        "1yjlWmScuUFDsU/aXhwBVuNx76xofnrRzCg4olUlTgQ0JxqhqxBSb3JLK6GcJj3V\n"
        "kM/eudOiih4wcBU9c1GDZfqOACEf8aV3kgmVquHmRjx+gZtZcHDBf8ejkdoV0Pep\n"
        "mg8+UT4frlfkFi+flzN7U6uyMbnEDKOwhGrx06rYsQKBgQDcTgO5xY4Na71K8E2Q\n"
        "3bwZBjaexRLdFrSErp3hpx8OlXCtX1qsmJwFrPapPl1c/Dtb20ZBQgKDZgwGZEBO\n"
        "tCjdhda5GfU1i9J662JChHuZTLCJPT5Xe3mtnqPi2n4szayxNP6TqVVGBuo6Dddz\n"
        "uSI11Og8XFFDfBsk1JeJZl/ouQKBgQDHSI1o3K7S8vljbgVmIz8Oiv0CYg+2sElb\n"
        "B97TacrZZShOwlsXdemQNbGWxthvf2FUWlsnJcRzMAIWTA3znkGunNZR0QthrtoG\n"
        "0/Lu3QOq/uFWl8UPGajNjFCJlyUqaHmGmrlJgA6uCiPeAosbkasfeRcBv7n9b9kz\n"
        "idtqbx8hjQKBgEwLaeHQPY6IaBjcBgpBX9JLgMMhR7elRL6f/8OKin/gObq+tW/q\n"
        "ZcDXyXT2IAge0OaONBwGixOMQA5cwI3qRkjhEBNo0GmhUBA5+/r1/CwYer+EsmZE\n"
        "KuYxYmTGAtO4UyoAHvgddV/styE+8eXyO8rVKSzcuPhQeJYoA/7bpbORAoGAcHjm\n"
        "NpS2pqAzWIazzV1/LToMadfmfnkoLZRXkoJW1jNdeHYA61DFLXrga/R2GxeNWwpT\n"
        "/9g0873Yr7Tk+uYKs/4Yh7yv68W/j7L3nRBoDY4kp7aopUkaGEhk/AKuGy0zyWBx\n"
        "yqXXoypd6+MLl9ey+ORis739vqftskTP7VYh/9ECgYA2GE/R2GYPsmY/wAz8qOLV\n"
        "XzYAvkcpmSDuhqsn7KO9SgSt79NZxz5GG603KQsCHC5Zxe7dZGjBGqwCCsGRqd6n\n"
        "98YqBhvcdAd5m7jnwahsiBDUYYUfhfhBVF54wkeq8qJRCglwGBrEF/0fYAGEFN4p\n"
        "pbeb9YgyQGYwtL7WLXQnNA==\n"
        "-----END PRIVATE KEY-----\n"
    ),
    "client_email": "virventures-sheets@gen-lang-client-0887627891.iam.gserviceaccount.com",
    "client_id": "104843377759949550086",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/virventures-sheets%40gen-lang-client-0887627891.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com",
}


def has_credentials() -> bool:
    return True  # embedded credentials always available


def _get_client() -> gspread.Client:
    """Return an authorised gspread client using embedded service account."""
    try:
        import streamlit as st
        if "google_service_account" in st.secrets:
            info = {k: str(v) for k, v in dict(st.secrets["google_service_account"]).items()}
            creds = Credentials.from_service_account_info(info, scopes=SCOPES)
            return gspread.authorize(creds)
    except Exception:
        pass
    creds = Credentials.from_service_account_info(_SA_INFO, scopes=SCOPES)
    return gspread.authorize(creds)


def _get_sheet_id() -> str:
    try:
        import streamlit as st
        val = st.secrets.get("GOOGLE_SHEET_ID")
        if val:
            return str(val)
    except Exception:
        pass
    return os.getenv("GOOGLE_SHEET_ID") or _SHEET_ID
