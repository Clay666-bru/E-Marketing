"""
Auditoría de integridad de los datos simulados (solo lectura: no modifica nada).

Uso:
    python pruebas/auditoria_datos.py      # audita la base original spotify_uadeo_db

Cada regla cuenta registros que NO deberían existir; todas deben dar 0.
Termina con código 1 si alguna regla falla.
"""
import os
import sys

import mysql.connector

db = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SPOTIFY_DB", "spotify_uadeo_db")
cx = mysql.connector.connect(host=os.environ.get("MYSQL_HOST", "localhost"), user=os.environ.get("MYSQL_USER", "root"),
                             password=os.environ.get("MYSQL_PASSWORD", ""), database=db)
c = cx.cursor()
print(f"Auditando la base '{db}'\n")
CORTE = "'2026-11-04 23:00:00'"   # FECHA_CORTE de "base de datos.py"
checks = {
 "plays después del corte": f"SELECT COUNT(*) FROM song_played WHERE played_at > {CORTE}",
 "sesiones que terminan después del corte": f"SELECT COUNT(*) FROM app_sessions WHERE ended_at > {CORTE}",
 "likes después del corte": f"SELECT COUNT(*) FROM song_liked WHERE liked_at > {CORTE}",
 "ads después del corte": f"SELECT COUNT(*) FROM ad_events WHERE event_at > {CORTE}",
 "ui después del corte": f"SELECT COUNT(*) FROM ui_events WHERE event_at > {CORTE}",
 "perf después del corte": f"SELECT COUNT(*) FROM app_performance_events WHERE event_at > {CORTE}",
 "recs después del corte": f"SELECT COUNT(*) FROM recommendation_events WHERE shown_at > {CORTE}",
 "shares/downloads después del corte": f"SELECT (SELECT COUNT(*) FROM share_events WHERE shared_at > {CORTE})+(SELECT COUNT(*) FROM download_events WHERE downloaded_at > {CORTE})",
 "notif abiertas después del corte": f"SELECT COUNT(*) FROM notification_events WHERE opened_at > {CORTE}",
 "plays antes del registro": "SELECT COUNT(*) FROM song_played sp JOIN users u USING(user_id) WHERE sp.played_at < u.signup_date",
 "eventos de suscripción antes del registro": "SELECT COUNT(*) FROM subscription_events e JOIN users u USING(user_id) WHERE e.event_at < u.signup_date",
 "ui antes del registro": "SELECT COUNT(*) FROM ui_events e JOIN users u USING(user_id) WHERE e.event_at < u.signup_date",
 "recs antes del registro": "SELECT COUNT(*) FROM recommendation_events e JOIN users u USING(user_id) WHERE e.shown_at < u.signup_date",
 "notif antes del registro": "SELECT COUNT(*) FROM notification_events e JOIN users u USING(user_id) WHERE e.sent_at < u.signup_date",
 "follows/playlists antes del registro": "SELECT (SELECT COUNT(*) FROM artist_follows e JOIN users u USING(user_id) WHERE e.followed_at < u.signup_date)+(SELECT COUNT(*) FROM playlist_created e JOIN users u USING(user_id) WHERE e.created_at < u.signup_date)",
 "recs mostradas antes de iniciar la sesión": "SELECT COUNT(*) FROM recommendation_events r JOIN app_sessions s USING(session_id) WHERE r.shown_at < s.started_at",
 "plays fuera de su sesión": "SELECT COUNT(*) FROM song_played p JOIN app_sessions s USING(session_id) WHERE p.played_at < s.started_at OR p.played_at > s.ended_at",
 "plays con sesión de otro usuario": "SELECT COUNT(*) FROM song_played p JOIN app_sessions s USING(session_id) WHERE p.user_id <> s.user_id",
 "tracks_played != plays de la sesión": "SELECT COUNT(*) FROM app_sessions s WHERE tracks_played <> (SELECT COUNT(*) FROM song_played p WHERE p.session_id=s.session_id)",
 "likes duplicados (user,song)": "SELECT COUNT(*) FROM (SELECT user_id, song_id FROM song_liked GROUP BY 1,2 HAVING COUNT(*)>1) x",
 "follows duplicados": "SELECT COUNT(*) FROM (SELECT user_id, artist FROM artist_follows GROUP BY 1,2 HAVING COUNT(*)>1) x",
 "ads a usuarios mientras eran premium": "SELECT COUNT(*) FROM ad_events a JOIN premium_subscribed p USING(user_id) WHERE a.event_at >= p.subscribed_at AND a.event_at < IFNULL((SELECT MIN(event_at) FROM subscription_events c WHERE c.user_id=p.user_id AND c.event_type='cancelled'), '2100-01-01')",
 "usuarios cancelados que nunca vuelven a ver anuncios (con plays después)": "SELECT COUNT(*) FROM (SELECT c.user_id FROM subscription_events c WHERE c.event_type='cancelled' AND EXISTS (SELECT 1 FROM song_played sp WHERE sp.user_id=c.user_id AND sp.played_at > c.event_at + INTERVAL 1 DAY GROUP BY sp.user_id HAVING COUNT(*)>=6) AND NOT EXISTS (SELECT 1 FROM ad_events a WHERE a.user_id=c.user_id AND a.event_at > c.event_at)) x",
 "eventos de suscripción después del corte": "SELECT COUNT(*) FROM subscription_events WHERE event_at > " + CORTE,
 "account_type premium sin suscripción": "SELECT COUNT(*) FROM users u WHERE account_type='premium' AND NOT EXISTS (SELECT 1 FROM premium_subscribed p WHERE p.user_id=u.user_id AND p.status<>'cancelada')",
 "suscripción activa pero account_type free": "SELECT COUNT(*) FROM users u WHERE account_type='free' AND EXISTS (SELECT 1 FROM premium_subscribed p WHERE p.user_id=u.user_id AND p.status<>'cancelada')",
 "ms_played > duración": "SELECT COUNT(*) FROM song_played p JOIN songs s USING(song_id) WHERE p.ms_played > s.duration_ms",
 "skip con ms_played >= 30s": "SELECT COUNT(*) FROM song_played WHERE skipped=1 AND ms_played > 30000",
 "recs clicked=0 pero played=1": "SELECT COUNT(*) FROM recommendation_events WHERE clicked=0 AND played=1",
 "recs saved sin play": "SELECT COUNT(*) FROM recommendation_events WHERE saved=1 AND played=0",
 "playlist_tracks duplicados": "SELECT COUNT(*) FROM (SELECT playlist_id, song_id FROM playlist_tracks GROUP BY 1,2 HAVING COUNT(*)>1) x",
 "notif abiertas antes de enviadas": "SELECT COUNT(*) FROM notification_events WHERE opened_at < sent_at",
 "user_recommendations de canciones con like": "SELECT COUNT(*) FROM user_recommendations r JOIN song_liked l ON l.user_id=r.user_id AND l.song_id=r.song_id",
 "user_recommendations < 10 teniendo canciones disponibles": "SELECT COUNT(*) FROM (SELECT r.user_id FROM user_recommendations r GROUP BY r.user_id HAVING COUNT(*) < LEAST(10, (SELECT COUNT(*) FROM songs s WHERE NOT EXISTS (SELECT 1 FROM song_liked l WHERE l.user_id=r.user_id AND l.song_id=s.song_id)))) x",
 "usuarios sin recomendaciones": "SELECT COUNT(*) FROM users u WHERE NOT EXISTS (SELECT 1 FROM user_recommendations r WHERE r.user_id=u.user_id)",
 "emails duplicados": "SELECT COUNT(*) FROM (SELECT email FROM users GROUP BY email HAVING COUNT(*)>1) x",
 "usernames duplicados": "SELECT COUNT(*) FROM (SELECT username FROM users GROUP BY username HAVING COUNT(*)>1) x",
 "paywall_view de usuarios ya premium (fuera de suscribir)": "SELECT COUNT(*) FROM subscription_events e JOIN premium_subscribed p USING(user_id) WHERE e.event_type='paywall_view' AND e.plan_type IS NULL AND e.event_at > p.subscribed_at AND p.status<>'cancelada'",
 "trial con pago antes del fin de prueba": "SELECT COUNT(*) FROM premium_subscribed p WHERE trial_used=1 AND status='prueba' AND subscribed_at < DATE_SUB(" + CORTE + ", INTERVAL 30 DAY)",
}
malos = 0
for k, sql in checks.items():
    c.execute(sql); n = c.fetchone()[0]
    if n: malos += 1
    print(f"{'❌' if n else '✅'} {k}: {n}")
print("\nPROBLEMAS:", malos)
cx.close()
sys.exit(1 if malos else 0)
