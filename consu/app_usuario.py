"""
Mi Spotify · la app vista desde el lado del USUARIO.

Te registras (o entras con una cuenta que ya existe), eliges canciones que te gustan y
empiezas a escuchar. Cada cosa que haces se guarda como telemetría en la base real
spotify_uadeo_db (sesión, reproducciones, skips, likes, búsquedas, impresiones de
recomendaciones) y el motor aprendizaje.py recalcula tus recomendaciones al instante
a partir de esas señales.

Abrir:  cd consu ; python -m streamlit run app_usuario.py --server.port 8502
"""
import html
import os
import random
import sys
import time
from datetime import datetime

import altair as alt
import mysql.connector
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aprendizaje  # noqa: E402

DB_NAME = os.environ.get("SPOTIFY_DB", "spotify_uadeo_db")
MYSQL_CONFIG = {'host': os.environ.get("MYSQL_HOST", "localhost"), 'user': os.environ.get("MYSQL_USER", "root"),
                'password': os.environ.get("MYSQL_PASSWORD", ""), 'database': DB_NAME}

# Cómo se identifica esta app en la telemetría
FUENTE_REGISTRO = "app_en_vivo"          # users.signup_source
DISPOSITIVO, SO, VERSION_APP = "web_player", "Web", "9.0.6.205"
SUPERFICIE, MODELO, GRUPO_AB = "Home - Hecho para ti", "live-v1", "L"   # grupo L = en vivo (fuera del A/B)
_T0 = time.time()

st.set_page_config(page_title="Mi Spotify", page_icon="🎵", layout="wide", initial_sidebar_state="expanded")

VERDE = "#1DB954"
st.markdown(f"""
<style>
  .stApp {{ background: linear-gradient(180deg, #1f2f4a 0%, #121212 360px); color:#fff; }}
  [data-testid="stSidebar"] {{ background:#000; }}
  [data-testid="stSidebar"] * {{ color:#b3b3b3; }}
  [data-testid="stHeader"] {{ background:transparent; }}
  h1, h2, h3, h4 {{ color:#fff !important; letter-spacing:-0.5px; }}
  p, label, .stMarkdown {{ color:#e5e5e5; }}
  .block-container {{ padding-top:1.6rem; }}
  .hola {{ font-size:2.2rem; font-weight:900; color:#fff; margin:0 0 4px; }}
  .sub {{ color:#b3b3b3; font-size:.95rem; margin-bottom:14px; }}
  .card {{ background:#181818; border-radius:10px; padding:12px; border:1px solid #232323;
           transition:background .2s, transform .2s; margin-bottom:6px; }}
  .card:hover {{ background:#282828; transform:translateY(-2px); }}
  .cover {{ aspect-ratio:1/1; border-radius:8px; display:flex; align-items:center; justify-content:center;
            font-size:2.4rem; margin-bottom:8px; box-shadow:0 6px 16px rgba(0,0,0,.5); position:relative; }}
  .mov {{ position:absolute; top:6px; right:6px; font-size:.7rem; font-weight:800; padding:2px 7px;
          border-radius:999px; background:rgba(0,0,0,.65); }}
  .card .t {{ color:#fff; font-weight:700; font-size:.92rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .card .a {{ color:#b3b3b3; font-size:.78rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .card .s {{ color:{VERDE}; font-size:.74rem; font-weight:700; margin-top:4px; }}
  .card .r {{ color:#9a9a9a; font-size:.7rem; margin-top:4px; height:2.2em; overflow:hidden; }}
  .player {{ display:flex; gap:18px; align-items:center; background:linear-gradient(90deg,#2a5d3f,#181818);
             border-radius:14px; padding:16px 20px; margin:6px 0 10px; }}
  .player .cv {{ width:76px; height:76px; border-radius:8px; display:flex; align-items:center; justify-content:center;
                 font-size:2rem; flex-shrink:0; }}
  .player .t {{ color:#fff; font-size:1.25rem; font-weight:800; }}
  .player .a {{ color:#d0d0d0; font-size:.9rem; }}
  .eq {{ display:inline-flex; gap:2px; align-items:flex-end; height:14px; margin-right:6px; }}
  .eq span {{ width:3px; background:{VERDE}; animation:eq 0.9s infinite ease-in-out; }}
  .eq span:nth-child(2) {{ animation-delay:.2s; }} .eq span:nth-child(3) {{ animation-delay:.4s; }}
  @keyframes eq {{ 0%,100% {{ height:3px; }} 50% {{ height:14px; }} }}
  .chip {{ display:inline-block; padding:3px 11px; border-radius:999px; background:#2a2a2a; color:#fff;
           font-size:.78rem; margin:2px 4px 2px 0; border:1px solid #3a3a3a; }}
  .chip.verde {{ background:{VERDE}; color:#000; border-color:{VERDE}; font-weight:700; }}
  .evt {{ font-family:ui-monospace,Consolas,monospace; font-size:.78rem; color:#cfcfcf; padding:3px 0;
          border-bottom:1px solid #222; }}
  .evt b {{ color:{VERDE}; }}
  .stButton > button, .stFormSubmitButton > button {{ border-radius:999px; font-weight:700; border:1px solid #535353;
                                                      background:transparent; color:#fff; }}
  .stButton > button:hover {{ border-color:#fff; color:#fff; }}
  .stButton > button {{ padding:0.25rem 0.35rem; min-width:0; }}
  [data-testid="stColumn"] {{ min-width:0; }}
  .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{ background:{VERDE};
                                                      color:#000; border:none; }}
  .stButton > button[kind="primary"]:hover {{ background:#1ed760; color:#000; }}
  .login {{ max-width:520px; margin:0 auto; }}
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


def ahora():
    return datetime.now().replace(microsecond=0)


# =====================================================================
# BASE DE DATOS (siempre la real: spotify_uadeo_db)
# =====================================================================
def conectar():
    return mysql.connector.connect(**MYSQL_CONFIG)


def leer(sql, params=()):
    cx = conectar()
    cur = cx.cursor(dictionary=True)
    cur.execute(sql, params)
    filas = cur.fetchall()
    cur.close(); cx.close()
    return filas


def escribir(sql, params=()):
    cx = conectar()
    cur = cx.cursor()
    cur.execute(sql, params)
    cx.commit()
    nuevo = cur.lastrowid
    cur.close(); cx.close()
    return nuevo


@st.cache_data(ttl=300, show_spinner=False)
def catalogo():
    filas = leer("SELECT song_id, title, artist, album, genre, duration_ms, popularity FROM songs ORDER BY popularity DESC")
    return {f['song_id']: f for f in filas}


def portada(song_id, genero, extra=""):
    return (f'<div class="cover" style="background:{GRADIENTES[int(song_id) % len(GRADIENTES)]}">'
            f'{ICONO_GENERO.get(genero, "🎵")}{extra}</div>')


def registrar(evento, detalle):
    """Bitácora visible de lo que esta sesión escribió en la base."""
    st.session_state.bitacora.insert(0, (ahora().strftime("%H:%M:%S"), evento, detalle))


# =====================================================================
# TELEMETRÍA
# =====================================================================
def tocar_sesion(t):
    """Extiende la sesión hasta t para que todos los eventos queden dentro de ella."""
    escribir("""UPDATE app_sessions SET ended_at=%s, duration_sec=TIMESTAMPDIFF(SECOND, started_at, %s)
                WHERE session_id=%s""", (t, t, st.session_state.sid))


def evento_ui(screen, action, element):
    t = ahora()
    tocar_sesion(t)
    escribir("INSERT INTO ui_events (user_id, session_id, screen, action, element, event_at) VALUES (%s,%s,%s,%s,%s,%s)",
             (st.session_state.uid, st.session_state.sid, screen, action, element, t))
    registrar("ui_events", f"{screen} › {action} › {element}")


def abrir_sesion(user):
    t = ahora()
    st.session_state.uid = int(user['user_id'])
    st.session_state.usuario = user
    st.session_state.sid = escribir("""
        INSERT INTO app_sessions (user_id, device_type, os, app_version, network_type, city, started_at, ended_at,
                                  duration_sec, tracks_played)
        VALUES (%s,%s,%s,%s,'wifi',%s,%s,%s,0,0)""", (st.session_state.uid, DISPOSITIVO, SO, VERSION_APP,
                                                        user.get('city'), t, t))
    escribir("""INSERT INTO app_performance_events (user_id, session_id, event_type, latency_ms, network_type,
                app_version, event_at) VALUES (%s,%s,'app_startup',%s,'wifi',%s,%s)""",
             (st.session_state.uid, st.session_state.sid, int((time.time() - _T0) * 1000) % 4000 + 300,
              VERSION_APP, t))
    registrar("app_sessions", f"sesión #{st.session_state.sid} abierta ({DISPOSITIVO})")
    evento_ui("home", "screen_view", "app_open")


def cerrar_sesion():
    tocar_sesion(ahora())
    registrar("app_sessions", f"sesión #{st.session_state.sid} cerrada")
    for k in list(st.session_state.keys()):
        del st.session_state[k]


def refrescar_recs(motivo):
    """Reaprende con toda la telemetría del usuario, guarda las recomendaciones y registra las impresiones."""
    uid, t = st.session_state.uid, ahora()
    cx = conectar()
    res = aprendizaje.guardar(cx, uid, top_n=10, ahora=t)
    cx.close()
    antes = {r['song_id']: i for i, r in enumerate(st.session_state.recs)}
    tocar_sesion(t)
    impresiones = {}
    for i, r in enumerate(res['recs'], start=1):
        impresiones[r['song_id']] = escribir("""
            INSERT INTO recommendation_events (user_id, session_id, song_id, surface, algorithm, model_version,
                ab_test_group, position_in_list, relevance_score, reason_shown, shown_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (uid, st.session_state.sid, r['song_id'], SUPERFICIE, aprendizaje.ALGORITMO, MODELO, GRUPO_AB, i,
             r['score'], r['reason'][:150], t))
        r['movimiento'] = None if r['song_id'] not in antes else antes[r['song_id']] - (i - 1)
    st.session_state.recs = res['recs']
    st.session_state.impresiones = impresiones
    st.session_state.perfil = res
    st.session_state.evolucion.append({'paso': len(st.session_state.evolucion), 'motivo': motivo,
                                       **{g: v for g, v in res['generos'].items()}})
    registrar("recommendation_events", f"{len(impresiones)} impresiones · modelo reentrenado ({motivo})")


def reproducir(song_id, origen, detalle, rec_event_id=None, busqueda=None):
    st.session_state.sonando = {'song_id': song_id, 'origen': origen, 'detalle': detalle,
                                'rec_event_id': rec_event_id, 'inicio': time.time()}
    if rec_event_id:
        escribir("UPDATE recommendation_events SET clicked=1 WHERE rec_event_id=%s", (rec_event_id,))
    if busqueda:
        sid_busq, pos, t0 = busqueda
        escribir("""UPDATE search_events SET clicked_song_id=%s, click_position=%s, time_to_click_ms=%s
                    WHERE search_id=%s""", (song_id, pos, int((time.time() - t0) * 1000), sid_busq))
        registrar("search_events", f"clic en resultado #{pos}")
    evento_ui("now_playing", "click", f"play_{origen}")


def terminar(completa):
    """Cierra la reproducción actual: completa (trackdone) o saltada (fwdbtn)."""
    s = st.session_state.sonando
    cancion = catalogo()[s['song_id']]
    dur = int(cancion['duration_ms'] or 180000)
    ms = dur if completa else random.randint(6000, 28000)   # un skip ocurre antes de 30 s
    t = ahora()
    tocar_sesion(t)
    escribir("""INSERT INTO song_played (user_id, song_id, played_at, session_id, ms_played, source, source_detail,
                reason_start, reason_end, skipped, device_type, audio_quality)
                VALUES (%s,%s,%s,%s,%s,%s,%s,'clickrow',%s,%s,%s,'normal')""",
             (st.session_state.uid, s['song_id'], t, st.session_state.sid, ms, s['origen'], s['detalle'][:150],
              'trackdone' if completa else 'fwdbtn', 0 if completa else 1, DISPOSITIVO))
    escribir("UPDATE app_sessions SET tracks_played = tracks_played + 1 WHERE session_id=%s", (st.session_state.sid,))
    if s['rec_event_id']:
        escribir("""UPDATE recommendation_events SET played=1, ms_played=%s, completed=%s, skipped=%s
                    WHERE rec_event_id=%s""", (ms, int(completa), int(not completa), s['rec_event_id']))
    registrar("song_played", f"«{cancion['title']}» {'completa' if completa else f'saltada a los {ms//1000}s'}")
    st.session_state.sonando = None
    refrescar_recs(("escuchó " if completa else "saltó ") + cancion['title'])


def me_gusta(song_id, origen, rec_event_id=None):
    t = ahora()
    tocar_sesion(t)
    nuevo = escribir("""INSERT INTO song_liked (user_id, song_id, liked_at, source)
                        SELECT %s,%s,%s,%s FROM DUAL
                         WHERE NOT EXISTS (SELECT 1 FROM song_liked WHERE user_id=%s AND song_id=%s)""",
                     (st.session_state.uid, song_id, t, origen, st.session_state.uid, song_id))
    if rec_event_id:   # "guardada" solo cuenta si ya se reprodujo (regla de la auditoría)
        escribir("UPDATE recommendation_events SET clicked=1, saved=played WHERE rec_event_id=%s", (rec_event_id,))
    titulo = catalogo()[song_id]['title']
    registrar("song_liked", f"❤ «{titulo}»" if nuevo else f"«{titulo}» ya estaba en Tus me gusta")
    refrescar_recs("le gustó " + titulo)


def no_me_interesa(song_id, rec_event_id):
    escribir("UPDATE recommendation_events SET dismissed=1 WHERE rec_event_id=%s", (rec_event_id,))
    evento_ui("home", "click", "btn_not_interested")
    refrescar_recs("descartó " + catalogo()[song_id]['title'])


def seguir_artista(artista, origen):
    t = ahora()
    tocar_sesion(t)
    escribir("""INSERT INTO artist_follows (user_id, artist, followed_at, source)
                SELECT %s,%s,%s,%s FROM DUAL
                 WHERE NOT EXISTS (SELECT 1 FROM artist_follows WHERE user_id=%s AND artist=%s)""",
             (st.session_state.uid, artista, t, origen, st.session_state.uid, artista))
    registrar("artist_follows", f"sigue a {artista}")


# =====================================================================
# ESTADO
# =====================================================================
for k, v in {'uid': None, 'sid': None, 'usuario': None, 'paso': 'entrar', 'recs': [], 'impresiones': {},
             'perfil': None, 'sonando': None, 'evolucion': [], 'bitacora': [], 'busqueda': None}.items():
    st.session_state.setdefault(k, v)

try:
    conectar().close()
except Exception as e:
    st.error(f"No se pudo conectar a MySQL (base `{DB_NAME}`). Enciende MySQL en XAMPP y, si la base no existe, "
             f"corre `python \"base de datos.py\"`.\n\n{e}")
    st.stop()


def tiene_historial(uid):
    f = leer("""SELECT (SELECT COUNT(*) FROM song_played WHERE user_id=%s) +
                       (SELECT COUNT(*) FROM song_liked WHERE user_id=%s) AS n""", (uid, uid))
    return f[0]['n'] > 0


# =====================================================================
# PANTALLA 1: REGISTRO / INICIO DE SESIÓN
# =====================================================================
def pantalla_entrar():
    st.markdown(f"""<div style="text-align:center;margin:10px 0 18px">
        <div style="width:72px;height:72px;border-radius:50%;background:{VERDE};display:inline-flex;align-items:center;
        justify-content:center;font-size:38px">🎵</div>
        <div class="hola" style="margin-top:10px">Millones de canciones. Gratis.</div>
        <div class="sub">Crea tu cuenta y te recomendamos música que aprende de lo que escuchas.</div></div>""",
                unsafe_allow_html=True)
    _, centro, _ = st.columns([1, 2, 1])
    with centro:
        tab_reg, tab_ent = st.tabs(["📝 Crear cuenta", "🔑 Ya tengo cuenta"])
        with tab_reg:
            with st.form("registro"):
                nombre = st.text_input("¿Cómo te llamas?", placeholder="Nombre y apellido")
                email = st.text_input("Correo electrónico", placeholder="tucorreo@ejemplo.com")
                c1, c2 = st.columns(2)
                anio = c1.number_input("Año de nacimiento", 1940, datetime.now().year - 13, 2003)
                genero = c2.selectbox("Género", ["Femenino", "Masculino", "No binario", "No especificado"])
                c3, c4 = st.columns(2)
                ciudad = c3.text_input("Ciudad", "Los Mochis")
                estado = c4.text_input("Estado", "Sinaloa")
                acepto = st.checkbox("Acepto los términos y la política de privacidad (proyecto escolar)")
                enviar = st.form_submit_button("Registrarme", type="primary", width="stretch")
            if enviar:
                nombre, email = nombre.strip(), email.strip().lower()
                if not nombre or "@" not in email or "." not in email.split("@")[-1]:
                    st.error("Escribe tu nombre y un correo válido.")
                elif not acepto:
                    st.error("Debes aceptar los términos para continuar.")
                elif leer("SELECT 1 FROM users WHERE email=%s OR username=%s", (email, nombre)):
                    st.error("Ya existe una cuenta con ese nombre o correo. Entra en «Ya tengo cuenta».")
                else:
                    uid = escribir("""INSERT INTO users (username, signup_date, email, birth_year, gender, country, city,
                                      state, signup_source, signup_platform, account_type)
                                      VALUES (%s,%s,%s,%s,%s,'MX',%s,%s,%s,'Web','free')""",
                                   (nombre, ahora(), email, int(anio), genero, ciudad.strip() or None,
                                    estado.strip() or None, FUENTE_REGISTRO))
                    user = leer("SELECT * FROM users WHERE user_id=%s", (uid,))[0]
                    abrir_sesion(user)
                    registrar("users", f"nueva cuenta #{uid} ({FUENTE_REGISTRO})")
                    evento_ui("onboarding", "screen_view", "pick_songs")
                    st.session_state.paso = 'onboarding'
                    st.rerun()
        with tab_ent:
            with st.form("entrar"):
                quien = st.text_input("Correo o nombre de usuario")
                entrar = st.form_submit_button("Entrar", type="primary", width="stretch")
            if entrar:
                f = leer("SELECT * FROM users WHERE email=%s OR username=%s LIMIT 1", (quien.strip().lower(), quien.strip()))
                if not f:
                    st.error("No encontramos esa cuenta.")
                else:
                    abrir_sesion(f[0])
                    if tiene_historial(st.session_state.uid):
                        st.session_state.paso = 'app'
                        refrescar_recs("inicio de sesión")
                    else:
                        evento_ui("onboarding", "screen_view", "pick_songs")
                        st.session_state.paso = 'onboarding'
                    st.rerun()
            demo = leer("SELECT username FROM users ORDER BY user_id LIMIT 3")
            st.caption("Cuentas de ejemplo: " + ", ".join(f"`{d['username']}`" for d in demo))


# =====================================================================
# PANTALLA 2: ONBOARDING (elige canciones)
# =====================================================================
def pantalla_onboarding():
    nombre = (st.session_state.usuario['username'].split() or ["👋"])[0]
    st.markdown(f'<div class="hola">¡Bienvenido, {esc(nombre)}! 🎉</div>'
                '<div class="sub">Elige al menos <b>3 canciones</b> que te gusten. Con eso arrancamos tus '
                'recomendaciones; después aprenderán de todo lo que escuches, saltes o guardes.</div>',
                unsafe_allow_html=True)
    cat = catalogo()
    generos = sorted({c['genre'] for c in cat.values() if c['genre']})
    filtro = st.pills("Filtra por género", generos, selection_mode="multi", key="pills_genero")
    visibles = [c for c in cat.values() if not filtro or c['genre'] in filtro]
    st.session_state.setdefault('elegidas', set())
    cols = st.columns(6)
    for i, c in enumerate(visibles):
        with cols[i % 6]:
            marcada = c['song_id'] in st.session_state.elegidas
            st.markdown(f'<div class="card">{portada(c["song_id"], c["genre"], "<span class=mov>✓</span>" if marcada else "")}'
                        f'<div class="t">{esc(c["title"])}</div><div class="a">{esc(c["artist"])}</div></div>',
                        unsafe_allow_html=True)
            if st.button("✓ Elegida" if marcada else "Elegir", key=f"pick_{c['song_id']}", width="stretch",
                         type="primary" if marcada else "secondary"):
                st.session_state.elegidas ^= {c['song_id']}
                st.rerun()
    n = len(st.session_state.elegidas)
    st.markdown("---")
    c1, c2 = st.columns([3, 1])
    c1.markdown(f"**{n}** elegida(s). " + ("¡Listo para empezar!" if n >= 3 else f"Te faltan {3 - n}."))
    if c2.button("Empezar a escuchar ▶", type="primary", disabled=n < 3, width="stretch"):
        for sid in st.session_state.elegidas:
            me = cat[sid]
            t = ahora()
            tocar_sesion(t)
            escribir("""INSERT INTO song_liked (user_id, song_id, liked_at, source) SELECT %s,%s,%s,'onboarding'
                        FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM song_liked WHERE user_id=%s AND song_id=%s)""",
                     (st.session_state.uid, sid, t, st.session_state.uid, sid))
            escribir("""INSERT INTO ui_events (user_id, session_id, screen, action, element, event_at)
                        VALUES (%s,%s,'onboarding','click','pick_song',%s)""", (st.session_state.uid, st.session_state.sid, t))
            for a in [x.strip() for x in me['artist'].split(',')][:1]:
                seguir_artista(a, 'onboarding')
        registrar("song_liked", f"{n} canciones elegidas en el onboarding")
        del st.session_state['elegidas']
        st.session_state.paso = 'app'
        refrescar_recs("onboarding")
        st.rerun()


# =====================================================================
# PANTALLA 3: LA APP
# =====================================================================
def reproductor():
    s = st.session_state.sonando
    if not s:
        return
    c = catalogo()[s['song_id']]
    st.markdown(f"""<div class="player"><div class="cv" style="background:{GRADIENTES[c['song_id'] % 8]}">
        {ICONO_GENERO.get(c['genre'], '🎵')}</div><div style="flex:1"><div style="font-size:.75rem;color:#fff">
        <span class="eq"><span></span><span></span><span></span></span>SONANDO AHORA · {esc(s['detalle'])}</div>
        <div class="t">{esc(c['title'])}</div><div class="a">{esc(c['artist'])} · {esc(c['genre'])}</div></div></div>""",
                unsafe_allow_html=True)
    b1, b2, b3, _ = st.columns([1.3, 1, 1, 2])
    if b1.button("✅ Escuchar completa", type="primary", width="stretch", key="fin_ok"):
        terminar(True); st.rerun()
    if b2.button("⏭ Saltar", width="stretch", key="fin_skip"):
        terminar(False); st.rerun()
    if b3.button("❤ Me gusta", width="stretch", key="np_like"):
        me_gusta(s['song_id'], 'now_playing', s['rec_event_id']); st.rerun()


def pagina_inicio():
    nombre = (st.session_state.usuario['username'].split() or [""])[0]
    hora = datetime.now().hour
    saludo = "Buenos días" if hora < 12 else "Buenas tardes" if hora < 19 else "Buenas noches"
    st.markdown(f'<div class="hola">{saludo}, {esc(nombre)}</div>', unsafe_allow_html=True)
    reproductor()
    ultimo = st.session_state.evolucion[-1]['motivo'] if st.session_state.evolucion else ""
    st.markdown(f"### Hecho para ti")
    st.caption(f"🧠 Se reentrena con cada cosa que haces · último aprendizaje: **{esc(ultimo)}**. "
               "Las flechas muestran cuántos lugares subió o bajó cada canción.")
    cat = catalogo()
    recs = st.session_state.recs
    for fila in range(0, len(recs), 5):
        cols = st.columns(5)
        for col, (i, r) in zip(cols, enumerate(recs[fila:fila + 5], start=fila)):
            c = cat.get(r['song_id'])
            if not c:
                continue
            m = r.get('movimiento')
            badge = ('<span class="mov" style="color:#1ed760">NUEVA</span>' if m is None and len(st.session_state.evolucion) > 1
                     else f'<span class="mov" style="color:#1ed760">▲{m}</span>' if m and m > 0
                     else f'<span class="mov" style="color:#ff6b6b">▼{-m}</span>' if m and m < 0 else "")
            ev = st.session_state.impresiones.get(r['song_id'])
            with col:
                st.markdown(f"""<div class="card">{portada(c['song_id'], c['genre'], badge)}
                    <div class="t">{esc(c['title'])}</div><div class="a">{esc(c['artist'])}</div>
                    <div class="s">{r['score']*100:.0f}% match</div><div class="r">{esc(r['reason'])}</div></div>""",
                            unsafe_allow_html=True)
                if st.button("▶ Escuchar", key=f"p_{i}", type="primary", width="stretch"):
                    reproducir(c['song_id'], 'recommendation', SUPERFICIE, ev); st.rerun()
                b2, b3 = st.columns(2, gap="small")
                if b2.button("❤", key=f"l_{i}", help="Me gusta", width="stretch"):
                    me_gusta(c['song_id'], 'recommendation', ev); st.rerun()
                if b3.button("✕", key=f"d_{i}", help="No me interesa", width="stretch"):
                    no_me_interesa(c['song_id'], ev); st.rerun()


def pagina_buscar():
    st.markdown('<div class="hola">Buscar</div>', unsafe_allow_html=True)
    reproductor()
    with st.form("buscar", border=False):
        c1, c2 = st.columns([5, 1])
        q = c1.text_input("¿Qué quieres escuchar?", placeholder="Canción, artista o género", label_visibility="collapsed")
        ir = c2.form_submit_button("🔎 Buscar", type="primary", width="stretch")
    if ir and q.strip():
        texto = q.strip()
        res = leer("""SELECT song_id FROM songs WHERE title LIKE %s OR artist LIKE %s OR genre LIKE %s OR album LIKE %s
                      ORDER BY popularity DESC LIMIT 12""", tuple([f"%{texto}%"] * 4))
        t = ahora()
        tocar_sesion(t)
        search_id = escribir("""INSERT INTO search_events (user_id, session_id, query_text, search_type, results_count,
                                searched_at) VALUES (%s,%s,%s,'track',%s,%s)""",
                             (st.session_state.uid, st.session_state.sid, texto[:150], len(res), t))
        registrar("search_events", f"buscó \"{texto}\" ({len(res)} resultados)")
        st.session_state.busqueda = {'id': search_id, 't0': time.time(), 'texto': texto,
                                     'ids': [r['song_id'] for r in res], 'clic': False}
    b = st.session_state.busqueda
    if not b:
        st.caption("Busca algo: cuando haces clic en un resultado también se guarda como señal para tus recomendaciones.")
        return
    if not b['ids']:
        st.info(f"Sin resultados para «{b['texto']}».")
        return
    cat = catalogo()
    st.caption(f"Resultados para «{b['texto']}»")
    for pos, sid in enumerate(b['ids'], start=1):
        c = cat[sid]
        c1, c2, c3, c4 = st.columns([0.4, 5, 1, 1.3])
        c1.markdown(f"<div style='font-size:1.6rem'>{ICONO_GENERO.get(c['genre'], '🎵')}</div>", unsafe_allow_html=True)
        c2.markdown(f"**{esc(c['title'])}**  \n<span style='color:#b3b3b3'>{esc(c['artist'])} · {esc(c['genre'])}</span>",
                    unsafe_allow_html=True)
        if c3.button("▶", key=f"bs_{sid}", width="stretch"):
            busq = None if b['clic'] else (b['id'], pos, b['t0'])
            b['clic'] = True
            reproducir(sid, 'search', f"Búsqueda: {b['texto']}", busqueda=busq); st.rerun()
        if c4.button("➕ Seguir", key=f"fa_{sid}", help="Seguir al artista", width="stretch"):
            seguir_artista(c['artist'].split(',')[0].strip(), 'search')
            refrescar_recs("sigue a " + c['artist'].split(',')[0].strip()); st.rerun()


def pagina_biblioteca():
    st.markdown('<div class="hola">Tu biblioteca</div>', unsafe_allow_html=True)
    reproductor()
    uid = st.session_state.uid
    t1, t2 = st.tabs(["💚 Tus me gusta", "🕒 Escuchado recientemente"])
    with t1:
        likes = leer("""SELECT s.song_id, s.title, s.artist, s.genre, l.liked_at, l.source FROM song_liked l
                        JOIN songs s USING(song_id) WHERE l.user_id=%s ORDER BY l.liked_at DESC""", (uid,))
        if not likes:
            st.info("Aún no tienes canciones guardadas.")
        for i, l in enumerate(likes):
            c1, c2, c3 = st.columns([5, 2, 1])
            c1.markdown(f"**{esc(l['title'])}** · <span style='color:#b3b3b3'>{esc(l['artist'])}</span>",
                        unsafe_allow_html=True)
            c2.caption(f"{l['genre']} · {l['source']}")
            if c3.button("▶", key=f"lk_{i}", width="stretch"):
                reproducir(l['song_id'], 'liked_songs', 'Tus me gusta'); st.rerun()
    with t2:
        hist = leer("""SELECT s.title, s.artist, p.played_at, p.ms_played, p.skipped, p.source FROM song_played p
                       JOIN songs s USING(song_id) WHERE p.user_id=%s ORDER BY p.played_at DESC LIMIT 30""", (uid,))
        if hist:
            df = pd.DataFrame(hist)
            df["escuchado"] = (df.ms_played.fillna(0) / 1000).round().astype(int).astype(str) + " s"
            df["skip"] = df.skipped.map({1: "⏭ sí", 0: ""})
            st.dataframe(df[["played_at", "title", "artist", "source", "escuchado", "skip"]], hide_index=True,
                         width="stretch")
        else:
            st.info("Todavía no escuchas nada.")


def pagina_aprendizaje():
    st.markdown('<div class="hola">🧠 Lo que aprendimos de ti</div>'
                '<div class="sub">Así ve el recomendador tu gusto ahora mismo, calculado con la telemetría guardada '
                'en la base de datos.</div>', unsafe_allow_html=True)
    p = st.session_state.perfil
    if not p:
        st.info("Aún no hay datos.")
        return
    s = p['senales']
    cols = st.columns(5)
    for col, (lbl, k, ico) in zip(cols, [("Reproducciones", 'reproducciones', "▶️"), ("Skips", 'skips', "⏭"),
                                         ("Me gusta", 'me_gusta', "💚"), ("Descartadas", 'descartadas', "✕"),
                                         ("Clics en búsqueda", 'busquedas', "🔎")]):
        col.metric(f"{ico} {lbl}", s.get(k, 0))

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Afinidad por género")
        if p['generos']:
            df = pd.DataFrame({'genero': list(p['generos']), 'afinidad': list(p['generos'].values())})
            ch = alt.Chart(df).mark_bar(cornerRadius=4).encode(
                x=alt.X('afinidad:Q', scale=alt.Scale(domain=[-1, 1]), title="← no te gusta · te gusta →"),
                y=alt.Y('genero:N', sort='-x', title=None),
                color=alt.condition(alt.datum.afinidad >= 0, alt.value(VERDE), alt.value("#e05555")),
                tooltip=['genero', alt.Tooltip('afinidad:Q', format='.2f')]).properties(height=300)
            st.altair_chart(ch, width="stretch")
    with c2:
        st.markdown("##### Artistas que más pesan")
        top = list(p['artistas'].items())[:10]
        if top:
            df = pd.DataFrame(top, columns=['artista', 'afinidad'])
            ch = alt.Chart(df).mark_bar(cornerRadius=4).encode(
                x=alt.X('afinidad:Q', scale=alt.Scale(domain=[-1, 1]), title=None),
                y=alt.Y('artista:N', sort='-x', title=None),
                color=alt.condition(alt.datum.afinidad >= 0, alt.value(VERDE), alt.value("#e05555")),
                tooltip=['artista', alt.Tooltip('afinidad:Q', format='.2f')]).properties(height=300)
            st.altair_chart(ch, width="stretch")

    ev = st.session_state.evolucion
    if len(ev) > 1:
        st.markdown("##### Cómo cambió tu perfil en esta sesión")
        df = pd.DataFrame(ev).fillna(0)
        largo = df.melt(id_vars=['paso', 'motivo'], var_name='genero', value_name='afinidad')
        principales = largo.groupby('genero').afinidad.apply(lambda x: x.abs().max()).nlargest(6).index
        largo = largo[largo.genero.isin(principales)]
        ch = alt.Chart(largo).mark_line(point=True).encode(
            x=alt.X('paso:O', title="interacción"), y=alt.Y('afinidad:Q', scale=alt.Scale(domain=[-1, 1])),
            color=alt.Color('genero:N', title=None), tooltip=['motivo', 'genero', alt.Tooltip('afinidad:Q', format='.2f')]
        ).properties(height=280)
        st.altair_chart(ch, width="stretch")
    with st.expander("ℹ️ ¿Cómo aprende?"):
        st.markdown("""
Cada evento se convierte en una señal con signo para la canción, su género y su artista:
**escuchar completa** +1 · **saltar** −0.6 · **me gusta** +3 · **no me interesa** −2.5 ·
**clic en búsqueda** +0.5 · **seguir artista** +2. Lo reciente pesa más (vida media de 14 días).
Luego: `score = 0.45·género + 0.25·artista + 0.20·sonido parecido + 0.10·popularidad`.
Las canciones que te gustan o que descartaste no se vuelven a recomendar.""")


def pagina_telemetria():
    st.markdown('<div class="hola">📡 Tu telemetría</div>'
                '<div class="sub">Cada fila es un registro real en <code>spotify_uadeo_db</code>.</div>',
                unsafe_allow_html=True)
    uid, sid = st.session_state.uid, st.session_state.sid
    ses = leer("SELECT started_at, ended_at, duration_sec, tracks_played FROM app_sessions WHERE session_id=%s", (sid,))[0]
    c = st.columns(4)
    c[0].metric("Sesión", f"#{sid}")
    c[1].metric("Duración", f"{ses['duration_sec'] // 60} min {ses['duration_sec'] % 60} s")
    c[2].metric("Canciones en la sesión", ses['tracks_played'])
    ctr = leer("""SELECT COUNT(*) n, IFNULL(SUM(clicked),0) c FROM recommendation_events WHERE session_id=%s""", (sid,))[0]
    c[3].metric("CTR de tus recomendaciones", f"{(100 * ctr['c'] / ctr['n']) if ctr['n'] else 0:.1f}%",
                help=f"{ctr['c']} clics de {ctr['n']} impresiones en esta sesión")
    t1, t2 = st.tabs(["📝 Lo que escribió esta sesión", "🕒 Línea de tiempo en la base"])
    with t1:
        if not st.session_state.bitacora:
            st.caption("Todavía nada.")
        st.markdown("".join(f'<div class="evt">{h} · <b>{esc(tabla)}</b> · {esc(d)}</div>'
                            for h, tabla, d in st.session_state.bitacora[:80]), unsafe_allow_html=True)
    with t2:
        filas = leer("""SELECT event_at, event_type, detalle FROM v_telemetria_unificada WHERE user_id=%s
                        ORDER BY event_at DESC LIMIT 200""", (uid,))
        st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch")


def app_principal():
    u = st.session_state.usuario
    with st.sidebar:
        inicial = (u['username'][:1] or "?").upper()
        st.markdown(f"""<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
            <div style="width:42px;height:42px;border-radius:50%;background:{VERDE};display:flex;align-items:center;
            justify-content:center;font-weight:900;color:#000;font-size:1.2rem">{esc(inicial)}</div>
            <div><div style="color:#fff;font-weight:800">{esc(u['username'])}</div>
            <div style="font-size:.75rem">{esc(u.get('account_type') or 'free').capitalize()} · sesión #{st.session_state.sid}</div>
            </div></div>""", unsafe_allow_html=True)
        pagina = st.radio("Menú", ["🏠 Inicio", "🔎 Buscar", "📚 Tu biblioteca", "🧠 Lo que aprendimos", "📡 Tu telemetría"],
                          label_visibility="collapsed", key="menu")
        if st.session_state.get('_ultima_pagina') != pagina:
            st.session_state._ultima_pagina = pagina
            evento_ui({"🏠 Inicio": "home", "🔎 Buscar": "search", "📚 Tu biblioteca": "your_library",
                       "🧠 Lo que aprendimos": "profile", "📡 Tu telemetría": "settings"}[pagina], "screen_view", "nav")
        st.markdown("---")
        if st.button("🔄 Reentrenar ahora", width="stretch"):
            refrescar_recs("manual"); st.rerun()
        if st.button("Cerrar sesión", width="stretch"):
            cerrar_sesion(); st.rerun()
        st.caption(f"🗄️ Base `{DB_NAME}` (datos reales)")
    {"🏠 Inicio": pagina_inicio, "🔎 Buscar": pagina_buscar, "📚 Tu biblioteca": pagina_biblioteca,
     "🧠 Lo que aprendimos": pagina_aprendizaje, "📡 Tu telemetría": pagina_telemetria}[pagina]()


if st.session_state.paso == 'entrar' or not st.session_state.uid:
    pantalla_entrar()
elif st.session_state.paso == 'onboarding':
    pantalla_onboarding()
else:
    app_principal()
