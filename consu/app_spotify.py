import os
import sys
import html
import math
from datetime import datetime, timedelta
from decimal import Decimal

import altair as alt
import mysql.connector
import pandas as pd
import streamlit as st

# El motor de recomendaciones vive en la carpeta de arriba (recomendador.py)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import recomendador  # noqa: E402
import aprendizaje  # noqa: E402  (motor en vivo de la app de usuario)


# Conexión a MySQL/MariaDB (XAMPP). Se puede cambiar con las mismas variables de entorno
# que usa "base de datos.py": MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD y SPOTIFY_DB.
DB_NAME = os.environ.get("SPOTIFY_DB", "spotify_uadeo_db")
MYSQL_CONFIG = {
    'host': os.environ.get("MYSQL_HOST", "localhost"),
    'user': os.environ.get("MYSQL_USER", "root"),
    'password': os.environ.get("MYSQL_PASSWORD", ""),
}
FORMATO_FECHA = "%Y-%m-%d %H:%M:%S"


def conectar_db():
    return mysql.connector.connect(**MYSQL_CONFIG, database=DB_NAME)


st.set_page_config(page_title="Admin · Spotify Analytics", page_icon="🛡️", layout="wide",
                   initial_sidebar_state="expanded")

# =====================================================================
# ESTILO (tema oscuro tipo Spotify)
# =====================================================================
VERDE = "#1DB954"
st.markdown(f"""
<style>
  .stApp {{ background: linear-gradient(180deg, #1e3a2a 0%, #121212 340px); color: #fff; }}
  [data-testid="stSidebar"] {{ background: #000; }}
  [data-testid="stSidebar"] * {{ color: #b3b3b3; }}
  [data-testid="stHeader"] {{ background: transparent; }}
  h1, h2, h3, h4 {{ color: #fff !important; letter-spacing: -0.5px; }}
  p, label, .stMarkdown {{ color: #e5e5e5; }}
  .block-container {{ padding-top: 2rem; }}

  .hero {{ display:flex; align-items:center; gap:22px; margin-bottom: 18px; }}
  .hero .logo {{ width:72px; height:72px; border-radius:50%; background:{VERDE}; display:flex;
                 align-items:center; justify-content:center; font-size:38px; box-shadow:0 8px 24px rgba(0,0,0,.5); }}
  .hero h1 {{ font-size: 2.6rem; font-weight: 900; margin: 0; }}
  .hero .sub {{ color:#b3b3b3; font-size: .95rem; }}

  .kpi {{ background:#181818; border-radius:12px; padding:16px 18px; border:1px solid #282828;
          transition: background .2s; height: 100%; min-width: 0; }}
  .kpi:hover {{ background:#232323; }}
  .kpi .top {{ display:flex; justify-content:space-between; align-items:center; gap:6px; }}
  .kpi .lbl {{ color:#b3b3b3; font-size:.72rem; text-transform:uppercase; letter-spacing:.5px;
               white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .kpi .val {{ color:#fff; font-size:clamp(1.2rem, 2.2vw, 1.9rem); font-weight:800; margin-top:4px; white-space:nowrap; }}
  .kpi .ico {{ font-size:1.3rem; opacity:.85; flex-shrink:0; }}
  .kpi .delta {{ color:{VERDE}; font-size:.75rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}

  .perfil {{ display:flex; gap:24px; align-items:flex-end; background:linear-gradient(90deg,#2a5d3f,#181818);
             border-radius:14px; padding:24px; margin-bottom:16px; }}
  .avatar {{ width:110px; height:110px; border-radius:50%; background:#535353; display:flex; align-items:center;
             justify-content:center; font-size:44px; font-weight:800; color:#fff; box-shadow:0 8px 24px rgba(0,0,0,.6); }}
  .perfil .tipo {{ font-size:.75rem; text-transform:uppercase; letter-spacing:1px; color:#fff; }}
  .perfil .nombre {{ font-size:2.4rem; font-weight:900; color:#fff; line-height:1.1; }}
  .perfil .meta {{ color:#d0d0d0; font-size:.9rem; margin-top:6px; }}

  .chip {{ display:inline-block; padding:4px 12px; border-radius:999px; background:#2a2a2a; color:#fff;
           font-size:.8rem; margin:2px 4px 2px 0; border:1px solid #3a3a3a; }}
  .chip.verde {{ background:{VERDE}; color:#000; border-color:{VERDE}; font-weight:700; }}

  .card {{ background:#181818; border-radius:10px; padding:14px; border:1px solid #232323; height:100%;
           transition: background .2s, transform .2s; }}
  .card:hover {{ background:#282828; transform: translateY(-2px); }}
  .cover {{ aspect-ratio:1/1; border-radius:8px; display:flex; align-items:center; justify-content:center;
            font-size:2.6rem; margin-bottom:10px; box-shadow:0 6px 16px rgba(0,0,0,.5); }}
  .card .t {{ color:#fff; font-weight:700; font-size:.95rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .card .a {{ color:#b3b3b3; font-size:.8rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .card .s {{ color:{VERDE}; font-size:.75rem; font-weight:700; margin-top:6px; }}


  .stButton > button, .stFormSubmitButton > button {{ border-radius:999px; font-weight:700; border:1px solid #535353;
                                                      background:transparent; color:#fff; }}
  .stButton > button:hover, .stFormSubmitButton > button:hover {{ border-color:#fff; color:#fff; transform:scale(1.03); }}
  .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{ background:{VERDE}; color:#000;
                                                      border:none; }}
  .stButton > button[kind="primary"]:hover {{ background:#1ed760; color:#000; }}
  [data-testid="stDataFrame"] {{ border-radius:10px; overflow:hidden; }}
  .stTabs [data-baseweb="tab"] {{ color:#b3b3b3; }}
  .stTabs [aria-selected="true"] {{ color:#fff !important; }}
  div[role="dialog"] {{ background:#181818 !important; }}
</style>
""", unsafe_allow_html=True)

GRADIENTES = ["linear-gradient(135deg,#1DB954,#0d5c2b)", "linear-gradient(135deg,#e91e63,#6a1b9a)",
              "linear-gradient(135deg,#ff9800,#c62828)", "linear-gradient(135deg,#2196f3,#1a237e)",
              "linear-gradient(135deg,#9c27b0,#311b92)", "linear-gradient(135deg,#00bcd4,#004d40)",
              "linear-gradient(135deg,#ffc107,#e65100)", "linear-gradient(135deg,#607d8b,#212121)"]
ICONO_GENERO = {"Corridos tumbados": "🤠", "Regional mexicano": "🎺", "Reggaetón": "🔥", "Trap latino": "💎",
                "Salsa": "💃", "Pop latino": "🌴", "Pop": "🎤", "Pop alternativo": "🌙", "Hip hop": "🎧",
                "Soul": "🎷", "Electrónica": "🎛️"}


def esc(x):
    return html.escape(str(x)) if x is not None else ""


# =====================================================================
# ACCESO A DATOS
# =====================================================================
@st.cache_data(ttl=60, show_spinner=False)
def consulta(sql, params=None):
    cx = conectar_db()
    cur = cx.cursor(dictionary=True)
    cur.execute(sql, params or ())
    filas = cur.fetchall()
    columnas = list(cur.column_names)
    cur.close(); cx.close()
    # Se pasan las columnas para que una consulta sin filas conserve su estructura
    # (si no, df.columna truena con AttributeError cuando la tabla está vacía)
    df = pd.DataFrame(filas, columns=columnas)
    # MySQL devuelve DECIMAL como objetos Decimal: se convierten a float para tablas y gráficas
    for col in df.columns:
        if df[col].map(lambda x: isinstance(x, Decimal)).any():
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def ejecutar(sql, params=None):
    cx = conectar_db()
    cur = cx.cursor()
    cur.execute(sql, params or ())
    cx.commit()
    cur.close(); cx.close()
    st.cache_data.clear()


def avisar(mensaje, icono="✅"):
    """Guarda un aviso para mostrarlo como pop-up (toast) después del st.rerun()."""
    st.session_state["_toast"] = (mensaje, icono)


if "_toast" in st.session_state:
    msg, ico = st.session_state.pop("_toast")
    st.toast(msg, icon=ico)


def fecha_valida(texto):
    """True si el texto tiene el formato AAAA-MM-DD HH:MM:SS."""
    try:
        datetime.strptime(str(texto).strip(), FORMATO_FECHA)
        return True
    except ValueError:
        return False


def actualizar_tipo_cuenta(cur, user_ids):
    """Deja account_type en 'premium' solo si el usuario tiene una suscripción no cancelada."""
    for uid in user_ids:
        cur.execute("""UPDATE users SET account_type = IF(EXISTS(
                           SELECT 1 FROM premium_subscribed WHERE user_id = %s AND status <> 'cancelada'),
                           'premium', 'free') WHERE user_id = %s""", (uid, uid))


def obtener_ids(tabla, campo_id):
    try:
        df = consulta(f"SELECT {campo_id} FROM {tabla};")
        return df[campo_id].tolist() if not df.empty else []
    except Exception:
        return []


def kpi(col, etiqueta, valor, icono, delta=""):
    col.markdown(f"""<div class="kpi" title="{esc(etiqueta)}"><div class="top"><div class="lbl">{etiqueta}</div>
                 <span class="ico">{icono}</span></div>
                 <div class="val">{valor}</div><div class="delta">{delta}</div></div>""", unsafe_allow_html=True)


def barras(df, x, y, height=260):
    """Gráfica de barras; si no hay datos muestra un aviso en lugar de una gráfica vacía."""
    if df.empty:
        st.caption("Sin datos todavía.")
    else:
        st.bar_chart(df, x=x, y=y, color=VERDE, height=height)


def guia(texto):
    """Recuadro plegable que explica cómo leer la página (pensado para quien revisa el proyecto)."""
    with st.expander("ℹ️ ¿Cómo leer esta página?"):
        st.markdown(texto)


def portada(song_id, genero):
    return (f'<div class="cover" style="background:{GRADIENTES[int(song_id) % len(GRADIENTES)]}">'
            f'{ICONO_GENERO.get(genero, "🎵")}</div>')


# Verificar conexión antes de dibujar nada
try:
    conectar_db().close()
except Exception as e:
    st.error(f"No se pudo conectar a MySQL (base `{DB_NAME}`). Inicia MySQL desde el panel de XAMPP "
             f"y, si la base no existe, ejecuta primero `python \"base de datos.py\"`.\n\n{e}")
    st.stop()


# =====================================================================
# ACCESO DE ADMINISTRADOR
# Esta app es el lado del ADMINISTRADOR (análisis, telemetría y gestión de la base).
# Los usuarios usan app_usuario.py. Contraseña: variable ADMIN_PASSWORD (por defecto "admin").
# =====================================================================
ADMIN_USUARIO = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")

if not st.session_state.get("admin_ok"):
    st.markdown(f"""<div style="text-align:center;margin:40px 0 18px">
        <div style="width:72px;height:72px;border-radius:50%;background:{VERDE};display:inline-flex;align-items:center;
        justify-content:center;font-size:38px">🛡️</div>
        <h1 style="margin:10px 0 0">Panel de administrador</h1>
        <div style="color:#b3b3b3">Spotify Analytics · E-Marketing UAdeO</div></div>""", unsafe_allow_html=True)
    _, centro, _ = st.columns([1, 1.2, 1])
    with centro:
        with st.form("login_admin"):
            usuario_admin = st.text_input("Usuario")
            clave_admin = st.text_input("Contraseña", type="password")
            entrar_admin = st.form_submit_button("Entrar", type="primary", width="stretch")
        if entrar_admin:
            if usuario_admin.strip() == ADMIN_USUARIO and clave_admin == ADMIN_PASSWORD:
                st.session_state.admin_ok = True
                st.rerun()
            st.error("Usuario o contraseña incorrectos.")
        st.caption("¿Eres usuario? Abre la app «Mi Spotify» en http://localhost:8502")
    st.stop()


# =====================================================================
# BARRA LATERAL
# =====================================================================
with st.sidebar:
    st.markdown(f"""<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
        <div style="width:40px;height:40px;border-radius:50%;background:{VERDE};display:flex;align-items:center;
        justify-content:center;font-size:22px">🛡️</div>
        <div><div style="color:#fff;font-weight:900;font-size:1.2rem">Panel de administrador</div>
        <div style="font-size:.75rem">Spotify Analytics · E-Marketing UAdeO</div></div></div>""", unsafe_allow_html=True)
    pagina = st.radio("Menú", ["🏠 Inicio", "📺 En vivo", "📈 Marketing", "🧠 Recomendaciones", "📡 Telemetría",
                               "🗄️ Base de datos"], label_visibility="collapsed")
    try:
        _ult = consulta("SELECT MAX(played_at) AS ultima FROM song_played")
        _ult = _ult.ultima.iloc[0] if not _ult.empty else None
        _txt = pd.Timestamp(_ult).strftime("%d/%m/%Y %H:%M") if _ult is not None and pd.notna(_ult) else "sin datos"
    except Exception:
        _txt = "sin datos"
    st.caption(f"🗄️ Base `{DB_NAME}`  \n📅 Datos hasta: **{_txt}**")
    if st.button("🔒 Cerrar sesión de administrador", width="stretch"):
        st.session_state.admin_ok = False
        st.rerun()
    st.markdown("---")


# =====================================================================
# RECOMENDACIONES Y POP-UP DE CONFIRMACIÓN
# =====================================================================
def tabla_recs(user_id):
    """Recomendaciones actuales del usuario. «status» es el RESULTADO real: lo que el usuario hizo con
    cada recomendación después de recibirla (en la app «Mi Spotify» o en los datos simulados)."""
    return consulta("""
        SELECT ur.recommendation_id, ur.rank_position, ur.song_id, s.title, s.artist, s.genre, s.album,
               s.popularity, ur.score, ur.genre_affinity, ur.artist_affinity, ur.audio_similarity,
               ur.reason, ur.algorithm, ur.generated_at, b.title AS based_on,
               CASE
                 WHEN EXISTS (SELECT 1 FROM recommendation_events e WHERE e.user_id = ur.user_id
                               AND e.song_id = ur.song_id AND e.dismissed = 1 AND e.shown_at >= ur.generated_at)
                      THEN 'descartada'
                 WHEN EXISTS (SELECT 1 FROM song_liked l WHERE l.user_id = ur.user_id AND l.song_id = ur.song_id
                               AND l.liked_at >= ur.generated_at) THEN 'guardada'
                 WHEN EXISTS (SELECT 1 FROM song_played p WHERE p.user_id = ur.user_id AND p.song_id = ur.song_id
                               AND p.played_at >= ur.generated_at AND p.skipped = 0) THEN 'escuchada'
                 WHEN EXISTS (SELECT 1 FROM song_played p WHERE p.user_id = ur.user_id AND p.song_id = ur.song_id
                               AND p.played_at >= ur.generated_at AND p.skipped = 1) THEN 'saltada'
                 ELSE ur.status
               END AS status
          FROM user_recommendations ur
          JOIN songs s ON s.song_id = ur.song_id
          LEFT JOIN songs b ON b.song_id = ur.based_on_song_id
         WHERE ur.user_id = %s
         ORDER BY ur.rank_position
    """, (int(user_id),))


@st.dialog("⚠️ Confirmar eliminación")
def popup_confirmar_borrado(tabla, campo_pk, ids):
    st.markdown(f"Vas a eliminar **{len(ids)} registro(s)** de `{tabla}` de forma permanente:")
    st.code(", ".join(str(i) for i in ids))
    if tabla == "users":
        st.warning("También se borrarán sus reproducciones, playlists, likes, suscripciones, "
                   "telemetría y recomendaciones.")
    elif tabla == "songs":
        st.warning("También se borrarán sus reproducciones, likes, recomendaciones y eventos de telemetría "
                   "de esa canción.")
    c1, c2 = st.columns(2)
    if c1.button("Cancelar", width="stretch"):
        st.rerun()
    if c2.button("Sí, eliminar", type="primary", width="stretch"):
        cx = None
        try:
            cx = conectar_db(); cur = cx.cursor()
            marcadores = ", ".join(["%s"] * len(ids))
            # Tablas cuya llave foránea no tiene ON DELETE CASCADE: se borran primero
            dependientes = {
                "users": ("user_id", ["song_played", "playlist_created", "song_liked", "premium_subscribed"]),
                "songs": ("song_id", ["song_played", "song_liked"]),
            }
            if tabla in dependientes:
                campo_fk, deps = dependientes[tabla]
                for dep in deps:
                    cur.execute(f"DELETE FROM {dep} WHERE {campo_fk} IN ({marcadores});", tuple(ids))
            afectados = []
            if tabla == "premium_subscribed":
                cur.execute(f"SELECT DISTINCT user_id FROM premium_subscribed WHERE subscription_id IN ({marcadores})",
                            tuple(ids))
                afectados = [r[0] for r in cur.fetchall() if r[0] is not None]
            cur.execute(f"DELETE FROM {tabla} WHERE {campo_pk} IN ({marcadores});", tuple(ids))
            # Si se borró una suscripción, el usuario vuelve a 'free' cuando ya no le queda ninguna activa
            actualizar_tipo_cuenta(cur, afectados)
            cx.commit(); cur.close(); cx.close()
            st.cache_data.clear()
            avisar(f"Se eliminaron {len(ids)} registros de {tabla}", "🗑️")
            st.rerun()
        except mysql.connector.Error as e:
            if cx:
                cx.rollback(); cx.close()
            st.error(f"Error al eliminar: {e}")


# =====================================================================
# PÁGINA: INICIO
# =====================================================================
def pagina_inicio():
    st.markdown(f"""<div class="hero"><div class="logo">🎧</div><div><div class="sub">PANEL GENERAL</div>
        <h1>Panel de administrador</h1><div class="sub">Usuarios, reproducciones, recomendaciones y telemetría
        · base <code>{esc(DB_NAME)}</code></div></div></div>""", unsafe_allow_html=True)
    guia("""
- **Usuarios activos**: escucharon algo en los 7 días previos a la última reproducción registrada.
- **Reproducciones**: la flecha compara los **últimos 7 días contra los 7 anteriores** (tendencia semanal).
- **Premium**: porcentaje de usuarios con una suscripción no cancelada.
- **CTR de recomendaciones**: de cada 100 recomendaciones mostradas en la app, cuántas recibieron clic.
- Para ver la hipótesis de retención, el embudo y los ingresos, abre **📈 Marketing**.""")

    r = consulta("""
        SELECT (SELECT COUNT(*) FROM users) AS usuarios,
               (SELECT COUNT(*) FROM users WHERE account_type='premium') AS premium,
               (SELECT COUNT(*) FROM song_played) AS plays,
               (SELECT ROUND(SUM(ms_played)/3600000, 0) FROM song_played) AS horas,
               (SELECT ROUND(100*AVG(clicked), 1) FROM recommendation_events) AS ctr,
               (SELECT COUNT(DISTINCT user_id) FROM song_played
                 WHERE played_at >= (SELECT MAX(played_at) FROM song_played) - INTERVAL 7 DAY) AS activos,
               (SELECT COUNT(*) FROM song_played
                 WHERE played_at > (SELECT MAX(played_at) FROM song_played) - INTERVAL 7 DAY) AS plays_7d,
               (SELECT COUNT(*) FROM song_played
                 WHERE played_at >  (SELECT MAX(played_at) FROM song_played) - INTERVAL 14 DAY
                   AND played_at <= (SELECT MAX(played_at) FROM song_played) - INTERVAL 7 DAY) AS plays_prev_7d
    """).iloc[0]
    p7, p_prev = int(r.plays_7d or 0), int(r.plays_prev_7d or 0)
    if p_prev:
        cambio = 100 * (p7 - p_prev) / p_prev
        tendencia = f"{'▲' if cambio >= 0 else '▼'} {abs(cambio):.0f}% vs semana anterior"
    else:
        tendencia = f"{p7:,} en los últimos 7 días"
    c = st.columns(5)
    kpi(c[0], "Usuarios", f"{int(r.usuarios):,}", "👥", f"{int(r.activos or 0)} activos últimos 7 días")
    kpi(c[1], "Reproducciones", f"{int(r.plays):,}", "▶️", tendencia)
    kpi(c[2], "Horas escuchadas", f"{int(r.horas or 0):,}", "⏱️", "suma de ms_played")
    kpi(c[3], "Premium", f"{100*int(r.premium)/max(int(r.usuarios),1):.0f}%", "💎", f"{int(r.premium)} suscriptores")
    kpi(c[4], "CTR recomendaciones", f"{float(r.ctr or 0):.1f}%", "✨", "clics / impresiones")

    st.write("")
    c1, c2 = st.columns([3, 2])
    with c1:
        st.subheader("Reproducciones por día")
        df = consulta("""SELECT DATE(played_at) AS dia, COUNT(*) AS reproducciones FROM song_played
                         GROUP BY DATE(played_at) ORDER BY dia""")
        if not df.empty:
            st.area_chart(df, x="dia", y="reproducciones", color=VERDE, height=300)
    with c2:
        st.subheader("Géneros más escuchados")
        df = consulta("""SELECT IFNULL(NULLIF(s.genre, ''), 'Sin género') AS genero,
                                ROUND(SUM(sp.ms_played)/3600000, 1) AS horas
                         FROM song_played sp JOIN songs s ON s.song_id = sp.song_id
                         GROUP BY genero ORDER BY horas DESC""")
        if not df.empty:
            st.bar_chart(df, x="genero", y="horas", color=VERDE, horizontal=True, height=300)

    st.subheader("🔥 Top 10 canciones")
    top = consulta("""SELECT s.song_id, s.title AS cancion, s.artist AS artista, s.genre AS genero,
                             COUNT(*) AS reproducciones, ROUND(100*AVG(sp.skipped), 1) AS skip_pct, s.popularity
                        FROM song_played sp JOIN songs s ON s.song_id = sp.song_id
                       GROUP BY s.song_id ORDER BY reproducciones DESC LIMIT 10""")
    if not top.empty:
        cols = st.columns(5)
        for i, (_, s) in enumerate(top.head(5).iterrows()):
            cols[i].markdown(f"""<div class="card">{portada(s.song_id, s.genero)}<div class="t">#{i+1} {esc(s.cancion)}</div>
                <div class="a">{esc(s.artista)}</div><div class="s">{int(s.reproducciones):,} plays</div></div>""",
                             unsafe_allow_html=True)
        st.write("")
        st.dataframe(top.drop(columns=["song_id"]), hide_index=True, width="stretch", column_config={
            "reproducciones": st.column_config.ProgressColumn("Reproducciones", format="%d", min_value=0,
                                                              max_value=int(top.reproducciones.max())),
            "skip_pct": st.column_config.NumberColumn("Skip %", format="%.1f%%"),
            "popularity": st.column_config.ProgressColumn("Popularidad", format="%d", min_value=0, max_value=100),
        })


# =====================================================================
# PÁGINA: RECOMENDACIONES (inspector del administrador)
# =====================================================================
def pagina_recomendaciones():
    """Inspector del ADMINISTRADOR: qué se le recomienda a cada usuario, por qué y cómo le funcionó."""
    usuarios = consulta("SELECT user_id, username, account_type, city, signup_source FROM users ORDER BY user_id")
    if usuarios.empty:
        st.info("No hay usuarios registrados.")
        return
    opciones = {int(r.user_id): f"{r.username}  ·  #{r.user_id}" + ("  · app" if r.signup_source == "app_en_vivo" else "")
                for r in usuarios.itertuples()}
    with st.sidebar:
        st.markdown("**👤 Usuario**")
        uid = st.selectbox("Usuario", list(opciones), format_func=opciones.get, label_visibility="collapsed")
    u = usuarios[usuarios.user_id == uid].iloc[0]

    perfil = consulta("""
        SELECT COUNT(*) AS plays, ROUND(SUM(ms_played)/3600000, 1) AS horas,
               COUNT(DISTINCT song_id) AS canciones, ROUND(100*AVG(skipped), 0) AS skip,
               MAX(played_at) AS ultima
          FROM song_played WHERE user_id = %s""", (uid,)).iloc[0]
    generos = consulta("""SELECT IFNULL(NULLIF(s.genre, ''), 'Sin género') AS genre, SUM(sp.ms_played) AS ms
                          FROM song_played sp JOIN songs s USING(song_id)
                          WHERE sp.user_id = %s GROUP BY 1 ORDER BY ms DESC""", (uid,))
    artistas = consulta("""SELECT s.artist, COUNT(*) AS n FROM song_played sp JOIN songs s USING(song_id)
                           WHERE sp.user_id = %s GROUP BY s.artist ORDER BY n DESC LIMIT 5""", (uid,))

    iniciales = "".join(p[0] for p in str(u.username).split()[:2]).upper()
    plan = "PREMIUM 💎" if u.account_type == "premium" else "FREE"
    chips = "".join(f'<span class="chip">{esc(g)}</span>' for g in generos.genre.head(4)) if not generos.empty else ""
    ultima = pd.Timestamp(perfil.ultima).strftime("%d/%m/%Y %H:%M") if pd.notna(perfil.ultima) else "nunca"
    st.markdown(f"""<div class="perfil"><div class="avatar">{esc(iniciales)}</div><div>
        <div class="tipo">Usuario #{int(uid)} · <span class="chip verde">{plan}</span>
        <span class="chip">{esc(u.signup_source or '')}</span></div>
        <div class="nombre">{esc(u.username)}</div>
        <div class="meta">📍 {esc(u.city or 'México')} · {int(perfil.plays or 0):,} reproducciones ·
        {float(perfil.horas or 0):.1f} h · {int(perfil.canciones or 0)} canciones distintas ·
        {int(perfil.skip or 0)}% saltadas · última escucha: {ultima}</div>
        <div style="margin-top:8px">{chips}</div></div></div>""", unsafe_allow_html=True)
    guia("""
- Elige un **usuario** en la barra lateral. Aquí ves **qué le recomienda el sistema, por qué y qué hizo con eso**;
  el usuario las ve en la app «Mi Spotify».
- **Motores**: `recomendador.py` (por historial, el que usa el generador) y `aprendizaje.py` (en vivo: también usa
  saltos, likes, descartes, búsquedas y artistas seguidos). La app de usuario usa el motor en vivo.
- `score = 0.45·género + 0.25·artista + 0.20·sonido + 0.10·popularidad`.
- **Resultado** se calcula con lo que hizo el usuario **después** de recibir la recomendación:
  `descartada` (✕), `guardada` (me gusta), `escuchada` (la escuchó sin saltarla), `saltada` o `nueva`.
- **🔄 Regenerar** recalcula con el motor elegido y reemplaza las 10 recomendaciones del usuario.""")

    # Rendimiento de las recomendaciones que se le mostraron a este usuario
    r = consulta("""SELECT COUNT(*) AS imp, IFNULL(SUM(clicked),0) AS clic, IFNULL(SUM(played),0) AS rep,
                           IFNULL(SUM(saved),0) AS guard, IFNULL(SUM(dismissed),0) AS desc_,
                           IFNULL(SUM(skipped),0) AS salt
                      FROM recommendation_events WHERE user_id = %s""", (uid,)).iloc[0]
    c = st.columns(5)
    kpi(c[0], "Impresiones", f"{int(r.imp):,}", "👀", "veces que se le mostraron")
    kpi(c[1], "CTR", f"{pct(r.clic, r.imp):.1f}%", "🖱️", f"{int(r.clic):,} clics")
    kpi(c[2], "Reproducidas", f"{int(r.rep):,}", "▶️", f"{pct(r.salt, r.rep):.0f}% saltadas")
    kpi(c[3], "Guardadas", f"{int(r.guard):,}", "💚", f"{pct(r.guard, r.rep):.0f}% de las reproducidas")
    kpi(c[4], "Descartadas", f"{int(r.desc_):,}", "🚫", "«no me interesa»")
    st.write("")

    df = tabla_recs(uid)
    algoritmo_actual = df.algorithm.iloc[0] if not df.empty else ""
    motores = {"📜 Historial · recomendador.py": "historial", "🧠 En vivo · aprendizaje.py": "vivo"}
    a1, a2, a3 = st.columns([2.6, 2.2, 1.4], vertical_alignment="bottom")
    motor = a1.segmented_control("Motor", list(motores), label_visibility="collapsed", key="motor_recs",
                                 default=list(motores)[1 if algoritmo_actual == aprendizaje.ALGORITMO else 0])
    if a2.button("🔄 Regenerar recomendaciones", type="primary", width="stretch"):
        cx = conectar_db()
        try:
            if motores.get(motor or "", "historial") == "vivo":
                n = len(aprendizaje.guardar(cx, int(uid), top_n=10)['recs'])
            else:
                n = recomendador.guardar_recomendaciones(cx, user_ids=[uid], top_n=10)
        finally:
            cx.close()
        st.cache_data.clear()
        avisar(f"Se generaron {n} recomendaciones con el motor «{motor}»", "✨")
        st.rerun()
    filtro = a3.selectbox("Resultado", ["Todas", "nueva", "escuchada", "saltada", "guardada", "descartada"],
                          label_visibility="collapsed")

    if df.empty:
        st.info("Este usuario aún no tiene recomendaciones. Pulsa **Regenerar recomendaciones**.")
    else:
        vista = df if filtro == "Todas" else df[df.status == filtro]
        st.subheader("📋 Recomendaciones actuales")
        st.caption(f"Motor: `{algoritmo_actual}` · generadas: {df.generated_at.iloc[0]}")
        if vista.empty:
            st.info(f"No hay recomendaciones con resultado «{filtro}» para este usuario.")
        else:
            st.dataframe(
                vista[["rank_position", "title", "artist", "genre", "score", "genre_affinity", "artist_affinity",
                       "audio_similarity", "reason", "based_on", "status"]],
                hide_index=True, width="stretch",
                column_config={
                    "rank_position": st.column_config.NumberColumn("#", width="small"),
                    "title": "Canción", "artist": "Artista", "genre": "Género",
                    "score": st.column_config.ProgressColumn("Score", format="%.2f", min_value=0, max_value=1),
                    "genre_affinity": st.column_config.ProgressColumn("Género", format="%.2f", min_value=0, max_value=1),
                    "artist_affinity": st.column_config.ProgressColumn("Artista", format="%.2f", min_value=0, max_value=1),
                    "audio_similarity": st.column_config.ProgressColumn("Sonido", format="%.2f", min_value=0, max_value=1),
                    "reason": st.column_config.TextColumn("Razón que ve el usuario", width="large"),
                    "based_on": "Basada en", "status": "Resultado",
                })

    st.subheader("🧠 Qué aprendió el modelo en vivo")
    cx = conectar_db()
    try:
        res = aprendizaje.aprender(cx, int(uid), top_n=10)
    finally:
        cx.close()
    st.caption(" · ".join(f"{k.replace('_', ' ')}: **{v}**" for k, v in res['senales'].items())
               or "Sin señales: arranque en frío (recomendaciones por popularidad).")
    p1, p2 = st.columns(2)
    for col, datos, titulo in [(p1, res['generos'], "Afinidad por género"), (p2, res['artistas'], "Afinidad por artista")]:
        with col:
            st.markdown(f"**{titulo}** (−1 no le gusta · 1 le gusta)")
            if datos:
                d = pd.DataFrame(list(datos.items())[:10], columns=['nombre', 'afinidad'])
                st.altair_chart(_alt_config(alt.Chart(d).mark_bar(cornerRadius=4).encode(
                    x=alt.X('afinidad:Q', scale=alt.Scale(domain=[-1, 1]), title=None),
                    y=alt.Y('nombre:N', sort='-x', title=None),
                    color=alt.condition(alt.datum.afinidad >= 0, alt.value(VERDE), alt.value("#e05555")),
                    tooltip=['nombre', alt.Tooltip('afinidad:Q', format='.2f')]).properties(height=260)),
                    width="stretch")
            else:
                st.caption("Sin datos.")

    st.subheader("🎚️ Perfil de escucha")
    p1, p2 = st.columns(2)
    with p1:
        st.markdown("**Géneros (horas)**")
        if not generos.empty:
            g = generos.assign(horas=(generos.ms.astype(float) / 3600000).round(2))[["genre", "horas"]]
            st.bar_chart(g, x="genre", y="horas", color=VERDE, horizontal=True, height=260)
        else:
            st.caption("Sin reproducciones todavía: se recomiendan las canciones más populares.")
    with p2:
        st.markdown("**Artistas más escuchados**")
        if not artistas.empty:
            st.dataframe(artistas, hide_index=True, width="stretch", column_config={
                "artist": "Artista",
                "n": st.column_config.ProgressColumn("Reproducciones", format="%d", min_value=0,
                                                     max_value=int(artistas.n.max()))})


# =====================================================================
# PÁGINA: TELEMETRÍA
# =====================================================================
def pagina_telemetria():
    st.markdown("""<div class="hero"><div class="logo">📡</div><div><div class="sub">EVENTOS DE LA APP</div>
        <h1>Telemetría</h1><div class="sub">Todo lo que la app registra: recomendaciones, reproducción, sesiones,
        búsquedas, anuncios, suscripción y rendimiento</div></div></div>""", unsafe_allow_html=True)
    guia("""
La **telemetría** son los eventos que la app registra automáticamente mientras se usa. Cada pestaña es una tabla:
- **CTR** = clics ÷ impresiones · **Guardado %** = guardadas ÷ reproducidas · **Skip %** = saltadas antes de 30 s.
- **Reproducción**: de dónde se reprodujo (playlist, búsqueda, recomendación…) y por qué terminó.
- **Suscripción**: el embudo de eventos (paywall → prueba → compra → renovación/cancelación).
- **Anuncios**: solo los ven los usuarios *free*; es la otra fuente de ingresos además de Premium.
- **Línea de tiempo**: todo lo que hizo un usuario, en orden, combinando todas las tablas.""")

    tabs = st.tabs(["✨ Recomendaciones", "▶️ Reproducción", "📱 Sesiones", "🔎 Búsquedas", "💳 Suscripción",
                    "📢 Anuncios", "⚙️ Rendimiento", "🕒 Línea de tiempo"])

    with tabs[0]:
        df = consulta("SELECT * FROM v_kpi_recomendaciones ORDER BY ctr_pct DESC")
        c = st.columns(4)
        kpi(c[0], "Impresiones", f"{int(df.impresiones.sum()):,}", "👀")
        kpi(c[1], "Clics", f"{int(df.clics.sum()):,}", "🖱️")
        kpi(c[2], "CTR global", f"{100*df.clics.sum()/max(df.impresiones.sum(),1):.1f}%", "🎯")
        kpi(c[3], "Superficies", len(df), "🧩")
        st.write("")
        barras(df, "surface", "ctr_pct", 280)
        st.dataframe(df, hide_index=True, width="stretch", column_config={
            "ctr_pct": st.column_config.ProgressColumn("CTR %", format="%.1f", min_value=0, max_value=100),
            "save_rate_pct": st.column_config.NumberColumn("Guardado %", format="%.1f"),
            "skip_rate_pct": st.column_config.NumberColumn("Skip %", format="%.1f"),
            "completion_rate_pct": st.column_config.NumberColumn("Completadas %", format="%.1f")})
        st.markdown("**Prueba A/B del modelo**")
        st.dataframe(consulta("""SELECT ab_test_group AS grupo, model_version AS modelo, COUNT(*) AS impresiones,
                                 ROUND(100*AVG(clicked),2) AS ctr_pct,
                                 ROUND(100*SUM(saved)/NULLIF(SUM(played),0),2) AS guardado_pct
                                 FROM recommendation_events GROUP BY ab_test_group, model_version"""),
                     hide_index=True, width="stretch")

    with tabs[1]:
        df = consulta("SELECT * FROM v_kpi_reproduccion ORDER BY reproducciones DESC")
        barras(df, "source", "reproducciones", 260)
        st.dataframe(df, hide_index=True, width="stretch")
        st.markdown("**Motivo de fin de reproducción**")
        st.dataframe(consulta("""SELECT reason_end AS motivo, COUNT(*) AS eventos FROM song_played
                                 GROUP BY reason_end ORDER BY eventos DESC"""), hide_index=True, width="stretch")

    with tabs[2]:
        df = consulta("""SELECT device_type AS dispositivo, os, COUNT(*) AS sesiones,
                         ROUND(AVG(duration_sec)/60,1) AS min_promedio, ROUND(AVG(tracks_played),1) AS canciones
                         FROM app_sessions GROUP BY device_type, os ORDER BY sesiones DESC""")
        barras(df, "os", "sesiones", 260)
        st.dataframe(df, hide_index=True, width="stretch")

    with tabs[3]:
        st.dataframe(consulta("""SELECT query_text AS busqueda, COUNT(*) AS veces,
                                 ROUND(100*AVG(clicked_song_id IS NOT NULL),1) AS clic_pct,
                                 ROUND(AVG(time_to_click_ms)) AS ms_hasta_clic
                                 FROM search_events GROUP BY query_text ORDER BY veces DESC"""),
                     hide_index=True, width="stretch")

    with tabs[4]:
        df = consulta("""SELECT event_type AS evento, COUNT(*) AS eventos, COUNT(DISTINCT user_id) AS usuarios
                         FROM subscription_events GROUP BY event_type ORDER BY usuarios DESC""")
        barras(df, "evento", "usuarios", 260)
        st.dataframe(df, hide_index=True, width="stretch")

    with tabs[5]:
        st.dataframe(consulta("""SELECT advertiser AS anunciante, ad_format AS formato,
                                 SUM(event_type='impression') AS impresiones, SUM(event_type='click') AS clics,
                                 SUM(event_type='skip') AS saltados, ROUND(SUM(revenue_mxn),2) AS ingreso_mxn
                                 FROM ad_events GROUP BY advertiser, ad_format ORDER BY impresiones DESC"""),
                     hide_index=True, width="stretch")

    with tabs[6]:
        st.dataframe(consulta("""SELECT event_type AS evento, IFNULL(error_code,'-') AS codigo, COUNT(*) AS eventos,
                                 ROUND(AVG(latency_ms)) AS latencia_ms FROM app_performance_events
                                 GROUP BY event_type, error_code ORDER BY eventos DESC"""),
                     hide_index=True, width="stretch")

    with tabs[7]:
        usuarios = consulta("SELECT user_id, username FROM users ORDER BY user_id")
        nombres = dict(zip(usuarios.user_id, usuarios.username))
        uid = st.selectbox("Usuario", usuarios.user_id.tolist(), format_func=lambda i: f"{nombres.get(i, i)}  ·  #{i}")
        if uid is None:
            st.info("No hay usuarios registrados.")
        else:
            st.dataframe(consulta("""SELECT event_at AS fecha, event_type AS evento, detalle, session_id AS sesion
                                     FROM v_telemetria_unificada WHERE user_id = %s ORDER BY event_at DESC LIMIT 300""",
                                  (int(uid),)), hide_index=True, width="stretch", height=420)


# =====================================================================
# PÁGINA: BASE DE DATOS (visor + altas / modificaciones / bajas en lote)
# =====================================================================
TEMA_ALTAIR = dict(background="transparent")
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def _alt_config(chart):
    """Estilo oscuro común para las gráficas de Altair."""
    return (chart.configure(**TEMA_ALTAIR)
            .configure_axis(labelColor="#b3b3b3", titleColor="#b3b3b3", gridColor="#2a2a2a", domainColor="#3a3a3a")
            .configure_legend(labelColor="#e5e5e5", titleColor="#b3b3b3")
            .configure_view(strokeWidth=0))


def prueba_z_proporciones(exitos_a, n_a, exitos_b, n_b):
    """Prueba z de dos proporciones (bilateral). Devuelve (z, valor_p, IC95% de la diferencia B−A)."""
    if min(n_a, n_b) == 0:
        return 0.0, 1.0, (0.0, 0.0)
    p_a, p_b = exitos_a / n_a, exitos_b / n_b
    p_pool = (exitos_a + exitos_b) / (n_a + n_b)
    se_pool = math.sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b))
    z = (p_b - p_a) / se_pool if se_pool else 0.0
    valor_p = math.erfc(abs(z) / math.sqrt(2))
    se_dif = math.sqrt(p_a * (1 - p_a) / n_a + p_b * (1 - p_b) / n_b)
    return z, valor_p, (p_b - p_a - 1.96 * se_dif, p_b - p_a + 1.96 * se_dif)


def fecha_referencia():
    """Fecha 'de hoy' para los datos: la última reproducción registrada (los datos son simulados)."""
    df = consulta("SELECT MAX(played_at) AS ref FROM song_played")
    ref = df.ref.iloc[0] if not df.empty else None
    return pd.Timestamp(ref) if ref is not None and pd.notna(ref) else pd.Timestamp(datetime.now())


def pct(a, b):
    return 100.0 * a / b if b else 0.0


def pagina_marketing():
    st.markdown("""<div class="hero"><div class="logo">📈</div><div><div class="sub">ANÁLISIS DE MARKETING</div>
        <h1>Marketing</h1><div class="sub">Hipótesis de retención (Aha! Moment), embudo de conversión, cohortes,
        ingresos y prueba A/B del recomendador</div></div></div>""", unsafe_allow_html=True)
    guia("""
- **🎯 Hipótesis Aha!**: *“Un usuario que crea al menos 1 playlist y escucha 20 o más canciones en sus primeros
  7 días se queda y se vuelve Premium”*. Se comparan los usuarios que **sí** vivieron el Aha! contra los que **no**.
  La **retención** se mide entre los días 8 y 30 después del registro, y solo cuenta a quienes ya llevan 30 días registrados.
- **🔻 Embudo**: cuántos usuarios llegan a cada etapa, desde que se registran hasta que pagan Premium.
- **📅 Cohortes**: los usuarios se agrupan por la semana en que se registraron; cada celda dice qué % siguió
  escuchando música *n* semanas después. Lo ideal es que los colores se mantengan verdes hacia la derecha.
- **💰 Ingresos**: MRR (ingreso mensual recurrente de suscripciones activas), ARPU (ingreso promedio por usuario),
  churn (porcentaje de suscripciones canceladas) y la publicidad que pagan los usuarios free.
- **🧪 Prueba A/B**: compara el CTR del modelo de recomendación del grupo A contra el B con una **prueba z de
  dos proporciones**. Si el valor p es menor a 0.05, la diferencia es estadísticamente significativa.
- La fecha de referencia («hoy») es la **última reproducción registrada**, porque los datos son simulados.""")

    ref = fecha_referencia()
    tabs = st.tabs(["🎯 Hipótesis Aha!", "🔻 Embudo", "📅 Cohortes", "💰 Ingresos", "🧪 Prueba A/B"])

    # ---------------- Hipótesis Aha! Moment ----------------
    with tabs[0]:
        df = consulta("""
            SELECT u.user_id, u.username, u.signup_date, u.account_type,
                   (SELECT COUNT(*) FROM playlist_created p WHERE p.user_id = u.user_id
                       AND p.created_at BETWEEN u.signup_date AND u.signup_date + INTERVAL 7 DAY) AS playlists_7d,
                   (SELECT COUNT(*) FROM song_played s WHERE s.user_id = u.user_id
                       AND s.played_at BETWEEN u.signup_date AND u.signup_date + INTERVAL 7 DAY) AS plays_7d,
                   (SELECT COUNT(*) FROM song_played s WHERE s.user_id = u.user_id
                       AND s.played_at >  u.signup_date + INTERVAL 7 DAY
                       AND s.played_at <= u.signup_date + INTERVAL 30 DAY) AS plays_8_30,
                   (SELECT COUNT(*) FROM song_played s WHERE s.user_id = u.user_id) AS plays_total,
                   EXISTS(SELECT 1 FROM premium_subscribed ps WHERE ps.user_id = u.user_id) AS fue_premium
              FROM users u ORDER BY u.user_id""")
        if df.empty:
            st.info("No hay usuarios registrados.")
        else:
            df["signup_date"] = pd.to_datetime(df.signup_date)
            df["aha"] = (df.playlists_7d >= 1) & (df.plays_7d >= 20)
            df["elegible"] = df.signup_date <= ref - pd.Timedelta(days=30)
            df["retenido"] = df.plays_8_30 > 0
            df["fue_premium"] = df.fue_premium.astype(int) == 1
            n_aha = int(df.aha.sum())

            filas = []
            for nombre, g in [("Con Aha! Moment", df[df.aha]), ("Sin Aha! Moment", df[~df.aha])]:
                ge = g[g.elegible]
                filas.append({"Grupo": nombre, "Usuarios": len(g), "Elegibles (≥30 días)": len(ge),
                              "Retención días 8-30 %": round(pct(ge.retenido.sum(), len(ge)), 1) if len(ge) else None,
                              "Conversión a Premium %": round(pct(g.fue_premium.sum(), len(g)), 1),
                              "Reproducciones promedio": round(g.plays_total.mean(), 1) if len(g) else 0})
            comp = pd.DataFrame(filas)
            con, sin = comp.iloc[0], comp.iloc[1]

            c = st.columns(4)
            kpi(c[0], "Usuarios con Aha!", f"{n_aha}", "🎯", f"{pct(n_aha, len(df)):.0f}% de {len(df)} usuarios")
            ret_con = "—" if pd.isna(con["Retención días 8-30 %"]) else f"{con['Retención días 8-30 %']:.0f}%"
            ret_sin = "—" if pd.isna(sin["Retención días 8-30 %"]) else f"{sin['Retención días 8-30 %']:.0f}%"
            kpi(c[1], "Retención con Aha!", ret_con, "🔁", f"sin Aha!: {ret_sin}")
            kpi(c[2], "Premium con Aha!", f"{con['Conversión a Premium %']:.0f}%", "💎",
                f"sin Aha!: {sin['Conversión a Premium %']:.0f}%")
            veces = (con["Conversión a Premium %"] / sin["Conversión a Premium %"]
                     if sin["Conversión a Premium %"] else None)
            kpi(c[3], "Efecto en Premium", f"×{veces:.1f}" if veces else "—", "🚀", "con Aha! vs sin Aha!")
            st.write("")

            largo = comp.melt(id_vars="Grupo", value_vars=["Retención días 8-30 %", "Conversión a Premium %"],
                              var_name="Métrica", value_name="Porcentaje").dropna()
            base_g = alt.Chart(largo).encode(
                x=alt.X("Métrica:N", title=None, axis=alt.Axis(labelAngle=0, labelLimit=400)),
                xOffset=alt.XOffset("Grupo:N"),
                y=alt.Y("Porcentaje:Q", title="%", scale=alt.Scale(domain=[0, 105])))
            graf = base_g.mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
                color=alt.Color("Grupo:N", title=None, scale=alt.Scale(range=[VERDE, "#535353"]),
                                legend=alt.Legend(orient="top")),
                tooltip=["Grupo", "Métrica", "Porcentaje"])
            etiquetas = base_g.mark_text(dy=-8, color="#ffffff").encode(text=alt.Text("Porcentaje:Q", format=".0f"))
            st.altair_chart(_alt_config((graf + etiquetas).properties(height=280)), width="stretch")
            st.dataframe(comp, hide_index=True, width="stretch")

            # Conclusión automática
            if not pd.isna(con["Retención días 8-30 %"]) and not pd.isna(sin["Retención días 8-30 %"]):
                dif_ret = con["Retención días 8-30 %"] - sin["Retención días 8-30 %"]
                dif_prem = con["Conversión a Premium %"] - sin["Conversión a Premium %"]
                if dif_ret > 0 and dif_prem > 0:
                    st.success(f"✅ **La hipótesis se cumple con estos datos.** Quienes viven el Aha! Moment retienen "
                               f"**{dif_ret:.0f} puntos porcentuales más** y se vuelven Premium **{dif_prem:.0f} puntos "
                               f"más** que quienes no lo viven.")
                else:
                    st.warning(f"⚠️ **La hipótesis no se cumple del todo**: diferencia en retención {dif_ret:+.0f} pp, "
                               f"en Premium {dif_prem:+.0f} pp.")
                if min(con["Elegibles (≥30 días)"], sin["Elegibles (≥30 días)"]) < 10:
                    st.caption("Nota: algún grupo tiene menos de 10 usuarios elegibles; tómese como evidencia "
                               "exploratoria, no concluyente.")
            with st.expander(f"👥 Ver los {n_aha} usuarios que viven el Aha! Moment"):
                st.dataframe(df[df.aha][["user_id", "username", "signup_date", "playlists_7d", "plays_7d",
                                         "plays_8_30", "account_type"]],
                             hide_index=True, width="stretch", column_config={
                                 "user_id": "ID", "username": "Usuario", "signup_date": "Registro",
                                 "playlists_7d": "Playlists 7 días", "plays_7d": "Canciones 7 días",
                                 "plays_8_30": "Canciones días 8-30", "account_type": "Plan"})

    # ---------------- Embudo ----------------
    with tabs[1]:
        # Una fila por usuario con cada etapa (0/1); el embudo es ESTRICTO: cada etapa
        # solo cuenta a quienes también pasaron todas las anteriores.
        f = consulta("""
            SELECT u.user_id,
                   EXISTS(SELECT 1 FROM song_played s WHERE s.user_id = u.user_id) AS escucho,
                   ((SELECT COUNT(*) FROM playlist_created p WHERE p.user_id = u.user_id
                        AND p.created_at BETWEEN u.signup_date AND u.signup_date + INTERVAL 7 DAY) >= 1
                    AND (SELECT COUNT(*) FROM song_played s WHERE s.user_id = u.user_id
                        AND s.played_at BETWEEN u.signup_date AND u.signup_date + INTERVAL 7 DAY) >= 20) AS aha,
                   EXISTS(SELECT 1 FROM subscription_events e WHERE e.user_id = u.user_id
                           AND e.event_type = 'paywall_view') AS paywall,
                   EXISTS(SELECT 1 FROM subscription_events e WHERE e.user_id = u.user_id
                           AND e.event_type IN ('trial_started', 'purchase')) AS prueba_compra,
                   u.account_type = 'premium' AS premium
              FROM users u""")
        total = len(f)
        if total == 0:
            st.info("No hay usuarios registrados.")
        else:
            nombres = [("1. Se registraron", None), ("2. Escucharon al menos 1 canción", "escucho"),
                       ("3. Vivieron el Aha! Moment", "aha"), ("4. Vieron la oferta Premium", "paywall"),
                       ("5. Iniciaron prueba o compraron", "prueba_compra"), ("6. Premium activo hoy", "premium")]
            pasa = pd.Series(True, index=f.index)
            etapas = []
            for nombre, col in nombres:
                if col:
                    pasa = pasa & (f[col].astype(int) == 1)
                etapas.append((nombre, int(pasa.sum())))
            emb = pd.DataFrame(etapas, columns=["Etapa", "Usuarios"])
            emb["% del total"] = emb.Usuarios.map(lambda v: round(pct(v, total), 1))
            emb["% vs etapa anterior"] = [None] + [round(pct(b, a), 1)
                                                   for a, b in zip(emb.Usuarios[:-1], emb.Usuarios[1:])]
            emb["Etiqueta"] = emb.apply(lambda r: f"{r.Usuarios}  ({r['% del total']:.0f}%)", axis=1)
            premium_total = int((f.premium.astype(int) == 1).sum())
            premium_sin_aha = premium_total - int(emb.Usuarios.iloc[-1])

            c = st.columns(3)
            kpi(c[0], "Embudo completo", f"{emb['% del total'].iloc[-1]:.1f}%", "💎",
                f"{emb.Usuarios.iloc[-1]} de {total} llegan a Premium")
            caida = emb.assign(perdidos=emb.Usuarios.shift(1) - emb.Usuarios).iloc[1:]
            peor = caida.loc[caida.perdidos.idxmax()]
            kpi(c[1], "Mayor fuga", f"−{int(peor.perdidos)} usuarios", "🕳️", f"al llegar a: {peor.Etapa.split('. ', 1)[1]}")
            kpi(c[2], "Premium sin Aha!", f"{premium_sin_aha}", "🧭", f"de {premium_total} Premium activos")
            st.write("")
            base = alt.Chart(emb).encode(y=alt.Y("Etapa:N", sort=None, title=None, axis=alt.Axis(labelLimit=260)))
            barras_emb = base.mark_bar(color=VERDE, cornerRadiusEnd=4).encode(
                x=alt.X("Usuarios:Q", title="Usuarios"), tooltip=["Etapa", "Usuarios", "% del total", "% vs etapa anterior"])
            texto = base.mark_text(align="left", dx=6, color="#ffffff").encode(x="Usuarios:Q", text="Etiqueta:N")
            st.altair_chart(_alt_config((barras_emb + texto).properties(height=300)), width="stretch")
            st.dataframe(emb.drop(columns=["Etiqueta"]), hide_index=True, width="stretch")
            st.caption("Embudo estricto: cada etapa cuenta solo a los usuarios que también pasaron todas las anteriores. "
                       "«Premium sin Aha!» son los que pagan Premium sin haber vivido el Aha! Moment (llegaron por "
                       "otro camino).")

    # ---------------- Cohortes ----------------
    with tabs[2]:
        usuarios = consulta("SELECT user_id, signup_date FROM users")
        act = consulta("""SELECT DISTINCT sp.user_id, FLOOR(DATEDIFF(sp.played_at, u.signup_date) / 7) AS semana
                            FROM song_played sp JOIN users u USING (user_id)
                           WHERE sp.played_at >= u.signup_date""")
        if usuarios.empty:
            st.info("No hay usuarios registrados.")
        else:
            usuarios["signup_date"] = pd.to_datetime(usuarios.signup_date)
            usuarios["inicio"] = (usuarios.signup_date - pd.to_timedelta(usuarios.signup_date.dt.dayofweek, unit="D")
                                  ).dt.normalize()
            tam = usuarios.groupby("inicio").size()
            activos = {}
            if not act.empty:
                act["semana"] = act.semana.astype(int)
                act = act.merge(usuarios[["user_id", "inicio"]], on="user_id")
                activos = act.groupby(["inicio", "semana"]).user_id.nunique().to_dict()
            # Rejilla completa: cada cohorte con todas sus semanas ya terminadas (las que no tuvieron
            # actividad valen 0, no se dejan en blanco). La semana k termina para toda la cohorte
            # (registros del lunes al domingo) el día inicio + 7·(k+2).
            filas = []
            for inicio in tam.index:
                k = 0
                while k <= 12 and inicio + pd.Timedelta(days=7 * (k + 2)) <= ref:
                    filas.append({"inicio": inicio, "semana": k, "activos": activos.get((inicio, k), 0)})
                    k += 1
            coh = pd.DataFrame(filas, columns=["inicio", "semana", "activos"])
            if coh.empty:
                st.info("Todavía no hay semanas completas para medir retención.")
            else:
                coh["tamaño"] = coh.inicio.map(tam)
                coh["retencion"] = (100 * coh.activos / coh["tamaño"]).round(0)
                coh["Cohorte"] = coh.apply(lambda f: f"Sem. {f.inicio.day:02d} {MESES[f.inicio.month - 1]} "
                                                     f"(n={int(f['tamaño'])})", axis=1)
                coh["Semana"] = coh.semana.map(lambda s: f"S{s}")
                orden_sem = [f"S{i}" for i in range(int(coh.semana.max()) + 1)]
                orden_coh = coh.sort_values("inicio").Cohorte.unique().tolist()
                sumas = coh.groupby("semana")[["activos", "tamaño"]].sum()
                prom = (100 * sumas.activos / sumas["tamaño"]).fillna(0)
                c = st.columns(3)
                kpi(c[0], "Cohortes semanales", f"{coh.inicio.nunique()}", "📅", "semana de registro")
                kpi(c[1], "Retención semana 1", f"{prom.get(1, 0):.0f}%", "🔁",
                    f"{int(sumas['tamaño'].get(1, 0))} usuarios medidos")
                # Semana 4 (≈ un mes) si ya se puede medir; si no, la última disponible
                s4 = 4 if 4 in prom.index else int(prom.index.max())
                kpi(c[2], f"Retención semana {s4}", f"{prom.get(s4, 0):.0f}%", "📉",
                    f"{int(sumas['tamaño'].get(s4, 0))} usuarios medidos")
                st.write("")
                calor = alt.Chart(coh).mark_rect(cornerRadius=3).encode(
                    x=alt.X("Semana:N", sort=orden_sem, title="Semanas desde el registro", axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("Cohorte:N", sort=orden_coh, title=None),
                    color=alt.Color("retencion:Q", title="% activos",
                                    scale=alt.Scale(domain=[0, 100], range=["#1f1f1f", "#0d5c2b", VERDE])),
                    tooltip=["Cohorte", "Semana", "activos", "tamaño", "retencion"])
                num = alt.Chart(coh).mark_text(fontSize=11, color="#ffffff").encode(
                    x=alt.X("Semana:N", sort=orden_sem), y=alt.Y("Cohorte:N", sort=orden_coh),
                    text=alt.Text("retencion:Q", format=".0f"))
                st.altair_chart(_alt_config((calor + num).properties(height=max(220, 26 * len(orden_coh)))),
                                width="stretch")
                st.caption("S0 = la semana del registro. Solo se muestran semanas que ya terminaron para toda la cohorte.")

    # ---------------- Ingresos ----------------
    with tabs[3]:
        i = consulta("""
            SELECT (SELECT IFNULL(SUM(price_mxn), 0) FROM premium_subscribed WHERE status = 'activa') AS mrr,
                   (SELECT COUNT(*) FROM premium_subscribed WHERE status = 'activa') AS activas,
                   (SELECT COUNT(*) FROM premium_subscribed WHERE status = 'prueba') AS en_prueba,
                   (SELECT COUNT(*) FROM premium_subscribed WHERE status = 'cancelada') AS canceladas,
                   (SELECT COUNT(*) FROM premium_subscribed) AS total_subs,
                   (SELECT COUNT(*) FROM users) AS usuarios,
                   (SELECT IFNULL(SUM(revenue_mxn), 0) FROM ad_events WHERE event_at > %s - INTERVAL 30 DAY) AS ads_30d
        """, (ref.to_pydatetime(),)).iloc[0]
        arpu = (float(i.mrr) + float(i.ads_30d)) / max(int(i.usuarios), 1)
        c = st.columns(4)
        kpi(c[0], "MRR", f"${float(i.mrr):,.0f}", "💰", f"{int(i.activas)} suscripciones activas")
        kpi(c[1], "ARPU mensual", f"${arpu:,.2f}", "👤", "(MRR + anuncios 30 días) / usuarios")
        kpi(c[2], "Churn", f"{pct(i.canceladas, i.total_subs):.1f}%", "🚪",
            f"{int(i.canceladas)} de {int(i.total_subs)} suscripciones")
        kpi(c[3], "Anuncios (30 días)", f"${float(i.ads_30d):,.2f}", "📢", f"{int(i.en_prueba)} en prueba gratis")
        st.write("")
        meses = consulta("""
            SELECT DATE_FORMAT(event_at, '%Y-%m') AS mes, 'Suscripciones' AS fuente, SUM(price_mxn) AS ingreso
              FROM subscription_events WHERE event_type IN ('purchase', 'renewal') GROUP BY mes
            UNION ALL
            SELECT DATE_FORMAT(event_at, '%Y-%m'), 'Publicidad', SUM(revenue_mxn)
              FROM ad_events GROUP BY DATE_FORMAT(event_at, '%Y-%m')
            ORDER BY mes""")
        c1, c2 = st.columns([3, 2])
        with c1:
            st.markdown("**Ingresos por mes (MXN)**")
            if meses.empty:
                st.caption("Sin datos todavía.")
            else:
                g = alt.Chart(meses).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
                    x=alt.X("mes:N", title=None, axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("sum(ingreso):Q", title="MXN"),
                    color=alt.Color("fuente:N", title=None, legend=alt.Legend(orient="top"),
                                    scale=alt.Scale(domain=["Suscripciones", "Publicidad"], range=[VERDE, "#b3b3b3"])),
                    tooltip=["mes", "fuente", alt.Tooltip("ingreso:Q", format=",.2f")]).properties(height=280)
                st.altair_chart(_alt_config(g), width="stretch")
        with c2:
            st.markdown("**Suscripciones por plan**")
            planes = consulta("""SELECT plan_type AS plan, COUNT(*) AS suscripciones,
                                        SUM(status = 'activa') AS activas, IFNULL(SUM(IF(status = 'activa', price_mxn, 0)), 0) AS mrr
                                   FROM premium_subscribed GROUP BY plan_type ORDER BY mrr DESC""")
            st.dataframe(planes, hide_index=True, width="stretch", column_config={
                "plan": "Plan", "suscripciones": "Total", "activas": "Activas",
                "mrr": st.column_config.NumberColumn("MRR", format="$%.0f")})
        st.caption(f"MRR = suma del precio mensual de las suscripciones activas (las de prueba gratis no pagan todavía). "
                   f"El último mes puede estar incompleto: los datos llegan hasta el {ref:%d/%m/%Y}.")

    # ---------------- Prueba A/B ----------------
    with tabs[4]:
        ab = consulta("""SELECT ab_test_group AS grupo, GROUP_CONCAT(DISTINCT model_version ORDER BY model_version SEPARATOR ', ') AS modelos,
                                COUNT(*) AS impresiones, SUM(clicked) AS clics, SUM(played) AS reproducidas,
                                SUM(saved) AS guardadas
                           FROM recommendation_events WHERE ab_test_group IN ('A', 'B')
                          GROUP BY ab_test_group ORDER BY ab_test_group""")
        if set(ab.grupo) != {"A", "B"}:
            st.info("Se necesitan impresiones de los grupos A y B para la prueba.")
        else:
            a, b = ab.set_index("grupo").loc["A"], ab.set_index("grupo").loc["B"]
            ctr_a, ctr_b = pct(a.clics, a.impresiones), pct(b.clics, b.impresiones)
            z, valor_p, (ic_lo, ic_hi) = prueba_z_proporciones(int(a.clics), int(a.impresiones),
                                                              int(b.clics), int(b.impresiones))
            lift = (ctr_b - ctr_a) / ctr_a * 100 if ctr_a else 0
            c = st.columns(4)
            kpi(c[0], "CTR grupo A", f"{ctr_a:.2f}%", "🅰️", f"{int(a.impresiones):,} impresiones")
            kpi(c[1], "CTR grupo B", f"{ctr_b:.2f}%", "🅱️", f"{int(b.impresiones):,} impresiones")
            kpi(c[2], "Lift de B", f"{lift:+.1f}%", "📊", "cambio relativo del CTR")
            kpi(c[3], "Valor p", f"{valor_p:.4f}" if valor_p >= 0.0001 else "< 0.0001", "🧪", f"z = {z:.2f}")
            st.write("")
            if valor_p < 0.05:
                ganador = "B" if ctr_b > ctr_a else "A"
                st.success(f"✅ **Diferencia estadísticamente significativa (95% de confianza).** El modelo del grupo "
                           f"**{ganador}** tiene mejor CTR. La diferencia real B−A está entre **{100*ic_lo:+.2f}** y "
                           f"**{100*ic_hi:+.2f}** puntos porcentuales. Recomendación: usar el modelo {ganador} "
                           f"para todos los usuarios.")
            else:
                st.warning(f"⚠️ **No hay diferencia significativa** (p = {valor_p:.3f} ≥ 0.05). Con estos datos no se "
                           f"puede afirmar que un modelo sea mejor que el otro; conviene seguir la prueba.")
            tabla = ab.assign(**{"CTR %": (100 * ab.clics / ab.impresiones).round(2),
                                 "Guardado %": (100 * ab.guardadas / ab.reproducidas.replace(0, pd.NA)).astype(float).round(2)})
            st.dataframe(tabla, hide_index=True, width="stretch", column_config={
                "grupo": "Grupo", "modelos": "Versión del modelo", "impresiones": "Impresiones", "clics": "Clics",
                "reproducidas": "Reproducidas", "guardadas": "Guardadas"})
            st.caption("Prueba z de dos proporciones, bilateral: H₀ = el CTR de A es igual al de B. "
                       "El intervalo es el IC del 95% para la diferencia de CTR.")


TABLAS = {
    "Principales": ["users", "songs", "song_played", "playlist_created", "song_liked", "premium_subscribed",
                    "user_recommendations"],
    "Telemetría": ["app_sessions", "recommendation_events", "search_events", "ui_events", "playlist_tracks",
                   "artist_follows", "download_events", "share_events", "ad_events", "subscription_events",
                   "notification_events", "app_performance_events"],
    "Vistas KPI": ["v_kpi_recomendaciones", "v_kpi_reproduccion", "v_telemetria_unificada"],
}
pk_map = {
    "users": "user_id", "songs": "song_id", "song_played": "play_id", "playlist_created": "playlist_id",
    "song_liked": "like_id", "premium_subscribed": "subscription_id", "user_recommendations": "recommendation_id",
    "app_sessions": "session_id", "recommendation_events": "rec_event_id", "search_events": "search_id",
    "ui_events": "ui_event_id", "playlist_tracks": "playlist_track_id", "artist_follows": "follow_id",
    "download_events": "download_id", "share_events": "share_id", "ad_events": "ad_event_id",
    "subscription_events": "sub_event_id", "notification_events": "notif_id", "app_performance_events": "perf_event_id",
}
# Planes y precio mensual en MXN (los mismos que usa "base de datos.py")
PRECIOS_PLANES = {"Individual Premium": 139.0, "Dúo Premium": 179.0, "Familiar Premium": 219.0,
                  "Estudiantil Premium": 75.0}
PLANES = list(PRECIOS_PLANES)
TABLAS_CON_ALTAS = ["users", "songs", "song_played", "playlist_created", "song_liked", "premium_subscribed"]


def pagina_base_datos():
    with st.sidebar:
        st.markdown("**🗂️ Tabla**")
        grupo = st.radio("Grupo", list(TABLAS), horizontal=True, label_visibility="collapsed")
        tabla_seleccionada = st.selectbox("Tabla", TABLAS[grupo], label_visibility="collapsed")
    campo_pk = pk_map.get(tabla_seleccionada)

    st.markdown(f"""<div class="hero"><div class="logo">🗄️</div><div><div class="sub">TABLA</div>
        <h1>{esc(tabla_seleccionada)}</h1><div class="sub">{esc(DB_NAME)}</div></div></div>""",
                unsafe_allow_html=True)
    guia("""
- Elige el **grupo** y la **tabla** en la barra lateral. El buscador filtra en todas las columnas; con el icono de
  descarga de la tabla se exporta a **CSV**.
- **Gestión en lote** (1 a 5 registros): **Altas** valida campos y fechas (`AAAA-MM-DD HH:MM:SS`); **Modificar**
  conserva lo que dejes vacío; **Bajas** pide confirmación y borra también los datos dependientes.
- Las tablas de telemetría y las vistas `v_…` son de solo lectura (se generan automáticamente).
- El diccionario de datos completo está en `docs/DICCIONARIO_DATOS.md`.""")

    # ---- Visualización ----
    try:
        limite = "" if grupo == "Principales" else " LIMIT 2000"
        orden = f" ORDER BY {campo_pk} DESC" if campo_pk and grupo != "Principales" else ""
        df = consulta(f"SELECT * FROM {tabla_seleccionada}{orden}{limite};")
        if tabla_seleccionada == "users" and not df.empty:
            ult = consulta("SELECT user_id, MAX(played_at) AS ultima FROM song_played GROUP BY user_id")
            ult = dict(zip(ult.user_id, ult.ultima)) if not ult.empty else {}
            # Se mide contra la última reproducción registrada (no contra hoy) para que
            # los datos simulados no aparezcan todos inactivos con el paso de los días.
            fechas = [f for f in ult.values() if f is not None and pd.notna(f)]
            referencia = max(fechas) if fechas else datetime.now()
            df.insert(1, "Actividad", ["🟢 Activo (≤ 7 días)" if ult.get(u) is not None and pd.notna(ult.get(u))
                                       and referencia - ult[u] <= timedelta(days=7) else "🔴 Inactivo"
                                       for u in df.user_id])
        c = st.columns(3)
        kpi(c[0], "Registros mostrados", f"{len(df):,}", "📄", "máx. 2,000 en telemetría" if limite else "")
        kpi(c[1], "Columnas", len(df.columns), "🧱")
        kpi(c[2], "Llave primaria", campo_pk or "— (vista)", "🔑")
        st.write("")
        buscar = st.text_input("🔎 Buscar en la tabla", placeholder="Escribe para filtrar…")
        if buscar and not df.empty:
            mask = df.astype(str).apply(lambda col: col.str.contains(buscar, case=False, na=False, regex=False)).any(axis=1)
            df = df[mask]
        if not df.empty:
            st.dataframe(df, width="stretch", hide_index=True, height=380)
        else:
            st.info("La tabla está vacía o no hay coincidencias.")
    except Exception as e:
        st.error(f"Error al cargar la tabla: {e}")

    if tabla_seleccionada.startswith("v_"):
        st.caption("Esta es una vista de KPIs de telemetría: solo lectura.")
        return

    st.markdown("### 🛠️ Gestión en lote (1 a 5 registros)")
    opcion_gestion = st.segmented_control("Acción", ["➕ Altas", "✏️ Modificar", "🗑️ Bajas"],
                                          default="➕ Altas", label_visibility="collapsed")
    ahora_txt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # --- ALTAS ---
    if opcion_gestion == "➕ Altas":
        if tabla_seleccionada not in TABLAS_CON_ALTAS:
            st.info("Las altas manuales solo están disponibles para las tablas principales. "
                    "La telemetría y las recomendaciones se generan automáticamente.")
            return
        cantidad_altas = st.slider("¿Cuántos registros deseas agregar?", 1, 5, 1)
        u_ids, s_ids = obtener_ids("users", "user_id"), obtener_ids("songs", "song_id")
        with st.form("form_altas_lote"):
            datos_nuevos = []
            for i in range(cantidad_altas):
                st.markdown(f"**Registro #{i+1}**")
                c1, c2, c3 = st.columns(3)
                if tabla_seleccionada == "users":
                    datos_nuevos.append((c1.text_input("Nombre de usuario", key=f"user_{i}"),
                                         c2.text_input("Fecha registro", ahora_txt, key=f"signup_{i}")))
                elif tabla_seleccionada == "songs":
                    datos_nuevos.append((c1.text_input("Título", key=f"title_{i}"),
                                         c2.text_input("Artista", key=f"artist_{i}")))
                elif tabla_seleccionada == "song_played":
                    datos_nuevos.append((c1.selectbox("ID Usuario", u_ids, key=f"sp_u_{i}"),
                                         c2.selectbox("ID Canción", s_ids, key=f"sp_s_{i}"),
                                         c3.text_input("Fecha reproducción", ahora_txt, key=f"sp_t_{i}")))
                elif tabla_seleccionada == "playlist_created":
                    datos_nuevos.append((c1.selectbox("ID Usuario", u_ids, key=f"pl_u_{i}"),
                                         c2.text_input("Nombre playlist", key=f"pl_n_{i}"),
                                         c3.text_input("Fecha creación", ahora_txt, key=f"pl_t_{i}")))
                elif tabla_seleccionada == "song_liked":
                    datos_nuevos.append((c1.selectbox("ID Usuario", u_ids, key=f"lk_u_{i}"),
                                         c2.selectbox("ID Canción", s_ids, key=f"lk_s_{i}"),
                                         c3.text_input("Fecha like", ahora_txt, key=f"lk_t_{i}")))
                elif tabla_seleccionada == "premium_subscribed":
                    uid = c1.selectbox("ID Usuario", u_ids, key=f"pr_u_{i}")
                    ptype = c2.selectbox("Plan", PLANES, key=f"pr_p_{i}")
                    subat = c3.text_input("Fecha suscripción", ahora_txt, key=f"pr_t_{i}")
                    datos_nuevos.append((uid, subat, ptype))
            guardar = st.form_submit_button("Guardar registros", type="primary")

        if guardar:
            sql = {
                "users": "INSERT INTO users (username, signup_date) VALUES (%s, %s);",
                "songs": "INSERT INTO songs (title, artist) VALUES (%s, %s);",
                "song_played": "INSERT INTO song_played (user_id, song_id, played_at) VALUES (%s, %s, %s);",
                "playlist_created": "INSERT INTO playlist_created (user_id, playlist_name, created_at) VALUES (%s, %s, %s);",
                "song_liked": "INSERT INTO song_liked (user_id, song_id, liked_at) VALUES (%s, %s, %s);",
                "premium_subscribed": "INSERT INTO premium_subscribed (user_id, subscribed_at, plan_type, price_mxn) "
                                      "VALUES (%s, %s, %s, %s);",
            }[tabla_seleccionada]
            # ---- Validación antes de tocar la base ----
            datos_nuevos = [tuple(v.strip() if isinstance(v, str) else v for v in item) for item in datos_nuevos]
            errores = []
            for n, item in enumerate(datos_nuevos, start=1):
                if any(v is None for v in item):
                    errores.append(f"Registro #{n}: no hay usuarios o canciones para elegir.")
                elif any(isinstance(v, str) and not v for v in item):
                    errores.append(f"Registro #{n}: hay campos vacíos.")
                elif not any(isinstance(v, str) and fecha_valida(v) for v in item):
                    errores.append(f"Registro #{n}: la fecha debe tener el formato AAAA-MM-DD HH:MM:SS.")
            if tabla_seleccionada == "songs":
                errores = [e for e in errores if "fecha" not in e]   # songs no lleva fecha
            if tabla_seleccionada == "song_liked":
                pares = [(int(i[0]), int(i[1])) for i in datos_nuevos if i[0] is not None and i[1] is not None]
                if len(set(pares)) != len(pares):
                    errores.append("Hay likes repetidos (mismo usuario y canción) en el formulario.")
                for uid_l, sid_l in set(pares):
                    if not consulta("SELECT 1 FROM song_liked WHERE user_id=%s AND song_id=%s",
                                    (uid_l, sid_l)).empty:
                        errores.append(f"El usuario {uid_l} ya le dio like a la canción {sid_l}.")
            if errores:
                for e in errores:
                    st.error(e)
                return
            if tabla_seleccionada == "premium_subscribed":
                datos_nuevos = [(uid_p, subat, ptype, PRECIOS_PLANES[ptype]) for uid_p, subat, ptype in datos_nuevos]
            cx = None
            try:
                cx = conectar_db(); cur = cx.cursor()
                for item in datos_nuevos:
                    cur.execute(sql, item)
                if tabla_seleccionada == "premium_subscribed":
                    actualizar_tipo_cuenta(cur, {int(i[0]) for i in datos_nuevos})
                cx.commit(); cur.close(); cx.close()
                st.cache_data.clear()
                avisar(f"¡Se registraron {len(datos_nuevos)} registros en {tabla_seleccionada}!", "🎉")
                st.rerun()
            except Exception as e:
                if cx:
                    cx.rollback(); cx.close()
                st.error(f"Error al insertar en lote: {e}")

    # --- MODIFICACIONES ---
    elif opcion_gestion == "✏️ Modificar":
        editables = ["users", "songs", "playlist_created", "premium_subscribed"]
        if tabla_seleccionada not in editables:
            st.info("La modificación en lote está disponible para: " + ", ".join(editables) + ".")
            return
        ids_disponibles = obtener_ids(tabla_seleccionada, campo_pk)
        ids_sel = st.multiselect("Selecciona los IDs a modificar (máximo 5):", ids_disponibles, max_selections=5)
        if not ids_sel:
            st.caption("Selecciona al menos un ID para comenzar.")
            return
        st.caption("Deja un campo vacío para conservar su valor actual.")
        with st.form("form_mod_lote"):
            cambios = {}
            for idx in ids_sel:
                st.markdown(f"**Registro ID {idx}**")
                if tabla_seleccionada == "users":
                    cambios[idx] = st.text_input("Nuevo nombre", key=f"mod_u_{idx}")
                elif tabla_seleccionada == "songs":
                    c1, c2 = st.columns(2)
                    cambios[idx] = (c1.text_input("Nuevo título", key=f"mod_st_{idx}"),
                                    c2.text_input("Nuevo artista", key=f"mod_sa_{idx}"))
                elif tabla_seleccionada == "playlist_created":
                    cambios[idx] = st.text_input("Nuevo nombre de playlist", key=f"mod_pl_{idx}")
                elif tabla_seleccionada == "premium_subscribed":
                    cambios[idx] = st.selectbox("Nuevo plan", PLANES, key=f"mod_pr_{idx}")
            aplicar = st.form_submit_button("Aplicar cambios", type="primary")
        if aplicar:
            # Los textos vacíos no se guardan: NULLIF('', '') -> NULL y COALESCE conserva el valor actual
            def limpio(v):
                return tuple(x.strip() for x in v) if isinstance(v, tuple) else v.strip()
            cambios = {int(k): limpio(v) for k, v in cambios.items()}
            if all((not any(v) if isinstance(v, tuple) else not v) for v in cambios.values()):
                st.warning("No escribiste ningún cambio.")
                return
            cx = None
            try:
                cx = conectar_db(); cur = cx.cursor()
                for idx, val in cambios.items():
                    if tabla_seleccionada == "users":
                        cur.execute("UPDATE users SET username = COALESCE(NULLIF(%s, ''), username) WHERE user_id = %s;",
                                    (val, idx))
                    elif tabla_seleccionada == "songs":
                        cur.execute("""UPDATE songs SET title = COALESCE(NULLIF(%s, ''), title),
                                              artist = COALESCE(NULLIF(%s, ''), artist) WHERE song_id = %s;""",
                                    (val[0], val[1], idx))
                    elif tabla_seleccionada == "playlist_created":
                        cur.execute("""UPDATE playlist_created SET playlist_name = COALESCE(NULLIF(%s, ''), playlist_name)
                                       WHERE playlist_id = %s;""", (val, idx))
                    elif tabla_seleccionada == "premium_subscribed":
                        cur.execute("UPDATE premium_subscribed SET plan_type = %s, price_mxn = %s WHERE subscription_id = %s;",
                                    (val, PRECIOS_PLANES[val], idx))
                cx.commit(); cur.close(); cx.close()
                st.cache_data.clear()
                avisar(f"Se actualizaron {len(cambios)} registros", "✏️")
                st.rerun()
            except Exception as e:
                if cx:
                    cx.rollback(); cx.close()
                st.error(f"Error al modificar en lote: {e}")

    # --- BAJAS ---
    elif opcion_gestion == "🗑️ Bajas":
        ids_disponibles = obtener_ids(tabla_seleccionada, campo_pk)
        ids_borrar = st.multiselect("Selecciona los IDs a eliminar (máximo 5):", ids_disponibles, max_selections=5)
        if ids_borrar and st.button("Eliminar seleccionados", type="primary"):
            popup_confirmar_borrado(tabla_seleccionada, campo_pk, ids_borrar)


# =====================================================================
# PÁGINA: EN VIVO (lo que hacen los usuarios en la app «Mi Spotify»)
# =====================================================================
def consulta_vivo(sql, params=None):
    """Igual que consulta() pero SIN caché: esta página muestra datos al segundo."""
    cx = conectar_db()
    cur = cx.cursor(dictionary=True)
    cur.execute(sql, params or ())
    filas, columnas = cur.fetchall(), list(cur.column_names)
    cur.close(); cx.close()
    df = pd.DataFrame(filas, columns=columnas)
    for col in df.columns:
        if df[col].map(lambda x: isinstance(x, Decimal)).any():
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def pagina_en_vivo():
    st.markdown("""<div class="hero"><div class="logo">📺</div><div><div class="sub">ACTIVIDAD EN VIVO</div>
        <h1>En vivo</h1><div class="sub">Lo que hacen ahora los usuarios en la app «Mi Spotify» (puerto 8502)
        · se actualiza cada 5 segundos</div></div></div>""", unsafe_allow_html=True)
    guia("""
- Todo sale de la base real con la **fecha y hora de hoy**: registros, sesiones, reproducciones, saltos, anuncios y Premium.
- **En línea**: sesiones de la app web con actividad en los últimos 5 minutos.
- **CTR del modelo en vivo**: clics sobre las recomendaciones del grupo `L` (motor `aprendizaje.py`), que queda fuera de la prueba A/B.
- Lo que aprendió el modelo de cada usuario está en **🧠 Recomendaciones**.""")

    @st.fragment(run_every=5)
    def tablero():
        ahora_ = datetime.now().replace(microsecond=0)
        hoy = ahora_.replace(hour=0, minute=0, second=0)
        hace5 = ahora_ - timedelta(minutes=5)
        k = consulta_vivo("""
            SELECT (SELECT COUNT(*) FROM users WHERE signup_source='app_en_vivo') AS registrados,
                   (SELECT COUNT(*) FROM users WHERE signup_source='app_en_vivo' AND signup_date >= %s) AS registrados_hoy,
                   (SELECT COUNT(DISTINCT user_id) FROM app_sessions WHERE os='Web' AND ended_at >= %s) AS en_linea,
                   (SELECT COUNT(*) FROM song_played WHERE played_at >= %s) AS plays_hoy,
                   (SELECT ROUND(100*AVG(skipped),1) FROM song_played WHERE played_at >= %s) AS skip_hoy,
                   (SELECT COUNT(*) FROM recommendation_events WHERE ab_test_group='L') AS imp_l,
                   (SELECT IFNULL(SUM(clicked),0) FROM recommendation_events WHERE ab_test_group='L') AS clic_l,
                   (SELECT COUNT(*) FROM ad_events WHERE event_type='impression' AND event_at >= %s) AS ads_hoy,
                   (SELECT IFNULL(SUM(revenue_mxn),0) FROM ad_events WHERE event_at >= %s) AS ingreso_ads,
                   (SELECT COUNT(*) FROM subscription_events WHERE event_type='paywall_view' AND event_at >= %s) AS paywall_hoy,
                   (SELECT COUNT(*) FROM subscription_events WHERE event_type IN ('trial_started','purchase')
                       AND event_at >= %s) AS premium_hoy
        """, (hoy, hace5, hoy, hoy, hoy, hoy, hoy, hoy)).iloc[0]
        c = st.columns(6)
        kpi(c[0], "Registros app", f"{int(k.registrados)}", "📝", f"+{int(k.registrados_hoy)} hoy")
        kpi(c[1], "En línea", f"{int(k.en_linea)}", "🟢", "últimos 5 min")
        kpi(c[2], "Plays hoy", f"{int(k.plays_hoy)}", "▶️",
            f"{0 if pd.isna(k.skip_hoy) else k.skip_hoy}% saltadas")
        kpi(c[3], "CTR en vivo", f"{pct(k.clic_l, k.imp_l):.1f}%", "🧠", f"{int(k.imp_l)} impresiones")
        kpi(c[4], "Anuncios hoy", f"{int(k.ads_hoy)}", "📢", f"${float(k.ingreso_ads):.2f} MXN")
        kpi(c[5], "Premium hoy", f"{int(k.premium_hoy)}", "💎", f"{int(k.paywall_hoy)} vieron la oferta")

        st.markdown("#### 🟢 Usuarios en línea")
        enl = consulta_vivo("""
            SELECT u.username AS usuario, u.account_type AS plan, s.session_id AS sesion, s.started_at AS inicio,
                   s.duration_sec AS segundos, s.tracks_played AS canciones,
                   (SELECT CONCAT(so.title, ' · ', so.artist) FROM song_played p JOIN songs so USING(song_id)
                     WHERE p.session_id = s.session_id ORDER BY p.play_id DESC LIMIT 1) AS ultima_cancion
              FROM app_sessions s JOIN users u USING(user_id)
             WHERE s.os='Web' AND s.ended_at >= %s ORDER BY s.ended_at DESC""", (hace5,))
        if enl.empty:
            st.info("Nadie está usando «Mi Spotify» en este momento. Ábrela en http://localhost:8502.")
        else:
            st.dataframe(enl, hide_index=True, width="stretch")

        st.markdown("#### 📜 Eventos de hoy (más recientes primero)")
        ev = consulta_vivo("""
            SELECT t.event_at AS hora, u.username AS usuario, t.event_type AS evento, t.detalle
              FROM v_telemetria_unificada t JOIN users u USING(user_id)
             WHERE t.event_at >= %s ORDER BY t.event_at DESC LIMIT 80""", (hoy,))
        if ev.empty:
            st.caption("Todavía no hay eventos hoy.")
        else:
            st.dataframe(ev, hide_index=True, width="stretch", height=320)

    tablero()

    st.caption("Para ver qué aprendió el modelo de un usuario y qué se le recomienda, abre **🧠 Recomendaciones**.")


# =====================================================================
# ENRUTADOR
# =====================================================================
if pagina == "🏠 Inicio":
    pagina_inicio()
elif pagina == "📺 En vivo":
    pagina_en_vivo()
elif pagina == "📈 Marketing":
    pagina_marketing()
elif pagina == "🧠 Recomendaciones":
    pagina_recomendaciones()
elif pagina == "📡 Telemetría":
    pagina_telemetria()
else:
    pagina_base_datos()
