# Diccionario de datos · `spotify_uadeo_db`

Lo crea `base de datos.py`: **19 tablas y 3 vistas**. Los datos simulados van del 1 de agosto al 4 de noviembre de 2026. Esta tabla se generó automáticamente a partir de `information_schema`.

**Leyenda:** PK = llave primaria · FK = llave foránea (→ tabla.columna referenciada) · AI = autoincremental

## Índice

- **Tablas principales:** [`users`](#users), [`songs`](#songs), [`song_played`](#song_played), [`playlist_created`](#playlist_created), [`song_liked`](#song_liked), [`premium_subscribed`](#premium_subscribed), [`user_recommendations`](#user_recommendations)
- **Tablas de telemetría:** [`app_sessions`](#app_sessions), [`recommendation_events`](#recommendation_events), [`search_events`](#search_events), [`ui_events`](#ui_events), [`playlist_tracks`](#playlist_tracks), [`artist_follows`](#artist_follows), [`download_events`](#download_events), [`share_events`](#share_events), [`ad_events`](#ad_events), [`subscription_events`](#subscription_events), [`notification_events`](#notification_events), [`app_performance_events`](#app_performance_events)
- **Vistas KPI (solo lectura):** [`v_telemetria_unificada`](#v_telemetria_unificada), [`v_kpi_recomendaciones`](#v_kpi_recomendaciones), [`v_kpi_reproduccion`](#v_kpi_reproduccion)

## Tablas principales

### users

Usuarios registrados. `account_type` = premium si tiene una suscripción no cancelada.

| Columna | Tipo | Nulo | Default | Llave |
|---|---|---|---|---|
| `user_id` | int(11) | no |  | PK AI |
| `username` | varchar(100) | no |  |  |
| `signup_date` | datetime | no |  |  |
| `email` | varchar(150) | sí |  |  |
| `birth_year` | smallint(6) | sí |  |  |
| `gender` | varchar(20) | sí | `'No especificado'` |  |
| `country` | char(2) | sí | `'MX'` |  |
| `city` | varchar(80) | sí |  |  |
| `state` | varchar(80) | sí |  |  |
| `signup_source` | varchar(50) | sí | `'organic'` |  |
| `signup_platform` | varchar(30) | sí | `'Android'` |  |
| `account_type` | varchar(20) | sí | `'free'` |  |

### songs

Catálogo de canciones con atributos de audio (0–1) y tempo (BPM).

| Columna | Tipo | Nulo | Default | Llave |
|---|---|---|---|---|
| `song_id` | int(11) | no |  | PK AI |
| `title` | varchar(150) | no |  |  |
| `artist` | varchar(150) | no |  |  |
| `album` | varchar(150) | sí |  |  |
| `genre` | varchar(60) | sí |  |  |
| `duration_ms` | int(11) | sí | `180000` |  |
| `release_date` | date | sí |  |  |
| `popularity` | tinyint(4) | sí | `50` |  |
| `explicit` | tinyint(1) | sí | `0` |  |
| `danceability` | decimal(4,3) | sí |  |  |
| `energy` | decimal(4,3) | sí |  |  |
| `valence` | decimal(4,3) | sí |  |  |
| `tempo` | decimal(6,2) | sí |  |  |

### song_played

Historial de reproducciones con la telemetría de reproducción de Spotify (fuente, motivo de inicio/fin, skip, shuffle, offline).

| Columna | Tipo | Nulo | Default | Llave |
|---|---|---|---|---|
| `play_id` | int(11) | no |  | PK AI |
| `user_id` | int(11) | sí |  | FK → `users.user_id` |
| `song_id` | int(11) | sí |  | FK → `songs.song_id` |
| `played_at` | datetime | no |  |  |
| `session_id` | int(11) | sí |  | FK → `app_sessions.session_id` |
| `ms_played` | int(11) | sí | `0` |  |
| `source` | varchar(40) | sí | `'manual'` |  |
| `source_detail` | varchar(150) | sí |  |  |
| `reason_start` | varchar(20) | sí | `'clickrow'` |  |
| `reason_end` | varchar(20) | sí | `'trackdone'` |  |
| `skipped` | tinyint(1) | sí | `0` |  |
| `shuffle` | tinyint(1) | sí | `0` |  |
| `offline` | tinyint(1) | sí | `0` |  |
| `device_type` | varchar(30) | sí | `'smartphone'` |  |
| `audio_quality` | varchar(15) | sí | `'normal'` |  |

### playlist_created

Playlists creadas por los usuarios.

| Columna | Tipo | Nulo | Default | Llave |
|---|---|---|---|---|
| `playlist_id` | int(11) | no |  | PK AI |
| `user_id` | int(11) | sí |  | FK → `users.user_id` |
| `playlist_name` | varchar(150) | no |  |  |
| `created_at` | datetime | no |  |  |
| `description` | varchar(255) | sí |  |  |
| `is_public` | tinyint(1) | sí | `1` |  |
| `is_collaborative` | tinyint(1) | sí | `0` |  |
| `followers` | int(11) | sí | `0` |  |

### song_liked

Canciones guardadas en *Tus me gusta* (un like por usuario y canción).

| Columna | Tipo | Nulo | Default | Llave |
|---|---|---|---|---|
| `like_id` | int(11) | no |  | PK AI |
| `user_id` | int(11) | sí |  | FK → `users.user_id` |
| `song_id` | int(11) | sí |  | FK → `songs.song_id` |
| `liked_at` | datetime | no |  |  |
| `source` | varchar(40) | sí | `'now_playing'` |  |

### premium_subscribed

Suscripciones Premium. `status`: activa, prueba o cancelada.

| Columna | Tipo | Nulo | Default | Llave |
|---|---|---|---|---|
| `subscription_id` | int(11) | no |  | PK AI |
| `user_id` | int(11) | sí |  | FK → `users.user_id` |
| `subscribed_at` | datetime | no |  |  |
| `plan_type` | varchar(50) | no |  |  |
| `price_mxn` | decimal(8,2) | sí |  |  |
| `payment_method` | varchar(30) | sí | `'tarjeta'` |  |
| `trial_used` | tinyint(1) | sí | `0` |  |
| `status` | varchar(20) | sí | `'activa'` |  |

### user_recommendations

Recomendaciones personalizadas que genera `recomendador.py` (10 por usuario), con la explicación y su estado (nueva, escuchada, guardada, descartada).

| Columna | Tipo | Nulo | Default | Llave |
|---|---|---|---|---|
| `recommendation_id` | int(11) | no |  | PK AI |
| `user_id` | int(11) | no |  | FK → `users.user_id` |
| `song_id` | int(11) | no |  | FK → `songs.song_id` |
| `rank_position` | tinyint(4) | no |  |  |
| `score` | decimal(5,4) | no |  |  |
| `genre_affinity` | decimal(5,4) | no |  |  |
| `artist_affinity` | decimal(5,4) | no |  |  |
| `audio_similarity` | decimal(5,4) | no |  |  |
| `reason` | varchar(200) | no |  |  |
| `based_on_song_id` | int(11) | sí |  | FK → `songs.song_id` |
| `algorithm` | varchar(40) | no |  |  |
| `status` | varchar(20) | no | `'nueva'` |  |
| `generated_at` | datetime | no |  |  |

## Tablas de telemetría

### app_sessions

Cada apertura de la app: dispositivo, red, versión y duración.

| Columna | Tipo | Nulo | Default | Llave |
|---|---|---|---|---|
| `session_id` | int(11) | no |  | PK AI |
| `user_id` | int(11) | no |  | FK → `users.user_id` |
| `device_type` | varchar(30) | no |  |  |
| `os` | varchar(30) | no |  |  |
| `app_version` | varchar(20) | no |  |  |
| `network_type` | varchar(10) | no |  |  |
| `city` | varchar(80) | sí |  |  |
| `started_at` | datetime | no |  |  |
| `ended_at` | datetime | no |  |  |
| `duration_sec` | int(11) | no |  |  |
| `tracks_played` | int(11) | sí | `0` |  |

### recommendation_events

Cada impresión de una recomendación en la app (superficie, algoritmo, grupo A/B) y lo que hizo el usuario con ella.

| Columna | Tipo | Nulo | Default | Llave |
|---|---|---|---|---|
| `rec_event_id` | int(11) | no |  | PK AI |
| `user_id` | int(11) | no |  | FK → `users.user_id` |
| `session_id` | int(11) | sí |  | FK → `app_sessions.session_id` |
| `song_id` | int(11) | no |  | FK → `songs.song_id` |
| `surface` | varchar(40) | no |  |  |
| `algorithm` | varchar(50) | no |  |  |
| `model_version` | varchar(20) | no |  |  |
| `ab_test_group` | char(1) | no |  |  |
| `position_in_list` | tinyint(4) | no |  |  |
| `relevance_score` | decimal(5,4) | no |  |  |
| `reason_shown` | varchar(150) | sí |  |  |
| `shown_at` | datetime | no |  |  |
| `clicked` | tinyint(1) | sí | `0` |  |
| `played` | tinyint(1) | sí | `0` |  |
| `ms_played` | int(11) | sí | `0` |  |
| `completed` | tinyint(1) | sí | `0` |  |
| `skipped` | tinyint(1) | sí | `0` |  |
| `saved` | tinyint(1) | sí | `0` |  |
| `added_to_playlist` | tinyint(1) | sí | `0` |  |
| `dismissed` | tinyint(1) | sí | `0` |  |

### search_events

Búsquedas y en qué resultado se hizo clic.

| Columna | Tipo | Nulo | Default | Llave |
|---|---|---|---|---|
| `search_id` | int(11) | no |  | PK AI |
| `user_id` | int(11) | no |  | FK → `users.user_id` |
| `session_id` | int(11) | sí |  | FK → `app_sessions.session_id` |
| `query_text` | varchar(150) | no |  |  |
| `search_type` | varchar(20) | no |  |  |
| `results_count` | int(11) | no |  |  |
| `clicked_song_id` | int(11) | sí |  | FK → `songs.song_id` |
| `click_position` | tinyint(4) | sí |  |  |
| `time_to_click_ms` | int(11) | sí |  |  |
| `searched_at` | datetime | no |  |  |

### ui_events

Interacciones con la interfaz (vistas de pantalla, clics, scroll).

| Columna | Tipo | Nulo | Default | Llave |
|---|---|---|---|---|
| `ui_event_id` | int(11) | no |  | PK AI |
| `user_id` | int(11) | no |  | FK → `users.user_id` |
| `session_id` | int(11) | sí |  | FK → `app_sessions.session_id` |
| `screen` | varchar(40) | no |  |  |
| `action` | varchar(30) | no |  |  |
| `element` | varchar(60) | no |  |  |
| `event_at` | datetime | no |  |  |

### playlist_tracks

Canciones dentro de cada playlist.

| Columna | Tipo | Nulo | Default | Llave |
|---|---|---|---|---|
| `playlist_track_id` | int(11) | no |  | PK AI |
| `playlist_id` | int(11) | no |  | FK → `playlist_created.playlist_id` |
| `song_id` | int(11) | no |  | FK → `songs.song_id` |
| `added_at` | datetime | no |  |  |
| `added_from` | varchar(40) | no |  |  |

### artist_follows

Artistas que sigue cada usuario.

| Columna | Tipo | Nulo | Default | Llave |
|---|---|---|---|---|
| `follow_id` | int(11) | no |  | PK AI |
| `user_id` | int(11) | no |  | FK → `users.user_id` |
| `artist` | varchar(150) | no |  |  |
| `followed_at` | datetime | no |  |  |
| `source` | varchar(40) | no |  |  |

### download_events

Descargas para escuchar offline (solo Premium).

| Columna | Tipo | Nulo | Default | Llave |
|---|---|---|---|---|
| `download_id` | int(11) | no |  | PK AI |
| `user_id` | int(11) | no |  | FK → `users.user_id` |
| `song_id` | int(11) | no |  | FK → `songs.song_id` |
| `audio_quality` | varchar(15) | no |  |  |
| `file_size_mb` | decimal(6,2) | no |  |  |
| `downloaded_at` | datetime | no |  |  |

### share_events

Canciones compartidas y si el enlace se abrió.

| Columna | Tipo | Nulo | Default | Llave |
|---|---|---|---|---|
| `share_id` | int(11) | no |  | PK AI |
| `user_id` | int(11) | no |  | FK → `users.user_id` |
| `song_id` | int(11) | no |  | FK → `songs.song_id` |
| `channel` | varchar(30) | no |  |  |
| `link_opened` | tinyint(1) | sí | `0` |  |
| `shared_at` | datetime | no |  |  |

### ad_events

Anuncios mostrados a usuarios free: impresión, clic, completado o saltado, con ingreso.

| Columna | Tipo | Nulo | Default | Llave |
|---|---|---|---|---|
| `ad_event_id` | int(11) | no |  | PK AI |
| `user_id` | int(11) | no |  | FK → `users.user_id` |
| `session_id` | int(11) | sí |  | FK → `app_sessions.session_id` |
| `ad_id` | varchar(20) | no |  |  |
| `advertiser` | varchar(60) | no |  |  |
| `ad_format` | varchar(15) | no |  |  |
| `event_type` | varchar(20) | no |  |  |
| `revenue_mxn` | decimal(6,3) | sí | `0.000` |  |
| `event_at` | datetime | no |  |  |

### subscription_events

Embudo de suscripción: paywall_view, trial_started, purchase, payment_failed, renewal, cancelled.

| Columna | Tipo | Nulo | Default | Llave |
|---|---|---|---|---|
| `sub_event_id` | int(11) | no |  | PK AI |
| `user_id` | int(11) | no |  | FK → `users.user_id` |
| `event_type` | varchar(30) | no |  |  |
| `plan_type` | varchar(50) | sí |  |  |
| `price_mxn` | decimal(8,2) | sí |  |  |
| `trigger_source` | varchar(50) | sí |  |  |
| `event_at` | datetime | no |  |  |

### notification_events

Notificaciones push/email/in-app enviadas, abiertas y convertidas.

| Columna | Tipo | Nulo | Default | Llave |
|---|---|---|---|---|
| `notif_id` | int(11) | no |  | PK AI |
| `user_id` | int(11) | no |  | FK → `users.user_id` |
| `campaign` | varchar(80) | no |  |  |
| `channel` | varchar(15) | no |  |  |
| `sent_at` | datetime | no |  |  |
| `opened_at` | datetime | sí |  |  |
| `converted` | tinyint(1) | sí | `0` |  |

### app_performance_events

Arranque de la app, buffering, errores de reproducción y crashes.

| Columna | Tipo | Nulo | Default | Llave |
|---|---|---|---|---|
| `perf_event_id` | int(11) | no |  | PK AI |
| `user_id` | int(11) | no |  | FK → `users.user_id` |
| `session_id` | int(11) | sí |  | FK → `app_sessions.session_id` |
| `event_type` | varchar(30) | no |  |  |
| `latency_ms` | int(11) | sí |  |  |
| `error_code` | varchar(30) | sí |  |  |
| `error_message` | varchar(150) | sí |  |  |
| `network_type` | varchar(10) | sí |  |  |
| `app_version` | varchar(20) | sí |  |  |
| `event_at` | datetime | no |  |  |

## Vistas KPI (solo lectura)

### v_telemetria_unificada

Vista: todos los eventos de todas las tablas en una sola línea de tiempo (`user_id`, `session_id`, `event_type`, `event_at`, `detalle`).

| Columna | Tipo | Nulo | Default | Llave |
|---|---|---|---|---|
| `user_id` | int(11) | sí |  |  |
| `session_id` | int(11) | sí |  |  |
| `event_type` | varchar(35) | no | `''` |  |
| `event_at` | datetime | no | `'0000-00-00 00:00:00'` |  |
| `detalle` | varchar(207) | sí |  |  |

### v_kpi_recomendaciones

Vista: KPIs de recomendaciones por superficie y algoritmo (CTR, % guardado, % skip, % completadas).

| Columna | Tipo | Nulo | Default | Llave |
|---|---|---|---|---|
| `surface` | varchar(40) | no |  |  |
| `algorithm` | varchar(50) | no |  |  |
| `impresiones` | bigint(21) | no | `0` |  |
| `clics` | decimal(25,0) | sí |  |  |
| `ctr_pct` | decimal(31,2) | sí |  |  |
| `save_rate_pct` | decimal(31,2) | sí |  |  |
| `skip_rate_pct` | decimal(31,2) | sí |  |  |
| `completion_rate_pct` | decimal(31,2) | sí |  |  |
| `score_promedio` | decimal(6,4) | sí |  |  |

### v_kpi_reproduccion

Vista: KPIs de reproducción por fuente (reproducciones, horas, % skip, % shuffle, % offline).

| Columna | Tipo | Nulo | Default | Llave |
|---|---|---|---|---|
| `source` | varchar(40) | sí | `'manual'` |  |
| `reproducciones` | bigint(21) | no | `0` |  |
| `horas_escuchadas` | decimal(35,2) | sí |  |  |
| `skip_rate_pct` | decimal(31,2) | sí |  |  |
| `shuffle_pct` | decimal(31,2) | sí |  |  |
| `offline_pct` | decimal(31,2) | sí |  |  |

## Reglas de borrado

- `song_played`, `playlist_created`, `song_liked` y `premium_subscribed` **no** tienen `ON DELETE CASCADE` hacia `users`/`songs`. Por eso la app borra primero esos registros dependientes cuando se elimina un usuario o una canción.
- Las tablas de telemetría y `user_recommendations` tienen `ON DELETE CASCADE`, así que se borran solas.
- `session_id`, `clicked_song_id` y `based_on_song_id` usan `ON DELETE SET NULL`: si se borra la sesión o la canción, el evento se conserva sin esa referencia.
