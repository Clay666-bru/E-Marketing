"""
Pruebas automáticas de la app Streamlit (consu/app_spotify.py), apartado por apartado.

Corren sobre la base ORIGINAL (spotify_uadeo_db, o la que indique SPOTIFY_DB).
Las pruebas dan de alta, modifican y borran registros, pero antes se toma una foto
de la base (pruebas/respaldo.py) y al terminar se restaura y se verifica con
CHECKSUM TABLE que las 19 tablas quedaron idénticas. Uso:

    python pruebas/test_app.py

Los pop-ups (st.dialog) no se pueden presionar desde AppTest; se prueban a mano en el
navegador (ver docs/PRUEBAS.md, apartado 8).
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


def nueva():
    """La app es el panel de ADMINISTRADOR: las pruebas entran ya con la sesión de administrador."""
    at = AppTest.from_file(APP, default_timeout=90)
    at.session_state["admin_ok"] = True
    return at.run()


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


def pruebas():
    print("== Apartado 0: acceso de administrador")
    at = AppTest.from_file(APP, default_timeout=90).run()
    ok = not at.sidebar.radio and len(at.text_input) == 2
    at.text_input[0].set_value("admin"); at.text_input[1].set_value("incorrecta"); at.button[0].click().run()
    ok = ok and any("incorrectos" in str(e.value) for e in at.error) and not at.sidebar.radio
    at.text_input[1].set_value(os.environ.get("ADMIN_PASSWORD", "admin")); at.button[0].click().run()
    ok = ok and bool(at.sidebar.radio) and not at.exception
    print(f"[{'OK' if ok else 'FAIL'}] Pide usuario y contraseña, rechaza la incorrecta y entra con la correcta")
    if not ok: FALLAS.append("acceso de administrador")

    print("== Apartado 1: páginas")
    for p in ["🏠 Inicio", "📺 En vivo", "📈 Marketing", "🧠 Recomendaciones", "📡 Telemetría", "🗄️ Base de datos"]:
        check(pagina(p), f"Página {p}")
    guias = [len(pagina(p).expander) for p in ["🏠 Inicio", "📈 Marketing", "📡 Telemetría", "🗄️ Base de datos"]]
    ok = all(n >= 1 for n in guias)
    print(f"[{'OK' if ok else 'FAIL'}] Guía «¿Cómo leer esta página?» en cada página {guias}")
    if not ok: FALLAS.append("guías")

    print("== Apartado 1b: 📈 Marketing (resultados contra SQL independiente)")
    at = pagina("📈 Marketing")
    textos = " ".join(m.value for m in at.markdown)
    aha_sql = q("""SELECT COUNT(*) FROM users u
                    WHERE (SELECT COUNT(*) FROM playlist_created p WHERE p.user_id=u.user_id
                             AND p.created_at BETWEEN u.signup_date AND u.signup_date + INTERVAL 7 DAY) >= 1
                      AND (SELECT COUNT(*) FROM song_played s WHERE s.user_id=u.user_id
                             AND s.played_at BETWEEN u.signup_date AND u.signup_date + INTERVAL 7 DAY) >= 20""")[0][0]
    ok = f'<div class="val">{aha_sql}</div>' in textos
    print(f"[{'OK' if ok else 'FAIL'}] KPI usuarios con Aha! = {aha_sql} (igual que la consulta del script)")
    if not ok: FALLAS.append("Marketing Aha")
    mrr = q("SELECT IFNULL(SUM(price_mxn),0) FROM premium_subscribed WHERE status='activa'")[0][0]
    ok = f'<div class="val">${float(mrr):,.0f}</div>' in textos
    print(f"[{'OK' if ok else 'FAIL'}] KPI MRR = ${float(mrr):,.0f}")
    if not ok: FALLAS.append("Marketing MRR")
    conclusiones = [s.value for s in at.success] + [w.value for w in at.warning]
    ok = any("hipótesis" in c.lower() for c in conclusiones) and any("significativa" in c.lower() for c in conclusiones)
    print(f"[{'OK' if ok else 'FAIL'}] Conclusiones automáticas de la hipótesis y de la prueba A/B")
    if not ok: FALLAS.append("Marketing conclusiones")
    if q("SELECT COUNT(*) FROM users")[0][0] == 0:
        at = pagina("🗄️ Base de datos")
        for g in ["Principales", "Telemetría", "Vistas KPI"]:
            at.sidebar.radio[1].set_value(g).run()
            for t in at.sidebar.selectbox[0].options:
                at.sidebar.selectbox[0].set_value(t).run(); check(at, f"Tabla vacía {t}")
        return

    print("== Apartado 2: 🧠 Recomendaciones (inspector del administrador)")
    at = pagina("🧠 Recomendaciones")
    ids = [r[0] for r in q("SELECT user_id FROM users")]
    malos = []
    for uid in ids:
        at.sidebar.selectbox[0].set_value(uid).run()
        errs = [str(e.value) for e in at.exception] + [str(e.value) for e in at.error]
        if errs: malos.append((uid, errs))
    if malos: FALLAS.append("Recomendaciones recorrido")
    print(f"[{'FAIL' if malos else 'OK'}] Recomendaciones recorrido de {len(ids)} usuarios {malos or ''}")
    for f in ["nueva", "escuchada", "saltada", "guardada", "descartada", "Todas"]:
        at.selectbox[0].set_value(f).run(); check(at, f"Filtro {f}")
    at.sidebar.selectbox[0].set_value(3).run()
    [b for b in at.button if b.label.startswith("🔄")][0].click().run(); check(at, "Regenerar (usuario sin historial)")
    at.sidebar.selectbox[0].set_value(1).run()
    at.button_group[0].set_value("🧠 En vivo · aprendizaje.py").run()
    [b for b in at.button if b.label.startswith("🔄")][0].click().run(); check(at, "Regenerar con el motor en vivo")
    alg = q("SELECT DISTINCT algorithm FROM user_recommendations WHERE user_id=1")
    ok = alg == [("telemetry_live_learning",)]
    print(f"[{'OK' if ok else 'FAIL'}] El motor en vivo guardó sus recomendaciones {alg}")
    if not ok: FALLAS.append("motor en vivo")
    ok = not [b for b in at.button if b.label in ("▶ Escuchar", "❤ Me gusta", "Detalles", "✨ Ver pop-up")]
    print(f"[{'OK' if ok else 'FAIL'}] El administrador no escucha ni da me gusta en nombre del usuario")
    if not ok: FALLAS.append("acciones de usuario en el panel")
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
    at = pagina("🧠 Recomendaciones"); at.sidebar.selectbox[0].set_value(vacio).run(); check(at, "Recomendaciones usuario con nombre vacío")
    [b for b in at.button if b.label.startswith("🔄")][0].click().run(); check(at, "Regenerar con canción sin artista/género")
    print("   razones:", [r[0] for r in q("SELECT reason FROM user_recommendations WHERE user_id=%s LIMIT 3", (vacio,))])
    check(pagina("🏠 Inicio"), "Inicio con canción sin género")
    at = pagina("📡 Telemetría"); at.selectbox[0].set_value(vacio).run(); check(at, "Telemetría usuario nuevo")


# La base original se fotografía antes y se restaura después, pase lo que pase
foto = respaldo.tomar_foto()
print(f"Foto de '{DB}' tomada: se restaurará al terminar.\n")
try:
    pruebas()
except Exception as e:                      # una excepción inesperada también cuenta como falla
    FALLAS.append(f"excepción: {e!r}")
    print("[FAIL] excepción inesperada:", repr(e))
finally:
    distintas = respaldo.restaurar(foto)
    if distintas:
        FALLAS.append(f"restauración incompleta: {distintas}")
        print(f"\n[FAIL] ATENCIÓN: no quedaron idénticas: {distintas}")
    else:
        print(f"\n[OK] '{DB}' restaurada: las 19 tablas quedaron idénticas a la foto (CHECKSUM TABLE)")
print("\nFALLAS:", FALLAS)
sys.exit(1 if FALLAS else 0)
