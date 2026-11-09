# Bitácora de cambios: errores encontrados y soluciones

Resultado de la revisión profunda del 9 de noviembre de 2026. Cada error se reprodujo antes de corregirlo y después se verificó con las pruebas de [PRUEBAS.md](PRUEBAS.md).

Severidad: 🔴 truena o pierde datos · 🟠 dato o comportamiento incorrecto · 🟡 detalle menor (microerror)

## Generador · `base de datos.py`

| # | Sev. | Error | Solución |
|---|---|---|---|
| G1 | 🟠 | **1,094 impresiones de recomendaciones mostradas antes de que empezara la sesión.** La lista sin clic se generaba 10 s antes de la primera canción, que coincide con el inicio de la sesión. | Esa hora se limita al inicio de la sesión: `max(momento − 10 s, inicio)`. |
| G2 | 🟠 | **Eventos de suscripción (paywall) antes de que el usuario se registrara**: se ponían a las 20:xx del día de registro aunque el usuario se registrara más tarde. | La hora del evento nunca es anterior al registro + 10 min ni posterior al corte. |
| G3 | 🟠 | **Pantallas de «hazte Premium» a usuarios que ya eran Premium**: se revisaba si era Premium a la medianoche, no a la hora del evento. | Se revisa a la hora exacta del evento. |
| G4 | 🟠 | **Al cancelar Premium, la simulación seguía tratando al usuario como Premium** (sin anuncios, calidad alta, descargas). | La suscripción se simula antes que los días de uso y guarda `premium_hasta`. Desde la cancelación el usuario vuelve a ser free. |
| G5 | 🟠 | **Reproducciones y sesiones después de `FECHA_CORTE`** (datos «del futuro») cuando una sesión empezaba poco antes de las 23:00. | Ya no empiezan sesiones en las 3 h previas al corte. Una sesión dura ~1.5 h como máximo. |
| G6 | 🟡 | La conexión (`root`, sin contraseña) estaba escrita directamente en el código en dos lugares. | Variables de entorno `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD` y `SPOTIFY_DB`, con los mismos valores por defecto. |

> Por G4 y G5 cambia el orden en que se usan los números aleatorios, así que los datos generados ya no son idénticos a los de la versión anterior. Siguen siendo **deterministas**: la semilla es fija y cada corrida da lo mismo. Las historias de Dora, Carlos y Ana no cambian.

## Motor de recomendaciones · `recomendador.py`

| # | Sev. | Error | Solución |
|---|---|---|---|
| R1 | 🟠 | **Razones contradictorias**: recomendaba una canción y al mismo tiempo la usaba como razón de otra. Por ejemplo, a Dora le recomendaba *Titi Me Preguntó* (#3) y en la #2 decía «te gustó 'Titi Me Preguntó'». | La canción que se cita como «te gustó» se elige entre las que **no** se están recomendando (las que ya escuchó bastante o tienen like). Queda en 0 contradicciones en los 45 usuarios. |
| R2 | 🔴 | **Truena** (`ValueError: max() arg is an empty sequence`) al regenerar si existe una canción con el artista vacío (posible desde SQL o desde una versión vieja de la app). | Un artista vacío se trata como «Artista desconocido», que no cuenta como afinidad. |
| R3 | 🟡 | Las canciones sin género (las altas desde la app no lo piden) generaban razones como «Para descubrir algo nuevo: None». | Se agrupan como «Sin género» y la razón omite el género. |

## App · `consu/app_spotify.py`

| # | Sev. | Error | Solución |
|---|---|---|---|
| A1 | 🔴 | **Varias páginas truenan con tablas vacías** (`AttributeError`): una consulta sin filas devolvía un DataFrame sin columnas. | `consulta()` conserva los nombres de las columnas aunque no haya filas. Con base vacía las 4 páginas y las 22 tablas cargan bien. |
| A2 | 🔴 | **El pop-up de bienvenida truena** (`IndexError`) si el usuario tiene el nombre vacío (`nombre.split()[0]`). | Usa el primer nombre si existe y si no un saludo genérico. Además, las altas ya no aceptan nombres vacíos (A4). |
| A3 | 🟠 | **«❤ Me gusta» duplicaba el like** si se presionaba dos veces (o sobre una canción que ya tenía like). | El INSERT solo se hace si no existe ya el like (`WHERE NOT EXISTS`). |
| A4 | 🟠 | **Las altas aceptaban campos vacíos o con solo espacios y fechas inválidas** («31/12/2026», «2026-02-30»). | Validación antes de guardar: textos sin espacios sobrantes y no vacíos, fecha con formato `AAAA-MM-DD HH:MM:SS` y real. Si algo falla no se guarda nada y se muestra el error. |
| A5 | 🟠 | **Se podía dar el mismo like dos veces** desde Altas (repetido en el formulario o ya existente). | Se rechazan los pares usuario-canción repetidos o que ya existen. |
| A6 | 🟠 | **El alta de una suscripción Premium no guardaba el precio** y el usuario seguía como `free`. | Guarda `price_mxn` según el plan y actualiza `users.account_type`. |
| A7 | 🟠 | **Al borrar una suscripción, el usuario seguía como `premium`.** | Después de borrar se recalcula `account_type` (premium solo si le queda una suscripción no cancelada). |
| A8 | 🟠 | **Modificar con un campo vacío borraba el valor** (por ejemplo, cambiar solo el título de una canción dejaba al artista en blanco). | Un campo vacío conserva el valor actual (`COALESCE(NULLIF(…))`). Si no se escribe ningún cambio aparece un aviso. |
| A9 | 🟡 | Al cambiar de plan Premium no se actualizaba el precio. | Se actualiza `price_mxn` junto con `plan_type`. |
| A10 | 🟡 | «▶ Escuchar» registraba la reproducción con `ms_played = 0`, así que no sumaba horas en Inicio. | Guarda la duración completa de la canción. |
| A11 | 🟡 | Las canciones sin género salían como `None` en las gráficas de géneros. | Se muestran como «Sin género». |
| A12 | 🟡 | Las gráficas de Telemetría sin datos mostraban advertencias de Altair y un recuadro vacío. | Si no hay datos se muestra «Sin datos todavía.». |
| A13 | 🟡 | Si un filtro de estado no tenía resultados, la página quedaba en blanco. | Aviso: «No hay recomendaciones con estado …». |
| A14 | 🟡 | Si fallaba un alta o una modificación en lote, la conexión quedaba abierta. | Se hace `rollback()` y se cierra la conexión. No se guarda nada a medias. |
| A15 | 🟡 | La conexión estaba escrita en el código y el mensaje de error no decía qué hacer si la base no existía. | Variables de entorno (igual que el generador) y un mensaje que indica correr `base de datos.py`. |

## Proyecto

- Control de versiones con Git y `.gitignore` (excluye `__pycache__`, `.pyc` y configuración local).
- `requirements.txt`, `README.md`, `docs/` y las pruebas automáticas en `pruebas/`.
- **Las pruebas corren sobre la base original** (`spotify_uadeo_db`) y ya no hay bases falsas. Se agregó `pruebas/respaldo.py`, que toma una foto antes de probar, la restaura al final y verifica con `CHECKSUM TABLE` que las 19 tablas quedaron idénticas. `test_app.py` lo hace automáticamente. Se borró la base vieja `spotify_uadeo_db_respaldo` (versión sin telemetría).
- **Nota:** en `consu/__pycache__/` había archivos compilados de `consulta_*.py` y `gestion_completa.py` cuyos `.py` ya no existen. La app no los usa y no se suben al repositorio.
