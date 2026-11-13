"""
Pruebas automáticas de la app de usuario «Mi Spotify» (consu/app_usuario.py).

Recorre el flujo de un usuario nuevo sobre la base ORIGINAL y comprueba en la base que
cada acción dejó su telemetría. Antes toma una foto (pruebas/respaldo.py) y al final la
restaura, así que no deja rastro. Uso:

    python pruebas/test_usuario.py

El pop-up de Premium (st.dialog) no se puede presionar desde AppTest: la suscripción se
prueba llamando a la función de la app y el pop-up se revisa a mano en el navegador.
"""
import os
import sys

import mysql.connector
from streamlit.testing.v1 import AppTest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import respaldo  # noqa: E402

DB = respaldo.DB
MYSQL = dict(host=os.environ.get("MYSQL_HOST", "localhost"), user=os.environ.get("MYSQL_USER", "root"),
             password=os.environ.get("MYSQL_PASSWORD", ""))
APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "consu", "app_usuario.py")
FALLAS = []
EMAIL = "prueba.automatica@test.local"


def q(sql, params=()):
    cx = mysql.connector.connect(**MYSQL, database=DB); c = cx.cursor()
    c.execute(sql, params); r = c.fetchall(); cx.close(); return r


def check(cond, label, detalle=""):
    if not cond: FALLAS.append(label)
    print(f"[{'OK' if cond else 'FAIL'}] {label}" + ("" if cond else f" -> {detalle}"))


def sin_errores(at, label):
    errs = [str(e.value) for e in at.exception] + [str(e.value) for e in at.error]
    check(not errs, label, errs)


def boton(at, texto, n=0):
    bs = [b for b in at.button if b.label == texto]
    bs[n].click().run()
    return at


foto = respaldo.tomar_foto()
try:
    at = AppTest.from_file(APP, default_timeout=120).run()
    sin_errores(at, "Pantalla de registro")

    # ---- Registro ----
    at.text_input[0].set_value("Prueba Automática")
    at.text_input[1].set_value(EMAIL)
    at.checkbox[0].check()
    boton(at, "Registrarme")
    sin_errores(at, "Registro")
    u = q("SELECT user_id, signup_source, account_type FROM users WHERE email=%s", (EMAIL,))
    check(len(u) == 1 and u[0][1] == "app_en_vivo" and u[0][2] == "free", "Usuario creado como free/app_en_vivo", u)
    uid = u[0][0]
    check(q("SELECT COUNT(*) FROM app_sessions WHERE user_id=%s", (uid,))[0][0] == 1, "Sesión abierta")

    # ---- Onboarding: 3 artistas ----
    for _ in range(3):
        boton(at, "Elegir")
    boton(at, "Listo ▶")
    sin_errores(at, "Onboarding e inicio")
    check(q("SELECT COUNT(*) FROM artist_follows WHERE user_id=%s AND source='onboarding'", (uid,))[0][0] == 3,
          "3 artistas seguidos en el onboarding")
    check(q("SELECT COUNT(*) FROM user_recommendations WHERE user_id=%s", (uid,))[0][0] == 10, "10 recomendaciones")
    check(q("SELECT COUNT(*) FROM recommendation_events WHERE user_id=%s AND ab_test_group='L'", (uid,))[0][0] == 10,
          "10 impresiones registradas al ver el inicio")

    # ---- Reproducir una recomendación y dejarla terminar ----
    boton(at, "▶ Escuchar")
    check(at.session_state.sonando is not None, "Reproduciendo una recomendación")
    at.session_state.sonando['acum'] = 10 ** 9       # la canción ya terminó
    at.run()
    sin_errores(at, "Fin de canción y siguiente automática")
    r = q("SELECT reason_end, skipped, ms_played > 0 FROM song_played WHERE user_id=%s ORDER BY play_id", (uid,))
    check(r and r[0][0] == "trackdone" and r[0][1] == 0, "Reproducción completa guardada", r)
    check(q("SELECT COUNT(*) FROM recommendation_events WHERE user_id=%s AND played=1 AND completed=1", (uid,))[0][0] == 1,
          "La recomendación quedó como reproducida y completada")

    # ---- Saltar ----
    boton(at, "⏭")
    sin_errores(at, "Saltar")
    r = q("SELECT reason_end, skipped FROM song_played WHERE user_id=%s ORDER BY play_id DESC LIMIT 1", (uid,))
    check(r[0] == ("fwdbtn", 1), "Skip guardado (fwdbtn, skipped=1)", r)

    # ---- Anuncio cada 3 canciones (cuenta Free) ----
    boton(at, "⏭")     # 1 completa + 1 salto + este = 3 canciones
    check(at.session_state.anuncio is not None, "Anuncio después de 3 canciones")
    check(q("SELECT COUNT(*) FROM ad_events WHERE user_id=%s AND event_type='impression'", (uid,))[0][0] == 1,
          "Impresión de anuncio guardada")
    at.session_state.anuncio['desde'] = 0               # el anuncio ya terminó
    at.run()
    check(q("SELECT COUNT(*) FROM ad_events WHERE user_id=%s AND event_type='complete'", (uid,))[0][0] == 1,
          "Anuncio completado y la música sigue")

    # ---- Límite de 6 saltos por hora ----
    for _ in range(5):      # 2 saltos previos + 5 intentos: el 7.º choca con el límite
        if at.session_state.anuncio:
            at.session_state.anuncio['desde'] = 0; at.run()
        boton(at, "⏭")
    saltos = q("SELECT COUNT(*) FROM song_played WHERE user_id=%s AND skipped=1 AND reason_end='fwdbtn'", (uid,))[0][0]
    check(saltos <= 6, "No pasa de 6 saltos por hora", saltos)
    check(q("SELECT COUNT(*) FROM subscription_events WHERE user_id=%s AND trigger_source='skip_limit_reached'",
            (uid,))[0][0] >= 1, "Al llegar al límite aparece la oferta Premium (paywall_view)")

    # ---- Me gusta / quitar me gusta / no me interesa ----
    at = AppTest.from_file(APP, default_timeout=120).run()   # sesión nueva, como al volver a abrir la app
    at.text_input[-1].set_value(EMAIL)
    boton(at, "Iniciar sesión")
    sin_errores(at, "Iniciar sesión con la cuenta creada")
    antes = q("SELECT COUNT(*) FROM song_liked WHERE user_id=%s", (uid,))[0][0]
    boton(at, "♡")
    check(q("SELECT COUNT(*) FROM song_liked WHERE user_id=%s", (uid,))[0][0] == antes + 1, "Me gusta")
    check(q("SELECT COUNT(*) FROM user_recommendations r JOIN song_liked l ON l.user_id=r.user_id AND l.song_id=r.song_id WHERE r.user_id=%s", (uid,))[0][0] == 0,
          "La canción con like sale de las recomendaciones")
    at.session_state.detalle = ('likes',); at.run()
    sin_errores(at, "Tus me gusta")
    boton(at, "💚")
    at.session_state.detalle = None; at.run()
    check(q("SELECT COUNT(*) FROM song_liked WHERE user_id=%s", (uid,))[0][0] == antes, "Quitar me gusta")
    boton(at, "✕")
    check(q("SELECT COUNT(*) FROM recommendation_events WHERE user_id=%s AND dismissed=1", (uid,))[0][0] == 1,
          "No me interesa")
    check(q("""SELECT COUNT(*) FROM user_recommendations r JOIN recommendation_events e
                 ON e.user_id=r.user_id AND e.song_id=r.song_id AND e.dismissed=1 WHERE r.user_id=%s""", (uid,))[0][0] == 0,
          "La canción descartada ya no se recomienda")

    # ---- Buscar ----
    at.sidebar.radio[0].set_value("🔎 Buscar").run()
    at.text_input[0].set_value("bad bunny")
    boton(at, "🔎 Buscar")
    sin_errores(at, "Buscar")
    boton(at, "▶")
    s = q("SELECT results_count, clicked_song_id, click_position FROM search_events WHERE user_id=%s", (uid,))
    check(s and s[0][0] > 0 and s[0][1] is not None and s[0][2] == 1, "Búsqueda y clic guardados", s)

    # ---- Playlist ----
    at.sidebar.radio[0].set_value("📚 Tu biblioteca").run()
    sin_errores(at, "Tu biblioteca")
    boton(at, "Crear")
    sin_errores(at, "Crear playlist")
    pl = q("SELECT playlist_id FROM playlist_created WHERE user_id=%s", (uid,))
    check(len(pl) == 1, "Playlist creada", pl)
    check(at.session_state.detalle == ('playlist', pl[0][0]), "La playlist nueva se abre sola")

    # ---- Artista ----
    a = q("SELECT artist FROM artist_follows WHERE user_id=%s LIMIT 1", (uid,))[0][0]
    at.session_state.detalle = ('artista', a); at.run()
    sin_errores(at, "Página de artista")
    boton(at, "✓ Siguiendo")
    check(q("SELECT COUNT(*) FROM artist_follows WHERE user_id=%s AND artist=%s", (uid, a))[0][0] == 0, "Dejar de seguir")

    # ---- Tu gusto musical ----
    at.session_state.detalle = None
    at.sidebar.radio[0].set_value("🧠 Tu gusto musical").run()
    sin_errores(at, "Tu gusto musical")

    # ---- Integridad: las reglas de la auditoría que no dependen de la fecha ----
    reglas = {
        "plays fuera de su sesión": "SELECT COUNT(*) FROM song_played p JOIN app_sessions s USING(session_id) WHERE p.played_at < s.started_at OR p.played_at > s.ended_at",
        "tracks_played != plays": "SELECT COUNT(*) FROM app_sessions s WHERE tracks_played <> (SELECT COUNT(*) FROM song_played p WHERE p.session_id=s.session_id)",
        "skip con >= 30 s": "SELECT COUNT(*) FROM song_played WHERE skipped=1 AND ms_played > 30000",
        "saved sin play": "SELECT COUNT(*) FROM recommendation_events WHERE saved=1 AND played=0",
        "clicked=0 pero played=1": "SELECT COUNT(*) FROM recommendation_events WHERE clicked=0 AND played=1",
        "recs con like": "SELECT COUNT(*) FROM user_recommendations r JOIN song_liked l ON l.user_id=r.user_id AND l.song_id=r.song_id",
        "playlist_tracks duplicados": "SELECT COUNT(*) FROM (SELECT playlist_id, song_id FROM playlist_tracks GROUP BY 1,2 HAVING COUNT(*)>1) x",
    }
    for nombre, sql in reglas.items():
        n = q(sql)[0][0]
        check(n == 0, f"Integridad: {nombre}", n)
except Exception as e:                      # una excepción inesperada también cuenta como falla
    FALLAS.append(f"excepción: {e!r}")
    print("[FAIL] excepción inesperada:", repr(e))
finally:
    distintas = respaldo.restaurar(foto)
    check(not distintas, f"'{DB}' restaurada: las 19 tablas quedaron idénticas a la foto", distintas)

print("\nFALLAS:", FALLAS)
sys.exit(1 if FALLAS else 0)
