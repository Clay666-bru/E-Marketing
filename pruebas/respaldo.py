"""
Foto y restauración de la base ORIGINAL para poder probar sobre ella sin dejar rastro.

Las pruebas dan de alta, modifican y borran registros. Antes de empezar se toma una
"foto" de la base y al terminar se restaura:

  1. Se borran los registros nuevos (IDs mayores a los de la foto), de hijos a padres.
  2. Se regresan los valores de las tablas editables (users, songs, playlist_created,
     premium_subscribed) y se repone completa user_recommendations.
  3. Se regresan los contadores AUTO_INCREMENT.
  4. Se compara CHECKSUM TABLE de las 19 tablas: la base debe quedar idéntica.

Uso desde la terminal (por ejemplo, alrededor de pruebas manuales en el navegador):

    python pruebas/respaldo.py foto        # guarda la foto en pruebas/.foto_base.pkl
    python pruebas/respaldo.py restaurar   # restaura y verifica
"""
import os
import pickle
import sys

import mysql.connector

DB = os.environ.get("SPOTIFY_DB", "spotify_uadeo_db")
MYSQL = dict(host=os.environ.get("MYSQL_HOST", "localhost"), user=os.environ.get("MYSQL_USER", "root"),
             password=os.environ.get("MYSQL_PASSWORD", ""))
ARCHIVO = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".foto_base.pkl")

# Tabla -> llave primaria, en orden de borrado (primero las que dependen de otras)
TABLAS = [
    ("user_recommendations", "recommendation_id"), ("app_performance_events", "perf_event_id"),
    ("notification_events", "notif_id"), ("subscription_events", "sub_event_id"), ("ad_events", "ad_event_id"),
    ("share_events", "share_id"), ("download_events", "download_id"), ("ui_events", "ui_event_id"),
    ("search_events", "search_id"), ("recommendation_events", "rec_event_id"), ("artist_follows", "follow_id"),
    ("playlist_tracks", "playlist_track_id"), ("premium_subscribed", "subscription_id"), ("song_liked", "like_id"),
    ("playlist_created", "playlist_id"), ("song_played", "play_id"), ("app_sessions", "session_id"),
    ("songs", "song_id"), ("users", "user_id"),
]
EDITABLES = ["users", "songs", "playlist_created", "premium_subscribed"]


def _conectar():
    return mysql.connector.connect(**MYSQL, database=DB)


def checksums(cur):
    cur.execute("CHECKSUM TABLE " + ", ".join(t for t, _ in TABLAS))
    return {fila[0].split(".")[-1]: fila[1] for fila in cur.fetchall()}


def tomar_foto():
    cx = _conectar(); cur = cx.cursor()
    foto = {"db": DB, "max": {}, "auto": {}, "filas": {}, "columnas": {}}
    for tabla, pk in TABLAS:
        cur.execute(f"SELECT IFNULL(MAX({pk}), 0) FROM {tabla}")
        foto["max"][tabla] = cur.fetchone()[0]
        cur.execute("SELECT AUTO_INCREMENT FROM information_schema.tables WHERE table_schema=%s AND table_name=%s",
                    (DB, tabla))
        foto["auto"][tabla] = cur.fetchone()[0] or 1
    for tabla in EDITABLES + ["user_recommendations"]:
        cur.execute(f"SELECT * FROM {tabla}")
        foto["filas"][tabla] = cur.fetchall()
        foto["columnas"][tabla] = list(cur.column_names)
    foto["checksum"] = checksums(cur)
    cur.close(); cx.close()
    return foto


def restaurar(foto):
    """Regresa la base al estado de la foto. Devuelve la lista de tablas que NO quedaron idénticas."""
    if foto["db"] != DB:
        raise RuntimeError(f"La foto es de '{foto['db']}' y la base actual es '{DB}'")
    cx = _conectar(); cur = cx.cursor()
    # 1) Registros nuevos fuera (hijos primero)
    for tabla, pk in TABLAS:
        cur.execute(f"DELETE FROM {tabla} WHERE {pk} > %s", (foto["max"][tabla],))
    # 2) Valores originales de las tablas editables
    pks = dict(TABLAS)
    for tabla in EDITABLES:
        cols = foto["columnas"][tabla]; pk = pks[tabla]
        resto = [c for c in cols if c != pk]
        sql = f"UPDATE {tabla} SET " + ", ".join(f"{c}=%s" for c in resto) + f" WHERE {pk}=%s"
        for fila in foto["filas"][tabla]:
            valores = dict(zip(cols, fila))
            cur.execute(sql, [valores[c] for c in resto] + [valores[pk]])
    cols = foto["columnas"]["user_recommendations"]
    cur.execute("DELETE FROM user_recommendations")
    if foto["filas"]["user_recommendations"]:
        cur.executemany(f"INSERT INTO user_recommendations ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))})",
                        foto["filas"]["user_recommendations"])
    cx.commit()
    # 3) Contadores AUTO_INCREMENT
    for tabla, _ in TABLAS:
        cur.execute(f"ALTER TABLE {tabla} AUTO_INCREMENT = {int(foto['auto'][tabla])}")
    # 4) Verificación
    ahora = checksums(cur)
    cur.close(); cx.close()
    return [t for t in foto["checksum"] if foto["checksum"][t] != ahora.get(t)]


if __name__ == "__main__":
    accion = sys.argv[1] if len(sys.argv) > 1 else ""
    if accion == "foto":
        with open(ARCHIVO, "wb") as f:
            pickle.dump(tomar_foto(), f)
        print(f"Foto de '{DB}' guardada en {ARCHIVO}")
    elif accion == "restaurar":
        with open(ARCHIVO, "rb") as f:
            distintas = restaurar(pickle.load(f))
        if distintas:
            sys.exit(f"ATENCIÓN: estas tablas no quedaron idénticas: {distintas}")
        print(f"'{DB}' restaurada: las 19 tablas son idénticas a la foto (CHECKSUM TABLE).")
        os.remove(ARCHIVO)
    else:
        sys.exit("Uso: python pruebas/respaldo.py foto | restaurar")
