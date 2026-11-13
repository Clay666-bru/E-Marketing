"""
Mi Spotify · la app desde el lado del USUARIO, con el comportamiento de Spotify.

- Registro o inicio de sesión y onboarding eligiendo artistas.
- Reproductor fijo abajo con tiempo real: pausa, siguiente, anterior, aleatorio, repetir y
  reproducción automática (Autoplay) cuando se acaba la cola.
- Cuenta Free: anuncio cada 3 canciones y máximo 6 saltos por hora; si se pasa, aparece la
  oferta de Premium. Premium: sin anuncios, saltos ilimitados y descargas.
- Playlists, Tus me gusta, página de artista (seguir), Daily Mix, búsqueda y compartir.

Cada acción se guarda como telemetría en la base real spotify_uadeo_db y el motor
aprendizaje.py reentrena las recomendaciones con esas señales. El panel de administrador
(app_spotify.py) ve todo en su página «📺 En vivo».

Abrir:  python -m streamlit run consu/app_usuario.py --server.port 8502
"""
import html
import os
import random
import sys
import time
from datetime import datetime, timedelta

import mysql.connector
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

# Reglas de Spotify Free / Premium (mismos valores que la simulación de "base de datos.py")
PLANES = {'Individual Premium': 139.0, 'Dúo Premium': 179.0, 'Familiar Premium': 219.0, 'Estudiantil Premium': 75.0}
ANUNCIANTES = [('AD-1001', 'Coca-Cola México', 'audio'), ('AD-1002', 'Mercado Libre', 'video'),
               ('AD-1003', 'Telcel', 'audio'), ('AD-1004', 'OXXO', 'banner'),
               ('AD-1005', 'Spotify Premium (auto-promo)', 'audio'), ('AD-1006', 'Bimbo', 'video'),
               ('AD-1007', 'Liverpool', 'banner'), ('AD-1008', 'Didi Food', 'audio')]
CANCIONES_POR_ANUNCIO = 3
LIMITE_SALTOS_HORA = 6
DURACION_ANUNCIO_MS = 15000
UMBRAL_SKIP_MS = 30000       # antes de 30 s una canción terminada a mano cuenta como skip
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
  .block-container {{ padding-top:1.4rem; padding-bottom:150px; }}
  .hola {{ font-size:2.1rem; font-weight:900; color:#fff; margin:0 0 6px; }}
  .sub {{ color:#b3b3b3; font-size:.92rem; margin-bottom:12px; }}
  .seccion {{ font-size:1.35rem; font-weight:800; color:#fff; margin:18px 0 6px; }}
  .card {{ background:#181818; border-radius:10px; padding:12px; border:1px solid #232323;
           transition:background .2s, transform .2s; margin-bottom:6px; }}
  .card:hover {{ background:#282828; transform:translateY(-2px); }}
  .cover {{ aspect-ratio:1/1; border-radius:8px; display:flex; align-items:center; justify-content:center;
            font-size:2.4rem; margin-bottom:8px; box-shadow:0 6px 16px rgba(0,0,0,.5); position:relative; }}
  .cover.redonda {{ border-radius:50%; }}
  .mov {{ position:absolute; top:6px; right:6px; font-size:.7rem; font-weight:800; padding:2px 7px;
          border-radius:999px; background:rgba(0,0,0,.65); }}
  .card .t {{ color:#fff; font-weight:700; font-size:.92rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .card .a {{ color:#b3b3b3; font-size:.78rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .card .s {{ color:{VERDE}; font-size:.74rem; font-weight:700; margin-top:4px; }}
  .card .r {{ color:#9a9a9a; font-size:.7rem; margin-top:4px; height:2.2em; overflow:hidden; }}
  .cab {{ display:flex; gap:22px; align-items:flex-end; border-radius:14px; padding:22px; margin-bottom:12px; }}
  .cab .cv {{ width:150px; height:150px; border-radius:8px; display:flex; align-items:center; justify-content:center;
              font-size:4rem; box-shadow:0 8px 24px rgba(0,0,0,.6); flex-shrink:0; }}
  .cab .tipo {{ font-size:.75rem; text-transform:uppercase; letter-spacing:1px; color:#fff; }}
  .cab .nombre {{ font-size:2.6rem; font-weight:900; color:#fff; line-height:1.1; }}
  .cab .meta {{ color:#d0d0d0; font-size:.88rem; margin-top:6px; }}
  .fila-t {{ color:#fff; font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .fila-t.on {{ color:{VERDE}; }}
  .fila-a {{ color:#b3b3b3; font-size:.8rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .eq {{ display:inline-flex; gap:2px; align-items:flex-end; height:14px; margin-right:6px; }}
  .eq span {{ width:3px; background:{VERDE}; animation:eq 0.9s infinite ease-in-out; }}
  .eq span:nth-child(2) {{ animation-delay:.2s; }} .eq span:nth-child(3) {{ animation-delay:.4s; }}
  @keyframes eq {{ 0%,100% {{ height:3px; }} 50% {{ height:14px; }} }}
  .chip {{ display:inline-block; padding:3px 11px; border-radius:999px; background:#2a2a2a; color:#fff;
           font-size:.78rem; margin:2px 4px 2px 0; border:1px solid #3a3a3a; }}
  .chip.verde {{ background:{VERDE}; color:#000; border-color:{VERDE}; font-weight:700; }}
  .chip.oro {{ background:#f5c518; color:#000; border-color:#f5c518; font-weight:800; }}
  .stButton > button, .stFormSubmitButton > button, [data-testid="stPopover"] button {{ border-radius:999px;
      font-weight:700; border:1px solid #535353; background:transparent; color:#fff; padding:0.25rem 0.5rem; min-width:0; }}
  .stButton > button:hover {{ border-color:#fff; color:#fff; }}
  .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{ background:{VERDE};
      color:#000; border:none; }}
  .stButton > button[kind="primary"]:hover {{ background:#1ed760; color:#000; }}
  [data-testid="stColumn"] {{ min-width:0; }}
  /* Reproductor fijo abajo, como en Spotify */
  [data-testid="stSidebarContent"] {{ padding-bottom:110px; }}
  .st-key-barra {{ position:fixed; left:0; right:0; bottom:0; z-index:1000001; background:#000;
                   border-top:1px solid #282828; padding:8px 22px 10px; }}
  .st-key-barra p {{ margin:0; }}
  .np-t {{ color:#fff; font-weight:700; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .np-a {{ color:#b3b3b3; font-size:.8rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .np-cv {{ width:52px; height:52px; border-radius:6px; display:flex; align-items:center; justify-content:center;
            font-size:1.6rem; flex-shrink:0; }}
  .tiempo {{ color:#b3b3b3; font-size:.75rem; text-align:center; }}
  .anuncio {{ background:linear-gradient(90deg,#3b2a6b,#000); border-radius:8px; padding:6px 12px; color:#fff; }}
  .st-key-barra [data-testid="stProgress"] > div > div > div > div {{ background:{VERDE}; }}
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


def fmt_t(ms):
    m, s = divmod(int(max(ms, 0)) // 1000, 60)
    return f"{m}:{s:02d}"


def grad(n):
    clave = n if isinstance(n, int) else sum(ord(ch) for ch in str(n))   # estable entre reinicios
    return GRADIENTES[clave % len(GRADIENTES)]


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


def artistas_de(c):
    return [a.strip() for a in (c.get('artist') or '').split(',') if a.strip()]


@st.cache_data(ttl=300, show_spinner=False)
def artistas():
    """{artista: {'genero': el más común, 'canciones': [...]}}."""
    res = {}
    for c in catalogo().values():
        for a in artistas_de(c):
            res.setdefault(a, {'canciones': [], 'generos': []})
            res[a]['canciones'].append(c['song_id'])
            res[a]['generos'].append(c['genre'] or 'Sin género')
    for a, d in res.items():
        d['genero'] = max(set(d['generos']), key=d['generos'].count)
    return res


def portada(clave, genero=None, extra="", redonda=False, icono=None):
    ic = icono or ICONO_GENERO.get(genero, "🎵")
    return f'<div class="cover{" redonda" if redonda else ""}" style="background:{grad(clave)}">{ic}{extra}</div>'


# =====================================================================
# ESTADO
# =====================================================================
for k, v in {'uid': None, 'sid': None, 'usuario': None, 'paso': 'entrar', 'recs': [], 'perfil': None,
             'recs_version': 0, 'impresiones': {}, 'impresiones_version': -1,
             'cola': [], 'pos': 0, 'sonando': None, 'anuncio': None, 'desde_anuncio': 0,
             'shuffle': False, 'repeat': 'off', 'vel_demo': 10, 'paywall': None, 'detalle': None,
             'busqueda': None, 'aviso': None, 'premium_abierto': None}.items():
    st.session_state.setdefault(k, v)
S = st.session_state

try:
    conectar().close()
except Exception as e:
    st.error("😕 No pudimos conectarnos al servicio. Intenta de nuevo en unos minutos.")
    with st.expander("Detalle técnico"):
        st.caption(f"MySQL / base `{DB_NAME}`: enciende MySQL en XAMPP y, si la base no existe, "
                   f"corre `python \"base de datos.py\"`. {e}")
    st.stop()


def es_premium():
    return (S.usuario or {}).get('account_type') == 'premium'


def recargar_usuario():
    S.usuario = leer("SELECT * FROM users WHERE user_id=%s", (S.uid,))[0]


def avisar(texto, icono="✅"):
    S.aviso = (texto, icono)


def mis_likes():
    return {r['song_id'] for r in leer("SELECT song_id FROM song_liked WHERE user_id=%s", (S.uid,))}


def mis_follows():
    return {r['artist'] for r in leer("SELECT artist FROM artist_follows WHERE user_id=%s", (S.uid,))}


def mis_playlists():
    return leer("""SELECT p.playlist_id, p.playlist_name, p.description, p.created_at,
                          (SELECT COUNT(*) FROM playlist_tracks t WHERE t.playlist_id=p.playlist_id) AS n
                     FROM playlist_created p WHERE p.user_id=%s ORDER BY p.created_at DESC""", (S.uid,))


# =====================================================================
# TELEMETRÍA
# =====================================================================
def tocar_sesion(t):
    """Extiende la sesión hasta t para que todos los eventos queden dentro de ella."""
    escribir("""UPDATE app_sessions SET ended_at=%s, duration_sec=TIMESTAMPDIFF(SECOND, started_at, %s)
                WHERE session_id=%s""", (t, t, S.sid))


def evento_ui(screen, action, element):
    t = ahora()
    tocar_sesion(t)
    escribir("INSERT INTO ui_events (user_id, session_id, screen, action, element, event_at) VALUES (%s,%s,%s,%s,%s,%s)",
             (S.uid, S.sid, screen, action, element, t))


def abrir_sesion(user):
    t = ahora()
    S.uid, S.usuario = int(user['user_id']), user
    S.sid = escribir("""
        INSERT INTO app_sessions (user_id, device_type, os, app_version, network_type, city, started_at, ended_at,
                                  duration_sec, tracks_played)
        VALUES (%s,%s,%s,%s,'wifi',%s,%s,%s,0,0)""", (S.uid, DISPOSITIVO, SO, VERSION_APP, user.get('city'), t, t))
    escribir("""INSERT INTO app_performance_events (user_id, session_id, event_type, latency_ms, network_type,
                app_version, event_at) VALUES (%s,%s,'app_startup',%s,'wifi',%s,%s)""",
             (S.uid, S.sid, int((time.time() - _T0) * 1000) % 4000 + 300, VERSION_APP, t))
    evento_ui("home", "screen_view", "app_open")


def cerrar_sesion():
    if S.sonando:
        finalizar('endplay', reentrenar=False)
    tocar_sesion(ahora())
    for k in list(S.keys()):
        del S[k]


def refrescar_recs(motivo=None):
    """Reaprende con toda la telemetría del usuario y guarda sus recomendaciones.
    (motivo solo documenta qué lo disparó; el administrador ve el resultado en «Recomendaciones»)."""
    cx = conectar()
    res = aprendizaje.guardar(cx, S.uid, top_n=10, ahora=ahora())
    cx.close()
    S.recs, S.perfil = res['recs'], res
    S.recs_version += 1


def registrar_impresiones():
    """Solo cuando el usuario de verdad VE la fila «Hecho para ti» con una lista nueva."""
    if S.impresiones_version == S.recs_version:
        return
    t = ahora()
    tocar_sesion(t)
    S.impresiones = {}
    for i, r in enumerate(S.recs, start=1):
        S.impresiones[r['song_id']] = escribir("""
            INSERT INTO recommendation_events (user_id, session_id, song_id, surface, algorithm, model_version,
                ab_test_group, position_in_list, relevance_score, reason_shown, shown_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (S.uid, S.sid, r['song_id'], SUPERFICIE, aprendizaje.ALGORITMO, MODELO, GRUPO_AB, i,
             r['score'], r['reason'][:150], t))
    S.impresiones_version = S.recs_version


# =====================================================================
# REPRODUCTOR (cola, tiempo real, skips, anuncios, autoplay)
# =====================================================================
def item(song_id, origen, detalle, rec_event_id=None):
    return {'song_id': int(song_id), 'origen': origen, 'detalle': detalle, 'rec_event_id': rec_event_id}


def transcurrido():
    s = S.sonando
    if not s:
        return 0
    if s['pausado']:
        return s['acum']
    return s['acum'] + (time.time() - s['desde']) * 1000 * S.vel_demo


def duracion(song_id):
    return int(catalogo()[song_id]['duration_ms'] or 180000)


def iniciar_item():
    if not S.cola:
        S.sonando = None
        return
    it = S.cola[S.pos]
    if it.get('rec_event_id'):
        escribir("UPDATE recommendation_events SET clicked=1 WHERE rec_event_id=%s", (it['rec_event_id'],))
    S.sonando = {**it, 'acum': 0, 'desde': time.time(), 'pausado': False}


def reproducir(items, idx=0):
    """Reemplaza la cola (como dar ▶ a una playlist, un álbum o una canción)."""
    if S.sonando:
        finalizar('clickrow', reentrenar=False)
    S.cola, S.pos = list(items), idx
    if S.shuffle and len(S.cola) > idx + 1:
        resto = S.cola[idx + 1:]
        random.shuffle(resto)
        S.cola = S.cola[:idx + 1] + resto
    evento_ui("now_playing", "click", f"play_{items[idx]['origen']}")
    if not S.anuncio:          # durante un anuncio la música espera a que termine
        iniciar_item()


def finalizar(razon, reentrenar=True):
    """Guarda la reproducción actual en song_played (y en recommendation_events si vino de una recomendación)."""
    s = S.sonando
    if not s:
        return
    dur = duracion(s['song_id'])
    completa = razon == 'trackdone'
    ms = dur if completa else int(min(transcurrido(), dur))
    skip = int(not completa and razon in ('fwdbtn', 'clickrow') and ms < UMBRAL_SKIP_MS)
    t = ahora()
    tocar_sesion(t)
    escribir("""INSERT INTO song_played (user_id, song_id, played_at, session_id, ms_played, source, source_detail,
                reason_start, reason_end, skipped, shuffle, offline, device_type, audio_quality)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0,%s,%s)""",
             (S.uid, s['song_id'], t, S.sid, ms, s['origen'], (s['detalle'] or '')[:150],
              'trackdone' if s.get('auto') else 'clickrow', razon, skip, int(S.shuffle), DISPOSITIVO,
              'high' if es_premium() else 'normal'))
    escribir("UPDATE app_sessions SET tracks_played = tracks_played + 1 WHERE session_id=%s", (S.sid,))
    if s.get('rec_event_id'):
        escribir("""UPDATE recommendation_events SET played=1, ms_played=%s, completed=%s, skipped=%s
                    WHERE rec_event_id=%s""", (ms, int(completa), skip, s['rec_event_id']))
    S.sonando = None
    S.desde_anuncio += 1
    if reentrenar:
        titulo = catalogo()[s['song_id']]['title']
        refrescar_recs(("escuchó " if completa else "saltó " if skip else "cambió de ") + titulo)


def saltos_ultima_hora():
    return leer("""SELECT COUNT(*) AS n FROM song_played WHERE user_id=%s AND skipped=1 AND reason_end='fwdbtn'
                   AND played_at >= %s""", (S.uid, ahora() - timedelta(hours=1)))[0]['n']


def iniciar_anuncio():
    ad_id, anunciante, formato = random.choice(ANUNCIANTES)
    t = ahora()
    tocar_sesion(t)
    escribir("""INSERT INTO ad_events (user_id, session_id, ad_id, advertiser, ad_format, event_type, revenue_mxn, event_at)
                VALUES (%s,%s,%s,%s,%s,'impression',0.045,%s)""", (S.uid, S.sid, ad_id, anunciante, formato, t))
    S.anuncio = {'ad_id': ad_id, 'anunciante': anunciante, 'formato': formato, 'desde': time.time(), 'clic': False}
    S.desde_anuncio = 0


def evento_anuncio(tipo, ingreso):
    a = S.anuncio
    t = ahora()
    tocar_sesion(t)
    escribir("""INSERT INTO ad_events (user_id, session_id, ad_id, advertiser, ad_format, event_type, revenue_mxn, event_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""", (S.uid, S.sid, a['ad_id'], a['anunciante'], a['formato'], tipo,
                                                      ingreso, t))


def avanzar(razon):
    """Pasa a la siguiente de la cola; si se acaba, Autoplay sigue con tus recomendaciones."""
    if S.repeat == 'one' and razon == 'trackdone':
        sig = S.pos
    else:
        sig = S.pos + 1
    if sig >= len(S.cola):
        if S.repeat == 'all' and S.cola:
            sig = 0
        else:
            en_cola = {i['song_id'] for i in S.cola[-10:]}
            nuevas = [item(r['song_id'], 'recommendation', 'Autoplay') for r in S.recs if r['song_id'] not in en_cola][:5]
            if not nuevas:
                S.sonando = None
                return
            S.cola += nuevas
    S.pos = sig
    if not es_premium() and S.desde_anuncio >= CANCIONES_POR_ANUNCIO:
        iniciar_anuncio()
        return
    iniciar_item()
    if S.sonando:
        S.sonando['auto'] = True


def siguiente(razon='fwdbtn'):
    if razon == 'fwdbtn' and not es_premium() and saltos_ultima_hora() >= LIMITE_SALTOS_HORA:
        S.paywall = 'skip_limit_reached'
        return
    if razon == 'fwdbtn':
        evento_ui("now_playing", "click", "btn_next")
    finalizar(razon)
    avanzar(razon)


def anterior():
    evento_ui("now_playing", "click", "btn_previous")
    reiniciar = transcurrido() > 3000 or S.pos == 0
    finalizar('backbtn')
    if not reiniciar:
        S.pos -= 1
    iniciar_item()


def pausar():
    s = S.sonando
    if s['pausado']:
        s['desde'], s['pausado'] = time.time(), False
        evento_ui("now_playing", "click", "btn_play")
    else:
        s['acum'], s['pausado'] = transcurrido(), True
        evento_ui("now_playing", "click", "btn_pause")


def cambiar_velocidad():
    if S.sonando and not S.sonando['pausado']:
        # se congela lo ya escuchado con la velocidad anterior antes de cambiarla
        S.sonando['acum'] += (time.time() - S.sonando['desde']) * 1000 * S.vel_demo
        S.sonando['desde'] = time.time()
    if S.vel_widget:          # si se deselecciona el botón, se conserva la velocidad actual
        S.vel_demo = S.vel_widget


# =====================================================================
# ACCIONES DEL USUARIO
# =====================================================================
def alternar_like(song_id, origen, rec_event_id=None):
    t = ahora()
    tocar_sesion(t)
    titulo = catalogo()[song_id]['title']
    if leer("SELECT 1 FROM song_liked WHERE user_id=%s AND song_id=%s", (S.uid, song_id)):
        escribir("DELETE FROM song_liked WHERE user_id=%s AND song_id=%s", (S.uid, song_id))
        avisar(f"Se quitó «{titulo}» de Tus me gusta", "💔")
        refrescar_recs("quitó el like de " + titulo)
        return
    escribir("INSERT INTO song_liked (user_id, song_id, liked_at, source) VALUES (%s,%s,%s,%s)",
             (S.uid, song_id, t, origen))
    if rec_event_id:   # "guardada" solo cuenta si ya se reprodujo (regla de la auditoría)
        escribir("UPDATE recommendation_events SET clicked=1, saved=played WHERE rec_event_id=%s", (rec_event_id,))
    avisar(f"Se agregó «{titulo}» a Tus me gusta", "💚")
    refrescar_recs("le gustó " + titulo)


def no_me_interesa(song_id, rec_event_id):
    if rec_event_id:
        escribir("UPDATE recommendation_events SET dismissed=1 WHERE rec_event_id=%s", (rec_event_id,))
    evento_ui("home", "click", "btn_not_interested")
    avisar("Listo, te mostraremos menos música así", "👌")
    refrescar_recs("descartó " + catalogo()[song_id]['title'])


def alternar_follow(artista, origen):
    t = ahora()
    tocar_sesion(t)
    if artista in mis_follows():
        escribir("DELETE FROM artist_follows WHERE user_id=%s AND artist=%s", (S.uid, artista))
        avisar(f"Dejaste de seguir a {artista}", "👋")
    else:
        escribir("INSERT INTO artist_follows (user_id, artist, followed_at, source) VALUES (%s,%s,%s,%s)",
                 (S.uid, artista, t, origen))
        avisar(f"Ahora sigues a {artista}", "➕")
    refrescar_recs(("sigue a " if artista in mis_follows() else "dejó de seguir a ") + artista)


def crear_playlist(nombre, descripcion=None, canciones=()):
    t = ahora()
    tocar_sesion(t)
    pid = escribir("""INSERT INTO playlist_created (user_id, playlist_name, created_at, description, is_public,
                      is_collaborative, followers) VALUES (%s,%s,%s,%s,1,0,0)""",
                   (S.uid, nombre[:150], t, (descripcion or None)))
    for sid in canciones:
        agregar_a_playlist(pid, sid, 'now_playing', aviso=False)
    evento_ui("your_library", "click", "btn_create_playlist")
    return pid


def agregar_a_playlist(pid, song_id, origen, aviso=True):
    t = ahora()
    tocar_sesion(t)
    nuevo = escribir("""INSERT INTO playlist_tracks (playlist_id, song_id, added_at, added_from)
                        SELECT %s,%s,%s,%s FROM DUAL
                         WHERE NOT EXISTS (SELECT 1 FROM playlist_tracks WHERE playlist_id=%s AND song_id=%s)""",
                     (pid, song_id, t, origen, pid, song_id))
    if aviso:
        avisar("Agregada a la playlist" if nuevo else "Esa canción ya estaba en la playlist", "➕" if nuevo else "ℹ️")


def compartir(song_id, canal):
    t = ahora()
    tocar_sesion(t)
    escribir("INSERT INTO share_events (user_id, song_id, channel, link_opened, shared_at) VALUES (%s,%s,%s,0,%s)",
             (S.uid, song_id, canal, t))
    avisar(f"Enlace de «{catalogo()[song_id]['title']}» compartido por {canal}", "🔗")


def descargar(song_id):
    t = ahora()
    tocar_sesion(t)
    tam = round(duracion(song_id) / 60000 * 1.2, 2)
    escribir("""INSERT INTO download_events (user_id, song_id, audio_quality, file_size_mb, downloaded_at)
                VALUES (%s,%s,'high',%s,%s)""", (S.uid, song_id, tam, t))
    avisar(f"Descargada para escuchar sin conexión ({tam} MB)", "⬇️")


def suscribir(plan, metodo, prueba):
    t = ahora()
    tocar_sesion(t)
    precio = PLANES[plan]
    if prueba:
        escribir("""INSERT INTO subscription_events (user_id, event_type, plan_type, price_mxn, trigger_source, event_at)
                    VALUES (%s,'trial_started',%s,0,'oferta_1_mes_gratis',%s)""", (S.uid, plan, t))
    else:
        escribir("""INSERT INTO subscription_events (user_id, event_type, plan_type, price_mxn, trigger_source, event_at)
                    VALUES (%s,'purchase',%s,%s,'checkout',%s)""", (S.uid, plan, precio, t))
    escribir("""INSERT INTO premium_subscribed (user_id, subscribed_at, plan_type, price_mxn, payment_method, trial_used, status)
                VALUES (%s,%s,%s,%s,%s,%s,%s)""", (S.uid, t, plan, precio, metodo, int(prueba),
                                                   'prueba' if prueba else 'activa'))
    escribir("UPDATE users SET account_type='premium' WHERE user_id=%s", (S.uid,))
    recargar_usuario()
    if S.anuncio:           # Premium quita el anuncio en curso
        S.anuncio = None
        iniciar_item()
    avisar(f"¡Bienvenido a {plan}! Sin anuncios y con saltos ilimitados", "💎")


def cancelar_premium():
    t = ahora()
    tocar_sesion(t)
    sub = leer("""SELECT plan_type FROM premium_subscribed WHERE user_id=%s AND status<>'cancelada'
                  ORDER BY subscribed_at DESC LIMIT 1""", (S.uid,))
    escribir("""INSERT INTO subscription_events (user_id, event_type, plan_type, price_mxn, trigger_source, event_at)
                VALUES (%s,'cancelled',%s,NULL,'ya_no_lo_uso',%s)""", (S.uid, sub[0]['plan_type'] if sub else None, t))
    escribir("UPDATE premium_subscribed SET status='cancelada' WHERE user_id=%s AND status<>'cancelada'", (S.uid,))
    escribir("UPDATE users SET account_type='free' WHERE user_id=%s", (S.uid,))
    recargar_usuario()
    avisar("Tu cuenta volvió a Free", "ℹ️")


def cerrar_premium():
    S.premium_abierto = None


# El diálogo se vuelve a abrir en cada recarga completa mientras el usuario no lo cierre:
# así no desaparece cuando termina una canción y la reproducción automática recarga la página.
@st.dialog("💎 Premium", width="large", on_dismiss=cerrar_premium)
def dialogo_premium(trigger):
    motivo = {'skip_limit_reached': "Llegaste al límite de **6 saltos por hora** de la cuenta Free.",
              'ad_break': "Escucha tu música **sin anuncios**.",
              'download_button': "Las **descargas** para escuchar sin conexión son de Premium.",
              'home_banner': "Disfruta la música sin límites."}.get(trigger, "")
    st.markdown(f"### Prueba Premium\n{motivo}")
    st.markdown("✔ Sin anuncios &nbsp; ✔ Saltos ilimitados &nbsp; ✔ Descargas &nbsp; ✔ Mejor calidad de audio")
    ya_probo = bool(leer("SELECT 1 FROM premium_subscribed WHERE user_id=%s AND trial_used=1", (S.uid,)))
    plan = st.radio("Elige tu plan", list(PLANES), format_func=lambda p: f"{p} · ${PLANES[p]:.0f} MXN/mes",
                    horizontal=True)
    metodo = st.selectbox("Método de pago", ["tarjeta", "paypal", "oxxo_pay", "tarjeta_regalo"])
    st.caption("Proyecto escolar: no se cobra nada ni se piden datos de pago reales.")
    texto = f"Suscribirme por ${PLANES[plan]:.0f}/mes" if ya_probo else "Empezar 1 mes gratis"
    c1, c2 = st.columns(2)
    if c1.button(texto, type="primary", width="stretch"):
        suscribir(plan, metodo, prueba=not ya_probo)
        cerrar_premium()
        st.rerun()
    if c2.button("Ahora no", width="stretch"):
        cerrar_premium()
        st.rerun()


def mostrar_paywall():
    trigger, S.paywall = S.paywall, None
    t = ahora()
    tocar_sesion(t)
    escribir("""INSERT INTO subscription_events (user_id, event_type, plan_type, price_mxn, trigger_source, event_at)
                VALUES (%s,'paywall_view','Individual Premium',%s,%s,%s)""",
             (S.uid, PLANES['Individual Premium'], trigger, t))
    S.premium_abierto = trigger


# =====================================================================
# COMPONENTES
# =====================================================================
def menu_cancion(c, key, playlist_actual=None):
    """El menú «⋯» de cada canción, como en Spotify."""
    with st.popover("⋯", width="stretch"):
        st.markdown(f"**{esc(c['title'])}**")
        for a in artistas_de(c):
            if st.button(f"👤 Ir a {a}", key=f"{key}_art_{a}", width="stretch"):
                S.detalle = ('artista', a); st.rerun()
        pls = [p for p in mis_playlists() if p['playlist_id'] != playlist_actual]
        if pls:
            st.caption("Agregar a playlist")
            for p in pls[:8]:
                if st.button(f"➕ {p['playlist_name']}", key=f"{key}_pl_{p['playlist_id']}", width="stretch"):
                    agregar_a_playlist(p['playlist_id'], c['song_id'], 'tracklist'); st.rerun()
        if st.button("➕ Nueva playlist con esta canción", key=f"{key}_np", width="stretch"):
            pid = crear_playlist(f"Mi playlist n.º {len(mis_playlists()) + 1}", canciones=[c['song_id']])
            S.detalle = ('playlist', pid); st.rerun()
        st.caption("Compartir")
        cc = st.columns(3)
        for col, canal in zip(cc, ["whatsapp", "instagram", "copy_link"]):
            if col.button({"whatsapp": "WhatsApp", "instagram": "Instagram", "copy_link": "Enlace"}[canal],
                          key=f"{key}_sh_{canal}", width="stretch"):
                compartir(c['song_id'], canal); st.rerun()
        if st.button("⬇ Descargar" + ("" if es_premium() else " (Premium)"), key=f"{key}_dl", width="stretch"):
            if es_premium():
                descargar(c['song_id'])
            else:
                S.paywall = 'download_button'
            st.rerun()


def fila(c, n, cola, idx, key, likes, playlist_actual=None, quitar=None):
    """Una fila de lista de canciones: número, título, ▶, ❤ y menú."""
    sonando = S.sonando and S.sonando['song_id'] == c['song_id']
    cols = st.columns([0.5, 5, 0.9, 0.8, 0.8] + ([0.8] if quitar else []), vertical_alignment="center")
    cols[0].markdown('<span class="eq"><span></span><span></span><span></span></span>' if sonando
                     else f"<span style='color:#b3b3b3'>{n}</span>", unsafe_allow_html=True)
    cols[1].markdown(f'<div class="fila-t{" on" if sonando else ""}">{esc(c["title"])}</div>'
                     f'<div class="fila-a">{esc(c["artist"])} · {esc(c["genre"])} · {fmt_t(c["duration_ms"] or 0)}</div>',
                     unsafe_allow_html=True)
    if cols[2].button("▶", key=f"{key}_p", width="stretch"):
        reproducir(cola, idx); st.rerun()
    if cols[3].button("💚" if c['song_id'] in likes else "♡", key=f"{key}_l", width="stretch",
                      help="Quitar de Tus me gusta" if c['song_id'] in likes else "Guardar en Tus me gusta"):
        alternar_like(c['song_id'], 'tracklist'); st.rerun()
    with cols[4]:
        menu_cancion(c, key, playlist_actual)
    if quitar:
        if cols[5].button("✕", key=f"{key}_q", help="Quitar de la playlist", width="stretch"):
            quitar(); st.rerun()


def lista(ids, origen, detalle, key, likes, **kw):
    cat = catalogo()
    cola = [item(s, origen, detalle) for s in ids if s in cat]
    for i, it in enumerate(cola):
        fila(cat[it['song_id']], i + 1, cola, i, f"{key}_{i}", likes, **kw)
    return cola


def tarjeta_play(clave, titulo, subtitulo, cola, key, icono=None, genero=None, redonda=False):
    st.markdown(f'<div class="card">{portada(clave, genero, redonda=redonda, icono=icono)}'
                f'<div class="t">{esc(titulo)}</div><div class="a">{esc(subtitulo)}</div></div>', unsafe_allow_html=True)
    if cola and st.button("▶", key=key, width="stretch", type="primary"):
        reproducir(cola); st.rerun()


# =====================================================================
# PANTALLA 1: REGISTRO / INICIO DE SESIÓN
# =====================================================================
def pantalla_entrar():
    st.markdown(f"""<div style="text-align:center;margin:10px 0 18px">
        <div style="width:72px;height:72px;border-radius:50%;background:{VERDE};display:inline-flex;align-items:center;
        justify-content:center;font-size:38px">🎵</div>
        <div class="hola" style="margin-top:10px">Millones de canciones. Gratis.</div>
        <div class="sub">Crea tu cuenta y escucha música que aprende de lo que te gusta.</div></div>""",
                unsafe_allow_html=True)
    _, centro, _ = st.columns([1, 2, 1])
    with centro:
        tab_reg, tab_ent = st.tabs(["📝 Regístrate gratis", "🔑 Iniciar sesión"])
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
                    st.error("Ya existe una cuenta con ese nombre o correo. Entra en «Iniciar sesión».")
                else:
                    uid = escribir("""INSERT INTO users (username, signup_date, email, birth_year, gender, country, city,
                                      state, signup_source, signup_platform, account_type)
                                      VALUES (%s,%s,%s,%s,%s,'MX',%s,%s,%s,'Web','free')""",
                                   (nombre, ahora(), email, int(anio), genero, ciudad.strip() or None,
                                    estado.strip() or None, FUENTE_REGISTRO))
                    abrir_sesion(leer("SELECT * FROM users WHERE user_id=%s", (uid,))[0])
                    evento_ui("onboarding", "screen_view", "pick_artists")
                    S.paso = 'onboarding'
                    st.rerun()
        with tab_ent:
            with st.form("entrar"):
                quien = st.text_input("Correo o nombre de usuario")
                entrar = st.form_submit_button("Iniciar sesión", type="primary", width="stretch")
            if entrar:
                f = leer("SELECT * FROM users WHERE email=%s OR username=%s LIMIT 1", (quien.strip().lower(), quien.strip()))
                if not f:
                    st.error("No encontramos esa cuenta.")
                else:
                    abrir_sesion(f[0])
                    hay = leer("""SELECT (SELECT COUNT(*) FROM song_played WHERE user_id=%s) +
                                         (SELECT COUNT(*) FROM song_liked WHERE user_id=%s) +
                                         (SELECT COUNT(*) FROM artist_follows WHERE user_id=%s) AS n""",
                               (S.uid, S.uid, S.uid))[0]['n']
                    if hay:
                        S.paso = 'app'
                        refrescar_recs("inicio de sesión")
                    else:
                        evento_ui("onboarding", "screen_view", "pick_artists")
                        S.paso = 'onboarding'
                    st.rerun()
            st.caption("Entra con el correo o el nombre con el que te registraste.")


# =====================================================================
# PANTALLA 2: ONBOARDING (elige artistas, como Spotify)
# =====================================================================
def pantalla_onboarding():
    nombre = (S.usuario['username'].split() or ["👋"])[0]
    st.markdown(f'<div class="hola">Elige 3 o más artistas que te gusten, {esc(nombre)}</div>'
                '<div class="sub">Con eso armamos tu inicio. Después todo lo que escuches, saltes o guardes '
                'afina tus recomendaciones.</div>', unsafe_allow_html=True)
    arts = artistas()
    generos = sorted({d['genero'] for d in arts.values()})
    filtro = st.pills("Filtra por género", generos, selection_mode="multi", key="pills_genero")
    visibles = sorted([a for a, d in arts.items() if not filtro or d['genero'] in filtro],
                      key=lambda a: -max(catalogo()[s]['popularity'] or 0 for s in arts[a]['canciones']))
    S.setdefault('elegidos', set())
    cols = st.columns(6)
    for i, a in enumerate(visibles):
        with cols[i % 6]:
            marcado = a in S.elegidos
            st.markdown(f'<div class="card">{portada(a, arts[a]["genero"], "<span class=mov>✓</span>" if marcado else "", redonda=True)}'
                        f'<div class="t" style="text-align:center">{esc(a)}</div>'
                        f'<div class="a" style="text-align:center">{esc(arts[a]["genero"])}</div></div>',
                        unsafe_allow_html=True)
            if st.button("✓ Elegido" if marcado else "Elegir", key=f"pick_{i}", width="stretch",
                         type="primary" if marcado else "secondary"):
                S.elegidos ^= {a}
                st.rerun()
    n = len(S.elegidos)
    st.markdown("---")
    c1, c2 = st.columns([3, 1])
    c1.markdown(f"**{n}** elegido(s). " + ("¡Listo!" if n >= 3 else f"Te faltan {3 - n}."))
    if c2.button("Listo ▶", type="primary", disabled=n < 3, width="stretch"):
        t = ahora()
        tocar_sesion(t)
        for a in S.elegidos:
            escribir("""INSERT INTO artist_follows (user_id, artist, followed_at, source) SELECT %s,%s,%s,'onboarding'
                        FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM artist_follows WHERE user_id=%s AND artist=%s)""",
                     (S.uid, a, t, S.uid, a))
            escribir("""INSERT INTO ui_events (user_id, session_id, screen, action, element, event_at)
                        VALUES (%s,%s,'onboarding','click','pick_artist',%s)""", (S.uid, S.sid, t))
        del S['elegidos']
        S.paso = 'app'
        refrescar_recs("onboarding")
        st.rerun()


# =====================================================================
# PÁGINAS DE LA APP
# =====================================================================
def pagina_inicio(likes):
    nombre = (S.usuario['username'].split() or [""])[0]
    hora = datetime.now().hour
    saludo = "Buenos días" if hora < 12 else "Buenas tardes" if hora < 19 else "Buenas noches"
    st.markdown(f'<div class="hola">{saludo}, {esc(nombre)}</div>', unsafe_allow_html=True)
    cat = catalogo()

    # Accesos rápidos: Tus me gusta + lo último que escuchaste
    recientes = leer("""SELECT song_id, MAX(played_at) AS u FROM song_played WHERE user_id=%s
                        GROUP BY song_id ORDER BY u DESC LIMIT 5""", (S.uid,))
    rapidos = [("💚 Tus me gusta", ('likes',))] + [(f"{ICONO_GENERO.get(cat[r['song_id']]['genre'], '🎵')} "
                                                    f"{cat[r['song_id']]['title']}", ('cancion', r['song_id']))
                                                   for r in recientes if r['song_id'] in cat]
    cols = st.columns(3)
    for i, (txt, destino) in enumerate(rapidos[:6]):
        if cols[i % 3].button(txt, key=f"rap_{i}", width="stretch"):
            if destino[0] == 'likes':
                S.detalle = ('likes',)
            else:
                reproducir([item(destino[1], 'recently_played', 'Escuchado recientemente')])
            st.rerun()

    # Hecho para ti (lo que aprendió el modelo)
    registrar_impresiones()
    st.markdown('<div class="seccion">Hecho para ti</div>', unsafe_allow_html=True)
    st.caption("Según lo que escuchas, guardas y saltas. Se actualiza con cada canción.")
    recs = S.recs
    for fila_i in range(0, len(recs), 5):
        cols = st.columns(5)
        for col, (i, r) in zip(cols, enumerate(recs[fila_i:fila_i + 5], start=fila_i)):
            c = cat.get(r['song_id'])
            if not c:
                continue
            ev = S.impresiones.get(r['song_id'])
            with col:
                st.markdown(f"""<div class="card">{portada(c['song_id'], c['genre'])}
                    <div class="t">{esc(c['title'])}</div><div class="a">{esc(c['artist'])}</div>
                    <div class="r">{esc(r['reason'])}</div></div>""",
                            unsafe_allow_html=True)
                if st.button("▶ Escuchar", key=f"rec_p_{i}", type="primary", width="stretch"):
                    # como en Spotify: al dar play a una recomendación, la cola es el resto de la fila
                    cola = [item(x['song_id'], 'recommendation', SUPERFICIE, S.impresiones.get(x['song_id']))
                            for x in recs]
                    reproducir(cola, i); st.rerun()
                b2, b3 = st.columns(2, gap="small")
                if b2.button("💚" if c['song_id'] in likes else "♡", key=f"rec_l_{i}", width="stretch"):
                    alternar_like(c['song_id'], 'recommendation', ev); st.rerun()
                if b3.button("✕", key=f"rec_d_{i}", help="No me interesa", width="stretch"):
                    no_me_interesa(c['song_id'], ev); st.rerun()

    # Tus mixes diarios: uno por cada género que te gusta
    gustos = [g for g, v in (S.perfil or {}).get('generos', {}).items() if v > 0][:3]
    if gustos:
        st.markdown('<div class="seccion">Tus mixes diarios</div>', unsafe_allow_html=True)
        cols = st.columns(5)
        for n, g in enumerate(gustos, start=1):
            ids = [s for s, c in cat.items() if c['genre'] == g]
            random.Random(S.uid * 100 + n).shuffle(ids)
            arts = ", ".join(dict.fromkeys(a for s in ids for a in artistas_de(cat[s])))
            with cols[n - 1]:
                tarjeta_play(f"mix{n}{g}", f"Daily Mix {n}", f"{g} · {arts}",
                             [item(s, 'recommendation', f"Daily Mix {n}") for s in ids], f"mix_{n}", genero=g)

    # Populares
    st.markdown('<div class="seccion">Populares en México</div>', unsafe_allow_html=True)
    top = list(cat)[:10]
    cola_top = [item(s, 'playlist', 'Top 50 México') for s in top]
    cols = st.columns(5)
    for i, s in enumerate(top[:5]):
        with cols[i]:
            st.markdown(f'<div class="card">{portada(s, cat[s]["genre"])}<div class="t">{esc(cat[s]["title"])}</div>'
                        f'<div class="a">{esc(cat[s]["artist"])}</div></div>', unsafe_allow_html=True)
            if st.button("▶", key=f"top_{i}", width="stretch"):
                reproducir(cola_top, i); st.rerun()


def pagina_buscar(likes):
    st.markdown('<div class="hola">Buscar</div>', unsafe_allow_html=True)
    with st.form("buscar", border=False):
        c1, c2 = st.columns([5, 1])
        q = c1.text_input("¿Qué quieres escuchar?", placeholder="Artistas, canciones o géneros",
                          label_visibility="collapsed")
        ir = c2.form_submit_button("🔎 Buscar", type="primary", width="stretch")
    if ir and q.strip():
        buscar(q.strip())
        st.rerun()
    b = S.busqueda
    if not b:
        st.markdown('<div class="seccion">Explorar todo</div>', unsafe_allow_html=True)
        generos = sorted({c['genre'] for c in catalogo().values() if c['genre']})
        cols = st.columns(4)
        for i, g in enumerate(generos):
            with cols[i % 4]:
                st.markdown(f'<div class="card" style="background:{grad(g)}"><div style="font-size:1.8rem">'
                            f'{ICONO_GENERO.get(g, "🎵")}</div><div class="t">{esc(g)}</div></div>', unsafe_allow_html=True)
                if st.button("Ver", key=f"gen_{i}", width="stretch"):
                    buscar(g); st.rerun()
        return
    cat = catalogo()
    st.caption(f"Resultados para «{b['texto']}»")
    arts = [a for a in artistas() if b['texto'].lower() in a.lower()]
    if arts:
        st.markdown('<div class="seccion">Artistas</div>', unsafe_allow_html=True)
        cols = st.columns(6)
        for i, a in enumerate(arts[:6]):
            with cols[i]:
                st.markdown(f'<div class="card">{portada(a, artistas()[a]["genero"], redonda=True)}'
                            f'<div class="t" style="text-align:center">{esc(a)}</div></div>', unsafe_allow_html=True)
                if st.button("Abrir", key=f"ba_{i}", width="stretch"):
                    S.detalle = ('artista', a); st.rerun()
    if not b['ids']:
        st.info(f"Sin canciones para «{b['texto']}».")
        return
    st.markdown('<div class="seccion">Canciones</div>', unsafe_allow_html=True)
    cola = [item(s, 'search', f"Búsqueda: {b['texto']}") for s in b['ids']]
    for i, it in enumerate(cola):
        c = cat[it['song_id']]
        cols = st.columns([0.5, 5, 0.9, 0.8, 0.8], vertical_alignment="center")
        cols[0].markdown(f"<span style='color:#b3b3b3'>{i + 1}</span>", unsafe_allow_html=True)
        cols[1].markdown(f'<div class="fila-t">{esc(c["title"])}</div><div class="fila-a">{esc(c["artist"])} · '
                         f'{esc(c["genre"])}</div>', unsafe_allow_html=True)
        if cols[2].button("▶", key=f"bs_{i}", width="stretch"):
            if not b['clic']:     # el primer clic de la búsqueda se guarda en search_events
                escribir("""UPDATE search_events SET clicked_song_id=%s, click_position=%s, time_to_click_ms=%s
                            WHERE search_id=%s""", (c['song_id'], i + 1, int((time.time() - b['t0']) * 1000), b['id']))
                b['clic'] = True
            reproducir(cola, i); st.rerun()
        if cols[3].button("💚" if c['song_id'] in likes else "♡", key=f"bs_l_{i}", width="stretch"):
            alternar_like(c['song_id'], 'tracklist'); st.rerun()
        with cols[4]:
            menu_cancion(c, f"bsm_{i}")


def buscar(texto):
    res = leer("""SELECT song_id FROM songs WHERE title LIKE %s OR artist LIKE %s OR genre LIKE %s OR album LIKE %s
                  ORDER BY popularity DESC LIMIT 15""", tuple([f"%{texto}%"] * 4))
    t = ahora()
    tocar_sesion(t)
    tipo = 'artist' if any(texto.lower() in a.lower() for a in artistas()) else 'track'
    sid = escribir("""INSERT INTO search_events (user_id, session_id, query_text, search_type, results_count, searched_at)
                      VALUES (%s,%s,%s,%s,%s,%s)""", (S.uid, S.sid, texto[:150], tipo, len(res), t))
    S.busqueda = {'id': sid, 't0': time.time(), 'texto': texto, 'ids': [r['song_id'] for r in res], 'clic': False}


def pagina_biblioteca():
    st.markdown('<div class="hola">Tu biblioteca</div>', unsafe_allow_html=True)
    filtro = st.segmented_control("Ver", ["Playlists", "Artistas"], default="Playlists", label_visibility="collapsed")
    if filtro == "Artistas":
        seguidos = sorted(mis_follows())
        if not seguidos:
            st.info("Aún no sigues a ningún artista.")
        cols = st.columns(6)
        for i, a in enumerate(seguidos):
            with cols[i % 6]:
                st.markdown(f'<div class="card">{portada(a, artistas().get(a, {}).get("genero"), redonda=True)}'
                            f'<div class="t" style="text-align:center">{esc(a)}</div></div>', unsafe_allow_html=True)
                if st.button("Abrir", key=f"lib_a_{i}", width="stretch"):
                    S.detalle = ('artista', a); st.rerun()
        return
    n_likes = len(mis_likes())
    cols = st.columns(5)
    with cols[0]:
        st.markdown(f'<div class="card">{portada("likes", icono="💚")}<div class="t">Tus me gusta</div>'
                    f'<div class="a">Playlist · {n_likes} canciones</div></div>', unsafe_allow_html=True)
        if st.button("Abrir", key="lib_likes", width="stretch"):
            S.detalle = ('likes',); st.rerun()
    for i, p in enumerate(mis_playlists(), start=1):
        with cols[i % 5]:
            st.markdown(f'<div class="card">{portada(p["playlist_id"], icono="🎶")}<div class="t">{esc(p["playlist_name"])}</div>'
                        f'<div class="a">Playlist · {p["n"]} canciones</div></div>', unsafe_allow_html=True)
            if st.button("Abrir", key=f"lib_p_{p['playlist_id']}", width="stretch"):
                S.detalle = ('playlist', p['playlist_id']); st.rerun()
        if (i + 1) % 5 == 0:
            cols = st.columns(5)


def cabecera(clave, tipo, nombre, meta, icono, redonda=False):
    st.markdown(f"""<div class="cab" style="background:linear-gradient(180deg,rgba(255,255,255,.08),transparent)">
        <div class="cv" style="background:{grad(clave)};{'border-radius:50%' if redonda else ''}">{icono}</div>
        <div><div class="tipo">{esc(tipo)}</div><div class="nombre">{esc(nombre)}</div>
        <div class="meta">{meta}</div></div></div>""", unsafe_allow_html=True)


def botones_lista(cola, key):
    c1, c2, _ = st.columns([1, 1, 4])
    if c1.button("▶ Reproducir", key=f"{key}_play", type="primary", width="stretch", disabled=not cola):
        reproducir(cola); st.rerun()
    if c2.button("🔀 Aleatorio", key=f"{key}_shuf", width="stretch", disabled=not cola):
        S.shuffle = True
        cola = list(cola)
        random.shuffle(cola)
        reproducir(cola); st.rerun()


def vista_likes(likes):
    filas = leer("""SELECT song_id FROM song_liked WHERE user_id=%s ORDER BY liked_at DESC""", (S.uid,))
    ids = [f['song_id'] for f in filas]
    cabecera("likes", "Playlist", "Tus me gusta", f"{esc(S.usuario['username'])} · {len(ids)} canciones", "💚")
    botones_lista([item(s, 'liked_songs', 'Tus me gusta') for s in ids], "likes")
    lista(ids, 'liked_songs', 'Tus me gusta', "vl", likes)


def vista_playlist(pid, likes):
    p = leer("SELECT * FROM playlist_created WHERE playlist_id=%s AND user_id=%s", (pid, S.uid))
    if not p:
        S.detalle = None; st.rerun()
    p = p[0]
    pistas = leer("""SELECT playlist_track_id, song_id FROM playlist_tracks WHERE playlist_id=%s ORDER BY added_at""", (pid,))
    ids = [t['song_id'] for t in pistas]
    total = sum(catalogo()[s]['duration_ms'] or 0 for s in ids if s in catalogo())
    cabecera(pid, "Playlist", p['playlist_name'],
             f"{esc(p['description'] or '')} {esc(S.usuario['username'])} · {len(ids)} canciones · {fmt_t(total)}", "🎶")
    botones_lista([item(s, 'playlist', p['playlist_name']) for s in ids], f"pl{pid}")
    with st.expander("✏️ Editar detalles"):
        with st.form(f"edit_{pid}", border=False):
            nombre = st.text_input("Nombre", p['playlist_name'])
            desc = st.text_input("Descripción", p['description'] or "")
            if st.form_submit_button("Guardar", type="primary"):
                escribir("UPDATE playlist_created SET playlist_name=%s, description=%s WHERE playlist_id=%s",
                         (nombre.strip()[:150] or p['playlist_name'], desc.strip()[:255] or None, pid))
                st.rerun()
    if not ids:
        st.info("Esta playlist está vacía. Usa el menú «⋯» de cualquier canción para agregarla aquí.")
    cat = catalogo()
    cola = [item(s, 'playlist', p['playlist_name']) for s in ids]
    for i, t in enumerate(pistas):
        if t['song_id'] in cat:
            fila(cat[t['song_id']], i + 1, cola, i, f"vp{pid}_{i}", likes, playlist_actual=pid,
                 quitar=lambda ptid=t['playlist_track_id']: escribir(
                     "DELETE FROM playlist_tracks WHERE playlist_track_id=%s", (ptid,)))


def vista_artista(a, likes):
    d = artistas().get(a)
    if not d:
        S.detalle = None; st.rerun()
    oyentes = leer("""SELECT COUNT(DISTINCT p.user_id) AS n FROM song_played p JOIN songs s USING(song_id)
                      WHERE s.artist LIKE %s""", (f"%{a}%",))[0]['n']
    seguidores = leer("SELECT COUNT(*) AS n FROM artist_follows WHERE artist=%s", (a,))[0]['n']
    cabecera(a, "Artista", a, f"{oyentes} oyentes · {seguidores} seguidores · {esc(d['genero'])}",
             ICONO_GENERO.get(d['genero'], "🎤"), redonda=True)
    sigue = a in mis_follows()
    c1, c2, c3, _ = st.columns([1, 1, 1, 3])
    ids = sorted(d['canciones'], key=lambda s: -(catalogo()[s]['popularity'] or 0))
    cola = [item(s, 'artist', a) for s in ids]
    if c1.button("▶ Reproducir", type="primary", width="stretch"):
        reproducir(cola); st.rerun()
    if c2.button("✓ Siguiendo" if sigue else "Seguir", width="stretch"):
        alternar_follow(a, 'artist_page'); st.rerun()
    if c3.button("📻 Radio", width="stretch", help="Canciones parecidas del mismo género"):
        g = [s for s, c in catalogo().items() if c['genre'] == d['genero']]
        random.shuffle(g)
        reproducir([item(s, 'recommendation', f"Radio de {a}") for s in g]); st.rerun()
    st.markdown('<div class="seccion">Populares</div>', unsafe_allow_html=True)
    lista(ids, 'artist', a, "va", likes)


def pagina_perfil(likes):
    """Tu perfil, como en Spotify: lo que más escuchas. Sin datos internos del modelo (eso lo ve el administrador)."""
    u = S.usuario
    cat = catalogo()
    seguidos = mis_follows()
    pls = mis_playlists()
    plan = '<span class="chip oro">PREMIUM</span>' if es_premium() else '<span class="chip">FREE</span>'
    inicial = (u['username'][:1] or "?").upper()
    st.markdown(f"""<div class="cab" style="background:linear-gradient(180deg,rgba(255,255,255,.08),transparent)">
        <div class="cv" style="background:{VERDE};border-radius:50%;color:#000;font-weight:900">{esc(inicial)}</div>
        <div><div class="tipo">Perfil {plan}</div><div class="nombre">{esc(u['username'])}</div>
        <div class="meta">{len(pls)} playlists · {len(seguidos)} siguiendo · {len(likes)} me gusta ·
        miembro desde {u['signup_date']:%d/%m/%Y}</div></div></div>""", unsafe_allow_html=True)

    hace30 = ahora() - timedelta(days=30)
    m = leer("""SELECT IFNULL(SUM(ms_played),0) AS ms, COUNT(*) AS n, COUNT(DISTINCT song_id) AS distintas
                  FROM song_played WHERE user_id=%s AND played_at >= %s AND skipped=0""", (S.uid, hace30))[0]
    c = st.columns(3)
    c[0].metric("⏱️ Minutos escuchados", f"{int(m['ms']) // 60000:,}", help="Últimos 30 días")
    c[1].metric("▶️ Reproducciones", f"{m['n']:,}", help="Últimos 30 días, sin contar las saltadas")
    c[2].metric("🎵 Canciones distintas", f"{m['distintas']:,}", help="Últimos 30 días")

    top = leer("""SELECT song_id, COUNT(*) AS n FROM song_played WHERE user_id=%s AND played_at >= %s AND skipped=0
                  GROUP BY song_id ORDER BY n DESC LIMIT 50""", (S.uid, hace30))
    conteo_art = {}
    for t in top:
        for a in artistas_de(cat.get(t['song_id'], {})):
            conteo_art[a] = conteo_art.get(a, 0) + t['n']
    st.markdown('<div class="seccion">Artistas más escuchados este mes</div>', unsafe_allow_html=True)
    if not conteo_art:
        st.caption("Escucha música para ver aquí a tus artistas favoritos.")
    else:
        cols = st.columns(6)
        for i, (a, n) in enumerate(sorted(conteo_art.items(), key=lambda x: -x[1])[:6]):
            with cols[i]:
                st.markdown(f'<div class="card">{portada(a, artistas().get(a, {}).get("genero"), redonda=True)}'
                            f'<div class="t" style="text-align:center">{esc(a)}</div>'
                            f'<div class="a" style="text-align:center">{n} reproducciones</div></div>',
                            unsafe_allow_html=True)
                if st.button("Abrir", key=f"perf_a_{i}", width="stretch"):
                    S.detalle = ('artista', a); st.rerun()

    st.markdown('<div class="seccion">Canciones más escuchadas este mes</div>', unsafe_allow_html=True)
    ids = [t['song_id'] for t in top[:10] if t['song_id'] in cat]
    if not ids:
        st.caption("Todavía no hay canciones este mes.")
    else:
        lista(ids, 'playlist', 'Tus canciones top', "perf", likes)

    gustos = [g for g, v in (S.perfil or {}).get('generos', {}).items() if v > 0][:5]
    if gustos:
        st.markdown('<div class="seccion">Tus géneros</div>', unsafe_allow_html=True)
        st.markdown("".join(f'<span class="chip verde">{ICONO_GENERO.get(g, "🎵")} {esc(g)}</span>' for g in gustos),
                    unsafe_allow_html=True)


def aviso_saltos():
    """Como en Spotify Free: solo se avisa cuando ya casi no quedan saltos."""
    if es_premium():
        return ""
    quedan = LIMITE_SALTOS_HORA - saltos_ultima_hora()
    if quedan > 2:
        return ""
    return (f'<div class="np-a" style="color:#f5c518">Te quedan {max(quedan, 0)} saltos esta hora</div>')


# =====================================================================
# REPRODUCTOR FIJO (se actualiza cada segundo)
# =====================================================================
@st.fragment(run_every=1)
def barra_reproductor():
    with st.container(key="barra"):
        # --- Anuncio en curso (solo cuentas Free) ---
        if S.anuncio:
            a = S.anuncio
            vel_ad = min(S.vel_demo, 3)     # el anuncio se acelera poco: siempre dura >= 5 s reales
            pasado = (time.time() - a['desde']) * 1000 * vel_ad
            if pasado >= DURACION_ANUNCIO_MS:
                evento_anuncio('complete', 0.0)
                S.anuncio = None
                iniciar_item()
                st.rerun()
            c1, c2, c3 = st.columns([4, 3, 2], vertical_alignment="center")
            c1.markdown(f'<div class="anuncio">📢 <b>Anuncio</b> · {esc(a["anunciante"])} ({esc(a["formato"])}) · '
                        f'tu música sigue en {max(0, int((DURACION_ANUNCIO_MS - pasado) / 1000 / vel_ad) + 1)} s</div>',
                        unsafe_allow_html=True)
            c2.progress(min(pasado / DURACION_ANUNCIO_MS, 1.0))
            b1, b2 = c3.columns(2)
            if b1.button("Ver más", key="ad_clic", width="stretch", disabled=a['clic']):
                a['clic'] = True
                evento_anuncio('click', 0.35)
                if a['ad_id'] == 'AD-1005':
                    S.paywall = 'ad_break'
                st.rerun()
            if b2.button("Sin anuncios", key="ad_prem", width="stretch"):
                S.paywall = 'ad_break'
                st.rerun()
            return

        s = S.sonando
        if not s:
            st.markdown("<div class='np-a' style='padding:14px 0'>🎧 Elige algo para escuchar.</div>",
                        unsafe_allow_html=True)
            return
        c = catalogo()[s['song_id']]
        dur = duracion(s['song_id'])
        t = transcurrido()
        if t >= dur:   # terminó: la siguiente empieza sola, como en Spotify
            siguiente('trackdone')
            st.rerun()

        izq, centro, der = st.columns([3, 5, 2.4], vertical_alignment="center")
        with izq:
            ci, ct, cl = st.columns([1, 4, 1], vertical_alignment="center")
            ci.markdown(f'<div class="np-cv" style="background:{grad(c["song_id"])}">'
                        f'{ICONO_GENERO.get(c["genre"], "🎵")}</div>', unsafe_allow_html=True)
            ct.markdown(f'<div class="np-t">{esc(c["title"])}</div><div class="np-a">{esc(c["artist"])}</div>',
                        unsafe_allow_html=True)
            le_gusta = bool(leer("SELECT 1 FROM song_liked WHERE user_id=%s AND song_id=%s", (S.uid, c['song_id'])))
            if cl.button("💚" if le_gusta else "♡", key="np_like", width="stretch"):
                alternar_like(c['song_id'], 'now_playing', s.get('rec_event_id')); st.rerun()
        with centro:
            b = st.columns([1, 1, 1.2, 1, 1])
            if b[0].button("🔀", key="np_shuf", width="stretch", type="primary" if S.shuffle else "secondary",
                           help="Aleatorio"):
                S.shuffle = not S.shuffle
                evento_ui("now_playing", "click", "btn_shuffle")
                if S.shuffle and len(S.cola) > S.pos + 1:
                    resto = S.cola[S.pos + 1:]
                    random.shuffle(resto)
                    S.cola = S.cola[:S.pos + 1] + resto
                st.rerun(scope="fragment")
            if b[1].button("⏮", key="np_prev", width="stretch"):
                anterior(); st.rerun()
            if b[2].button("▶" if s['pausado'] else "⏸", key="np_play", width="stretch", type="primary"):
                pausar(); st.rerun(scope="fragment")
            if b[3].button("⏭", key="np_next", width="stretch"):
                siguiente('fwdbtn'); st.rerun()
            rep = {'off': "🔁", 'all': "🔁", 'one': "🔂"}[S.repeat]
            if b[4].button(rep, key="np_rep", width="stretch", type="secondary" if S.repeat == 'off' else "primary",
                           help="Repetir: no / todo / una"):
                S.repeat = {'off': 'all', 'all': 'one', 'one': 'off'}[S.repeat]
                evento_ui("now_playing", "click", "btn_repeat")
                st.rerun(scope="fragment")
            p1, p2, p3 = st.columns([1, 8, 1], vertical_alignment="center")
            p1.markdown(f'<div class="tiempo">{fmt_t(t)}</div>', unsafe_allow_html=True)
            p2.progress(min(t / dur, 1.0))
            p3.markdown(f'<div class="tiempo">{fmt_t(dur)}</div>', unsafe_allow_html=True)
        with der:
            sig = S.cola[S.pos + 1] if S.pos + 1 < len(S.cola) else None
            st.markdown(f'<div class="np-a">Desde: {esc(s["detalle"])}</div>'
                        f'<div class="np-a">Sigue: {esc(catalogo()[sig["song_id"]]["title"]) if sig else "Autoplay ✨"}</div>'
                        + aviso_saltos(),
                        unsafe_allow_html=True)


# =====================================================================
# APP PRINCIPAL
# =====================================================================
PAGINAS = ["🏠 Inicio", "🔎 Buscar", "📚 Tu biblioteca", "👤 Tu perfil"]
PANTALLA_UI = {"🏠 Inicio": "home", "🔎 Buscar": "search", "📚 Tu biblioteca": "your_library",
               "👤 Tu perfil": "profile"}


def al_cambiar_menu():
    S.detalle = None
    evento_ui(PANTALLA_UI[S.menu], "screen_view", "nav")


def app_principal():
    if S.aviso:
        texto, icono = S.aviso
        st.toast(texto, icon=icono)
        S.aviso = None
    if S.paywall:
        mostrar_paywall()          # registra la vista de la oferta una sola vez
    if S.premium_abierto and not es_premium():
        dialogo_premium(S.premium_abierto)
    u = S.usuario
    likes = mis_likes()
    with st.sidebar:
        inicial = (u['username'][:1] or "?").upper()
        plan = ('<span class="chip oro">PREMIUM</span>' if es_premium() else '<span class="chip">FREE</span>')
        st.markdown(f"""<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
            <div style="width:42px;height:42px;border-radius:50%;background:{VERDE};display:flex;align-items:center;
            justify-content:center;font-weight:900;color:#000;font-size:1.2rem">{esc(inicial)}</div>
            <div><div style="color:#fff;font-weight:800">{esc(u['username'])}</div>{plan}</div></div>""",
                    unsafe_allow_html=True)
        st.radio("Menú", PAGINAS, label_visibility="collapsed", key="menu", on_change=al_cambiar_menu)
        st.markdown("**Tu biblioteca**")
        if st.button("💚 Tus me gusta", key="sb_likes", width="stretch"):
            S.detalle = ('likes',); st.rerun()
        for p in mis_playlists()[:8]:
            if st.button(f"🎶 {p['playlist_name']}", key=f"sb_pl_{p['playlist_id']}", width="stretch"):
                S.detalle = ('playlist', p['playlist_id']); st.rerun()
        with st.popover("➕ Crear playlist", width="stretch"):
            with st.form("nueva_pl", border=False, clear_on_submit=True):
                nombre = st.text_input("Nombre", placeholder=f"Mi playlist n.º {len(mis_playlists()) + 1}")
                desc = st.text_input("Descripción (opcional)")
                if st.form_submit_button("Crear", type="primary", width="stretch"):
                    pid = crear_playlist(nombre.strip() or f"Mi playlist n.º {len(mis_playlists()) + 1}", desc.strip())
                    S.detalle = ('playlist', pid)
                    avisar("Playlist creada", "🎶")
                    st.rerun()
        st.markdown("---")
        if es_premium():
            sub = leer("""SELECT plan_type, status FROM premium_subscribed WHERE user_id=%s AND status<>'cancelada'
                          ORDER BY subscribed_at DESC LIMIT 1""", (S.uid,))
            if sub:
                st.caption(f"💎 {sub[0]['plan_type']} ({sub[0]['status']})")
            with st.popover("Administrar suscripción", width="stretch"):
                st.markdown("Si cancelas, vuelves a Free: con anuncios y 6 saltos por hora.")
                if st.button("Cancelar Premium", key="cancelar_prem", width="stretch"):
                    cancelar_premium(); st.rerun()
        elif st.button("💎 Hazte Premium", type="primary", width="stretch"):
            S.paywall = 'home_banner'; st.rerun()
        with st.popover("⚙️ Configuración", width="stretch"):
            st.segmented_control("⏩ Velocidad de reproducción (demo)", [1, 5, 10, 30], default=S.vel_demo,
                                 key="vel_widget", on_change=cambiar_velocidad, format_func=lambda v: f"x{v}")
            st.caption("x1 es tiempo real. Para una demostración conviene x10: una canción dura unos 20 s.")
        if st.button("Cerrar sesión", width="stretch"):
            cerrar_sesion(); st.rerun()

    d = S.detalle
    if d and d[0] == 'likes':
        vista_likes(likes)
    elif d and d[0] == 'playlist':
        vista_playlist(d[1], likes)
    elif d and d[0] == 'artista':
        vista_artista(d[1], likes)
    else:
        {"🏠 Inicio": lambda: pagina_inicio(likes), "🔎 Buscar": lambda: pagina_buscar(likes),
         "👤 Tu perfil": lambda: pagina_perfil(likes), "📚 Tu biblioteca": pagina_biblioteca}[S.get('menu', PAGINAS[0])]()
    barra_reproductor()


if S.paso == 'entrar' or not S.uid:
    pantalla_entrar()
elif S.paso == 'onboarding':
    pantalla_onboarding()
else:
    app_principal()
