"""
Motor de recomendaciones basado en la música escuchada.

Para cada usuario arma un "perfil de escucha" a partir de song_played y song_liked:
  - afinidad por género (tiempo escuchado, penalizando los skips)
  - afinidad por artista
  - perfil de audio promedio (danceability, energy, valence, tempo)
y puntúa las canciones que el usuario casi no ha escuchado:

  score = 0.45 * género + 0.25 * artista + 0.20 * similitud de audio + 0.10 * popularidad

Los resultados se guardan en la tabla user_recommendations.
Usuarios sin historial reciben recomendaciones por popularidad (arranque en frío).
"""
from collections import defaultdict
from datetime import datetime

DDL_USER_RECOMMENDATIONS = """
CREATE TABLE IF NOT EXISTS user_recommendations (
    recommendation_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    song_id INT NOT NULL,
    rank_position TINYINT NOT NULL,
    score DECIMAL(5,4) NOT NULL,
    genre_affinity DECIMAL(5,4) NOT NULL,
    artist_affinity DECIMAL(5,4) NOT NULL,
    audio_similarity DECIMAL(5,4) NOT NULL,
    reason VARCHAR(200) NOT NULL,
    based_on_song_id INT NULL,
    algorithm VARCHAR(40) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'nueva',
    generated_at DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (song_id) REFERENCES songs(song_id) ON DELETE CASCADE,
    FOREIGN KEY (based_on_song_id) REFERENCES songs(song_id) ON DELETE SET NULL
)
"""

PESOS = {'genero': 0.45, 'artista': 0.25, 'audio': 0.20, 'popularidad': 0.10}
MAX_ESCUCHAS_PARA_RECOMENDAR = 2   # canciones escuchadas más veces que esto ya no se recomiendan


def asegurar_tabla(cursor):
    cursor.execute(DDL_USER_RECOMMENDATIONS)


SIN_GENERO = 'Sin género'
ARTISTA_DESCONOCIDO = 'Artista desconocido'


def _artistas(texto):
    return [a.strip() for a in (texto or '').split(',') if a.strip()] or [ARTISTA_DESCONOCIDO]


def _genero(song):
    return (song['genre'] or '').strip() or SIN_GENERO


def _vector_audio(song):
    return [float(song['danceability'] or 0.5), float(song['energy'] or 0.5),
            float(song['valence'] or 0.5), min(float(song['tempo'] or 120) / 200.0, 1.0)]


def calcular_recomendaciones(conexion, user_ids=None, top_n=10):
    """Devuelve {user_id: [dict de recomendación, ...]} sin escribir en la base de datos."""
    cur = conexion.cursor(dictionary=True)
    cur.execute("SELECT song_id, title, artist, genre, popularity, danceability, energy, valence, tempo FROM songs")
    canciones = {s['song_id']: s for s in cur.fetchall()}
    for s in canciones.values():          # canciones dadas de alta desde la app pueden no tener género
        s['genre'] = _genero(s)
    if not canciones:
        cur.close()
        return {}

    if user_ids is None:
        cur.execute("SELECT user_id FROM users")
        user_ids = [r['user_id'] for r in cur.fetchall()]
    if not user_ids:
        cur.close()
        return {}

    marcadores = ', '.join(['%s'] * len(user_ids))
    cur.execute(f"""
        SELECT user_id, song_id, COUNT(*) AS escuchas,
               SUM(IFNULL(ms_played, 0)) AS ms, SUM(IFNULL(skipped, 0)) AS skips
          FROM song_played WHERE user_id IN ({marcadores})
         GROUP BY user_id, song_id
    """, tuple(user_ids))
    historial = defaultdict(dict)
    for r in cur.fetchall():
        historial[r['user_id']][r['song_id']] = r

    cur.execute(f"SELECT user_id, song_id FROM song_liked WHERE user_id IN ({marcadores})", tuple(user_ids))
    likes = defaultdict(set)
    for r in cur.fetchall():
        likes[r['user_id']].add(r['song_id'])
    cur.close()

    populares = sorted(canciones.values(), key=lambda s: -(s['popularity'] or 0))
    resultado = {}

    for uid in user_ids:
        escuchadas = historial.get(uid, {})
        gustadas = likes.get(uid, set())

        # ---- Arranque en frío: sin historial -> lo más popular ----
        if not escuchadas and not gustadas:
            resultado[uid] = [{
                'song_id': s['song_id'], 'score': round((s['popularity'] or 0) / 100, 4),
                'genre_affinity': 0, 'artist_affinity': 0, 'audio_similarity': 0,
                'reason': f"Popular en México ahora ({s['genre']})"[:200], 'based_on_song_id': None,
                'algorithm': 'cold_start_popularity',
            } for s in populares[:top_n]]
            continue

        # ---- Perfil de escucha ----
        peso_cancion = {}
        for sid in set(escuchadas) | gustadas:
            h = escuchadas.get(sid)
            minutos = (float(h['ms']) / 60000.0) if h else 0.0
            if h and not h['ms']:            # registros sin ms_played (alta manual desde la app)
                minutos = 3.0 * h['escuchas']
            ratio_skip = (float(h['skips']) / h['escuchas']) if h else 0.0
            peso_cancion[sid] = minutos * (1 - 0.5 * ratio_skip) + (5.0 if sid in gustadas else 0.0)

        genero, artista = defaultdict(float), defaultdict(float)
        audio_sum, audio_w = [0.0] * 4, 0.0
        for sid, w in peso_cancion.items():
            s = canciones.get(sid)
            if not s or w <= 0:
                continue
            genero[s['genre']] += w
            for a in _artistas(s['artist']):
                artista[a] += w
            for i, v in enumerate(_vector_audio(s)):
                audio_sum[i] += v * w
            audio_w += w
        max_g = max(genero.values(), default=1) or 1
        max_a = max(artista.values(), default=1) or 1
        perfil_audio = [v / audio_w for v in audio_sum] if audio_w else [0.5] * 4

        # ---- Candidatas: canciones poco o nada escuchadas y sin like ----
        def candidatas(limite):
            return [s for sid, s in canciones.items()
                    if sid not in gustadas and (escuchadas.get(sid, {}).get('escuchas', 0) <= limite)]

        lista = candidatas(MAX_ESCUCHAS_PARA_RECOMENDAR)
        limite = MAX_ESCUCHAS_PARA_RECOMENDAR
        while len(lista) < top_n and limite < 50:      # usuarios que ya escucharon casi todo
            limite *= 2
            lista = candidatas(limite)
        ids_candidatas = {s['song_id'] for s in lista}

        # canción "semilla" más escuchada por género (para explicar la recomendación).
        # Se prefieren canciones que NO se están recomendando, para no decir "te gustó X"
        # y a la vez recomendar X.
        orden_peso = sorted(peso_cancion, key=lambda x: -peso_cancion[x])
        semillas = [sid for sid in orden_peso if sid not in ids_candidatas] or orden_peso
        semilla_genero = {}
        for sid in semillas:
            s = canciones.get(sid)
            if s and s['genre'] not in semilla_genero:
                semilla_genero[s['genre']] = sid
        semilla_global = semillas[0] if semillas else None

        puntuadas = []
        for s in lista:
            g = genero.get(s['genre'], 0) / max_g
            artista_comun = max(_artistas(s['artist']), key=lambda x: artista.get(x, 0))
            # un artista "desconocido" (alta manual sin artista) no cuenta como afinidad
            a = 0.0 if artista_comun == ARTISTA_DESCONOCIDO else artista.get(artista_comun, 0) / max_a
            sim = 1 - sum(abs(x - y) for x, y in zip(_vector_audio(s), perfil_audio)) / 4
            pop = (s['popularity'] or 0) / 100
            score = PESOS['genero'] * g + PESOS['artista'] * a + PESOS['audio'] * sim + PESOS['popularidad'] * pop

            if a >= 0.35:
                razon = f"Porque escuchas mucho a {artista_comun}"
            elif g >= 0.5 and s['genre'] != SIN_GENERO:
                razon = f"Porque te gusta el {s['genre']}"
            elif sim >= 0.85:
                razon = "Tiene un sonido parecido a lo que escuchas"
            elif s['genre'] != SIN_GENERO:
                razon = f"Para descubrir algo nuevo: {s['genre']}"
            else:
                razon = "Para descubrir algo nuevo"
            base = semilla_genero.get(s['genre'], semilla_global)
            if a >= 0.35:
                # la canción base es la más escuchada de ese mismo artista
                del_artista = [sid for sid in semillas
                               if sid in canciones and artista_comun in _artistas(canciones[sid]['artist'])
                               and sid != s['song_id']]
                base = del_artista[0] if del_artista else base
            if base and base != s['song_id'] and canciones.get(base):
                razon += f" (te gustó '{canciones[base]['title']}')"

            puntuadas.append({
                'song_id': s['song_id'], 'score': round(min(score, 0.9999), 4),
                'genre_affinity': round(g, 4), 'artist_affinity': round(a, 4),
                'audio_similarity': round(max(sim, 0), 4), 'reason': razon[:200],
                'based_on_song_id': base if base != s['song_id'] else None,
                'algorithm': 'content_based_listening_profile',
            })
        puntuadas.sort(key=lambda r: -r['score'])
        resultado[uid] = puntuadas[:top_n]

    return resultado


def guardar_recomendaciones(conexion, user_ids=None, top_n=10, generado_en=None):
    """Recalcula y reemplaza las recomendaciones de los usuarios indicados (o de todos)."""
    generado_en = generado_en or datetime.now()
    cur = conexion.cursor()
    asegurar_tabla(cur)
    recs = calcular_recomendaciones(conexion, user_ids, top_n)
    filas = []
    for uid, lista in recs.items():
        cur.execute("DELETE FROM user_recommendations WHERE user_id = %s", (uid,))
        for pos, r in enumerate(lista, start=1):
            filas.append((uid, r['song_id'], pos, r['score'], r['genre_affinity'], r['artist_affinity'],
                          r['audio_similarity'], r['reason'], r['based_on_song_id'], r['algorithm'],
                          generado_en.strftime('%Y-%m-%d %H:%M:%S')))
    if filas:
        cur.executemany("""
            INSERT INTO user_recommendations (user_id, song_id, rank_position, score, genre_affinity,
                artist_affinity, audio_similarity, reason, based_on_song_id, algorithm, generated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, filas)
    conexion.commit()
    cur.close()
    return len(filas)
