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
├── requirements.txt        # Dependencias de Python
├── .streamlit/config.toml  # Tema oscuro estilo Spotify
├── consu/
│   ├── app_spotify.py      # Panel web en Streamlit (5 páginas)
│   └── .streamlit/config.toml
├── pruebas/
│   ├── test_app.py         # Pruebas automáticas de la app sobre la base original
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
4. **Abre el panel web** (funciona desde cualquier carpeta y aunque `streamlit` no esté en el PATH):
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

La barra lateral tiene un menú con 5 páginas y muestra hasta qué fecha llegan los datos. Cada página tiene un recuadro **ℹ️ ¿Cómo leer esta página?** que explica sus métricas.

### 🏠 Inicio — Panel general
- **5 KPIs**: usuarios (y activos en los últimos 7 días), reproducciones (con la **tendencia semanal**: últimos 7 días contra los 7 anteriores), horas escuchadas, % Premium y CTR de recomendaciones.
- **Reproducciones por día** (gráfica de área) y **géneros más escuchados** en horas.
- **Top 10 canciones**: tarjetas de las 5 primeras y una tabla con reproducciones, % de skips y popularidad.

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

### ✨ Para ti — Recomendaciones personalizadas
- En la barra lateral se elige el **usuario**. Se muestra su perfil: plan, ciudad, reproducciones, horas y géneros favoritos.
- La primera vez que se abre cada usuario aparece un **pop-up** con sus 5 mejores recomendaciones. El botón **✨ Ver pop-up** lo vuelve a abrir.
- **Hecho para ti**: tarjetas con el % de *match*. El botón **Detalles** abre un pop-up que explica *por qué* se recomienda la canción (afinidad por género y por artista, parecido en sonido y popularidad), con 3 acciones:
  - **▶ Escuchar**: registra una reproducción completa y marca la recomendación como `escuchada`.
  - **❤ Me gusta**: agrega la canción a *Tus me gusta* (sin duplicarla) y la marca como `guardada`.
  - **🚫 No me interesa**: la marca como `descartada`.
- **🔄 Regenerar recomendaciones** recalcula las recomendaciones con el historial actual del usuario.
- El selector **Estado** filtra por `nueva`, `escuchada`, `guardada` o `descartada`.
- Abajo están la tabla completa de recomendaciones y el **perfil de escucha** (géneros en horas y artistas más escuchados).

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
python pruebas/test_app.py           # 3) pruebas de la app, apartado por apartado
```

`test_app.py` da de alta, modifica y borra registros. Para no dejar rastro, **antes toma una foto** de la base con `pruebas/respaldo.py`, **al final la restaura** y comprueba con `CHECKSUM TABLE` que las 19 tablas quedaron idénticas. Para pruebas manuales en el navegador se usa lo mismo:

```bash
python pruebas/respaldo.py foto        # antes de probar a mano
python pruebas/respaldo.py restaurar   # al terminar: deja la base como estaba y lo verifica
```

## Solución de problemas

| Síntoma | Causa / solución |
|---|---|
| «streamlit no se reconoce como comando» | La carpeta de scripts de Python no está en el PATH: usa `python -m streamlit run app_spotify.py`, o agrega `%APPDATA%\Python\Python310\Scripts` al PATH y reabre la terminal |
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
