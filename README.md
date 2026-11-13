# 🎧 Spotify Analytics · E-Marketing UAdeO

Proyecto de E-Marketing que simula la base de datos de un servicio de streaming tipo Spotify. Incluye usuarios, canciones, reproducciones, suscripciones Premium y **telemetría** de la app. Con esos datos se valida una hipótesis de retención (*Aha! Moment*), se calculan KPIs de marketing y se generan **recomendaciones personalizadas** según la música que escucha cada usuario.

Todo se consulta desde un panel web hecho con **Streamlit**, que también permite dar de alta, modificar y eliminar registros.

---

## Contenido

1. [Estructura del proyecto](#estructura-del-proyecto)
2. [Requisitos](#requisitos)
3. [Instalación y puesta en marcha](#instalación-y-puesta-en-marcha)
4. [Configuración de la conexión](#configuración-de-la-conexión)
5. [La app, apartado por apartado](#la-app-apartado-por-apartado)
   - [App de usuario «Mi Spotify»](#app-de-usuario-mi-spotify)
6. [Generador de la base de datos](#generador-de-la-base-de-datos)
7. [Motor de recomendaciones](#motor-de-recomendaciones)
8. [Pruebas](#pruebas)
9. [Solución de problemas](#solución-de-problemas)
10. [Documentación adicional](#documentación-adicional)

---

## Estructura del proyecto

```
Marketing Proyecto/
├── base de datos.py        # Crea la base spotify_uadeo_db, la llena con datos simulados y corre consultas analíticas
├── recomendador.py         # Motor de recomendaciones según la música escuchada (lo usan el script y la app)
├── aprendizaje.py          # Recomendador que aprende en vivo de la telemetría (lo usa la app de usuario)
├── iniciar.bat             # Abre el panel de ADMINISTRADOR con doble clic (puerto 8501)
├── iniciar_usuario.bat     # Abre la app de usuario «Mi Spotify» (puerto 8502)
├── requirements.txt        # Dependencias de Python
├── .streamlit/config.toml  # Tema oscuro estilo Spotify
├── consu/
│   ├── app_spotify.py      # Panel de ADMINISTRADOR en Streamlit (6 páginas, con inicio de sesión)
│   ├── app_usuario.py      # App del USUARIO «Mi Spotify»: se comporta como Spotify y aprende de su telemetría
│   └── .streamlit/config.toml
├── pruebas/
│   ├── test_app.py         # Pruebas automáticas del panel de administrador sobre la base original
│   ├── test_usuario.py     # Pruebas automáticas de la app de usuario (flujo completo + integridad)
│   ├── respaldo.py         # Foto y restauración de la base: las pruebas no dejan rastro
│   └── auditoria_datos.py  # 39 reglas de integridad de los datos (solo lectura)
└── docs/
    ├── DICCIONARIO_DATOS.md  # Todas las tablas, columnas y vistas
    ├── PRUEBAS.md            # Plan y resultados de pruebas, apartado por apartado
    └── CAMBIOS.md            # Errores encontrados y cómo se corrigieron
```

## Requisitos

| Componente | Versión probada | Notas |
|---|---|---|
| Python | 3.10 | 3.10 o superior |
| MySQL / MariaDB | MariaDB 10.4 (XAMPP) | Se usa el usuario `root` sin contraseña de XAMPP por defecto |
| streamlit | 1.64 | Requiere ≥ 1.50 (`st.dialog`, `segmented_control`, `width="stretch"`) |
| pandas | 2.3 | |
| mysql-connector-python | 26.7 | |
| altair | 6.2 | Gráficas de la página Marketing (viene con Streamlit) |

## Instalación y puesta en marcha

1. **Arranca MySQL** desde el panel de control de XAMPP (botón *Start* en MySQL).
2. **Instala las dependencias** (una sola vez):
   ```bash
   pip install -r requirements.txt
   ```
3. **Crea y llena la base de datos**:
   ```bash
   python "base de datos.py"
   ```
   > ⚠️ Este script **borra y vuelve a crear** todas las tablas de `spotify_uadeo_db`. Cualquier cambio hecho desde la app se pierde. Usa una semilla fija, así que siempre genera exactamente los mismos datos.

   Al terminar imprime cuántos registros insertó por tabla y los resultados de las consultas analíticas (Aha! Moment, Premium y telemetría).
4. **Abre el panel web.** La forma más fácil es dar **doble clic en `iniciar.bat`**, o escribir `.\iniciar.bat` en la terminal desde la carpeta del proyecto. Revisa que Python esté instalado, instala las dependencias si faltan y abre la app; no necesita que `streamlit` esté en el PATH.

   También se puede abrir a mano (funciona desde cualquier carpeta):
   ```powershell
   cd "C:\Users\isaac\OneDrive\Documentos\Marketing Proyecto\consu"; python -m streamlit run app_spotify.py
   ```
   Se abre en http://localhost:8501. Para detenerla, presiona `Ctrl + C`.

## Configuración de la conexión

Por defecto el proyecto se conecta a `localhost` con el usuario `root` sin contraseña, como viene XAMPP. Para cambiarlo no hace falta editar el código: basta con definir estas variables de entorno, que leen tanto el script como la app.

| Variable | Valor por defecto | Uso |
|---|---|---|
| `MYSQL_HOST` | `localhost` | Servidor MySQL |
| `MYSQL_USER` | `root` | Usuario |
| `MYSQL_PASSWORD` | *(vacío)* | Contraseña |
| `SPOTIFY_DB` | `spotify_uadeo_db` | Nombre de la base de datos |

Ejemplo en PowerShell, si tu MySQL tiene contraseña:

```powershell
$env:MYSQL_PASSWORD = "tu_contraseña"
python "base de datos.py"
cd consu; streamlit run app_spotify.py
```

## La app, apartado por apartado

`app_spotify.py` es el **panel de administrador**. Al abrirlo pide **usuario y contraseña**: por defecto `admin` / `admin`, y se cambian con las variables de entorno `ADMIN_USER` y `ADMIN_PASSWORD`. El botón **🔒 Cerrar sesión de administrador** está en la barra lateral. Los usuarios no entran aquí: usan la app **Mi Spotify** (ver más abajo).

La barra lateral tiene un menú con 6 páginas y muestra hasta qué fecha llegan los datos. Cada página tiene un recuadro **ℹ️ ¿Cómo leer esta página?** que explica sus métricas.

### 🏠 Inicio — Panel general
- **5 KPIs**: usuarios (y activos en los últimos 7 días), reproducciones (con la **tendencia semanal**: últimos 7 días contra los 7 anteriores), horas escuchadas, % Premium y CTR de recomendaciones.
- **Reproducciones por día** (gráfica de área) y **géneros más escuchados** en horas.
- **Top 10 canciones**: tarjetas de las 5 primeras y una tabla con reproducciones, % de skips y popularidad.

### 📺 En vivo: lo que hacen ahora los usuarios
Se actualiza sola cada 5 segundos, sin caché:
- **6 KPIs de hoy**: registros desde la app, usuarios en línea (actividad en los últimos 5 min), reproducciones y % saltadas, CTR del modelo en vivo (grupo `L`), anuncios e ingreso, y altas Premium junto con cuántos vieron la oferta.
- **Usuarios en línea**: plan, sesión, duración, canciones y la última que sonó.
- **Eventos de hoy**: los 80 más recientes de `v_telemetria_unificada`, con el nombre del usuario.
- Lo que aprendió el modelo de cada usuario y qué se le recomienda está en **🧠 Recomendaciones**.

### 📈 Marketing: análisis para la toma de decisiones
Es la página central del proyecto de E-Marketing. Tiene 5 pestañas y todas sacan sus conclusiones automáticamente:

| Pestaña | Qué responde |
|---|---|
| 🎯 Hipótesis Aha! | ¿Quienes crean ≥ 1 playlist y escuchan ≥ 20 canciones en sus primeros 7 días **retienen más y compran más Premium**? Compara a los que sí lo vivieron con los que no: retención de los días 8 a 30 (solo usuarios con ≥ 30 días de antigüedad) y conversión a Premium. Muestra si la hipótesis se cumple |
| 🔻 Embudo | Embudo **estricto**: registro → escuchó → Aha! → vio la oferta Premium → prueba o compra → Premium activo. Señala la etapa donde más usuarios se pierden y cuántos Premium llegaron sin vivir el Aha! |
| 📅 Cohortes | Mapa de calor de la retención semanal por semana de registro, con el promedio ponderado de la semana 1 y la semana 4 |
| 💰 Ingresos | MRR, ARPU, churn, ingresos por publicidad, ingresos por mes (suscripciones y publicidad) y suscripciones por plan |
| 🧪 Prueba A/B | CTR del modelo de recomendación A contra B con una **prueba z de dos proporciones**: valor p, IC del 95%, lift y qué modelo conviene usar |

Con los datos actuales: quienes viven el Aha! retienen **100% contra 80%** y llegan a Premium **55% contra 12%** (×4.6). El modelo B mejora el CTR un **+8.3%** (p = 0.0036, significativo).

### 🧠 Recomendaciones: inspector del administrador
Aquí el administrador **revisa** las recomendaciones; no escucha ni da «me gusta» en nombre de nadie (eso lo hace cada usuario en «Mi Spotify»).
- En la barra lateral se elige el **usuario** (los registrados desde la app aparecen marcados con «· app»). Arriba se ve su perfil: plan, origen del registro, reproducciones, horas, % saltadas y última escucha.
- **5 KPIs del usuario**: impresiones de recomendaciones, CTR, reproducidas (y % saltadas), guardadas y descartadas.
- **Motor + 🔄 Regenerar**: recalcula sus 10 recomendaciones con `recomendador.py` (por historial) o con `aprendizaje.py` (en vivo, el mismo que usa la app de usuario).
- **Tabla de recomendaciones actuales**: score, afinidad por género, por artista y por sonido, la razón que ve el usuario, la canción en que se basa y el **resultado real**, calculado con lo que el usuario hizo después de recibirla: `descartada`, `guardada`, `escuchada`, `saltada` o `nueva`. Se puede filtrar por resultado.
- **Qué aprendió el modelo en vivo**: las señales del usuario y su afinidad por género y por artista, de −1 (no le gusta) a 1 (le gusta).
- **Perfil de escucha**: géneros en horas y artistas más escuchados.

### 📡 Telemetría — Eventos de la app
Hay 8 pestañas:

| Pestaña | Qué muestra |
|---|---|
| ✨ Recomendaciones | Impresiones, clics y CTR por superficie (Discover Weekly, Daily Mix…), además de la prueba A/B del modelo |
| ▶️ Reproducción | Reproducciones, horas, skip, shuffle y offline por fuente; motivo de fin de reproducción |
| 📱 Sesiones | Sesiones por dispositivo y sistema operativo, duración promedio |
| 🔎 Búsquedas | Términos más buscados, % de clic y tiempo hasta el clic |
| 💳 Suscripción | Embudo: paywall → prueba → compra → renovación / cancelación |
| 📢 Anuncios | Impresiones, clics, saltos e ingreso por anunciante (usuarios free) |
| ⚙️ Rendimiento | Tiempo de arranque, *buffering* y errores de reproducción o *crashes* |
| 🕒 Línea de tiempo | Todos los eventos de un usuario en orden cronológico (vista `v_telemetria_unificada`) |

### 🗄️ Base de datos — Visor y gestión en lote
- En la barra lateral se elige el **grupo** (Principales, Telemetría o Vistas KPI) y la **tabla**.
- La tabla se muestra con un **buscador**. Las tablas de telemetría se limitan a los 2,000 registros más recientes. En `users` se agrega la columna **Actividad** (🟢 activo si escuchó algo en los 7 días anteriores a la última reproducción registrada).
- **Gestión en lote (de 1 a 5 registros a la vez):**
  - **➕ Altas**: disponibles en `users`, `songs`, `song_played`, `playlist_created`, `song_liked` y `premium_subscribed`. Se valida que no haya campos vacíos, que las fechas tengan el formato `AAAA-MM-DD HH:MM:SS` y que no se repitan likes. Las altas en `premium_subscribed` guardan el precio del plan y marcan al usuario como `premium`.
  - **✏️ Modificar**: disponible en `users`, `songs`, `playlist_created` y `premium_subscribed`. Un campo vacío **conserva** su valor actual. Al cambiar de plan Premium se actualiza el precio.
  - **🗑️ Bajas**: piden confirmación en un pop-up. Al borrar un usuario o una canción también se borra su historial. Al borrar una suscripción, el usuario vuelve a `free` si ya no le queda ninguna activa.
- Las vistas (`v_…`) son de **solo lectura**.

## App de usuario «Mi Spotify»

El proyecto tiene **dos apps con papeles distintos**, que corren separadas:

| App | Quién la usa | Archivo | Puerto | Lanzador |
|---|---|---|---|---|
| **Mi Spotify** | El **usuario**: se registra, escucha, guarda y busca música, como en Spotify | `consu/app_usuario.py` | 8502 | `iniciar_usuario.bat` |
| **Panel de administrador** | El **administrador**: KPIs, marketing, telemetría, gestión de la base y actividad en vivo | `consu/app_spotify.py` | 8501 | `iniciar.bat` |

Cada ventana muestra solo lo que le corresponde. El usuario no ve datos internos (scores, % de match, pesos del modelo, nombres de otras cuentas ni el nombre de la base); el administrador no escucha ni da «me gusta» en nombre de nadie: solo observa, analiza y administra.

Todo lo que hace el usuario se guarda como telemetría en la base **real** `spotify_uadeo_db`; las recomendaciones se **reentrenan al instante** con esas señales y el administrador lo ve en la página **📺 En vivo**.

```powershell
python -m streamlit run consu/app_usuario.py --server.port 8502
```

### Flujo

1. **Regístrate gratis**: nombre, correo, año de nacimiento, género, ciudad y estado. Se valida que el nombre y el correo no existan. Se inserta en `users` con `signup_source = 'app_en_vivo'`, `signup_platform = 'Web'` y cuenta `free`. También se puede **iniciar sesión** con una cuenta existente (por ejemplo `Dora Zatarain`) escribiendo su correo o nombre.
2. **Onboarding como Spotify**: eliges **3 o más artistas** (con filtro por género). Se guardan en `artist_follows` (`source = 'onboarding'`) y con eso arrancan tus recomendaciones.
3. **La app**:

| Parte | Qué hace |
|---|---|
| 🎧 Reproductor (fijo abajo) | Avanza en **tiempo real** con barra de progreso. ⏮ anterior (o reinicia si ya pasaron 3 s), ⏯ pausa, ⏭ siguiente, 🔀 aleatorio, 🔁 repetir (no / todo / una) y ♡ me gusta. Muestra de dónde viene la canción y cuál sigue. Cuando se acaba la cola, **Autoplay** sigue con tus recomendaciones |
| 🏠 Inicio | Accesos rápidos (Tus me gusta y lo último que escuchaste), **Hecho para ti** (10 recomendaciones con la razón, por ejemplo «Porque te gusta Peso Pluma»; se actualizan con cada canción), **Tus mixes diarios** (un Daily Mix por cada género que te gusta) y **Populares en México** |
| 🔎 Buscar | Sin texto muestra **Explorar todo** por género. Busca canciones, artistas, géneros o álbumes; guarda la búsqueda y en qué resultado hiciste clic |
| 📚 Tu biblioteca | Tus me gusta, tus playlists y los artistas que sigues |
| 🎶 Playlists | **➕ Crear playlist** en la barra lateral; agrega canciones desde el menú **⋯** de cualquier canción, quítalas con ✕, edita nombre y descripción, ▶ reproducir o 🔀 aleatorio |
| 👤 Artista | Oyentes y seguidores reales de la base, **Seguir / Siguiendo**, ▶ reproducir y 📻 radio del género |
| ⋯ Menú de canción | Ir al artista, agregar a una playlist (o crear una nueva), compartir (WhatsApp, Instagram, enlace) y ⬇ descargar (solo Premium) |
| 👤 Tu perfil | Como el perfil de Spotify: playlists, siguiendo y me gusta; minutos escuchados, artistas y canciones más escuchadas del mes, y tus géneros |
| ⚙️ Configuración | Velocidad de reproducción para la demostración |

### Free y Premium (reglas de Spotify)

| | Free | Premium |
|---|---|---|
| Anuncios | Uno cada **3 canciones**, de unos 15 s; no se puede saltar. «Ver más» guarda un clic | Sin anuncios |
| Saltos | Máximo **6 por hora**. Al llegar al límite aparece la oferta Premium | Ilimitados |
| Descargas | Aparece la oferta Premium | ⬇ Descarga para escuchar sin conexión |

La oferta Premium aparece al llegar al límite de saltos, con **Sin anuncios** durante un anuncio, al intentar descargar o con **💎 Hazte Premium**. Ofrece los 4 planes con los mismos precios de la simulación. La primera vez es **1 mes gratis** (`status = 'prueba'`); si ya usaste la prueba, es una compra (`status = 'activa'`). No se piden datos de pago reales. En **Administrar suscripción** se puede cancelar y volver a Free.

### Velocidad de reproducción (demo)

Las canciones duran unos 3 minutos. Para la demo, la barra lateral tiene **⏩ Velocidad: x1, x5, x10 (por defecto) o x30**. En la base se guarda el tiempo **de canción** (`ms_played`), como si se hubiera escuchado en tiempo real. Los anuncios se aceleran como máximo x3, para que siempre duren al menos 5 segundos.

### Qué telemetría escribe

| Acción | Tablas |
|---|---|
| Abrir la app | `app_sessions` (web_player · Web), `app_performance_events` (`app_startup`), `ui_events` |
| Ver «Hecho para ti» con una lista nueva | `recommendation_events`: 10 impresiones (`surface = 'Home - Hecho para ti'`, `model_version = 'live-v1'`, `ab_test_group = 'L'`) |
| Cada reentrenamiento | `user_recommendations` (`algorithm = 'telemetry_live_learning'`) |
| ▶ Reproducir | `recommendation_events.clicked` si venía de una recomendación, `ui_events` |
| Fin de una canción | `song_played` con `session_id`, `ms_played`, `source`, `shuffle` y `reason_end`: `trackdone` (terminó), `fwdbtn` (⏭), `backbtn` (⏮), `clickrow` (pusiste otra), `endplay` (cerraste sesión). Es **skip** solo si duró menos de 30 s y la cambiaste con ⏭ o con otra canción. También `app_sessions.tracks_played` y `recommendation_events.played/completed/skipped` |
| Pausa, aleatorio, repetir, siguiente, anterior | `ui_events` (`btn_pause`, `btn_play`, `btn_shuffle`, `btn_repeat`, `btn_next`, `btn_previous`) |
| ♡ / 💚 Me gusta | `song_liked` (se agrega o se quita), `recommendation_events.saved` (solo si ya se reprodujo) |
| ✕ No me interesa | `recommendation_events.dismissed` |
| Buscar / clic en resultado | `search_events` (`search_type`, `results_count`, `clicked_song_id`, `click_position`, `time_to_click_ms`) |
| Seguir / dejar de seguir | `artist_follows` |
| Playlists | `playlist_created`, `playlist_tracks` (sin duplicar) |
| Compartir / descargar | `share_events`, `download_events` |
| Anuncios | `ad_events`: `impression` ($0.045), `click` ($0.35), `complete` |
| Premium | `subscription_events` (`paywall_view` con su motivo, `trial_started`, `purchase`, `cancelled`), `premium_subscribed`, `users.account_type` |

La sesión se va extendiendo (`ended_at`, `duration_sec`) con cada evento, así todo queda dentro de ella. El grupo `L` (en vivo) queda **fuera de la prueba A/B** de la página Marketing, que solo compara A contra B.

### Cómo aprende (`aprendizaje.py`)

Cada evento se vuelve una **señal con signo** para la canción, su género y su artista:

| Señal | Peso |
|---|---|
| Escuchar | +1 si es completa (proporcional a lo escuchado) |
| Saltar antes de 30 s | −0.6 |
| Me gusta | +3 |
| No me interesa | −2.5 |
| Clic en un resultado de búsqueda | +0.5 |
| Seguir al artista | +2 al artista, repartido también entre el género y el sonido de sus canciones |

Las señales se multiplican por un factor de **recencia** (vida media de 14 días). Con ellas se calcula la afinidad por género y por artista entre −1 y 1 y un perfil de audio de lo que sí te gustó, y se puntúa con la misma fórmula del proyecto:

```
score = 0.45 · género + 0.25 · artista + 0.20 · similitud de audio + 0.10 · popularidad
```

No se recomiendan canciones con like, descartadas, con señal neta negativa ni escuchadas completas en las últimas 24 h. Sin ninguna señal se usa el arranque en frío por popularidad.

### Ten en cuenta

- Los datos simulados terminan el 4 de noviembre de 2026; la app escribe con la **fecha y hora reales**. Por eso, después de usarla, `auditoria_datos.py` marca las reglas «… después del corte» (las demás deben seguir en 0), y en el panel la «fecha de hoy» pasa a ser la de tu última escucha.
- Para probar sin dejar rastro: `python pruebas/respaldo.py foto` antes y `python pruebas/respaldo.py restaurar` al terminar.
- Al recargar el navegador se cierra la sesión de Streamlit; vuelve a entrar con «Iniciar sesión».
- La cuenta no tiene contraseña porque la tabla `users` no la guarda; se entra con el correo o el nombre.
- Free solo ve un aviso de saltos cuando le quedan 2 o menos en la hora, como en Spotify.

## Generador de la base de datos

`base de datos.py` crea **19 tablas y 3 vistas** y simula la actividad del **1 de agosto al 4 de noviembre de 2026** (`FECHA_CORTE`):

- **40 canciones reales** (corridos tumbados, regional mexicano, reggaetón, pop…) con sus atributos de audio (danceability, energy, valence, tempo).
- **45 usuarios**. Los 3 originales del documento conservan su historia:
  - **Dora Zatarain** (#1): *power user*. Cumple el **Aha! Moment** (≥ 1 playlist y ≥ 20 canciones en sus primeros 7 días) y se hace Premium el 4 de septiembre de 2026.
  - **Carlos Perez** (#2): solo escuchó las canciones 1 y 3, y creó «Mi Playlist».
  - **Ana Gomez** (#3): se registró y nunca escuchó nada (sirve para probar el arranque en frío).
  - Los otros 42 se reparten en perfiles **power**, **casual** y **churn** (abandonan después de 1 a 3 semanas).
- **Telemetría realista**: sesiones, reproducciones, impresiones de recomendaciones con prueba A/B, búsquedas, eventos de interfaz, descargas, compartidos, anuncios (solo mientras el usuario es free), embudo de suscripción, notificaciones y rendimiento de la app.
- Al final genera **10 recomendaciones por usuario** e imprime las consultas analíticas.

El detalle de cada tabla y columna está en [docs/DICCIONARIO_DATOS.md](docs/DICCIONARIO_DATOS.md).

## Motor de recomendaciones

`recomendador.py` arma un **perfil de escucha** por usuario a partir de `song_played` y `song_liked`:

- **Peso de cada canción** = minutos escuchados × (1 − 0.5 × proporción de skips) + 5 si tiene like.
- Con esos pesos calcula la afinidad por **género** y por **artista**, y un **perfil de audio** promedio.
- Puntúa las canciones que el usuario casi no ha escuchado (≤ 2 veces) y que no tienen like:

```
score = 0.45 · género + 0.25 · artista + 0.20 · similitud de audio + 0.10 · popularidad
```

- Cada recomendación incluye una **razón legible** («Porque escuchas mucho a KAROL G (te gustó 'Si Antes Te Hubiera Conocido')»). La canción citada como «te gustó» siempre es una que el usuario ya escuchó bastante o marcó con like, nunca una que también se le está recomendando.
- **Arranque en frío**: un usuario sin historial recibe las canciones más populares.
- Si un usuario ya marcó casi todo el catálogo con like, puede recibir **menos de 10** recomendaciones. Es lo esperado, porque no se recomiendan canciones que ya le gustan.

## Pruebas

Todas las pruebas corren sobre la **base original** `spotify_uadeo_db`. No se usan bases falsas. El plan completo y los resultados están en [docs/PRUEBAS.md](docs/PRUEBAS.md).

```bash
python "base de datos.py"            # 1) genera la base original
python pruebas/auditoria_datos.py    # 2) 39 reglas de integridad: todas deben dar 0 (solo lectura)
python pruebas/test_app.py           # 3) pruebas del panel de administrador, apartado por apartado
python pruebas/test_usuario.py       # 4) pruebas de la app de usuario «Mi Spotify»
```

`test_usuario.py` recorre el flujo de un usuario nuevo: registro, onboarding, reproducción completa, skip, anuncio cada 3 canciones, límite de 6 saltos con oferta Premium, me gusta, no me interesa, búsqueda, playlist, artista 7 reglas de integridad y que el usuario no vea datos internos.

`test_app.py` y `test_usuario.py` dan de alta, modifican y borran registros. Para no dejar rastro, **antes toma una foto** de la base con `pruebas/respaldo.py`, **al final la restaura** y comprueba con `CHECKSUM TABLE` que las 19 tablas quedaron idénticas. Para pruebas manuales en el navegador se usa lo mismo:

```bash
python pruebas/respaldo.py foto        # antes de probar a mano
python pruebas/respaldo.py restaurar   # al terminar: deja la base como estaba y lo verifica
```

## Solución de problemas

| Síntoma | Causa / solución |
|---|---|
| «streamlit no se reconoce como comando» | La carpeta de scripts de Python no está en el PATH. Usa `iniciar.bat` o `python -m streamlit run app_spotify.py`. Si agregaste `%APPDATA%\Python\Python310\Scripts` al PATH, **cierra y vuelve a abrir** la terminal (o VS Code), porque las terminales ya abiertas no ven el cambio |
| La app corre en la terminal pero no se abre el navegador | La configuración usa `headless = true`, así que Streamlit no abre el navegador. Entra a mano a http://localhost:8501 (panel de administrador) o http://localhost:8502 (app de usuario). Los `.bat` lo abren solos a los pocos segundos |
| «Port 8502 is already in use» | Esa app ya está abierta en otra terminal: usa esa, o ciérrala con `Ctrl + C` antes de volver a abrirla |
| «No se pudo conectar a MySQL» | MySQL no está encendido en XAMPP, o la base no existe: corre `python "base de datos.py"` |
| `Unknown database 'spotify_uadeo_db'` | Falta generar la base (paso 3 de la instalación) |
| `Access denied for user 'root'` | Tu MySQL tiene contraseña: define `MYSQL_PASSWORD` |
| Los cambios hechos en la app desaparecieron | Se volvió a correr `base de datos.py`, que recrea todo |
| Los datos de una tabla tardan en refrescarse | Las consultas se guardan en caché 60 s. Cualquier alta, cambio o baja hecha desde la app limpia el caché |
| `AttributeError` con `st.dialog` o `segmented_control` | Tu Streamlit es muy viejo: `pip install -U streamlit` |

## Documentación adicional

- [docs/DICCIONARIO_DATOS.md](docs/DICCIONARIO_DATOS.md): tablas, columnas, relaciones y vistas.
- [docs/PRUEBAS.md](docs/PRUEBAS.md): plan de pruebas y resultados.
- [docs/CAMBIOS.md](docs/CAMBIOS.md): errores encontrados en la revisión y su solución.
