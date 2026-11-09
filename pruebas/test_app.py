"""
Pruebas automáticas de la app Streamlit (consu/app_spotify.py), apartado por apartado.

¡OJO! Estas pruebas DAN DE ALTA, MODIFICAN y BORRAN registros. Corren sobre una base de
prueba, nunca sobre la real. Uso (desde la carpeta del proyecto, en PowerShell):

    $env:SPOTIFY_DB = "spotify_prueba"
    python "base de datos.py"            # crea la base de prueba con datos
    python pruebas/test_app.py           # corre las pruebas
    python pruebas/auditoria_datos.py    # verifica la integridad de los datos

Con una base vacía (solo tablas) también funciona: prueba que ninguna página truene.
Los pop-ups (st.dialog) no se pueden presionar desde AppTest; se prueban a mano
(ver docs/PRUEBAS.md, apartado 8).
"""
import os
import sys

import mysql.connector
from streamlit.testing.v1 import AppTest

DB = os.environ.get("SPOTIFY_DB", "")
if DB in ("", "spotify_uadeo_db"):
    sys.exit("Estas pruebas modifican datos: define SPOTIFY_DB con una base de PRUEBA (no spotify_uadeo_db).")
MYSQL = dict(host=os.environ.get("MYSQL_HOST", "localhost"), user=os.environ.get("MYSQL_USER", "root"),
             password=os.environ.get("MYSQL_PASSWORD", ""))
APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "consu", "app_spotify.py")
FALLAS = []


def q(sql, params=(), commit=False):
    cx = mysql.connector.connect(**MYSQL, database=DB); c = cx.cursor()
    c.execute(sql, params); r = None if commit else c.fetchall()
    if commit: cx.commit()
    cx.close(); return r


def check(at, label, espera_error=None):
    errs = [str(e.value) for e in at.exception] + [str(e.value) for e in at.error]
    if espera_error:
        ok = any(espera_error in e for e in errs) and not at.exception
    else:
        ok = not errs
    if not ok: FALLAS.append(label)
    print(f"[{'OK' if ok else 'FAIL'}] {label}" + ("" if ok else f" -> {errs}"))


def nueva(): return AppTest.from_file(APP, default_timeout=90).run()


def pagina(p):
    at = nueva(); at.sidebar.radio[0].set_value(p).run(); return at


def bd(tabla, grupo="Principales"):
    at = pagina("🗄️ Base de datos"); at.sidebar.radio[1].set_value(grupo).run()
    at.sidebar.selectbox[0].set_value(tabla).run(); return at


def accion(at, a): at.get("button_group")[0].set_value(a).run(); return at


def boton(at, label): at.button[[b.label for b in at.button].index(label)].click().run(); return at


def fill(at, valores):
    for ti in at.text_input:
        if ti.key in valores: ti.set_value(valores[ti.key])
    at.run()


print("== Apartado 1: páginas")
for p in ["🏠 Inicio", "✨ Para ti", "📡 Telemetría", "🗄️ Base de datos"]:
    check(pagina(p), f"Página {p}")
if q("SELECT COUNT(*) FROM users")[0][0] == 0:
    at = pagina("🗄️ Base de datos")
    for g in ["Principales", "Telemetría", "Vistas KPI"]:
        at.sidebar.radio[1].set_value(g).run()
        for t in at.sidebar.selectbox[0].options:
            at.sidebar.selectbox[0].set_value(t).run(); check(at, f"Tabla vacía {t}")
    print("\nFALLAS:", FALLAS); sys.exit(1 if FALLAS else 0)

print("== Apartado 2: Para ti")
at = pagina("✨ Para ti")
ids = [r[0] for r in q("SELECT user_id FROM users")]
malos = []
for uid in ids:
    at.sidebar.selectbox[0].set_value(uid).run()
    errs = [str(e.value) for e in at.exception] + [str(e.value) for e in at.error]
    if errs: malos.append((uid, errs))
if malos: FALLAS.append("Para ti recorrido")
print(f"[{'FAIL' if malos else 'OK'}] Para ti recorrido de {len(ids)} usuarios {malos or ''}")
for f in ["nueva", "escuchada", "guardada", "descartada", "Todas"]:
    at.selectbox[0].set_value(f).run(); check(at, f"Filtro {f}")
at.sidebar.selectbox[0].set_value(3).run()
[b for b in at.button if b.label.startswith("🔄")][0].click().run(); check(at, "Regenerar (usuario sin historial)")
print("   recs usuario 3:", q("SELECT algorithm, COUNT(*) FROM user_recommendations WHERE user_id=3 GROUP BY 1"))

print("== Apartado 3: Telemetría")
at = pagina("📡 Telemetría")
for uid in ids[:5]:
    at.selectbox[0].set_value(uid).run()
check(at, "Línea de tiempo 5 usuarios")

print("== Apartado 4: Base de datos (visor)")
at = pagina("🗄️ Base de datos")
for g in ["Principales", "Telemetría", "Vistas KPI"]:
    at.sidebar.radio[1].set_value(g).run()
    for t in at.sidebar.selectbox[0].options:
        at.sidebar.selectbox[0].set_value(t).run(); check(at, f"Tabla {t}")
at = bd("users"); at.text_input[0].set_value("dora").run(); check(at, "Buscador 'dora'")
at.text_input[0].set_value("zzzz-no-existe").run(); check(at, "Buscador sin coincidencias")

print("== Apartado 5: Altas con validación")
n0 = q("SELECT COUNT(*) FROM users")[0][0]
at = bd("users"); boton(at, "Guardar registros"); check(at, "Alta users con nombre vacío -> error", "campos vacíos")
at = bd("users"); fill(at, {"user_0": "   "}); boton(at, "Guardar registros"); check(at, "Alta users solo espacios -> error", "campos vacíos")
at = bd("users"); fill(at, {"user_0": "Prueba Fecha", "signup_0": "31/12/2026"}); boton(at, "Guardar registros"); check(at, "Alta users fecha inválida -> error", "formato")
at = bd("users"); fill(at, {"user_0": "Prueba Fecha", "signup_0": "2026-02-30 10:00:00"}); boton(at, "Guardar registros"); check(at, "Alta users 30 de febrero -> error", "formato")
print("   users sin cambios:", q("SELECT COUNT(*) FROM users")[0][0] == n0)
at = bd("users"); at.slider[0].set_value(2).run(); fill(at, {"user_0": "  Usuario Nuevo Uno ", "user_1": "Usuario Nuevo Dos"}); boton(at, "Guardar registros"); check(at, "Alta 2 users válidos")
print("   nombre sin espacios extra:", q("SELECT COUNT(*) FROM users WHERE username='Usuario Nuevo Uno'")[0][0] == 1)
at = bd("songs"); fill(at, {"title_0": "Canción Prueba", "artist_0": ""}); boton(at, "Guardar registros"); check(at, "Alta song sin artista -> error", "campos vacíos")
at = bd("songs"); fill(at, {"title_0": "Canción Prueba", "artist_0": "Artista Prueba"}); boton(at, "Guardar registros"); check(at, "Alta song válida (sin género)")
nuevo_u = q("SELECT MAX(user_id) FROM users")[0][0]; nueva_s = q("SELECT MAX(song_id) FROM songs")[0][0]
at = bd("song_played"); at.selectbox[0].set_value(nuevo_u).run(); at.selectbox[1].set_value(nueva_s).run(); boton(at, "Guardar registros"); check(at, "Alta song_played (canción sin género)")
at = bd("song_liked"); at.selectbox[0].set_value(1).run(); at.selectbox[1].set_value(2).run(); boton(at, "Guardar registros"); check(at, "Alta like ya existente -> error", "ya le dio like")
at = bd("song_liked"); at.slider[0].set_value(2).run(); at.selectbox[0].set_value(nuevo_u).run(); at.selectbox[2].set_value(nuevo_u).run(); boton(at, "Guardar registros"); check(at, "Alta 2 likes iguales en el form -> error", "repetidos")
at = bd("song_liked"); at.selectbox[0].set_value(nuevo_u).run(); at.selectbox[1].set_value(nueva_s).run(); boton(at, "Guardar registros"); check(at, "Alta like válida")
at = bd("playlist_created"); fill(at, {"pl_n_0": "Playlist Prueba"}); boton(at, "Guardar registros"); check(at, "Alta playlist")
at = bd("premium_subscribed"); at.selectbox[0].set_value(nuevo_u).run(); at.selectbox[1].set_value("Dúo Premium").run(); boton(at, "Guardar registros"); check(at, "Alta premium")
print("   premium con precio y usuario premium:", q("SELECT p.price_mxn, u.account_type FROM premium_subscribed p JOIN users u USING(user_id) WHERE p.user_id=%s", (nuevo_u,)))
at = bd("app_sessions", "Telemetría"); check(at, "Altas en telemetría muestra aviso")

print("== Apartado 6: Modificaciones")
q("UPDATE users SET username='Original' WHERE user_id=%s", (nuevo_u,), commit=True)
at = accion(bd("users"), "✏️ Modificar"); at.multiselect[0].set_value([nuevo_u]).run(); boton(at, "Aplicar cambios"); check(at, "Modificar sin cambios -> aviso")
print("   nombre conservado:", q("SELECT username FROM users WHERE user_id=%s", (nuevo_u,)))
at = accion(bd("songs"), "✏️ Modificar"); at.multiselect[0].set_value([nueva_s]).run(); fill(at, {f"mod_st_{nueva_s}": "Título Cambiado"}); boton(at, "Aplicar cambios"); check(at, "Modificar solo título")
print("   canción:", q("SELECT title, artist FROM songs WHERE song_id=%s", (nueva_s,)))
sub = q("SELECT subscription_id FROM premium_subscribed WHERE user_id=%s", (nuevo_u,))[0][0]
at = accion(bd("premium_subscribed"), "✏️ Modificar"); at.multiselect[0].set_value([sub]).run(); at.selectbox[0].set_value("Estudiantil Premium").run(); boton(at, "Aplicar cambios"); check(at, "Modificar plan premium")
print("   plan/precio:", q("SELECT plan_type, price_mxn FROM premium_subscribed WHERE subscription_id=%s", (sub,)))
at = accion(bd("song_played"), "✏️ Modificar"); check(at, "Modificar tabla no editable -> aviso")

print("== Apartado 7: casos raros en datos")
q("INSERT INTO users (username, signup_date) VALUES ('', NOW())", commit=True)
vacio = q("SELECT MAX(user_id) FROM users")[0][0]
q("INSERT INTO songs (title, artist, genre) VALUES ('Sin artista', '', NULL)", commit=True)
sa = q("SELECT MAX(song_id) FROM songs")[0][0]
q("INSERT INTO song_played (user_id, song_id, played_at) VALUES (%s, %s, NOW())", (vacio, sa), commit=True)
at = pagina("✨ Para ti"); at.sidebar.selectbox[0].set_value(vacio).run(); check(at, "Para ti usuario con nombre vacío")
[b for b in at.button if b.label.startswith("🔄")][0].click().run(); check(at, "Regenerar con canción sin artista/género")
print("   razones:", [r[0] for r in q("SELECT reason FROM user_recommendations WHERE user_id=%s LIMIT 3", (vacio,))])
check(pagina("🏠 Inicio"), "Inicio con canción sin género")
at = pagina("📡 Telemetría"); at.selectbox[0].set_value(vacio).run(); check(at, "Telemetría usuario nuevo")
print("\nFALLAS:", FALLAS)
sys.exit(1 if FALLAS else 0)
