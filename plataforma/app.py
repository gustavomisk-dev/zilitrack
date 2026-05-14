import json
from datetime import datetime, timedelta
from pathlib import Path

import bcrypt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

HERE = Path(__file__).parent
ROOT = HERE.parent
PASTA_ENVIADOS    = ROOT / "corban" / "enviados"
PASTA_CONVERTIDOS = ROOT / "corban" / "convertidos"

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


def login_page():
    st.markdown(f"""
        <div style="text-align:center; margin-top:5rem; margin-bottom:2.5rem;">
            <h1 style="color:{GOLD}; font-size:2.8rem; font-weight:700;
                       letter-spacing:1px; margin-bottom:0.3rem;">
                {APP_NAME}
            </h1>
            <p style="color:{MUTED}; font-size:0.95rem; margin:0;">
                Plataforma de Gestão de Propostas · ZiliCred
            </p>
        </div>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1, 1])
    with col:
        with st.form("login_form"):
            username  = st.text_input("Usuário")
            password  = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Entrar", width="stretch")

    if submitted:
        attempt = _login_attempts.get(username, {"count": 0, "blocked_until": None})
        blocked_until = attempt["blocked_until"]

        if blocked_until and datetime.now() < blocked_until:
            remaining = int((blocked_until - datetime.now()).total_seconds() / 60)
            with col:
                st.error(f"Usuário bloqueado por tentativas inválidas. Tente novamente em {remaining} minuto(s).")
        else:
            users = load_users()
            user  = users.get(username)
            try:
                pw_ok = user is not None and bcrypt.checkpw(password.encode(), user["password"].encode())
            except Exception:
                pw_ok = False
            if pw_ok:
                _login_attempts.pop(username, None)
                st.session_state.update({
                    "logged_in":      True,
                    "corban":         user.get("corban"),
                    "display_name":   user["display_name"],
                    "is_admin":       user.get("is_admin", False),
                    "expand_sidebar": True,
                })
                st.rerun()
            else:
                attempt["count"] += 1
                if attempt["count"] >= 3:
                    attempt["blocked_until"] = datetime.now() + timedelta(hours=1)
                _login_attempts[username] = attempt
                with col:
                    if attempt["count"] >= 3:
                        st.error("Usuário bloqueado por 1 hora após tentativas inválidas.")
                    else:
                        st.error("Usuário ou senha incorretos.")


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


def files_by_date(pasta: Path, corban: str, suffix: str) -> dict:
    if not pasta.exists():
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


def calcular_ranking() -> list[dict]:
    """Retorna lista ordenada por taxa de conversão desc: [{corban, enviados, convertidos, taxa}]"""
    corbans = get_all_corbans()
    resultado = []
    for corban in corbans:
        enviados = sum(
            len(read_csv(f)) for f in PASTA_ENVIADOS.glob(f"*_{corban}_*_enviados.csv")
        )
        convertidos = 0
        if PASTA_CONVERTIDOS.exists():
            convertidos = sum(
                len(read_csv(f)) for f in PASTA_CONVERTIDOS.glob(f"*_{corban}_*_convertidos.csv")
            )
        taxa = convertidos / enviados if enviados else 0.0
        resultado.append({"corban": corban, "enviados": enviados, "convertidos": convertidos, "taxa": taxa})
    resultado.sort(key=lambda x: x["taxa"], reverse=True)
    return resultado


# ── páginas ───────────────────────────────────────────────────────────────────

def page_clientes(corban: str):
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
        sorted(available.keys(), reverse=True),
    )

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
    df_display = df.copy()
    df_display.index = range(1, len(df_display) + 1)
    st.dataframe(df_display, width="stretch", hide_index=False)

    st.download_button(
        "Baixar CSV",
        df.to_csv(index=False, sep=";").encode("utf-8-sig"),
        file_name=f"clientes_{selected}.csv",
        mime="text/csv",
    )


def page_conversao(corban: str):
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
        sorted(available_conv.keys(), reverse=True),
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

    df_conv_display = df_conv.copy()
    df_conv_display.index = range(1, len(df_conv_display) + 1)
    st.dataframe(df_conv_display, width="stretch", hide_index=False)

    st.download_button(
        "Baixar CSV",
        df_conv.to_csv(index=False, sep=";").encode("utf-8-sig"),
        file_name=f"conversao_{selected}.csv",
        mime="text/csv",
    )


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
            for f in uploaded_env:
                (PASTA_ENVIADOS / f.name).write_bytes(f.read())
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
            <div style="font-size:0.95rem; color:{MUTED}; margin-top:0.4rem;">
                entre {total} promotora{"s" if total > 1 else ""} participante{"s" if total > 1 else ""}
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

        <h4 style="color:{GOLD}; margin-top:1.5rem;">Clientes</h4>
        <p>
            Exibe a base de clientes que foi enviada para a sua promotora pela ZiliCred.
            Use o seletor <b>Data de envio da base</b> para escolher o lote desejado.
            A tabela mostra a data e hora do processamento, o CPF e o nome de cada cliente.
            Clique em <b>Baixar CSV</b> para exportar a lista.
        </p>

        <h4 style="color:{GOLD}; margin-top:1.5rem;">Conversão</h4>
        <p>
            Exibe os clientes da sua base que efetivaram um contrato.
            Selecione o lote pela data de envio para visualizar CPF, nome,
            data de processamento e valor do contrato.
            Clique em <b>Baixar CSV</b> para exportar o relatório.
        </p>

        <h4 style="color:{GOLD}; margin-top:1.5rem;">Atualização dos dados</h4>
        <p>
            Os dados são atualizados periodicamente pela equipe da ZiliCred.
            Caso a aba de Clientes ou Conversão apareça sem informações,
            aguarde a próxima atualização ou entre em contato com a equipe.
        </p>

        <h4 style="color:{GOLD}; margin-top:1.5rem;">Dúvidas</h4>
        <p>
            Entre em contato com a ZiliCred pelo e-mail ou pelo seu gerente de relacionamento.
        </p>

        </div>
    """, unsafe_allow_html=True)


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
        else:
            corban = st.session_state["corban"]

        menu = ["Clientes", "Conversão"] + (["Upload"] if is_admin else ["Ranking", "Como Usar"])
        page = st.radio("Menu", menu, label_visibility="collapsed")
        st.divider()
        if st.button("Sair", width="stretch"):
            for key in ["logged_in", "corban", "display_name", "is_admin"]:
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

    if page == "Clientes":
        page_clientes(corban)
    elif page == "Conversão":
        page_conversao(corban)
    elif page == "Upload":
        page_upload()
    elif page == "Ranking":
        page_ranking(corban)
    else:
        page_como_usar()


if __name__ == "__main__":
    main()
