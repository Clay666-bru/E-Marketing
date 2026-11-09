import os
import sys
import random
import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import recomendador  # noqa: E402  (motor de recomendaciones según la música escuchada)

# Conexión a MySQL/MariaDB (XAMPP). Se puede cambiar con variables de entorno:
#   MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD y SPOTIFY_DB (nombre de la base de datos)
DB_NAME = os.environ.get("SPOTIFY_DB", "spotify_uadeo_db")
MYSQL_CONFIG = {
    'host': os.environ.get("MYSQL_HOST", "localhost"),
    'user': os.environ.get("MYSQL_USER", "root"),
    'password': os.environ.get("MYSQL_PASSWORD", ""),
}

# Fecha de "hoy" para la simulación (los datos se generan hasta un día antes)
FECHA_CORTE = datetime(2026, 11, 4, 23, 0, 0)

# Semilla fija: cada vez que se ejecute el script se generan exactamente los mismos datos
rnd = random.Random(2026)


def crear_conexion_servidor():
    """Establece conexión con el servidor MySQL (sin especificar BD para crearla si no existe)"""
    try:
        return mysql.connector.connect(**MYSQL_CONFIG)
    except Error as e:
        print(f"Error al conectar al servidor MySQL: {e}")
        return None


# =====================================================================
# CATÁLOGOS PARA LA SIMULACIÓN
# =====================================================================

# (title, artist, album, genre, duration_ms, release_date, popularity, explicit,
#  danceability, energy, valence, tempo)
CANCIONES = [
    ('ELA TA ROMPE', 'Chino Pacas', 'Que Sigan Llegando', 'Corridos tumbados', 162000, '2023-11-10', 78, 1, 0.71, 0.66, 0.74, 140.1),
    ('Lady Gaga', 'Peso Pluma', 'GÉNESIS', 'Corridos tumbados', 211000, '2023-06-22', 85, 1, 0.68, 0.61, 0.55, 132.0),
    ('PRC', 'Peso Pluma, Natanael Cano', 'GÉNESIS', 'Corridos tumbados', 184000, '2023-06-22', 88, 1, 0.78, 0.69, 0.81, 138.0),
    ('Que Onda', 'Calle 24, Chino Pacas', 'Que Onda', 'Corridos tumbados', 175000, '2024-02-15', 82, 1, 0.74, 0.70, 0.86, 136.5),
    ('HARLEY QUINN', 'Fuerza Regida, Marshmello', 'HARLEY QUINN', 'Regional mexicano', 158000, '2023-05-19', 80, 1, 0.83, 0.79, 0.88, 124.0),
    ('Ella Baila Sola', 'Eslabon Armado, Peso Pluma', 'DESVELADO', 'Regional mexicano', 165000, '2023-03-16', 92, 0, 0.67, 0.72, 0.83, 148.0),
    ('La Bebe - Remix', 'Yng Lvcas, Peso Pluma', 'La Bebe (Remix)', 'Reggaetón', 234000, '2023-03-17', 87, 1, 0.81, 0.69, 0.56, 170.0),
    ('Tulum', 'Peso Pluma, Grupo Frontera', 'GÉNESIS', 'Regional mexicano', 194000, '2023-06-22', 76, 0, 0.62, 0.58, 0.71, 126.0),
    ('Un x100to', 'Grupo Frontera, Bad Bunny', 'Un x100to', 'Regional mexicano', 194000, '2023-04-17', 89, 0, 0.57, 0.49, 0.53, 165.0),
    ('Bebe Dame', 'Fuerza Regida, Grupo Frontera', 'Pa Las Baby\'s Y Belikeada', 'Regional mexicano', 226000, '2022-12-16', 84, 0, 0.53, 0.55, 0.62, 104.0),
    ('AMG', 'Natanael Cano, Peso Pluma, Gabito Ballesteros', 'AMG', 'Corridos tumbados', 168000, '2022-11-25', 83, 1, 0.75, 0.71, 0.79, 137.0),
    ('Rosa Pastel', 'Peso Pluma, Jasiel Nuñez', 'GÉNESIS', 'Corridos tumbados', 186000, '2023-06-22', 74, 0, 0.64, 0.52, 0.60, 120.0),
    ('Si No Quieres No', 'Luis R Conriquez, Neton Vega', 'Corridos Bélicos IV', 'Corridos tumbados', 190000, '2024-01-26', 79, 0, 0.66, 0.60, 0.69, 134.0),
    ('Gata Only', 'FloyyMenor, Cris MJ', 'Gata Only', 'Reggaetón', 222000, '2024-02-02', 90, 1, 0.79, 0.59, 0.66, 100.0),
    ('Monaco', 'Bad Bunny', 'nadie sabe lo que va a pasar mañana', 'Trap latino', 267000, '2023-10-13', 86, 1, 0.61, 0.66, 0.37, 140.0),
    ('DtMF', 'Bad Bunny', 'DeBÍ TiRAR MáS FOToS', 'Reggaetón', 237000, '2025-01-05', 94, 0, 0.60, 0.62, 0.42, 136.0),
    ('BAILE INoLVIDABLE', 'Bad Bunny', 'DeBÍ TiRAR MáS FOToS', 'Salsa', 367000, '2025-01-05', 91, 0, 0.72, 0.68, 0.81, 118.0),
    ('Tú Con Él', 'Rauw Alejandro', 'Saturno', 'Reggaetón', 196000, '2022-11-11', 80, 0, 0.77, 0.73, 0.58, 96.0),
    ('Si Antes Te Hubiera Conocido', 'KAROL G', 'Si Antes Te Hubiera Conocido', 'Pop latino', 195000, '2024-06-21', 89, 0, 0.92, 0.66, 0.79, 128.0),
    ('TQG', 'KAROL G, Shakira', 'MAÑANA SERÁ BONITO', 'Reggaetón', 197000, '2023-02-24', 87, 1, 0.72, 0.63, 0.61, 180.0),
    ('Columbia', 'Quevedo', 'Columbia', 'Reggaetón', 186000, '2023-07-07', 83, 0, 0.86, 0.71, 0.55, 100.0),
    ('Flowers', 'Miley Cyrus', 'Endless Summer Vacation', 'Pop', 200000, '2023-01-13', 88, 0, 0.71, 0.68, 0.65, 118.0),
    ('Espresso', 'Sabrina Carpenter', 'Short n\' Sweet', 'Pop', 175000, '2024-04-11', 92, 1, 0.70, 0.76, 0.69, 104.0),
    ('Blinding Lights', 'The Weeknd', 'After Hours', 'Pop', 200000, '2019-11-29', 93, 0, 0.51, 0.73, 0.33, 171.0),
    ('APT.', 'ROSÉ, Bruno Mars', 'rosie', 'Pop', 170000, '2024-10-18', 95, 0, 0.78, 0.78, 0.94, 149.0),
    ('Die With A Smile', 'Lady Gaga, Bruno Mars', 'Die With A Smile', 'Pop', 251000, '2024-08-16', 94, 0, 0.52, 0.59, 0.53, 158.0),
    ('BIRDS OF A FEATHER', 'Billie Eilish', 'HIT ME HARD AND SOFT', 'Pop alternativo', 210000, '2024-05-17', 96, 0, 0.75, 0.51, 0.44, 105.0),
    ('Not Like Us', 'Kendrick Lamar', 'Not Like Us', 'Hip hop', 274000, '2024-05-04', 90, 1, 0.90, 0.47, 0.21, 101.0),
    ('Lose Control', 'Teddy Swims', 'I\'ve Tried Everything But Therapy', 'Soul', 210000, '2023-06-30', 89, 0, 0.56, 0.60, 0.21, 160.0),
    ('Cupido', 'Tini', 'Cupido', 'Pop latino', 172000, '2023-02-14', 79, 0, 0.89, 0.70, 0.84, 120.0),
    ('Tattoo', 'Loreen', 'Tattoo', 'Electrónica', 183000, '2023-02-25', 77, 0, 0.55, 0.60, 0.29, 150.0),
    ('Mi Bello Ángel', 'Natanael Cano', 'Mi Bello Ángel', 'Corridos tumbados', 158000, '2023-08-04', 75, 0, 0.62, 0.48, 0.64, 128.0),
    ('Cara Bonita', 'Eslabon Armado', 'Cara Bonita', 'Regional mexicano', 189000, '2023-09-01', 72, 0, 0.58, 0.45, 0.62, 116.0),
    ('Me Porto Bonito', 'Bad Bunny, Chencho Corleone', 'Un Verano Sin Ti', 'Reggaetón', 178000, '2022-05-06', 88, 1, 0.91, 0.71, 0.43, 92.0),
    ('Titi Me Preguntó', 'Bad Bunny', 'Un Verano Sin Ti', 'Reggaetón', 243000, '2022-05-06', 87, 1, 0.65, 0.72, 0.19, 107.0),
    ('Qlona', 'KAROL G, Peso Pluma', 'MAÑANA SERÁ BONITO (BICHOTA SEASON)', 'Reggaetón', 172000, '2023-08-11', 85, 1, 0.88, 0.80, 0.77, 96.0),
    ('Luna', 'Feid, ATL Jacob', 'MOR, No Le Temas a la Oscuridad', 'Reggaetón', 198000, '2023-09-29', 82, 0, 0.82, 0.62, 0.58, 98.0),
    ('Perro Negro', 'Bad Bunny, Feid', 'nadie sabe lo que va a pasar mañana', 'Reggaetón', 162000, '2023-10-13', 84, 1, 0.91, 0.73, 0.35, 96.0),
    ('Corazón de Piedra', 'Xavi', 'Corazón de Piedra', 'Regional mexicano', 175000, '2024-05-10', 81, 0, 0.55, 0.47, 0.61, 112.0),
    ('La Diabla', 'Xavi', 'La Diabla', 'Regional mexicano', 179000, '2023-11-17', 86, 0, 0.59, 0.51, 0.66, 108.0),
]

NOMBRES = ['Luis', 'María', 'José', 'Fernanda', 'Jesús', 'Valeria', 'Miguel', 'Daniela', 'Diego',
           'Camila', 'Alejandro', 'Ximena', 'Jorge', 'Sofía', 'Ricardo', 'Andrea', 'Emiliano',
           'Paola', 'Ángel', 'Regina', 'Kevin', 'Itzel', 'Manuel', 'Karla', 'Iván', 'Renata',
           'Oscar', 'Mariana', 'Héctor', 'Alondra', 'Brandon', 'Guadalupe', 'Rafael', 'Natalia',
           'Eduardo', 'Melissa', 'Fernando', 'Abril', 'Isaac', 'Jimena']
APELLIDOS = ['López', 'García', 'Hernández', 'Martínez', 'Ramírez', 'Félix', 'Castro', 'Quintero',
             'Leyva', 'Valenzuela', 'Rodríguez', 'Soto', 'Medina', 'Beltrán', 'Ochoa', 'Inzunza',
             'Arechiga', 'Meza', 'Camacho', 'Armenta']
CIUDADES = [('Los Mochis', 'Sinaloa'), ('Culiacán', 'Sinaloa'), ('Mazatlán', 'Sinaloa'),
            ('Guasave', 'Sinaloa'), ('Hermosillo', 'Sonora'), ('Guadalajara', 'Jalisco'),
            ('Ciudad de México', 'CDMX'), ('Monterrey', 'Nuevo León'), ('Tijuana', 'Baja California')]
DISPOSITIVOS = [('smartphone', 'Android', 0.55), ('smartphone', 'iOS', 0.25), ('desktop', 'Windows', 0.08),
                ('desktop', 'macOS', 0.03), ('web_player', 'Web', 0.04), ('smart_speaker', 'Alexa', 0.02),
                ('car', 'Android Auto', 0.02), ('tv', 'Smart TV', 0.01)]
VERSIONES_APP = ['8.9.86.551', '8.9.90.312', '8.9.94.410', '9.0.2.117', '9.0.6.205']
REDES = ['wifi', 'wifi', 'wifi', '4g', '4g', '5g', '3g']
PLANES = {'Individual Premium': 139.0, 'Dúo Premium': 179.0, 'Familiar Premium': 219.0, 'Estudiantil Premium': 75.0}

# Superficies de recomendación de Spotify -> (algoritmo, prob. de clic)
SUPERFICIES_REC = {
    'Home - Hecho para ti': ('hybrid_ranker', 0.18),
    'Discover Weekly': ('collaborative_filtering', 0.26),
    'Release Radar': ('artist_follow_new_releases', 0.22),
    'Daily Mix': ('content_based_audio_features', 0.30),
    'Radio de canción': ('content_based_audio_features', 0.33),
    'Autoplay': ('sequence_model_next_track', 0.55),
    'Smart Shuffle': ('contextual_bandit', 0.40),
    'DJ (IA)': ('llm_dj_curation', 0.35),
    'On Repeat': ('listening_history_frequency', 0.42),
    'Blend': ('collaborative_filtering_social', 0.20),
}
VERSIONES_MODELO = ['recs-v3.4.1', 'recs-v3.5.0', 'recs-v3.5.2-ab']
RAZONES_REC = ['Porque escuchaste {cancion}', 'Similar a {artista}', 'Popular en tu zona',
               'Nuevo lanzamiento de un artista que sigues', 'Basado en tus gustos recientes',
               'Tendencia en México', 'Fans de {artista} también escuchan esto']

PANTALLAS = ['home', 'search', 'your_library', 'now_playing', 'playlist_view', 'artist_page',
             'album_view', 'settings', 'premium_paywall', 'queue']
ACCIONES_UI = [('home', 'scroll', 'shelf_hecho_para_ti'), ('home', 'click', 'card_daily_mix'),
               ('now_playing', 'click', 'btn_shuffle'), ('now_playing', 'click', 'btn_repeat'),
               ('now_playing', 'click', 'btn_add_to_queue'), ('now_playing', 'click', 'btn_lyrics'),
               ('now_playing', 'click', 'btn_connect_device'), ('now_playing', 'seek', 'progress_bar'),
               ('now_playing', 'volume_change', 'volume_slider'), ('your_library', 'click', 'filter_playlists'),
               ('your_library', 'sort', 'sort_recently_played'), ('artist_page', 'click', 'btn_follow'),
               ('search', 'click', 'browse_genre_card'), ('playlist_view', 'click', 'btn_download'),
               ('settings', 'toggle', 'audio_quality'), ('premium_paywall', 'click', 'btn_try_free')]
CANALES_SHARE = ['WhatsApp', 'Instagram Stories', 'TikTok', 'X (Twitter)', 'Facebook', 'Copiar enlace', 'Snapchat']
ANUNCIANTES = [('AD-1001', 'Coca-Cola México', 'audio'), ('AD-1002', 'Mercado Libre', 'video'),
               ('AD-1003', 'Telcel', 'audio'), ('AD-1004', 'OXXO', 'banner'),
               ('AD-1005', 'Spotify Premium (auto-promo)', 'audio'), ('AD-1006', 'Bimbo', 'video'),
               ('AD-1007', 'Liverpool', 'banner'), ('AD-1008', 'Didi Food', 'audio')]
CAMPANIAS_NOTIF = [('Tu Discover Weekly está listo', 'push'), ('Nuevo lanzamiento de Peso Pluma', 'push'),
                   ('3 meses de Premium por $0', 'email'), ('Tu Wrapped está casi listo', 'in_app'),
                   ('Vuelve: te extrañamos', 'email'), ('Concierto cerca de ti', 'push'),
                   ('Tu Release Radar se actualizó', 'push')]
ERRORES = [('E_NETWORK_TIMEOUT', 'Tiempo de espera agotado'), ('E_DRM_LICENSE', 'Licencia DRM inválida'),
           ('E_CDN_404', 'Archivo de audio no encontrado en CDN'), ('E_DECODER', 'Error en decodificador de audio'),
           ('E_OFFLINE_EXPIRED', 'Descarga offline expirada'), ('E_APP_CRASH', 'Cierre inesperado de la app')]
BUSQUEDAS = ['peso pluma', 'corridos tumbados', 'bad bunny', 'karol g', 'xavi la diabla', 'musica para estudiar',
             'gym', 'chino pacas', 'fuerza regida', 'bruno mars', 'billie eilish', 'reggaeton viejito',
             'banda', 'natanael cano', 'lofi', 'top 50 mexico', 'podcast true crime', 'grupo frontera',
             'sabrina carpenter', 'ela ta rompe', 'canciones tristes', 'feid']


def elegir_dispositivo():
    r = rnd.random()
    acumulado = 0
    for tipo, so, p in DISPOSITIVOS:
        acumulado += p
        if r <= acumulado:
            return tipo, so
    return DISPOSITIVOS[0][0], DISPOSITIVOS[0][1]


def fmt(dt):
    return dt.strftime('%Y-%m-%d %H:%M:%S')


# =====================================================================
# CREACIÓN DE TABLAS
# =====================================================================

TABLAS_EN_ORDEN_DE_BORRADO = [
    # Recomendaciones personalizadas
    'user_recommendations',
    # Telemetría
    'app_performance_events', 'notification_events', 'subscription_events', 'ad_events',
    'share_events', 'download_events', 'ui_events', 'search_events', 'recommendation_events',
    'artist_follows', 'playlist_tracks',
    # Tablas base
    'premium_subscribed', 'song_liked', 'playlist_created', 'song_played', 'app_sessions',
    'songs', 'users',
]


def crear_tablas(cursor):
    cursor.execute("DROP VIEW IF EXISTS v_telemetria_unificada;")
    cursor.execute("DROP VIEW IF EXISTS v_kpi_recomendaciones;")
    cursor.execute("DROP VIEW IF EXISTS v_kpi_reproduccion;")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
    for tabla in TABLAS_EN_ORDEN_DE_BORRADO:
        cursor.execute(f"DROP TABLE IF EXISTS {tabla};")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

    # ---------------- TABLAS BASE (diccionario de datos original + columnas nuevas) ----------------
    # Las columnas nuevas tienen valores por defecto para que los INSERT de la app sigan funcionando.
    cursor.execute("""
    CREATE TABLE users (
        user_id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(100) NOT NULL,
        signup_date DATETIME NOT NULL,
        email VARCHAR(150) NULL,
        birth_year SMALLINT NULL,
        gender VARCHAR(20) DEFAULT 'No especificado',
        country CHAR(2) DEFAULT 'MX',
        city VARCHAR(80) NULL,
        state VARCHAR(80) NULL,
        signup_source VARCHAR(50) DEFAULT 'organic',
        signup_platform VARCHAR(30) DEFAULT 'Android',
        account_type VARCHAR(20) DEFAULT 'free'
    );
    """)

    cursor.execute("""
    CREATE TABLE songs (
        song_id INT AUTO_INCREMENT PRIMARY KEY,
        title VARCHAR(150) NOT NULL,
        artist VARCHAR(150) NOT NULL,
        album VARCHAR(150) NULL,
        genre VARCHAR(60) NULL,
        duration_ms INT DEFAULT 180000,
        release_date DATE NULL,
        popularity TINYINT DEFAULT 50,
        explicit TINYINT(1) DEFAULT 0,
        danceability DECIMAL(4,3) NULL,
        energy DECIMAL(4,3) NULL,
        valence DECIMAL(4,3) NULL,
        tempo DECIMAL(6,2) NULL
    );
    """)

    # TELEMETRÍA: sesiones de la app (cada apertura de Spotify)
    cursor.execute("""
    CREATE TABLE app_sessions (
        session_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        device_type VARCHAR(30) NOT NULL,
        os VARCHAR(30) NOT NULL,
        app_version VARCHAR(20) NOT NULL,
        network_type VARCHAR(10) NOT NULL,
        city VARCHAR(80) NULL,
        started_at DATETIME NOT NULL,
        ended_at DATETIME NOT NULL,
        duration_sec INT NOT NULL,
        tracks_played INT DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );
    """)

    # song_played ampliada con los campos de telemetría de reproducción de Spotify
    cursor.execute("""
    CREATE TABLE song_played (
        play_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT,
        song_id INT,
        played_at DATETIME NOT NULL,
        session_id INT NULL,
        ms_played INT DEFAULT 0,
        source VARCHAR(40) DEFAULT 'manual',
        source_detail VARCHAR(150) NULL,
        reason_start VARCHAR(20) DEFAULT 'clickrow',
        reason_end VARCHAR(20) DEFAULT 'trackdone',
        skipped TINYINT(1) DEFAULT 0,
        shuffle TINYINT(1) DEFAULT 0,
        offline TINYINT(1) DEFAULT 0,
        device_type VARCHAR(30) DEFAULT 'smartphone',
        audio_quality VARCHAR(15) DEFAULT 'normal',
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (song_id) REFERENCES songs(song_id),
        FOREIGN KEY (session_id) REFERENCES app_sessions(session_id) ON DELETE SET NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE playlist_created (
        playlist_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT,
        playlist_name VARCHAR(150) NOT NULL,
        created_at DATETIME NOT NULL,
        description VARCHAR(255) NULL,
        is_public TINYINT(1) DEFAULT 1,
        is_collaborative TINYINT(1) DEFAULT 0,
        followers INT DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE song_liked (
        like_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT,
        song_id INT,
        liked_at DATETIME NOT NULL,
        source VARCHAR(40) DEFAULT 'now_playing',
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (song_id) REFERENCES songs(song_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE premium_subscribed (
        subscription_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT,
        subscribed_at DATETIME NOT NULL,
        plan_type VARCHAR(50) NOT NULL,
        price_mxn DECIMAL(8,2) NULL,
        payment_method VARCHAR(30) DEFAULT 'tarjeta',
        trial_used TINYINT(1) DEFAULT 0,
        status VARCHAR(20) DEFAULT 'activa',
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );
    """)

    # ---------------- TABLAS NUEVAS DE TELEMETRÍA ----------------
    cursor.execute("""
    CREATE TABLE playlist_tracks (
        playlist_track_id INT AUTO_INCREMENT PRIMARY KEY,
        playlist_id INT NOT NULL,
        song_id INT NOT NULL,
        added_at DATETIME NOT NULL,
        added_from VARCHAR(40) NOT NULL,
        FOREIGN KEY (playlist_id) REFERENCES playlist_created(playlist_id) ON DELETE CASCADE,
        FOREIGN KEY (song_id) REFERENCES songs(song_id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE artist_follows (
        follow_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        artist VARCHAR(150) NOT NULL,
        followed_at DATETIME NOT NULL,
        source VARCHAR(40) NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );
    """)

    # Recomendaciones: cada impresión (canción mostrada) y lo que el usuario hizo con ella
    cursor.execute("""
    CREATE TABLE recommendation_events (
        rec_event_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        session_id INT NULL,
        song_id INT NOT NULL,
        surface VARCHAR(40) NOT NULL,
        algorithm VARCHAR(50) NOT NULL,
        model_version VARCHAR(20) NOT NULL,
        ab_test_group CHAR(1) NOT NULL,
        position_in_list TINYINT NOT NULL,
        relevance_score DECIMAL(5,4) NOT NULL,
        reason_shown VARCHAR(150) NULL,
        shown_at DATETIME NOT NULL,
        clicked TINYINT(1) DEFAULT 0,
        played TINYINT(1) DEFAULT 0,
        ms_played INT DEFAULT 0,
        completed TINYINT(1) DEFAULT 0,
        skipped TINYINT(1) DEFAULT 0,
        saved TINYINT(1) DEFAULT 0,
        added_to_playlist TINYINT(1) DEFAULT 0,
        dismissed TINYINT(1) DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
        FOREIGN KEY (session_id) REFERENCES app_sessions(session_id) ON DELETE SET NULL,
        FOREIGN KEY (song_id) REFERENCES songs(song_id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE search_events (
        search_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        session_id INT NULL,
        query_text VARCHAR(150) NOT NULL,
        search_type VARCHAR(20) NOT NULL,
        results_count INT NOT NULL,
        clicked_song_id INT NULL,
        click_position TINYINT NULL,
        time_to_click_ms INT NULL,
        searched_at DATETIME NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
        FOREIGN KEY (session_id) REFERENCES app_sessions(session_id) ON DELETE SET NULL,
        FOREIGN KEY (clicked_song_id) REFERENCES songs(song_id) ON DELETE SET NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE ui_events (
        ui_event_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        session_id INT NULL,
        screen VARCHAR(40) NOT NULL,
        action VARCHAR(30) NOT NULL,
        element VARCHAR(60) NOT NULL,
        event_at DATETIME NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
        FOREIGN KEY (session_id) REFERENCES app_sessions(session_id) ON DELETE SET NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE download_events (
        download_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        song_id INT NOT NULL,
        audio_quality VARCHAR(15) NOT NULL,
        file_size_mb DECIMAL(6,2) NOT NULL,
        downloaded_at DATETIME NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
        FOREIGN KEY (song_id) REFERENCES songs(song_id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE share_events (
        share_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        song_id INT NOT NULL,
        channel VARCHAR(30) NOT NULL,
        link_opened TINYINT(1) DEFAULT 0,
        shared_at DATETIME NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
        FOREIGN KEY (song_id) REFERENCES songs(song_id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE ad_events (
        ad_event_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        session_id INT NULL,
        ad_id VARCHAR(20) NOT NULL,
        advertiser VARCHAR(60) NOT NULL,
        ad_format VARCHAR(15) NOT NULL,
        event_type VARCHAR(20) NOT NULL,
        revenue_mxn DECIMAL(6,3) DEFAULT 0,
        event_at DATETIME NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
        FOREIGN KEY (session_id) REFERENCES app_sessions(session_id) ON DELETE SET NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE subscription_events (
        sub_event_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        event_type VARCHAR(30) NOT NULL,
        plan_type VARCHAR(50) NULL,
        price_mxn DECIMAL(8,2) NULL,
        trigger_source VARCHAR(50) NULL,
        event_at DATETIME NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE notification_events (
        notif_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        campaign VARCHAR(80) NOT NULL,
        channel VARCHAR(15) NOT NULL,
        sent_at DATETIME NOT NULL,
        opened_at DATETIME NULL,
        converted TINYINT(1) DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE app_performance_events (
        perf_event_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        session_id INT NULL,
        event_type VARCHAR(30) NOT NULL,
        latency_ms INT NULL,
        error_code VARCHAR(30) NULL,
        error_message VARCHAR(150) NULL,
        network_type VARCHAR(10) NULL,
        app_version VARCHAR(20) NULL,
        event_at DATETIME NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
        FOREIGN KEY (session_id) REFERENCES app_sessions(session_id) ON DELETE SET NULL
    );
    """)

    # Recomendaciones personalizadas según la música escuchada (ver recomendador.py)
    recomendador.asegurar_tabla(cursor)

    crear_vistas(cursor)
    print("[✔] Tablas base + 12 tablas de telemetría + user_recommendations creadas correctamente.")


def crear_vistas(cursor):
    # Todos los eventos de telemetría en una sola línea de tiempo
    cursor.execute("""
    CREATE VIEW v_telemetria_unificada AS
        SELECT user_id, session_id, 'app_session' AS event_type, started_at AS event_at,
               CONCAT(device_type, ' / ', os, ' / v', app_version) AS detalle
          FROM app_sessions
        UNION ALL
        SELECT sp.user_id, sp.session_id, 'song_played', sp.played_at,
               CONCAT(s.title, ' | ', sp.source, IF(sp.skipped = 1, ' | SKIP', ''))
          FROM song_played sp JOIN songs s ON s.song_id = sp.song_id
        UNION ALL
        SELECT r.user_id, r.session_id, 'recommendation_impression', r.shown_at,
               CONCAT(r.surface, ' #', r.position_in_list, ' -> ', s.title,
                      IF(r.clicked = 1, ' (clic)', ''))
          FROM recommendation_events r JOIN songs s ON s.song_id = r.song_id
        UNION ALL
        SELECT user_id, session_id, 'search', searched_at, CONCAT('"', query_text, '"') FROM search_events
        UNION ALL
        SELECT user_id, session_id, CONCAT('ui_', action), event_at, CONCAT(screen, ' > ', element) FROM ui_events
        UNION ALL
        SELECT user_id, NULL, 'song_liked', liked_at, CONCAT('song_id=', song_id) FROM song_liked
        UNION ALL
        SELECT user_id, NULL, 'playlist_created', created_at, playlist_name FROM playlist_created
        UNION ALL
        SELECT user_id, NULL, 'artist_follow', followed_at, artist FROM artist_follows
        UNION ALL
        SELECT user_id, NULL, 'download', downloaded_at, CONCAT('song_id=', song_id) FROM download_events
        UNION ALL
        SELECT user_id, NULL, 'share', shared_at, channel FROM share_events
        UNION ALL
        SELECT user_id, session_id, CONCAT('ad_', event_type), event_at, advertiser FROM ad_events
        UNION ALL
        SELECT user_id, NULL, CONCAT('sub_', event_type), event_at, IFNULL(plan_type, '') FROM subscription_events
        UNION ALL
        SELECT user_id, NULL, 'notification_sent', sent_at, campaign FROM notification_events
        UNION ALL
        SELECT user_id, session_id, CONCAT('perf_', event_type), event_at,
               IFNULL(error_code, CONCAT(latency_ms, ' ms'))
          FROM app_performance_events;
    """)

    # KPIs de recomendaciones por superficie (CTR, tasa de guardado, skip rate)
    cursor.execute("""
    CREATE VIEW v_kpi_recomendaciones AS
    SELECT surface,
           algorithm,
           COUNT(*) AS impresiones,
           SUM(clicked) AS clics,
           ROUND(100 * SUM(clicked) / COUNT(*), 2) AS ctr_pct,
           ROUND(100 * SUM(saved) / NULLIF(SUM(played), 0), 2) AS save_rate_pct,
           ROUND(100 * SUM(skipped) / NULLIF(SUM(played), 0), 2) AS skip_rate_pct,
           ROUND(100 * SUM(completed) / NULLIF(SUM(played), 0), 2) AS completion_rate_pct,
           ROUND(AVG(relevance_score), 4) AS score_promedio
      FROM recommendation_events
     GROUP BY surface, algorithm;
    """)

    # KPIs de reproducción por fuente
    cursor.execute("""
    CREATE VIEW v_kpi_reproduccion AS
    SELECT source,
           COUNT(*) AS reproducciones,
           ROUND(SUM(ms_played) / 3600000, 2) AS horas_escuchadas,
           ROUND(100 * SUM(skipped) / COUNT(*), 2) AS skip_rate_pct,
           ROUND(100 * SUM(shuffle) / COUNT(*), 2) AS shuffle_pct,
           ROUND(100 * SUM(offline) / COUNT(*), 2) AS offline_pct
      FROM song_played
     GROUP BY source;
    """)


# =====================================================================
# GENERACIÓN DE DATOS
# =====================================================================

class Generador:
    """Construye todas las filas en memoria con IDs explícitos y luego las inserta."""

    def __init__(self):
        self.users, self.songs, self.sessions, self.plays = [], [], [], []
        self.playlists, self.playlist_tracks, self.likes, self.premium = [], [], [], []
        self.follows, self.recs, self.searches, self.ui = [], [], [], []
        self.downloads, self.shares, self.ads, self.sub_events = [], [], [], []
        self.notifs, self.perf = [], []
        self.liked_pairs = set()
        self.followed_pairs = set()

    # ---------- catálogo ----------
    def crear_canciones(self):
        for i, c in enumerate(CANCIONES, start=1):
            self.songs.append((i,) + c)

    def song(self, song_id):
        return self.songs[song_id - 1]

    # ---------- usuarios ----------
    def crear_usuarios(self):
        # Usuarios originales del documento (se conservan sus nombres y fechas)
        originales = [
            (1, 'Dora Zatarain', datetime(2026, 9, 1, 10, 0), 'power'),
            (2, 'Carlos Perez', datetime(2026, 9, 2, 14, 30), 'minimo'),
            (3, 'Ana Gomez', datetime(2026, 9, 5, 9, 15), 'inactivo'),
        ]
        perfiles = []
        for uid, nombre, fecha, perfil in originales:
            perfiles.append((uid, nombre, fecha, perfil))

        # Usuarios adicionales simulados
        nombres_usados = {p[1] for p in perfiles}
        tipos = ['power'] * 12 + ['casual'] * 20 + ['churn'] * 10
        rnd.shuffle(tipos)
        for uid, perfil in enumerate(tipos, start=4):
            while True:
                nombre = f"{rnd.choice(NOMBRES)} {rnd.choice(APELLIDOS)}"
                if nombre not in nombres_usados:
                    nombres_usados.add(nombre)
                    break
            fecha = datetime(2026, 8, 1) + timedelta(days=rnd.randint(0, 85), hours=rnd.randint(7, 23),
                                                     minutes=rnd.randint(0, 59))
            perfiles.append((uid, nombre, fecha, perfil))

        self.perfiles = {}
        for uid, nombre, fecha, perfil in perfiles:
            ciudad, estado = rnd.choice(CIUDADES[:4]) if rnd.random() < 0.6 else rnd.choice(CIUDADES)
            _, so = elegir_dispositivo()
            email = (nombre.lower().replace(' ', '.').replace('á', 'a').replace('é', 'e')
                     .replace('í', 'i').replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n')) + f"{uid}@mail.com"
            self.users.append([uid, nombre, fmt(fecha), email, rnd.randint(1975, 2009),
                               rnd.choice(['Femenino', 'Masculino', 'Masculino', 'Femenino', 'No binario', 'No especificado']),
                               'MX', ciudad, estado,
                               rnd.choice(['organic', 'organic', 'tiktok_ads', 'instagram_ads', 'referral', 'google_ads', 'app_store_featured']),
                               so if so in ('Android', 'iOS', 'Web', 'Windows', 'macOS') else 'Android',
                               'free'])
            # Gustos del usuario: 2 géneros favoritos
            generos = sorted({c[3] for c in CANCIONES})
            self.perfiles[uid] = {'nombre': nombre, 'signup': fecha, 'perfil': perfil,
                                  'generos': rnd.sample(generos, 2), 'ciudad': ciudad,
                                  'dispositivo': elegir_dispositivo(), 'premium': False,
                                  'premium_desde': None, 'idx': len(self.users) - 1}

    # ---------- utilidades ----------
    def cancion_por_gusto(self, uid):
        gustos = self.perfiles[uid]['generos']
        if rnd.random() < 0.7:
            candidatas = [s for s in self.songs if s[4] in gustos]
            if candidatas:
                return rnd.choice(candidatas)
        return rnd.choice(self.songs)

    def es_premium(self, uid, momento):
        p = self.perfiles[uid]
        if not p['premium'] or p['premium_desde'] is None or momento < p['premium_desde']:
            return False
        # Si canceló, deja de ser Premium desde la fecha de cancelación
        return p.get('premium_hasta') is None or momento < p['premium_hasta']

    # ---------- sesiones y reproducciones ----------
    def nueva_sesion(self, uid, inicio, n_canciones, forzar_canciones=None):
        p = self.perfiles[uid]
        tipo, so = p['dispositivo'] if rnd.random() < 0.8 else elegir_dispositivo()
        version = rnd.choice(VERSIONES_APP)
        red = rnd.choice(REDES)
        session_id = len(self.sessions) + 1
        momento = inicio
        reproducidas = 0
        premium = self.es_premium(uid, inicio)
        calidad = rnd.choice(['high', 'very_high']) if premium else rnd.choice(['low', 'normal', 'normal'])
        shuffle = 1 if (not premium or rnd.random() < 0.35) else 0
        fuente_sesion = rnd.choice(['playlist', 'playlist', 'liked_songs', 'album', 'artist', 'search', 'recommendation'])

        # Eventos de arranque de la app
        latencia = rnd.randint(350, 1400) if red in ('wifi', '5g') else rnd.randint(900, 4200)
        self.perf.append([None, uid, session_id, 'app_startup', latencia, None, None, red, version, fmt(inicio)])
        self.ui.append([None, uid, session_id, 'home', 'screen_view', 'home_feed', fmt(inicio + timedelta(seconds=2))])

        # Impresiones de recomendaciones en Home
        self.generar_recomendaciones(uid, session_id, inicio + timedelta(seconds=3),
                                     rnd.choice(['Home - Hecho para ti', 'Discover Weekly', 'Daily Mix', 'Release Radar', 'DJ (IA)']),
                                     n=rnd.randint(4, 8))

        # Búsquedas
        if rnd.random() < 0.45:
            self.generar_busqueda(uid, session_id, momento + timedelta(seconds=rnd.randint(5, 40)))

        lista = forzar_canciones or [None] * n_canciones
        for forzada in lista:
            s = self.song(forzada) if forzada else self.cancion_por_gusto(uid)
            fuente, detalle = fuente_sesion, None
            if fuente == 'recommendation':
                surface = rnd.choice(list(SUPERFICIES_REC))
                detalle = surface
                # La lista completa que vio el usuario (impresiones sin clic) + la canción que eligió
                # (nunca antes de que empiece la sesión)
                self.generar_recomendaciones(uid, session_id, max(momento - timedelta(seconds=10), inicio), surface,
                                             n=rnd.randint(3, 6), sin_clic=True)
                self.generar_recomendaciones(uid, session_id, momento, surface, n=1, cancion=s, forzar_play=True)
            elif fuente == 'playlist':
                detalle = 'Playlist del usuario'
            reason_start = 'clickrow' if reproducidas == 0 else rnd.choice(['trackdone', 'trackdone', 'trackdone', 'fwdbtn', 'autoplay'])
            skip = rnd.random() < (0.22 if fuente != 'recommendation' else 0.30)
            if skip:
                ms = rnd.randint(4000, 30000)
                reason_end = rnd.choice(['fwdbtn', 'fwdbtn', 'backbtn', 'clickrow'])
            else:
                ms = s[5] - rnd.randint(0, 3000)
                reason_end = 'trackdone'
            offline = 1 if premium and red == '3g' and rnd.random() < 0.6 else 0
            self.plays.append([None, uid, s[0], fmt(momento), session_id, ms, fuente, detalle, reason_start,
                               reason_end, int(skip), shuffle, offline, tipo, calidad])
            reproducidas += 1

            # Interacciones durante la reproducción
            if rnd.random() < 0.10 and (uid, s[0]) not in self.liked_pairs:
                self.liked_pairs.add((uid, s[0]))
                self.likes.append([None, uid, s[0], fmt(momento + timedelta(seconds=20)),
                                   rnd.choice(['now_playing', 'now_playing', 'tracklist', 'recommendation', 'widget'])])
            if rnd.random() < 0.15:
                pantalla, accion, elemento = rnd.choice(ACCIONES_UI)
                self.ui.append([None, uid, session_id, pantalla, accion, elemento, fmt(momento + timedelta(seconds=rnd.randint(5, 60)))])
            if rnd.random() < 0.03:
                self.shares.append([None, uid, s[0], rnd.choice(CANALES_SHARE), int(rnd.random() < 0.4),
                                    fmt(momento + timedelta(seconds=30))])
            if rnd.random() < 0.04:
                latencia_buf = rnd.randint(800, 6000)
                self.perf.append([None, uid, session_id, 'buffering', latencia_buf, None, None, red, version,
                                  fmt(momento + timedelta(seconds=rnd.randint(1, 50)))])
            if rnd.random() < 0.012:
                code, msg = rnd.choice(ERRORES)
                self.perf.append([None, uid, session_id, 'crash' if code == 'E_APP_CRASH' else 'playback_error', None,
                                  code, msg, red, version, fmt(momento + timedelta(seconds=5))])
            if premium and rnd.random() < 0.05:
                calidad_d = rnd.choice(['normal', 'high', 'very_high'])
                tam = round(s[5] / 60000 * {'normal': 0.72, 'high': 1.2, 'very_high': 2.4}[calidad_d], 2)
                self.downloads.append([None, uid, s[0], calidad_d, tam, fmt(momento + timedelta(seconds=10))])

            # Anuncios para usuarios free: uno cada ~3 canciones
            if not premium and reproducidas % 3 == 0:
                ad_id, anunciante, formato = rnd.choice(ANUNCIANTES)
                t = momento + timedelta(milliseconds=ms)
                self.ads.append([None, uid, session_id, ad_id, anunciante, formato, 'impression', 0.045, fmt(t)])
                r = rnd.random()
                if r < 0.06:
                    self.ads.append([None, uid, session_id, ad_id, anunciante, formato, 'click', 0.35, fmt(t + timedelta(seconds=8))])
                elif r < 0.75:
                    self.ads.append([None, uid, session_id, ad_id, anunciante, formato, 'complete', 0.0, fmt(t + timedelta(seconds=30))])
                else:
                    self.ads.append([None, uid, session_id, ad_id, anunciante, formato, 'skip', 0.0, fmt(t + timedelta(seconds=5))])
                momento += timedelta(seconds=30)

            momento += timedelta(milliseconds=ms + rnd.randint(500, 3000))

        # Autoplay al final de la sesión
        if rnd.random() < 0.3:
            self.generar_recomendaciones(uid, session_id, momento, 'Autoplay', n=rnd.randint(1, 3))

        fin = momento + timedelta(seconds=rnd.randint(10, 120))
        self.sessions.append([session_id, uid, tipo, so, version, red, p['ciudad'], fmt(inicio), fmt(fin),
                              int((fin - inicio).total_seconds()), reproducidas])
        return session_id, fin

    def generar_recomendaciones(self, uid, session_id, momento, surface, n=5, cancion=None, forzar_play=False,
                                sin_clic=False):
        algoritmo, p_click = SUPERFICIES_REC[surface]
        grupo = 'A' if uid % 2 == 0 else 'B'
        modelo = VERSIONES_MODELO[2] if grupo == 'B' else rnd.choice(VERSIONES_MODELO[:2])
        for pos in range(1, n + 1):
            s = cancion or self.cancion_por_gusto(uid)
            afinidad = s[4] in self.perfiles[uid]['generos']
            score = round(min(0.9999, max(0.05, rnd.gauss(0.72 if afinidad else 0.45, 0.12))), 4)
            prob = p_click * (1.25 if afinidad else 0.7) * (1.1 if grupo == 'B' else 1.0) / (1 + 0.15 * (pos - 1))
            clic = 1 if forzar_play else (0 if sin_clic else int(rnd.random() < prob))
            played = clic
            completed = skipped = saved = added = ms = 0
            if played:
                if rnd.random() < (0.72 if afinidad else 0.45):
                    completed, ms = 1, s[5]
                    saved = 1 if rnd.random() < 0.18 else 0
                    added = 1 if rnd.random() < 0.08 else 0
                else:
                    skipped, ms = 1, rnd.randint(3000, 30000)
            dismissed = 1 if (not clic and rnd.random() < 0.04) else 0
            artista_ref = self.cancion_por_gusto(uid)
            razon = rnd.choice(RAZONES_REC).format(cancion=artista_ref[1], artista=artista_ref[2].split(',')[0])
            self.recs.append([None, uid, session_id, s[0], surface, algoritmo, modelo, grupo, pos, score, razon,
                              fmt(momento + timedelta(seconds=pos)), clic, played, ms, completed, skipped, saved,
                              added, dismissed])
            if saved and (uid, s[0]) not in self.liked_pairs:
                self.liked_pairs.add((uid, s[0]))
                self.likes.append([None, uid, s[0], fmt(momento + timedelta(seconds=pos + 40)), 'recommendation'])

    def generar_busqueda(self, uid, session_id, momento):
        q = rnd.choice(BUSQUEDAS)
        tipo = 'podcast' if 'podcast' in q else rnd.choice(['track', 'track', 'artist', 'playlist'])
        resultados = rnd.randint(0, 3) if 'podcast' in q else rnd.randint(8, 50)
        coincidencias = [s for s in self.songs if any(w in (s[1] + ' ' + s[2]).lower() for w in q.split() if len(w) > 3)]
        clic = None
        pos = tiempo = None
        if resultados and rnd.random() < 0.78:
            clic = (rnd.choice(coincidencias) if coincidencias else rnd.choice(self.songs))[0]
            pos = rnd.choice([1, 1, 1, 2, 2, 3, 4, 6])
            tiempo = rnd.randint(1200, 9000)
        self.searches.append([None, uid, session_id, q, tipo, resultados, clic, pos, tiempo, fmt(momento)])
        self.ui.append([None, uid, session_id, 'search', 'screen_view', 'search_bar', fmt(momento - timedelta(seconds=3))])

    # ---------- actividad por perfil ----------
    def simular_actividad(self):
        for uid, p in self.perfiles.items():
            signup = p['signup']
            perfil = p['perfil']

            if perfil == 'inactivo':
                # Ana Gomez: se registró y nunca escuchó nada (dato original)
                self.notificacion(uid, signup + timedelta(days=3), forzar_campania=('Vuelve: te extrañamos', 'email'))
                continue

            if perfil == 'minimo':
                # Carlos Perez: solo 2 canciones (datos originales: canciones 1 y 3)
                self.nueva_sesion(uid, datetime(2026, 9, 2, 15, 0), 0, forzar_canciones=[1])
                self.nueva_sesion(uid, datetime(2026, 9, 2, 16, 0), 0, forzar_canciones=[3])
                self.crear_playlist(uid, 'Mi Playlist', datetime(2026, 9, 3, 10, 0), canciones=[1, 3])
                self.notificacion(uid, datetime(2026, 9, 10, 18, 0))
                self.notificacion(uid, datetime(2026, 10, 1, 18, 0))
                continue

            if uid == 1:
                # Dora Zatarain: cumple el Aha! Moment y se hace Premium el 2026-09-04
                p['premium'] = True
                p['premium_desde'] = datetime(2026, 9, 4, 15, 0)
                self.crear_playlist(uid, 'Corridos Tumbados 2026', datetime(2026, 9, 2, 12, 0),
                                    canciones=[1, 2, 3, 4, 5, 11, 13])
                self.liked_pairs.add((1, 2))
                self.likes.append([None, 1, 2, '2026-09-02 12:05:00', 'now_playing'])
                self.suscribir(uid, datetime(2026, 9, 4, 15, 0), 'Individual Premium', trial=False)

            # Frecuencia de uso por perfil
            if perfil == 'power':
                dias_activos_prob, sesiones_dia, canciones_sesion = 0.85, (1, 3), (4, 12)
                ultimo_dia = FECHA_CORTE
            elif perfil == 'casual':
                dias_activos_prob, sesiones_dia, canciones_sesion = 0.35, (1, 2), (2, 6)
                ultimo_dia = FECHA_CORTE
            else:  # churn: usa la app las primeras 1-3 semanas y abandona
                dias_activos_prob, sesiones_dia, canciones_sesion = 0.5, (1, 1), (1, 5)
                ultimo_dia = min(FECHA_CORTE, signup + timedelta(days=rnd.randint(5, 21)))

            # Decisión de conversión a Premium
            if uid != 1 and perfil in ('power', 'casual'):
                prob_premium = 0.65 if perfil == 'power' else 0.2
                if rnd.random() < prob_premium:
                    p['premium'] = True
                    p['premium_desde'] = signup + timedelta(days=rnd.randint(3, 25), hours=rnd.randint(0, 12))
                    if p['premium_desde'] > FECHA_CORTE:
                        p['premium'] = False
                        p['premium_desde'] = None

            # Suscripción: se registra antes de simular los días para que, si el usuario
            # cancela, a partir de esa fecha vuelva a ser free (anuncios, calidad normal, etc.)
            if p['premium'] and uid != 1:
                plan = rnd.choice(['Individual Premium', 'Individual Premium', 'Estudiantil Premium', 'Dúo Premium', 'Familiar Premium'])
                self.suscribir(uid, p['premium_desde'], plan, trial=rnd.random() < 0.6)

            # Playlists del usuario en sus primeros días
            n_playlists = {'power': rnd.randint(1, 4), 'casual': rnd.randint(0, 2), 'churn': rnd.randint(0, 1)}[perfil]
            if uid == 1:
                n_playlists = 2
            nombres_pl = ['Para el gym', 'Pa la carretera', 'Estudiar', 'Fiesta', 'Corridos', 'Chill', 'Bellakeo',
                          'Mis favoritas', 'Viernes', 'Desamor', 'Top 2026', 'Para manejar']
            for _ in range(n_playlists):
                fecha_pl = signup + timedelta(days=rnd.randint(0, 6), hours=rnd.randint(1, 12))
                if fecha_pl < ultimo_dia:
                    self.crear_playlist(uid, rnd.choice(nombres_pl), fecha_pl)

            # Seguir artistas
            for _ in range(rnd.randint(1, 6) if perfil != 'churn' else rnd.randint(0, 2)):
                artista = self.cancion_por_gusto(uid)[2].split(',')[0].strip()
                if (uid, artista) not in self.followed_pairs:
                    self.followed_pairs.add((uid, artista))
                    fecha_f = signup + timedelta(days=rnd.randint(0, 20), hours=rnd.randint(0, 12))
                    if fecha_f < ultimo_dia:
                        self.follows.append([None, uid, artista, fmt(fecha_f),
                                             rnd.choice(['artist_page', 'now_playing', 'search', 'onboarding'])])

            # Días de uso
            dia = signup
            primer_semana_canciones = 0
            while dia < ultimo_dia:
                en_primer_semana = dia < signup + timedelta(days=7)
                activo = (dia == signup) or rnd.random() < dias_activos_prob or (uid == 1 and en_primer_semana)
                if activo:
                    for _ in range(rnd.randint(*sesiones_dia)):
                        hora = dia.replace(hour=rnd.choice([7, 8, 9, 13, 14, 17, 18, 19, 20, 21, 22, 23]),
                                           minute=rnd.randint(0, 59))
                        if hora < signup:
                            hora = signup + timedelta(minutes=5)
                        # Una sesión dura a lo mucho ~1.5 h: si empieza 3 h antes del corte
                        # ninguna reproducción o evento queda después de FECHA_CORTE
                        if hora >= FECHA_CORTE - timedelta(hours=3):
                            break
                        n = rnd.randint(*canciones_sesion)
                        if uid == 1 and en_primer_semana:
                            n = max(n, 5)
                        self.nueva_sesion(uid, hora, n)
                        if en_primer_semana:
                            primer_semana_canciones += n
                    # Pantalla de Premium para usuarios free (nunca antes del registro ni después del corte)
                    if rnd.random() < 0.15:
                        motivo = rnd.choice(['skip_limit_reached', 'ad_break', 'download_button', 'home_banner'])
                        momento_pw = max(dia.replace(hour=20, minute=rnd.randint(0, 59)), signup + timedelta(minutes=10))
                        if momento_pw <= FECHA_CORTE and not self.es_premium(uid, momento_pw):
                            self.sub_events.append([None, uid, 'paywall_view', None, None, motivo, fmt(momento_pw)])
                dia = (dia + timedelta(days=1)).replace(hour=0, minute=0)

            # Notificaciones push/email
            for _ in range(rnd.randint(1, 5)):
                self.notificacion(uid, signup + timedelta(days=rnd.randint(1, 60), hours=rnd.randint(9, 20)))

            # Churn: cancelación si era premium
            if perfil == 'churn':
                self.notificacion(uid, ultimo_dia + timedelta(days=7), forzar_campania=('Vuelve: te extrañamos', 'email'))

    def crear_playlist(self, uid, nombre, fecha, canciones=None):
        pid = len(self.playlists) + 1
        self.playlists.append([pid, uid, nombre, fmt(fecha),
                               rnd.choice([None, 'Mis rolas', 'Para todo el día', 'Solo éxitos', None]),
                               int(rnd.random() < 0.7), int(rnd.random() < 0.1), rnd.choice([0, 0, 0, 1, 2, 5, 12])])
        if canciones is None:
            canciones = sorted({self.cancion_por_gusto(uid)[0] for _ in range(rnd.randint(3, 15))})
        for i, sid in enumerate(canciones):
            self.playlist_tracks.append([None, pid, sid, fmt(fecha + timedelta(minutes=i * 2)),
                                         rnd.choice(['search', 'now_playing', 'recommended_songs', 'album_view', 'liked_songs'])])
        return pid

    def suscribir(self, uid, fecha, plan, trial):
        precio = PLANES[plan]
        p = self.perfiles[uid]
        self.sub_events.append([None, uid, 'paywall_view', plan, precio, 'skip_limit_reached', fmt(fecha - timedelta(minutes=10))])
        if trial:
            self.sub_events.append([None, uid, 'trial_started', plan, 0, 'oferta_1_mes_gratis', fmt(fecha)])
            pago = fecha + timedelta(days=30)
        else:
            pago = fecha
        status = 'activa'
        if pago <= FECHA_CORTE:
            if rnd.random() < 0.08 and uid != 1:
                self.sub_events.append([None, uid, 'payment_failed', plan, precio, 'tarjeta_rechazada', fmt(pago)])
                pago = pago + timedelta(days=2)
            self.sub_events.append([None, uid, 'purchase', plan, precio, 'checkout', fmt(pago)])
            renovacion = pago + timedelta(days=30)
            while renovacion <= FECHA_CORTE:
                if uid != 1 and rnd.random() < 0.07:
                    self.sub_events.append([None, uid, 'cancelled', plan, None, rnd.choice(['precio', 'ya_no_lo_uso', 'cambio_a_otra_app']), fmt(renovacion)])
                    status = 'cancelada'
                    p['premium_hasta'] = renovacion
                    break
                self.sub_events.append([None, uid, 'renewal', plan, precio, 'auto_renew', fmt(renovacion)])
                renovacion += timedelta(days=30)
        else:
            status = 'prueba'
        self.premium.append([None, uid, fmt(fecha), plan, precio,
                             rnd.choice(['tarjeta', 'tarjeta', 'paypal', 'oxxo_pay', 'tarjeta_regalo']) if uid != 1 else 'tarjeta',
                             int(trial), status])
        self.users[p['idx']][11] = 'premium' if status != 'cancelada' else 'free'

    def notificacion(self, uid, fecha, forzar_campania=None):
        if fecha > FECHA_CORTE:
            return
        campania, canal = forzar_campania or rnd.choice(CAMPANIAS_NOTIF)
        abierta = rnd.random() < {'push': 0.18, 'email': 0.22, 'in_app': 0.45}[canal]
        abierta_en = fmt(fecha + timedelta(minutes=rnd.randint(1, 600))) if abierta else None
        convertida = int(abierta and rnd.random() < 0.3)
        self.notifs.append([None, uid, campania, canal, fmt(fecha), abierta_en, convertida])

    def ordenar_por_fecha(self):
        """Ordena los eventos cronológicamente para que los IDs sigan el tiempo."""
        self.plays.sort(key=lambda r: r[3])
        self.likes.sort(key=lambda r: r[3])
        self.recs.sort(key=lambda r: r[11])
        self.searches.sort(key=lambda r: r[9])
        self.ui.sort(key=lambda r: r[6])
        self.ads.sort(key=lambda r: r[8])
        self.sub_events.sort(key=lambda r: r[6])
        self.notifs.sort(key=lambda r: r[4])
        self.perf.sort(key=lambda r: r[9])
        self.premium.sort(key=lambda r: r[2])
        self.follows.sort(key=lambda r: r[3])
        self.shares.sort(key=lambda r: r[5])
        self.downloads.sort(key=lambda r: r[5])


def insertar(cursor, tabla, columnas, filas, con_id=True):
    """Inserta filas en lote. Si con_id=False se descarta la primera columna (ID autoincremental)."""
    if not filas:
        return
    if not con_id:
        filas = [tuple(f[1:]) for f in filas]
    placeholders = ', '.join(['%s'] * len(columnas))
    sql = f"INSERT INTO {tabla} ({', '.join(columnas)}) VALUES ({placeholders})"
    for i in range(0, len(filas), 500):
        cursor.executemany(sql, [tuple(f) for f in filas[i:i + 500]])


def insertar_datos(cursor):
    g = Generador()
    g.crear_canciones()
    g.crear_usuarios()
    g.simular_actividad()
    g.ordenar_por_fecha()

    insertar(cursor, 'users', ['user_id', 'username', 'signup_date', 'email', 'birth_year', 'gender', 'country',
                               'city', 'state', 'signup_source', 'signup_platform', 'account_type'], g.users)
    insertar(cursor, 'songs', ['song_id', 'title', 'artist', 'album', 'genre', 'duration_ms', 'release_date',
                               'popularity', 'explicit', 'danceability', 'energy', 'valence', 'tempo'], g.songs)
    insertar(cursor, 'app_sessions', ['session_id', 'user_id', 'device_type', 'os', 'app_version', 'network_type',
                                      'city', 'started_at', 'ended_at', 'duration_sec', 'tracks_played'], g.sessions)
    insertar(cursor, 'song_played', ['user_id', 'song_id', 'played_at', 'session_id', 'ms_played', 'source',
                                     'source_detail', 'reason_start', 'reason_end', 'skipped', 'shuffle', 'offline',
                                     'device_type', 'audio_quality'], g.plays, con_id=False)
    insertar(cursor, 'playlist_created', ['playlist_id', 'user_id', 'playlist_name', 'created_at', 'description',
                                          'is_public', 'is_collaborative', 'followers'], g.playlists)
    insertar(cursor, 'playlist_tracks', ['playlist_id', 'song_id', 'added_at', 'added_from'], g.playlist_tracks, con_id=False)
    insertar(cursor, 'song_liked', ['user_id', 'song_id', 'liked_at', 'source'], g.likes, con_id=False)
    insertar(cursor, 'premium_subscribed', ['user_id', 'subscribed_at', 'plan_type', 'price_mxn', 'payment_method',
                                            'trial_used', 'status'], g.premium, con_id=False)
    insertar(cursor, 'artist_follows', ['user_id', 'artist', 'followed_at', 'source'], g.follows, con_id=False)
    insertar(cursor, 'recommendation_events', ['user_id', 'session_id', 'song_id', 'surface', 'algorithm',
                                               'model_version', 'ab_test_group', 'position_in_list', 'relevance_score',
                                               'reason_shown', 'shown_at', 'clicked', 'played', 'ms_played', 'completed',
                                               'skipped', 'saved', 'added_to_playlist', 'dismissed'], g.recs, con_id=False)
    insertar(cursor, 'search_events', ['user_id', 'session_id', 'query_text', 'search_type', 'results_count',
                                       'clicked_song_id', 'click_position', 'time_to_click_ms', 'searched_at'],
             g.searches, con_id=False)
    insertar(cursor, 'ui_events', ['user_id', 'session_id', 'screen', 'action', 'element', 'event_at'], g.ui, con_id=False)
    insertar(cursor, 'download_events', ['user_id', 'song_id', 'audio_quality', 'file_size_mb', 'downloaded_at'],
             g.downloads, con_id=False)
    insertar(cursor, 'share_events', ['user_id', 'song_id', 'channel', 'link_opened', 'shared_at'], g.shares, con_id=False)
    insertar(cursor, 'ad_events', ['user_id', 'session_id', 'ad_id', 'advertiser', 'ad_format', 'event_type',
                                   'revenue_mxn', 'event_at'], g.ads, con_id=False)
    insertar(cursor, 'subscription_events', ['user_id', 'event_type', 'plan_type', 'price_mxn', 'trigger_source',
                                             'event_at'], g.sub_events, con_id=False)
    insertar(cursor, 'notification_events', ['user_id', 'campaign', 'channel', 'sent_at', 'opened_at', 'converted'],
             g.notifs, con_id=False)
    insertar(cursor, 'app_performance_events', ['user_id', 'session_id', 'event_type', 'latency_ms', 'error_code',
                                                'error_message', 'network_type', 'app_version', 'event_at'],
             g.perf, con_id=False)

    resumen = {
        'users': g.users, 'songs': g.songs, 'app_sessions': g.sessions, 'song_played': g.plays,
        'playlist_created': g.playlists, 'playlist_tracks': g.playlist_tracks, 'song_liked': g.likes,
        'premium_subscribed': g.premium, 'artist_follows': g.follows, 'recommendation_events': g.recs,
        'search_events': g.searches, 'ui_events': g.ui, 'download_events': g.downloads,
        'share_events': g.shares, 'ad_events': g.ads, 'subscription_events': g.sub_events,
        'notification_events': g.notifs, 'app_performance_events': g.perf,
    }
    print("[✔] Datos insertados:")
    for tabla, filas in resumen.items():
        print(f"    - {tabla:<24} {len(filas):>6} registros")


def inicializar_base_datos_sql():
    servidor_conexion = crear_conexion_servidor()
    if not servidor_conexion:
        return

    cursor = servidor_conexion.cursor()

    # 1. Crear la Base de Datos local si no existe
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    cursor.execute(f"USE {DB_NAME};")
    print(f"[✔] Base de datos '{DB_NAME}' creada y seleccionada exitosamente.")

    # 2. Tablas
    crear_tablas(cursor)

    # 3. Datos
    insertar_datos(cursor)

    servidor_conexion.commit()

    # 4. Recomendaciones personalizadas (top 10 por usuario según lo que ha escuchado)
    total_recs = recomendador.guardar_recomendaciones(servidor_conexion, top_n=10, generado_en=FECHA_CORTE)
    print(f"[✔] {total_recs} recomendaciones personalizadas generadas en user_recommendations.")

    cursor.close()
    servidor_conexion.close()
    print("[✔] Datos reales, historiales y telemetría insertados correctamente.\n")


def imprimir_tabla(cursor, titulo, query):
    print("=" * 70)
    print(titulo)
    print("=" * 70)
    cursor.execute(query)
    columnas = [d[0] for d in cursor.description]
    filas = cursor.fetchall()
    anchos = [max(len(str(c)), *(len(str(f[i])) for f in filas)) if filas else len(str(c)) for i, c in enumerate(columnas)]
    print(" | ".join(str(c).ljust(a) for c, a in zip(columnas, anchos)))
    print("-+-".join('-' * a for a in anchos))
    for f in filas:
        print(" | ".join(str(v).ljust(a) for v, a in zip(f, anchos)))
    print()


def ejecutar_consultas_analiticas():
    """Se conecta a la base de datos local para realizar consultas simuladas de negocio"""
    conexion = mysql.connector.connect(**MYSQL_CONFIG, database=DB_NAME)
    cursor = conexion.cursor()

    print("=" * 70)
    print("CONSULTA SQL 1: Validación de Hipótesis de Retención (Aha! Moment)")
    print("Usuarios que crearon al menos 1 playlist Y reprodujeron >= 20 canciones en sus primeros 7 días:")
    print("=" * 70)

    query_aha = """
    SELECT
        u.user_id,
        u.username,
        u.signup_date,
        COUNT(DISTINCT p.playlist_id) AS total_playlists,
        COUNT(DISTINCT sp.play_id) AS total_songs_played
    FROM users u
    JOIN playlist_created p ON u.user_id = p.user_id
    JOIN song_played sp ON u.user_id = sp.user_id
    WHERE sp.played_at >= u.signup_date
      AND sp.played_at <= DATE_ADD(u.signup_date, INTERVAL 7 DAY)
      AND p.created_at >= u.signup_date
      AND p.created_at <= DATE_ADD(u.signup_date, INTERVAL 7 DAY)
    GROUP BY u.user_id, u.username, u.signup_date
    HAVING total_playlists >= 1 AND total_songs_played >= 20;
    """

    cursor.execute(query_aha)
    resultados = cursor.fetchall()

    if resultados:
        for row in resultados:
            print(f"ID: {row[0]} | Usuario: {row[1]} | Registro: {row[2]}")
            print(f" -> Playlists creadas en 7 días: {row[3]}")
            print(f" -> Canciones reproducidas en 7 días: {row[4]}")
        print(f"\n[ESTADO]: {len(resultados)} usuarios cumplen el Aha! Moment.\n")
    else:
        print("No se encontraron usuarios que cumplan con la métrica exacta en este rango.\n")

    imprimir_tabla(cursor, "CONSULTA SQL 2: Conversión a Suscriptores Premium (premium_subscribed)", """
        SELECT ps.plan_type, ps.status, COUNT(*) AS suscriptores, SUM(ps.trial_used) AS con_prueba
          FROM premium_subscribed ps
         GROUP BY ps.plan_type, ps.status
         ORDER BY suscriptores DESC;
    """)

    imprimir_tabla(cursor, "TELEMETRÍA 1: KPIs de Recomendaciones por superficie", """
        SELECT surface, impresiones, clics, ctr_pct, save_rate_pct, skip_rate_pct, completion_rate_pct
          FROM v_kpi_recomendaciones ORDER BY ctr_pct DESC;
    """)

    imprimir_tabla(cursor, "TELEMETRÍA 2: Prueba A/B del modelo de recomendaciones", """
        SELECT ab_test_group, model_version, COUNT(*) AS impresiones,
               ROUND(100 * AVG(clicked), 2) AS ctr_pct, ROUND(100 * SUM(saved) / NULLIF(SUM(played), 0), 2) AS save_rate_pct
          FROM recommendation_events GROUP BY ab_test_group, model_version ORDER BY ab_test_group;
    """)

    imprimir_tabla(cursor, "TELEMETRÍA 3: Reproducción por fuente", """
        SELECT * FROM v_kpi_reproduccion ORDER BY reproducciones DESC;
    """)

    imprimir_tabla(cursor, "TELEMETRÍA 4: Sesiones por dispositivo", """
        SELECT device_type, os, COUNT(*) AS sesiones, ROUND(AVG(duration_sec) / 60, 1) AS min_promedio,
               ROUND(AVG(tracks_played), 1) AS canciones_promedio
          FROM app_sessions GROUP BY device_type, os ORDER BY sesiones DESC;
    """)

    imprimir_tabla(cursor, "TELEMETRÍA 5: Embudo de suscripción", """
        SELECT event_type, COUNT(*) AS eventos, COUNT(DISTINCT user_id) AS usuarios
          FROM subscription_events GROUP BY event_type ORDER BY eventos DESC;
    """)

    imprimir_tabla(cursor, "TELEMETRÍA 6: Publicidad (usuarios free)", """
        SELECT advertiser, ad_format,
               SUM(event_type = 'impression') AS impresiones, SUM(event_type = 'click') AS clics,
               SUM(event_type = 'skip') AS saltados, ROUND(SUM(revenue_mxn), 2) AS ingreso_mxn
          FROM ad_events GROUP BY advertiser, ad_format ORDER BY impresiones DESC;
    """)

    imprimir_tabla(cursor, "TELEMETRÍA 7: Rendimiento y errores de la app", """
        SELECT event_type, IFNULL(error_code, '-') AS error_code, COUNT(*) AS eventos,
               ROUND(AVG(latency_ms)) AS latencia_promedio_ms
          FROM app_performance_events GROUP BY event_type, error_code ORDER BY eventos DESC;
    """)

    imprimir_tabla(cursor, "RECOMENDACIONES: Top 5 para Dora Zatarain según su música escuchada", """
        SELECT ur.rank_position AS pos, s.title, s.artist, s.genre, ur.score, ur.reason
          FROM user_recommendations ur JOIN songs s ON s.song_id = ur.song_id
         WHERE ur.user_id = 1 ORDER BY ur.rank_position LIMIT 5;
    """)

    cursor.close()
    conexion.close()


if __name__ == "__main__":
    print("Iniciando configuración de la base de datos local MySQL...")
    inicializar_base_datos_sql()
    ejecutar_consultas_analiticas()
