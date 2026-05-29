import altair as alt
import json
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import bcrypt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

HERE = Path(__file__).parent
ROOT = HERE.parent
PASTA_ENVIADOS    = ROOT / "corban" / "enviados"
PASTA_CONVERTIDOS = ROOT / "corban" / "convertidos"
DATA_DIR          = HERE / "data"

APP_NAME  = "ZiliTrack"
GOLD      = "#F0B429"
DARK_CARD = "#1A1A1A"
BORDER    = "#262626"
MUTED     = "#6B7280"

CORBAN_NAMES = {
    "assuncao":      "Assunção",
    "suapromotora":  "Sua Promotora",
}

CSS = f"""
<style>
/* ── chrome do Streamlit ─────────────────────────────────────── */
#MainMenu {{ visibility: hidden; }}
footer {{ visibility: hidden; }}
[data-testid="stDecoration"] {{ display: none; }}
[data-testid="stToolbarActions"] {{ visibility: hidden; }}
[data-testid="stBaseButton-header"] {{ visibility: hidden; }}

/* ── sidebar largura fixa (só conteúdo interno) ──────────────── */
[data-testid="stSidebar"] > div:first-child {{
    width: 260px !important;
    min-width: 260px !important;
    max-width: 260px !important;
}}
[data-testid="InputInstructions"] {{ display: none !important; }}
h1 a, h2 a, h3 a, h4 a, h5 a, h6 a {{ display: none !important; }}

/* ── fundo geral ─────────────────────────────────────────────── */
.stApp {{ background-color: #0F0F0F; }}

/* ── sidebar ─────────────────────────────────────────────────── */
[data-testid="stSidebar"] > div:first-child {{
    background-color: #111111;
    border-right: 1px solid {BORDER};
    padding-top: 1.5rem;
}}

/* ── botão primário (Entrar, Sair) ───────────────────────────── */
.stButton > button {{
    background-color: {GOLD} !important;
    color: #0F0F0F !important;
    border: none !important;
    font-weight: 600 !important;
    border-radius: 6px !important;
    transition: background-color 0.15s;
}}
.stButton > button:hover {{
    background-color: #D4980F !important;
    color: #0F0F0F !important;
}}

/* ── botão de download ───────────────────────────────────────── */
.stDownloadButton > button {{
    background-color: transparent !important;
    color: {GOLD} !important;
    border: 1px solid {GOLD} !important;
    font-weight: 500 !important;
    border-radius: 6px !important;
}}
.stDownloadButton > button:hover {{
    background-color: rgba(240,180,41,0.08) !important;
}}

/* ── inputs de texto ─────────────────────────────────────────── */
[data-testid="InputInstructions"] {{ display: none !important; }}
div[data-baseweb="input"] > div {{
    background-color: {DARK_CARD} !important;
    border-color: #333333 !important;
    border-radius: 6px !important;
}}
div[data-baseweb="input"] > div:focus-within {{
    border-color: {GOLD} !important;
    box-shadow: none !important;
}}

/* ── selectbox ───────────────────────────────────────────────── */
div[data-baseweb="select"] > div {{
    background-color: {DARK_CARD} !important;
    border-color: #333333 !important;
    border-radius: 6px !important;
}}
div[data-baseweb="select"] > div:focus-within {{
    border-color: {GOLD} !important;
    box-shadow: none !important;
}}

/* ── dataframe ───────────────────────────────────────────────── */
[data-testid="stDataFrame"] {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    overflow: hidden;
}}

/* ── menu de navegação (radio sem bolinhas) ──────────────────── */
[data-testid="stSidebar"] div[data-testid="stRadio"] > div {{
    gap: 2px !important;
}}
[data-testid="stSidebar"] div[data-testid="stRadio"] > div > label > div:first-child {{
    display: none !important;
}}
[data-testid="stSidebar"] div[data-testid="stRadio"] > div > label {{
    padding: 0.45rem 0.75rem !important;
    border-radius: 6px !important;
    cursor: pointer !important;
    transition: background-color 0.15s !important;
    width: 100% !important;
}}
[data-testid="stSidebar"] div[data-testid="stRadio"] > div > label:hover {{
    background-color: rgba(255,255,255,0.05) !important;
}}
[data-testid="stSidebar"] div[data-testid="stRadio"] > div > label:has(input:checked) {{
    background-color: rgba(240,180,41,0.12) !important;
    color: {GOLD} !important;
    font-weight: 600 !important;
}}

/* ── divisor ─────────────────────────────────────────────────── */
hr {{ border-color: {BORDER} !important; }}

/* ── rodapé ──────────────────────────────────────────────────── */
.footer {{
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    text-align: center;
    padding: 0.55rem 1rem;
    background-color: #111111;
    border-top: 1px solid {BORDER};
    font-size: 0.72rem;
    color: {MUTED};
    z-index: 999;
}}
</style>
"""


# {username: {"count": int, "blocked_until": datetime | None}}
_login_attempts: dict = {}

# ── autenticação ──────────────────────────────────────────────────────────────

def load_users():
    if "users" in st.secrets:
        return {u: dict(data) for u, data in st.secrets["users"].items()}
    with open(HERE / "users.json", encoding="utf-8") as f:
        return json.load(f)


def _login_header(subtitle: str):
    st.markdown(f"""
        <div style="text-align:center; margin-top:5rem; margin-bottom:2.5rem;">
            <h1 style="color:{GOLD}; font-size:2.8rem; font-weight:700;
                       letter-spacing:1px; margin-bottom:0.3rem;">
                {APP_NAME}
            </h1>
            <p style="color:{MUTED}; font-size:0.95rem; margin:0;">{subtitle}</p>
        </div>
    """, unsafe_allow_html=True)


def find_user_by_email(email: str) -> tuple[str, dict] | tuple[None, None]:
    users = load_users()
    email = email.strip().lower()
    for username, data in users.items():
        if data.get("email", "").strip().lower() == email:
            return username, data
    return None, None


def login_page():
    if st.session_state.get("awaiting_2fa"):
        _login_2fa()
        return

    _login_header("Plataforma de Gestão de Propostas · ZiliCred")
    _, col, _ = st.columns([1, 1, 1])
    with col:
        with st.form("login_form"):
            email_input = st.text_input("E-mail")
            password    = st.text_input("Senha", type="password")
            submitted   = st.form_submit_button("Entrar", width="stretch")

    if submitted:
        username, user = find_user_by_email(email_input)
        attempt = _login_attempts.get(email_input, {"count": 0, "blocked_until": None})
        blocked_until = attempt["blocked_until"]

        if blocked_until and datetime.now() < blocked_until:
            remaining = int((blocked_until - datetime.now()).total_seconds() / 60)
            with col:
                st.error(f"Acesso bloqueado por tentativas inválidas. Tente novamente em {remaining} minuto(s).")
        else:
            try:
                pw_ok = user is not None and bcrypt.checkpw(password.encode(), user["password"].encode())
            except Exception:
                pw_ok = False
            if pw_ok:
                _login_attempts.pop(email_input, None)
                smtp_ok = bool(st.secrets.get("smtp", {}).get("user"))
                if user.get("email") and smtp_ok:
                    ok = generate_email_otp(username)
                    if ok:
                        st.session_state["awaiting_2fa"] = True
                        st.session_state["2fa_username"] = username
                        st.rerun()
                    else:
                        with col:
                            st.error("Erro ao enviar código de verificação. Tente novamente.")
                else:
                    _complete_login(username, user)
            else:
                attempt["count"] += 1
                if attempt["count"] >= 3:
                    attempt["blocked_until"] = datetime.now() + timedelta(hours=1)
                _login_attempts[email_input] = attempt
                with col:
                    if attempt["count"] >= 3:
                        st.error("Acesso bloqueado por 1 hora após tentativas inválidas.")
                    else:
                        st.error("E-mail ou senha incorretos.")


def _2fa_cleanup():
    for k in ["awaiting_2fa", "2fa_username"]:
        st.session_state.pop(k, None)


def _login_2fa():
    username     = st.session_state["2fa_username"]
    user         = load_users()[username]
    email_masked = _mask_email(user.get("email", ""))

    _login_header("Verificação em dois fatores")
    _, col, _ = st.columns([1, 1, 1])

    with col:
        st.info(f"Código enviado para **{email_masked}**. Válido por 10 minutos.")
        with st.form("otp_form"):
            code      = st.text_input("Código de verificação", max_chars=6, placeholder="000000")
            submitted = st.form_submit_button("Verificar", width="stretch")
        if submitted:
            if verify_email_otp(username, code):
                _2fa_cleanup()
                _complete_login(username, user)
            else:
                st.error("Código inválido ou expirado.")
        st.markdown("<div style='margin-top:0.5rem;'></div>", unsafe_allow_html=True)
        if st.button("Reenviar código", use_container_width=True):
            generate_email_otp(username)
            st.toast("Código reenviado.")
        if st.button("← Voltar ao login", use_container_width=True):
            _2fa_cleanup()
            st.rerun()


def _complete_login(username: str, user: dict):
    log_access(username, user["display_name"])
    st.session_state.update({
        "logged_in":      True,
        "username":       username,
        "corban":         user.get("corban"),
        "display_name":   user["display_name"],
        "is_admin":       user.get("is_admin", False),
        "expand_sidebar": True,
    })
    st.rerun()


# ── persistência ──────────────────────────────────────────────────────────────

def _load_json(path: Path, default):
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default


def _save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── OTP por e-mail ────────────────────────────────────────────────────────────

def _mask_email(email: str) -> str:
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    return local[:2] + "***@" + domain


def generate_email_otp(username: str) -> bool:
    import secrets as _secrets
    users = load_users()
    email = users.get(username, {}).get("email")
    if not email:
        return False
    try:
        smtp_cfg = st.secrets.get("smtp", {})
        if not smtp_cfg or not smtp_cfg.get("user"):
            return False
        code    = f"{_secrets.randbelow(1000000):06d}"
        expires = (datetime.utcnow() + timedelta(minutes=10)).isoformat(timespec="seconds")
        path    = DATA_DIR / "email_otp.json"
        data    = _load_json(path, {})
        data[username] = {"code": code, "expires": expires}
        _save_json(path, data)
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Código de verificação · {APP_NAME}"
        msg["From"]    = f"{APP_NAME} <{smtp_cfg['user']}>"
        msg["To"]      = email
        corpo = (
            f"Seu código de verificação é:\n\n"
            f"    {code}\n\n"
            f"Válido por 10 minutos.\n"
            f"Se você não solicitou este código, ignore este e-mail.\n\n"
            f"— ZiliCred"
        )
        msg.attach(MIMEText(corpo, "plain", "utf-8"))
        with smtplib.SMTP(smtp_cfg.get("host", "smtp.gmail.com"), int(smtp_cfg.get("port", 587))) as srv:
            srv.starttls()
            srv.login(smtp_cfg["user"], smtp_cfg["password"])
            srv.sendmail(smtp_cfg["user"], email, msg.as_string())
        return True
    except Exception:
        return False


def verify_email_otp(username: str, code: str) -> bool:
    path  = DATA_DIR / "email_otp.json"
    data  = _load_json(path, {})
    entry = data.get(username)
    if not entry:
        return False
    try:
        if datetime.utcnow() > datetime.fromisoformat(entry["expires"]):
            return False
        if entry["code"] == code.strip():
            data.pop(username)
            _save_json(path, data)
            return True
    except Exception:
        pass
    return False


# ── e-mail ─────────────────────────────────────────────────────────────────────

def send_upload_notification(corbans_notificados: list[str]):
    try:
        smtp_cfg = st.secrets.get("smtp", {})
        if not smtp_cfg or not smtp_cfg.get("user"):
            return
        app_url = st.secrets.get("app", {}).get("url", "https://zilitrack.streamlit.app")
        users   = load_users()
        # Notifica todos os usuários cujo corban está na lista
        destinatarios = [
            u for u in users.values()
            if u.get("corban") in corbans_notificados and u.get("email")
        ]
        for user in destinatarios:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Nova base disponível · {APP_NAME}"
            msg["From"]    = f"{APP_NAME} <{smtp_cfg['user']}>"
            msg["To"]      = user["email"]
            corpo = (
                f"Olá, {user.get('display_name', '')}!\n\n"
                f"Uma nova base de clientes está disponível na plataforma {APP_NAME}.\n\n"
                f"Acesse agora: {app_url}\n\n"
                f"— ZiliCred"
            )
            msg.attach(MIMEText(corpo, "plain", "utf-8"))
            with smtplib.SMTP(smtp_cfg.get("host", "smtp.gmail.com"), int(smtp_cfg.get("port", 587))) as srv:
                srv.starttls()
                srv.login(smtp_cfg["user"], smtp_cfg["password"])
                srv.sendmail(smtp_cfg["user"], user["email"], msg.as_string())
    except Exception:
        pass


# ── download seguro ───────────────────────────────────────────────────────────

def generate_download_otp(username: str) -> bool:
    import secrets as _secrets
    users = load_users()
    email = users.get(username, {}).get("email")
    if not email:
        return False
    try:
        smtp_cfg = st.secrets.get("smtp", {})
        if not smtp_cfg or not smtp_cfg.get("user"):
            return False
        code    = f"{_secrets.randbelow(1000000):06d}"
        expires = (datetime.utcnow() + timedelta(minutes=10)).isoformat(timespec="seconds")
        path    = DATA_DIR / "download_otp.json"
        data    = _load_json(path, {})
        data[username] = {"code": code, "expires": expires}
        _save_json(path, data)
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Código para download · {APP_NAME}"
        msg["From"]    = f"{APP_NAME} <{smtp_cfg['user']}>"
        msg["To"]      = email
        corpo = (
            f"Seu código para autorizar o download é:\n\n"
            f"    {code}\n\n"
            f"Válido por 10 minutos.\n\n— ZiliCred"
        )
        msg.attach(MIMEText(corpo, "plain", "utf-8"))
        with smtplib.SMTP(smtp_cfg.get("host", "smtp.gmail.com"), int(smtp_cfg.get("port", 587))) as srv:
            srv.starttls()
            srv.login(smtp_cfg["user"], smtp_cfg["password"])
            srv.sendmail(smtp_cfg["user"], email, msg.as_string())
        return True
    except Exception:
        return False


def verify_download_otp(username: str, code: str) -> bool:
    path  = DATA_DIR / "download_otp.json"
    data  = _load_json(path, {})
    entry = data.get(username)
    if not entry:
        return False
    try:
        if datetime.utcnow() > datetime.fromisoformat(entry["expires"]):
            return False
        if entry["code"] == code.strip():
            data.pop(username)
            _save_json(path, data)
            return True
    except Exception:
        pass
    return False


def generate_file_password() -> str:
    import secrets as _secrets
    import string
    alphabet = string.ascii_letters + string.digits
    return "".join(_secrets.choice(alphabet) for _ in range(10))


def send_file_password_email(username: str, password: str, filename: str):
    try:
        smtp_cfg = st.secrets.get("smtp", {})
        if not smtp_cfg or not smtp_cfg.get("user"):
            return
        users = load_users()
        email = users.get(username, {}).get("email")
        if not email:
            return
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Senha do arquivo · {APP_NAME}"
        msg["From"]    = f"{APP_NAME} <{smtp_cfg['user']}>"
        msg["To"]      = email
        corpo = (
            f"A senha para abrir o arquivo {filename} é:\n\n"
            f"    {password}\n\n"
            f"Use esta senha ao abrir o arquivo Excel baixado.\n\n— ZiliCred"
        )
        msg.attach(MIMEText(corpo, "plain", "utf-8"))
        with smtplib.SMTP(smtp_cfg.get("host", "smtp.gmail.com"), int(smtp_cfg.get("port", 587))) as srv:
            srv.starttls()
            srv.login(smtp_cfg["user"], smtp_cfg["password"])
            srv.sendmail(smtp_cfg["user"], email, msg.as_string())
    except Exception:
        pass


def create_encrypted_excel(df: pd.DataFrame, password: str) -> bytes:
    import io
    import msoffcrypto
    excel_buf = io.BytesIO()
    df.to_excel(excel_buf, index=False)
    excel_buf.seek(0)
    encrypted_buf = io.BytesIO()
    office_file = msoffcrypto.OfficeFile(excel_buf)
    office_file.encrypt(password, encrypted_buf)
    encrypted_buf.seek(0)
    return encrypted_buf.read()


def _render_download_seguro(username: str, page: str, selected: str,
                             df: pd.DataFrame, base_filename: str):
    """Renderiza o fluxo de download com OTP + Excel criptografado."""
    key      = f"{page}_{selected}"
    dl       = st.session_state.get("dl_state", {})
    xl_name  = base_filename.replace(".csv", ".xlsx")

    if dl.get("key") == key and dl.get("step") == "ready":
        st.success("Senha enviada por e-mail. Use-a para abrir o arquivo Excel.")
        clicked = st.download_button(
            "Baixar arquivo",
            data=dl["xl_bytes"],
            file_name=dl["filename"],
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        if clicked:
            st.session_state.pop("dl_state", None)
            st.rerun()

    elif dl.get("key") == key and dl.get("step") == "otp":
        users        = load_users()
        email_masked = _mask_email(users.get(username, {}).get("email", ""))
        st.info(f"Código enviado para **{email_masked}**. Válido por 10 minutos.")
        with st.form(f"dl_otp_{key}"):
            code      = st.text_input("Código de verificação", max_chars=6, placeholder="000000")
            submitted = st.form_submit_button("Confirmar download", width="stretch")
        if submitted:
            if verify_download_otp(username, code):
                pwd     = generate_file_password()
                xl_data = create_encrypted_excel(df, pwd)
                send_file_password_email(username, pwd, xl_name)
                st.session_state["dl_state"] = {
                    "key": key, "step": "ready",
                    "xl_bytes": xl_data, "filename": xl_name,
                }
                st.rerun()
            else:
                st.error("Código inválido ou expirado.")
        if st.button("Cancelar", key=f"dl_cancel_otp_{key}"):
            st.session_state.pop("dl_state", None)
            st.rerun()

    else:
        if st.button("Solicitar download", key=f"dl_btn_{key}"):
            if generate_download_otp(username):
                st.session_state["dl_state"] = {"key": key, "step": "otp"}
                st.rerun()
            else:
                st.error("Erro ao enviar código. Verifique a configuração de e-mail.")


_DUMMY_CLIENTES = pd.DataFrame([
    {"Data e Hora do Processamento": "DD/MM/AAAA HH:MM", "CPF": "111.111.111-11", "Nome do Cliente": "Nome Sobrenome"},
    {"Data e Hora do Processamento": "DD/MM/AAAA HH:MM", "CPF": "222.222.222-22", "Nome do Cliente": "Nome Sobrenome"},
    {"Data e Hora do Processamento": "DD/MM/AAAA HH:MM", "CPF": "333.333.333-33", "Nome do Cliente": "Nome Sobrenome"},
])

_DUMMY_CONVERSAO = pd.DataFrame([
    {"Data e Hora do Processamento": "DD/MM/AAAA HH:MM", "CPF": "111.111.111-11", "Nome do Cliente": "Nome Sobrenome", "Valor do Contrato": "R$ 0.000,00"},
    {"Data e Hora do Processamento": "DD/MM/AAAA HH:MM", "CPF": "222.222.222-22", "Nome do Cliente": "Nome Sobrenome", "Valor do Contrato": "R$ 0.000,00"},
    {"Data e Hora do Processamento": "DD/MM/AAAA HH:MM", "CPF": "333.333.333-33", "Nome do Cliente": "Nome Sobrenome", "Valor do Contrato": "R$ 0.000,00"},
])


def log_access(username: str, display_name: str):
    path = DATA_DIR / "access_log.json"
    log = _load_json(path, {})
    log[username] = {
        "last_access": datetime.now().isoformat(timespec="seconds"),
        "display_name": display_name,
    }
    _save_json(path, log)


def log_upload(filename: str):
    path = DATA_DIR / "upload_log.json"
    data = _load_json(path, {})
    data[filename] = datetime.utcnow().isoformat(timespec="seconds")
    _save_json(path, data)


def get_latest_processamento(df: pd.DataFrame) -> str | None:
    col = "Data e Hora do Processamento"
    if col not in df.columns or df.empty:
        return None
    try:
        dates = pd.to_datetime(df[col], format="%d/%m/%Y %H:%M:%S", errors="coerce").dropna()
        if dates.empty:
            return None
        return (dates.max() + timedelta(minutes=20)).strftime("%d/%m/%Y às %H:%M")
    except Exception:
        return None


def get_upload_time(filename: str, file_path: Path | None = None) -> str | None:
    data = _load_json(DATA_DIR / "upload_log.json", {})
    ts = data.get(filename)
    if ts:
        try:
            dt = datetime.fromisoformat(ts) - timedelta(hours=3)
            return dt.strftime("%d/%m/%Y às %H:%M")
        except Exception:
            pass
    if file_path and file_path.exists():
        try:
            dt = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc).replace(tzinfo=None) - timedelta(hours=3)
            return dt.strftime("%d/%m/%Y às %H:%M")
        except Exception:
            pass
    return None


def update_last_seen(corban: str, date_str: str):
    path = DATA_DIR / "last_seen.json"
    data = _load_json(path, {})
    data[corban] = date_str
    _save_json(path, data)


def get_last_seen(corban: str) -> str | None:
    return _load_json(DATA_DIR / "last_seen.json", {}).get(corban)


def has_new_base(corban: str) -> bool:
    available = files_by_date(PASTA_ENVIADOS, corban, "enviados")
    if not available:
        return False
    try:
        latest_date = max(datetime.strptime(d, "%d-%m-%Y") for d in available)
        last_seen_str = get_last_seen(corban)
        if not last_seen_str:
            return True
        return latest_date > datetime.strptime(last_seen_str, "%d-%m-%Y")
    except ValueError:
        return False


# ── helpers ───────────────────────────────────────────────────────────────────

def read_csv(path):
    return pd.read_csv(path, sep=";", encoding="utf-8-sig", dtype=str, keep_default_na=False)


_CONECTIVOS = {"de", "da", "do", "das", "dos", "e", "a", "o", "em", "na", "no", "nas", "nos", "por", "para", "com"}

def fmt_nome(val) -> str:
    if not isinstance(val, str) or not val.strip():
        return ""
    words = val.strip().split()
    return " ".join(
        w.capitalize() if i == 0 or w.lower() not in _CONECTIVOS else w.lower()
        for i, w in enumerate(words)
    )


def fmt_brl(val) -> str:
    try:
        s = str(val).strip().replace("R$", "").strip()
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        n = float(s)
        fmt = f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {fmt}"
    except (ValueError, TypeError):
        return ""


def files_by_date(pasta: Path, corban: str | None, suffix: str) -> dict:
    if not pasta.exists() or not corban:
        return {}
    result = {}
    for f in sorted(pasta.glob(f"*_{corban}_*_{suffix}.csv")):
        parts = f.stem.split("_")
        if len(parts) >= 3:
            result[parts[2]] = f
    return result


def get_all_corbans() -> list:
    if not PASTA_ENVIADOS.exists():
        return []
    corbans = set()
    for f in PASTA_ENVIADOS.glob("*_enviados.csv"):
        parts = f.stem.split("_")
        if len(parts) >= 4:
            corbans.add(parts[1])
    return sorted(corbans)


def _parse_valor(val) -> float:
    try:
        s = str(val).strip().replace("R$", "").replace("\xa0", "").strip()
        if not s or s in ("-", "—"):
            return 0.0
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        return float(s)
    except Exception:
        return 0.0


def calcular_ranking() -> list[dict]:
    """Retorna lista ordenada por taxa de conversão desc: [{corban, enviados, convertidos, taxa, valor_total}]"""
    corbans = get_all_corbans()
    resultado = []
    for corban in corbans:
        enviados = sum(
            len(read_csv(f)) for f in PASTA_ENVIADOS.glob(f"*_{corban}_*_enviados.csv")
        )
        convertidos = 0
        valor_total = 0.0
        if PASTA_CONVERTIDOS.exists():
            for f in PASTA_CONVERTIDOS.glob(f"*_{corban}_*_convertidos.csv"):
                df = read_csv(f)
                convertidos += len(df)
                col_valor = next((c for c in df.columns if "Valor" in c and "ontrat" in c), None)
                if col_valor:
                    try:
                        valor_total += float(df[col_valor].apply(_parse_valor).sum())
                    except Exception:
                        pass
        taxa = convertidos / enviados if enviados else 0.0
        resultado.append({
            "corban": corban,
            "enviados": enviados,
            "convertidos": convertidos,
            "taxa": taxa,
            "valor_total": valor_total,
        })
    resultado.sort(key=lambda x: x["taxa"], reverse=True)
    return resultado


def _sort_dates(dates: list[str]) -> list[str]:
    """Ordena datas no formato DD-MM-YYYY cronologicamente (mais recente primeiro)."""
    try:
        return sorted(dates, key=lambda d: datetime.strptime(d, "%d-%m-%Y"), reverse=True)
    except ValueError:
        return sorted(dates, reverse=True)


def get_evolution_data(corban: str | None) -> pd.DataFrame:
    if not corban or not PASTA_ENVIADOS.exists():
        return pd.DataFrame()
    rows = []
    for f_env in PASTA_ENVIADOS.glob(f"*_{corban}_*_enviados.csv"):
        parts = f_env.stem.split("_")
        if len(parts) < 3:
            continue
        date_str = parts[2]
        try:
            dt = datetime.strptime(date_str, "%d-%m-%Y")
        except ValueError:
            continue
        n_env = len(read_csv(f_env))
        n_conv = 0
        if PASTA_CONVERTIDOS.exists():
            for f_conv in PASTA_CONVERTIDOS.glob(f"*_{corban}_{date_str}_convertidos.csv"):
                n_conv += len(read_csv(f_conv))
        rows.append({
            "_date": dt,
            "Data": date_str,
            "Enviados": n_env,
            "Convertidos": n_conv,
            "Taxa (%)": round(n_conv / n_env * 100, 1) if n_env else 0.0,
        })
    if not rows:
        return pd.DataFrame()
    return (
        pd.DataFrame(rows)
        .sort_values("_date")
        .drop(columns=["_date"])
        .reset_index(drop=True)
    )


# ── páginas ───────────────────────────────────────────────────────────────────

def page_clientes(corban: str | None):
    st.header("Clientes", anchor=False)
    available = files_by_date(PASTA_ENVIADOS, corban, "enviados")
    if not available:
        if st.session_state.get("is_admin"):
            st.info("Nenhuma base enviada ainda. Acesse a página Upload para adicionar os arquivos.")
        else:
            st.info(
                "Nenhuma base de clientes disponível no momento. "
                "Assim que os dados forem enviados pela ZiliCred, eles aparecerão aqui automaticamente. "
                "Em caso de dúvidas, entre em contato com a equipe."
            )
        return

    selected = st.selectbox(
        "Data de envio da base",
        _sort_dates(list(available.keys())),
    )

    # Marca base como vista (apenas para corbans, não para admin)
    if corban and not st.session_state.get("is_admin"):
        latest = _sort_dates(list(available.keys()))[0]
        update_last_seen(corban, latest)

    df = (
        read_csv(available[selected])[["CPF", "NomeCliente", "Último Processamento"]]
        .rename(columns={"NomeCliente": "Nome do Cliente", "Último Processamento": "Data e Hora do Processamento"})
        [["Data e Hora do Processamento", "CPF", "Nome do Cliente"]]
    )
    if df.empty:
        st.info("Nenhum cliente registrado nesta base.")
        return

    df = df.fillna("")
    df["Nome do Cliente"] = df["Nome do Cliente"].apply(fmt_nome)

    total = len(df)
    enviado_em = get_latest_processamento(df)
    sep = f"<div style='width:1px; height:2.5rem; background:{BORDER};'></div>" if enviado_em else ""
    enviado_html = f"""
        {sep}
        <div>
            <div style="font-size:0.78rem; color:{MUTED}; margin-bottom:0.2rem;">Enviado em</div>
            <div style="font-size:1rem; font-weight:600; line-height:1;">{enviado_em}</div>
        </div>
    """ if enviado_em else ""
    st.markdown(f"""
        <div style="
            background: {DARK_CARD};
            border: 1px solid {BORDER};
            border-radius: 8px;
            padding: 1rem 1.5rem;
            margin-bottom: 1rem;
            display: flex;
            gap: 1.5rem;
            align-items: center;
            width: fit-content;
        ">
            <div>
                <div style="font-size:0.78rem; color:{MUTED}; margin-bottom:0.2rem;">Total de clientes</div>
                <div style="font-size:1.75rem; font-weight:700; color:{GOLD}; line-height:1;">{total}</div>
            </div>
            {enviado_html}
        </div>
    """, unsafe_allow_html=True)

    if st.session_state.get("is_admin"):
        df_display = df.copy()
        df_display.index = range(1, len(df_display) + 1)
        st.dataframe(df_display, width="stretch", hide_index=False)
        st.download_button(
            "Baixar CSV",
            df.to_csv(index=False, sep=";").encode("utf-8-sig"),
            file_name=f"clientes_{selected}.csv",
            mime="text/csv",
        )
    else:
        preview = _DUMMY_CLIENTES.copy()
        preview.index = range(1, len(preview) + 1)
        st.caption("Prévia do formato — dados reais disponíveis via download")
        st.dataframe(preview, use_container_width=True, hide_index=False)
        username = st.session_state.get("username", "")
        _render_download_seguro(username, "clientes", selected, df, f"clientes_{selected}.csv")


def page_conversao(corban: str | None):
    st.header("Conversão", anchor=False)

    available_conv = files_by_date(PASTA_CONVERTIDOS, corban, "convertidos")
    if not available_conv:
        if st.session_state.get("is_admin"):
            st.info("Nenhuma conversão disponível ainda. Acesse a página Upload para adicionar os arquivos.")
        else:
            st.info(
                "Nenhum relatório de conversão disponível no momento. "
                "Assim que os dados forem processados pela ZiliCred, eles aparecerão aqui automaticamente. "
                "Em caso de dúvidas, entre em contato com a equipe."
            )
        return

    selected = st.selectbox(
        "Data de envio da base",
        _sort_dates(list(available_conv.keys())),
    )

    df_conv = read_csv(available_conv[selected])

    available_env = files_by_date(PASTA_ENVIADOS, corban, "enviados")
    if selected in available_env:
        df_env = read_csv(available_env[selected])[["CPF", "NomeCliente", "Último Processamento"]]
        df_conv = df_conv.merge(df_env, on="CPF", how="left")

    cols = [c for c in ["CPF", "NomeCliente", "Último Processamento", "Valor Contratação"] if c in df_conv.columns]
    df_conv = (
        df_conv[cols]
        .rename(columns={
            "NomeCliente":          "Nome do Cliente",
            "Último Processamento": "Data e Hora do Processamento",
            "Valor Contratação":    "Valor do Contrato",
        })
    )
    if "Data e Hora do Processamento" in df_conv.columns:
        outras = [c for c in df_conv.columns if c != "Data e Hora do Processamento"]
        df_conv = df_conv[["Data e Hora do Processamento"] + outras]

    if df_conv.empty:
        st.info("Nenhuma conversão registrada para esta base.")
        return

    df_conv = df_conv.fillna("")
    if "Nome do Cliente" in df_conv.columns:
        df_conv["Nome do Cliente"] = df_conv["Nome do Cliente"].apply(fmt_nome)
    if "Valor do Contrato" in df_conv.columns:
        df_conv["Valor do Contrato"] = df_conv["Valor do Contrato"].apply(fmt_brl)

    total_conv = len(df_conv)
    upload_time = get_upload_time(available_conv[selected].name, available_conv[selected])
    sep = f"<div style='width:1px; height:2.5rem; background:{BORDER};'></div>" if upload_time else ""
    atualizado_html = f"""
        {sep}
        <div>
            <div style="font-size:0.78rem; color:{MUTED}; margin-bottom:0.2rem;">Atualizado em</div>
            <div style="font-size:1rem; font-weight:600; line-height:1;">{upload_time}</div>
        </div>
    """ if upload_time else ""
    st.markdown(f"""
        <div style="
            background: {DARK_CARD};
            border: 1px solid {BORDER};
            border-radius: 8px;
            padding: 1rem 1.5rem;
            margin-bottom: 1rem;
            display: flex;
            gap: 1.5rem;
            align-items: center;
            width: fit-content;
        ">
            <div>
                <div style="font-size:0.78rem; color:{MUTED}; margin-bottom:0.2rem;">Clientes convertidos</div>
                <div style="font-size:1.75rem; font-weight:700; color:{GOLD}; line-height:1;">{total_conv}</div>
            </div>
            {atualizado_html}
        </div>
    """, unsafe_allow_html=True)

    if st.session_state.get("is_admin"):
        df_conv_display = df_conv.copy()
        df_conv_display.index = range(1, len(df_conv_display) + 1)
        st.dataframe(df_conv_display, width="stretch", hide_index=False)
        st.download_button(
            "Baixar CSV",
            df_conv.to_csv(index=False, sep=";").encode("utf-8-sig"),
            file_name=f"conversao_{selected}.csv",
            mime="text/csv",
        )
    else:
        preview = _DUMMY_CONVERSAO.copy()
        preview.index = range(1, len(preview) + 1)
        st.caption("Prévia do formato — dados reais disponíveis via download")
        st.dataframe(preview, use_container_width=True, hide_index=False)
        username = st.session_state.get("username", "")
        _render_download_seguro(username, "conversao", selected, df_conv, f"conversao_{selected}.csv")

    evo = get_evolution_data(corban)
    if not evo.empty:
        st.divider()
        st.subheader("Evolução por Lote", anchor=False)
        chart = (
            alt.Chart(evo)
            .mark_line(color=GOLD, point=alt.OverlayMarkDef(color=GOLD, size=60))
            .encode(
                x=alt.X("Data:O", sort=None, title="Data de envio"),
                y=alt.Y("Taxa (%):Q", title="Taxa (%)"),
                tooltip=[
                    alt.Tooltip("Data:O", title="Data"),
                    alt.Tooltip("Enviados:Q", title="Enviados"),
                    alt.Tooltip("Convertidos:Q", title="Convertidos"),
                    alt.Tooltip("Taxa (%):Q", title="Taxa (%)", format=".1f"),
                ],
            )
            .properties(height=220)
        )
        st.altair_chart(chart, use_container_width=True)


def page_upload():
    st.header("Upload de Bases", anchor=False)

    st.session_state.setdefault("up_env_n", 0)
    st.session_state.setdefault("up_conv_n", 0)

    c1, c2 = st.columns(2)

    with c1:
        st.markdown(
            "<p style='font-weight:600; margin-bottom:0.5rem;'>Bases Enviadas</p>",
            unsafe_allow_html=True,
        )
        uploaded_env = st.file_uploader(
            "enviados", type="csv", accept_multiple_files=True,
            label_visibility="collapsed", key=f"up_env_{st.session_state.up_env_n}",
        )
        if uploaded_env and st.button("Salvar", key="btn_env"):
            PASTA_ENVIADOS.mkdir(parents=True, exist_ok=True)
            corbans_salvos = set()
            for f in uploaded_env:
                (PASTA_ENVIADOS / f.name).write_bytes(f.read())
                log_upload(f.name)
                parts = Path(f.name).stem.split("_")
                if len(parts) >= 2:
                    corbans_salvos.add(parts[1])
            send_upload_notification(list(corbans_salvos))
            st.session_state.up_env_n += 1
            st.rerun()

    with c2:
        st.markdown(
            "<p style='font-weight:600; margin-bottom:0.5rem;'>Conversões</p>",
            unsafe_allow_html=True,
        )
        uploaded_conv = st.file_uploader(
            "convertidos", type="csv", accept_multiple_files=True,
            label_visibility="collapsed", key=f"up_conv_{st.session_state.up_conv_n}",
        )
        bc1, bc2 = st.columns([1, 1])
        with bc1:
            if uploaded_conv and st.button("Salvar", key="btn_conv"):
                PASTA_CONVERTIDOS.mkdir(parents=True, exist_ok=True)
                for f in uploaded_conv:
                    (PASTA_CONVERTIDOS / f.name).write_bytes(f.read())
                    log_upload(f.name)
                st.session_state.up_conv_n += 1
                st.rerun()
        with bc2:
            if st.button("Limpar convertidos", key="btn_limpar"):
                if PASTA_CONVERTIDOS.exists():
                    for f in PASTA_CONVERTIDOS.glob("*.csv"):
                        f.unlink()
                st.rerun()

    st.divider()
    st.markdown(
        f"<p style='font-size:0.85rem; color:{MUTED}; margin-bottom:0.75rem;'>"
        f"Arquivos disponíveis no servidor</p>",
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        st.caption("Enviados")
        arqs_env = sorted(PASTA_ENVIADOS.glob("*.csv")) if PASTA_ENVIADOS.exists() else []
        for f in arqs_env:
            st.markdown(f"<span style='font-size:0.82rem;'>{f.name}</span>", unsafe_allow_html=True)
        if not arqs_env:
            st.markdown(f"<span style='font-size:0.82rem; color:{MUTED};'>Nenhum arquivo</span>", unsafe_allow_html=True)
    with c2:
        st.caption("Convertidos")
        arqs_conv = sorted(PASTA_CONVERTIDOS.glob("*.csv")) if PASTA_CONVERTIDOS.exists() else []
        for f in arqs_conv:
            st.markdown(f"<span style='font-size:0.82rem;'>{f.name}</span>", unsafe_allow_html=True)
        if not arqs_conv:
            st.markdown(f"<span style='font-size:0.82rem; color:{MUTED};'>Nenhum arquivo</span>", unsafe_allow_html=True)


def page_ranking(corban: str):
    st.header("Ranking", anchor=False)

    ranking = calcular_ranking()
    total = len(ranking)

    if total == 0:
        st.info("Ainda não há dados suficientes para exibir o ranking.")
        return

    posicao = next((i + 1 for i, r in enumerate(ranking) if r["corban"] == corban), None)

    if posicao is None:
        st.info("Sua promotora ainda não possui dados no ranking.")
        return

    sufixo = {1: "º", 2: "º", 3: "º"}.get(posicao, "º")
    medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(posicao, "")

    dados = next(r for r in ranking if r["corban"] == corban)
    taxa = dados["taxa"] * 100

    st.markdown(f"""
        <div style="margin-top:1.5rem; text-align:center;">
            <div style="font-size:4rem; line-height:1;">{medal if medal else "🏅"}</div>
            <div style="margin-top:1rem; font-size:1rem; color:{MUTED};">Você está em</div>
            <div style="font-size:3.5rem; font-weight:700; color:{GOLD}; line-height:1.1;">
                {posicao}{sufixo} lugar
            </div>
        </div>

        <div style="
            margin: 2.5rem auto 0 auto;
            max-width: 360px;
            background: #1A1A1A;
            border: 1px solid #262626;
            border-radius: 10px;
            padding: 1.25rem 1.5rem;
        ">
            <div style="display:flex; justify-content:space-between; margin-bottom:0.75rem;">
                <span style="color:{MUTED}; font-size:0.9rem;">Clientes enviados</span>
                <span style="font-weight:600;">{dados["enviados"]}</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:0.75rem;">
                <span style="color:{MUTED}; font-size:0.9rem;">Conversões</span>
                <span style="font-weight:600;">{dados["convertidos"]}</span>
            </div>
            <div style="display:flex; justify-content:space-between;">
                <span style="color:{MUTED}; font-size:0.9rem;">Taxa de conversão</span>
                <span style="font-weight:700; color:{GOLD};">{taxa:.1f}%</span>
            </div>
        </div>
    """, unsafe_allow_html=True)


def page_como_usar():
    st.header("Como Usar", anchor=False)

    st.markdown(f"""
        <div style="max-width:680px; line-height:1.75; color:#E5E7EB;">

        <h4 style="color:{GOLD}; margin-top:1.5rem;">Acesso à plataforma</h4>
        <p>
            O login é feito com o seu <b>e-mail</b> e <b>senha</b> fornecidos pela ZiliCred.
            Após inserir as credenciais corretamente, um <b>código de verificação</b> será
            enviado para o seu e-mail. Insira o código para concluir o acesso.
            O código é válido por 10 minutos — caso não chegue, verifique a caixa de spam
            ou clique em <b>Reenviar código</b>.
        </p>

        <h4 style="color:{GOLD}; margin-top:1.5rem;">Clientes</h4>
        <p>
            Exibe a base de clientes enviada pela ZiliCred para a sua promotora.
            Use o seletor <b>Data de envio da base</b> para alternar entre lotes.
            O card no topo mostra o total de clientes e a data de envio do lote selecionado.
            A tabela exibe uma prévia do formato — os dados reais são acessados via download.
        </p>
        <p>
            Para baixar a lista completa, clique em <b>Solicitar download</b>. Um código
            será enviado ao seu e-mail para autorizar o download. Após inserir o código,
            o arquivo Excel será gerado e uma senha para abri-lo será enviada por e-mail.
        </p>
        <p>
            Quando houver um lote novo ainda não visualizado, o menu exibirá
            um indicador <b>●</b> ao lado de <b>Clientes</b>. Ele desaparece assim que
            a página for aberta.
        </p>

        <h4 style="color:{GOLD}; margin-top:1.5rem;">Conversão</h4>
        <p>
            Exibe os clientes da sua base que efetivaram um contrato com a ZiliCred.
            Selecione o lote pela data de envio para visualizar o resumo de conversões.
            O download segue o mesmo fluxo da aba Clientes: código por e-mail para
            autorizar, e senha por e-mail para abrir o arquivo Excel.
        </p>
        <p>
            Abaixo da tabela, o gráfico <b>Evolução por Lote</b> mostra a taxa de
            conversão de cada lote ao longo do tempo. Passe o cursor sobre os pontos
            para ver o detalhe de enviados, convertidos e taxa de cada lote.
        </p>

        <h4 style="color:{GOLD}; margin-top:1.5rem;">Ranking</h4>
        <p>
            Mostra a sua posição no ranking geral de conversões entre as promotoras
            participantes. Os demais participantes não são identificados.
            Também são exibidos os seus totais de clientes enviados, convertidos
            e a taxa de conversão acumulada.
        </p>

        <h4 style="color:{GOLD}; margin-top:1.5rem;">Atualização dos dados</h4>
        <p>
            As bases de clientes e os relatórios de conversão são atualizados
            periodicamente pela equipe da ZiliCred. Caso alguma aba apareça sem
            informações, aguarde a próxima atualização. Você será notificado por
            e-mail assim que uma nova base for disponibilizada.
        </p>

        <h4 style="color:{GOLD}; margin-top:1.5rem;">Dúvidas ou problemas de acesso</h4>
        <p>
            Entre em contato com a ZiliCred pelo e-mail ou pelo seu gerente de relacionamento.
        </p>

        </div>
    """, unsafe_allow_html=True)


def page_dashboard():
    st.header("Dashboard", anchor=False)

    ranking = calcular_ranking()
    total_env   = sum(r["enviados"]    for r in ranking)
    total_conv  = sum(r["convertidos"] for r in ranking)
    taxa_geral  = total_conv / total_env * 100 if total_env else 0.0
    valor_total = sum(r["valor_total"] for r in ranking)

    # ── métricas globais ──────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Enviados", f"{total_env:,}".replace(",", "."))
    with c2:
        st.metric("Total Convertidos", f"{total_conv:,}".replace(",", "."))
    with c3:
        st.metric("Taxa Geral", f"{taxa_geral:.1f}%")
    with c4:
        st.metric("Valor Total Convertido", fmt_brl(valor_total))

    st.divider()

    # ── ranking completo ──────────────────────────────────────────
    st.subheader("Ranking de Conversão", anchor=False)
    if not ranking:
        st.info("Nenhum dado disponível.")
    else:
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        rows = []
        for i, r in enumerate(ranking, 1):
            rows.append({
                "#": i,
                "": medals.get(i, ""),
                "Promotora": CORBAN_NAMES.get(r["corban"], r["corban"]),
                "Enviados": r["enviados"],
                "Convertidos": r["convertidos"],
                "Taxa (%)": f"{r['taxa'] * 100:.1f}%",
                "Valor Convertido": fmt_brl(r["valor_total"]) if r["valor_total"] else "—",
            })
        df_rank = pd.DataFrame(rows)
        df_rank.index = df_rank["#"]
        df_rank = df_rank.drop(columns=["#"])
        st.dataframe(df_rank, use_container_width=True, hide_index=False)

    st.divider()

    # ── histórico de acessos ──────────────────────────────────────
    st.subheader("Último Acesso por Promotora", anchor=False)
    access_log = _load_json(DATA_DIR / "access_log.json", {})

    corban_log = {
        u: info for u, info in access_log.items()
        if not load_users().get(u, {}).get("is_admin", False)
    }

    if not corban_log:
        st.info("Nenhum acesso de promotora registrado ainda.")
    else:
        log_rows = []
        for username, info in sorted(corban_log.items()):
            try:
                dt = datetime.fromisoformat(info["last_access"]) - timedelta(hours=3)
                dt_fmt = dt.strftime("%d/%m/%Y às %H:%M")
            except Exception:
                dt_fmt = info.get("last_access", "—")
            log_rows.append({
                "Promotora": info.get("display_name", username),
                "Último Acesso": dt_fmt,
            })
        df_log = pd.DataFrame(log_rows)
        st.dataframe(df_log, use_container_width=True, hide_index=True)

    st.divider()

    # ── status de 2FA por e-mail ──────────────────────────────────
    st.subheader("Autenticação em Dois Fatores (2FA)", anchor=False)
    st.markdown(
        f"<p style='font-size:0.85rem; color:{MUTED}; margin-bottom:1rem;'>"
        "O 2FA é feito por código enviado ao e-mail de cada usuário. "
        "Usuários sem e-mail cadastrado entram sem 2FA.</p>",
        unsafe_allow_html=True,
    )
    rows_2fa = []
    for uname, udata in sorted(load_users().items()):
        email = udata.get("email", "")
        rows_2fa.append({
            "Usuário": udata.get("display_name", uname),
            "E-mail": email if email else "—",
            "2FA": "✓ Ativo" if email else "✗ Sem e-mail",
        })
    st.dataframe(pd.DataFrame(rows_2fa), use_container_width=True, hide_index=True)


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    st.set_page_config(page_title=APP_NAME, layout="wide", initial_sidebar_state="expanded")
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown("""
        <div class="footer">
            ALL IN CRED SOCIEDADE DE CREDITO DIRETO S.A. &nbsp;·&nbsp;
            CNPJ: 51.414.521/0001-26 &nbsp;·&nbsp;
            Rua José Maria Lisboa, 757 – Conj. 107 – Jardim Paulista, São Paulo – SP, 01423-001
        </div>
    """, unsafe_allow_html=True)

    if not st.session_state.get("logged_in"):
        login_page()
        return

    is_admin = st.session_state.get("is_admin", False)

    with st.sidebar:
        st.markdown(f"""
            <div style="padding:0 0.5rem 0.75rem 0.5rem;">
                <span style="font-size:1.35rem; font-weight:700; color:{GOLD};
                             letter-spacing:0.5px;">
                    {APP_NAME}
                </span><br>
                <span style="font-size:0.78rem; color:{MUTED};">ZiliCred</span>
            </div>
        """, unsafe_allow_html=True)
        st.divider()

        st.markdown(
            f"<p style='font-size:0.85rem; color:{MUTED}; margin-bottom:0.75rem;'>"
            f"{st.session_state['display_name']}</p>",
            unsafe_allow_html=True,
        )

        if is_admin:
            corbans = get_all_corbans()
            corban  = st.selectbox(
                "Corban", corbans if corbans else ["—"],
                format_func=lambda c: CORBAN_NAMES.get(c, c),
                disabled=not corbans,
            )
            if not corbans:
                corban = None
            st.divider()
            menu = ["Dashboard", "Clientes", "Conversão", "Upload"]
        else:
            corban = st.session_state["corban"]
            clientes_label = "Clientes ●" if has_new_base(corban) else "Clientes"
            menu = [clientes_label, "Conversão", "Ranking", "Como Usar"]

        page = st.radio("Menu", menu, label_visibility="collapsed")
        st.divider()
        if st.button("Sair", width="stretch"):
            for key in ["logged_in", "username", "corban", "display_name", "is_admin", "dl_state"]:
                st.session_state.pop(key, None)
            st.rerun()

    components.html("""
        <script>
        (function() {
            function removeResizeHandles() {
                var doc = window.parent.document;
                doc.querySelectorAll('*').forEach(function(el) {
                    var cursor = window.parent.getComputedStyle(el).cursor;
                    if (cursor === 'col-resize' || cursor === 'ew-resize') {
                        el.style.pointerEvents = 'none';
                        el.style.display = 'none';
                    }
                });
            }
            setTimeout(removeResizeHandles, 300);
            setTimeout(removeResizeHandles, 1000);
        })();
        </script>
    """, height=0, scrolling=False)

    if st.session_state.pop("expand_sidebar", False):
        components.html("""
            <script>
            setTimeout(function() {
                try {
                    var btn = window.parent.document.querySelector(
                        '[data-testid="collapsedControl"] button, [data-testid="collapsedControl"]'
                    );
                    if (btn) btn.click();
                } catch(e) {}
            }, 200);
            </script>
        """, height=0, scrolling=False)

    if page in ("Clientes", "Clientes ●"):
        page_clientes(corban)
    elif page == "Conversão":
        page_conversao(corban)
    elif page == "Upload":
        page_upload()
    elif page == "Ranking":
        page_ranking(corban)
    elif page == "Dashboard":
        page_dashboard()
    else:
        page_como_usar()


if __name__ == "__main__":
    main()
