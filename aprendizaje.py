"""
Recomendador que APRENDE de la telemetría del usuario, en vivo.

A diferencia de recomendador.py (que solo mira song_played y song_liked), este motor
convierte cada evento que el usuario genera en la app en una señal con signo:

  señal                                   peso por canción
  --------------------------------------  -------------------------------------------
  reproducción completa / parcial         + fracción escuchada (1.0 = completa)
  skip (saltó la canción)                 − 0.6
  me gusta (song_liked)                   + 3.0
  "no me interesa" (recommendation_events) − 2.5
  clic en un resultado de búsqueda        + 0.5
  seguir a un artista (artist_follows)    + 2.0 al artista

Cada señal se multiplica por un factor de recencia (vida media de 14 días), así lo que
el usuario hace hoy pesa más que lo de hace un mes. Con esos pesos se calcula una
afinidad por género y por artista en el rango [-1, 1] (negativa = no le gusta) y un
perfil de audio promedio de lo que sí le gustó. La puntuación final es la misma fórmula
del proyecto:

  score = 0.45 · género + 0.25 · artista + 0.20 · similitud de audio + 0.10 · popularidad

Se guarda en user_recommendations con algorithm = 'telemetry_live_learning'.
"""
from collections import defaultdict
from datetime import datetime

ALGORITMO = 'telemetry_live_learning'
PESOS = {'genero': 0.45, 'artista': 0.25, 'audio': 0.20, 'popularidad': 0.10}
SENAL = {'skip': -0.6, 'like': 3.0, 'descartada': -2.5, 'busqueda': 0.5, 'follow': 2.0}
VIDA_MEDIA_DIAS = 14.0
MAX_ESCUCHAS_PARA_RECOMENDAR = 2


def _artistas(texto):
    return [a.strip() for a in (texto or '').split(',') if a.strip()] or ['Artista desconocido']


def _genero(s):
    return (s.get('genre') or '').strip() or 'Sin género'


def _audio(s):
    return [float(s['danceability'] or 0.5), float(s['energy'] or 0.5),
            float(s['valence'] or 0.5), min(float(s['tempo'] or 120) / 200.0, 1.0)]


def _recencia(cuando, ahora):
    if cuando is None:
        return 1.0
    dias = max((ahora - cuando).total_seconds() / 86400.0, 0.0)
    return 0.5 ** (dias / VIDA_MEDIA_DIAS)


def _normalizar(d):
    m = max((abs(v) for v in d.values()), default=0) or 1.0
    return {k: v / m for k, v in d.items()}


def aprender(conexion, user_id, top_n=10, ahora=None):
    """Devuelve {'recs': [...], 'generos': {...}, 'artistas': {...}, 'senales': {...}} sin escribir nada."""
    ahora = ahora or datetime.now()
    cur = conexion.cursor(dictionary=True)
    cur.execute("SELECT song_id, title, artist, genre, popularity, duration_ms, danceability, energy, "
                "valence, tempo FROM songs")
    canciones = {s['song_id']: s for s in cur.fetchall()}
    for s in canciones.values():
        s['genre'] = _genero(s)

    peso = defaultdict(float)          # señal neta por canción
    artista_extra = defaultdict(float)  # señales que van directo al artista (follows)
    escuchas = defaultdict(int)         # reproducciones completas por canción
    recientes = set()                   # escuchadas completas en las últimas 24 h (no se repiten de inmediato)
    senales = defaultdict(int)

    cur.execute("SELECT song_id, played_at, ms_played, skipped FROM song_played WHERE user_id=%s", (user_id,))
    for r in cur.fetchall():
        s = canciones.get(r['song_id'])
        if not s:
            continue
        f = _recencia(r['played_at'], ahora)
        if r['skipped']:
            peso[r['song_id']] += SENAL['skip'] * f
            senales['skips'] += 1
        else:
            dur = float(s['duration_ms'] or 180000)
            frac = min(float(r['ms_played'] or dur) / dur, 1.0) if r['ms_played'] else 1.0
            peso[r['song_id']] += frac * f
            escuchas[r['song_id']] += 1
            if r['played_at'] and (ahora - r['played_at']).total_seconds() < 86400:
                recientes.add(r['song_id'])
            senales['reproducciones'] += 1

    cur.execute("SELECT song_id, liked_at FROM song_liked WHERE user_id=%s", (user_id,))
    gustadas = set()
    for r in cur.fetchall():
        gustadas.add(r['song_id'])
        peso[r['song_id']] += SENAL['like'] * _recencia(r['liked_at'], ahora)
        senales['me_gusta'] += 1

    cur.execute("SELECT song_id, MAX(shown_at) AS cuando FROM recommendation_events "
                "WHERE user_id=%s AND dismissed=1 GROUP BY song_id", (user_id,))
    descartadas = set()
    for r in cur.fetchall():
        descartadas.add(r['song_id'])
        peso[r['song_id']] += SENAL['descartada'] * _recencia(r['cuando'], ahora)
        senales['descartadas'] += 1

    cur.execute("SELECT clicked_song_id AS song_id, searched_at FROM search_events "
                "WHERE user_id=%s AND clicked_song_id IS NOT NULL", (user_id,))
    for r in cur.fetchall():
        peso[r['song_id']] += SENAL['busqueda'] * _recencia(r['searched_at'], ahora)
        senales['busquedas'] += 1

    cur.execute("SELECT artist, followed_at FROM artist_follows WHERE user_id=%s", (user_id,))
    for r in cur.fetchall():
        artista_extra[r['artist']] += SENAL['follow'] * _recencia(r['followed_at'], ahora)
        senales['artistas_seguidos'] += 1
    cur.close()

    # ---- Perfil: afinidades con signo y audio promedio de lo que sí gustó ----
    genero, artista = defaultdict(float), defaultdict(float, artista_extra)
    audio_sum, audio_w = [0.0] * 4, 0.0
    for sid, w in peso.items():
        s = canciones.get(sid)
        if not s or w == 0:
            continue
        genero[s['genre']] += w
        for a in _artistas(s['artist']):
            artista[a] += w
        if w > 0:
            for i, v in enumerate(_audio(s)):
                audio_sum[i] += v * w
            audio_w += w
    # Seguir a un artista también dice qué géneros y qué sonido te gustan: su peso se reparte
    # entre las canciones de ese artista (sin tocar peso[], para no citarlas como "te gustó").
    for art, w in artista_extra.items():
        suyas = [s for s in canciones.values() if art in _artistas(s['artist'])]
        for s in suyas:
            genero[s['genre']] += w / len(suyas)
            if w > 0:
                for i, v in enumerate(_audio(s)):
                    audio_sum[i] += v * w / len(suyas)
                audio_w += w / len(suyas)
    genero_n, artista_n = _normalizar(genero), _normalizar(artista)
    perfil_audio = [v / audio_w for v in audio_sum] if audio_w else None

    resultado = {'generos': dict(sorted(genero_n.items(), key=lambda x: -x[1])),
                 'artistas': dict(sorted(artista_n.items(), key=lambda x: -x[1])),
                 'senales': dict(senales), 'perfil_audio': perfil_audio}

    # ---- Arranque en frío ----
    if not peso and not artista_extra:
        populares = sorted(canciones.values(), key=lambda s: -(s['popularity'] or 0))
        resultado['recs'] = [{
            'song_id': s['song_id'], 'score': round((s['popularity'] or 0) / 100, 4),
            'genre_affinity': 0, 'artist_affinity': 0, 'audio_similarity': 0,
            'reason': f"Popular en México ahora ({s['genre']})", 'based_on_song_id': None,
        } for s in populares[:top_n]]
        return resultado

    # ---- Candidatas: sin like, no descartadas, poco escuchadas y sin señal negativa ----
    def candidatas(limite):
        return [s for sid, s in canciones.items()
                if sid not in gustadas and sid not in descartadas and sid not in recientes
                and escuchas.get(sid, 0) <= limite and peso.get(sid, 0) >= 0]

    limite, lista = MAX_ESCUCHAS_PARA_RECOMENDAR, candidatas(MAX_ESCUCHAS_PARA_RECOMENDAR)
    while len(lista) < top_n and limite < 64:
        limite *= 2
        lista = candidatas(limite)
    if len(lista) < top_n:   # catálogo casi agotado: se permiten las de señal negativa (nunca likes)
        lista = [s for sid, s in canciones.items() if sid not in gustadas]
    ids_cand = {s['song_id'] for s in lista}
    semillas = [sid for sid in sorted(peso, key=lambda x: -peso[x]) if peso[sid] > 0 and sid not in ids_cand]

    recs = []
    for s in lista:
        g = genero_n.get(s['genre'], 0.0)
        art = max(_artistas(s['artist']), key=lambda x: artista_n.get(x, -9))
        a = artista_n.get(art, 0.0)
        sim = (1 - sum(abs(x - y) for x, y in zip(_audio(s), perfil_audio)) / 4) if perfil_audio else 0.5
        pop = (s['popularity'] or 0) / 100
        score = PESOS['genero'] * g + PESOS['artista'] * a + PESOS['audio'] * sim + PESOS['popularidad'] * pop

        base = next((sid for sid in semillas if art in _artistas(canciones[sid]['artist'])), None) if a >= 0.35 \
            else next((sid for sid in semillas if canciones[sid]['genre'] == s['genre']), None)
        if a >= 0.35:
            razon = f"Porque te gusta {art}"
        elif g >= 0.4:
            razon = f"Porque escuchas {s['genre']}"
        elif sim >= 0.85:
            razon = "Suena parecido a lo que te gustó"
        else:
            razon, base = f"Para descubrir algo nuevo: {s['genre']}", None
        if base:
            razon += f" (como '{canciones[base]['title']}')"
        recs.append({'song_id': s['song_id'], 'score': round(max(min(score, 0.9999), 0), 4),
                     'genre_affinity': round(max(g, 0), 4), 'artist_affinity': round(max(a, 0), 4),
                     'audio_similarity': round(max(sim, 0), 4), 'reason': razon[:200],
                     'based_on_song_id': base, '_orden': score})
    recs.sort(key=lambda r: -r['_orden'])
    for r in recs:
        r.pop('_orden')
    resultado['recs'] = recs[:top_n]
    return resultado


def guardar(conexion, user_id, top_n=10, ahora=None):
    """Aprende, reemplaza las recomendaciones del usuario en user_recommendations y devuelve el resultado."""
    ahora = ahora or datetime.now()
    res = aprender(conexion, user_id, top_n, ahora)
    cur = conexion.cursor()
    cur.execute("DELETE FROM user_recommendations WHERE user_id=%s", (user_id,))
    cur.executemany("""
        INSERT INTO user_recommendations (user_id, song_id, rank_position, score, genre_affinity, artist_affinity,
            audio_similarity, reason, based_on_song_id, algorithm, generated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        [(user_id, r['song_id'], i, r['score'], r['genre_affinity'], r['artist_affinity'], r['audio_similarity'],
          r['reason'], r['based_on_song_id'], ALGORITMO, ahora.strftime('%Y-%m-%d %H:%M:%S'))
         for i, r in enumerate(res['recs'], start=1)])
    conexion.commit()
    cur.close()
    return res
