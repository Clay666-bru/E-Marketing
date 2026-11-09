# Plan y resultados de pruebas

**Fecha:** 9 de noviembre de 2026 · **Entorno:** Windows 11, Python 3.10.3, MariaDB 10.4.32 (XAMPP), Streamlit 1.64.0, pandas 2.3.3

**Resultado final: ✅ todo en verde.** El generador corre sin errores, las 39 reglas de integridad dan 0, pasan las 58 pruebas de la app (más el recorrido de los 45 usuarios) y las 26 pruebas con base vacía, y los pop-ups se verificaron a mano en el navegador.

Los errores encontrados durante estas pruebas y su corrección están en [CAMBIOS.md](CAMBIOS.md).

## Cómo repetir las pruebas

> Las pruebas de la app **modifican datos**. `pruebas/test_app.py` se niega a correr si `SPOTIFY_DB` no está definida o si es `spotify_uadeo_db`.

```powershell
$env:SPOTIFY_DB = "spotify_prueba"
python "base de datos.py"            # genera la base de prueba
python pruebas/auditoria_datos.py    # apartado 2
python pruebas/test_app.py           # apartados 3 a 7
```

Para probar con una base **vacía** (solo tablas), crea las tablas sin datos y vuelve a correr `test_app.py`:

```powershell
$env:SPOTIFY_DB = "spotify_vacia"
python -c "import importlib.util, mysql.connector; s=importlib.util.spec_from_file_location('bd','base de datos.py'); bd=importlib.util.module_from_spec(s); s.loader.exec_module(bd); cx=bd.crear_conexion_servidor(); c=cx.cursor(); c.execute('CREATE DATABASE IF NOT EXISTS spotify_vacia'); c.execute('USE spotify_vacia'); bd.crear_tablas(c); cx.commit()"
python pruebas/test_app.py
```

---

## Apartado 1 · Generador (`base de datos.py`)

| Prueba | Resultado |
|---|---|
| Compila sin errores (`py_compile` en los 3 módulos) | ✅ |
| Crea la base, las 19 tablas y las 3 vistas, e inserta los datos (exit 0) | ✅ |
| Datos generados | 45 usuarios · 40 canciones · 1,597 sesiones · 10,243 reproducciones · 18,252 impresiones de recomendaciones · 2,500 eventos de anuncios · 450 recomendaciones personalizadas |
| Consultas analíticas (Aha! Moment, Premium y 7 de telemetría) se imprimen sin error | ✅ (20 usuarios cumplen el Aha! Moment) |
| **Dora (#1)**: Premium desde el 4 de septiembre de 2026 con suscripción activa y cumple el Aha! Moment | ✅ |
| **Carlos (#2)**: solo reprodujo las canciones 1 y 3 y tiene 1 playlist | ✅ |
| **Ana (#3)**: 0 reproducciones y 0 playlists | ✅ |
| Determinista: la semilla fija produce los mismos datos en cada corrida | ✅ |

## Apartado 2 · Integridad de datos (`pruebas/auditoria_datos.py`)

39 reglas. Cada una cuenta registros que **no deberían existir**. **Resultado: 39 / 39 en 0.**

| Grupo | Reglas |
|---|---|
| Nada después de `FECHA_CORTE` | reproducciones, sesiones, likes, anuncios, eventos de interfaz y de rendimiento, recomendaciones, compartidos y descargas, notificaciones abiertas, eventos de suscripción |
| Nada antes del registro del usuario | reproducciones, eventos de suscripción, eventos de interfaz, recomendaciones, notificaciones, follows y playlists |
| Coherencia de sesiones | recomendaciones dentro de la sesión, reproducciones dentro de su sesión y del mismo usuario, `tracks_played` igual al número de reproducciones |
| Sin duplicados | likes, follows, canciones en playlists, emails, usernames |
| Reglas de negocio | sin anuncios mientras el usuario es Premium (respetando la cancelación) · los cancelados vuelven a ver anuncios · `account_type` coherente con las suscripciones · sin paywall a usuarios Premium · las pruebas gratis vencidas se cobran |
| Reproducción | `ms_played` ≤ duración de la canción · skip ⇒ < 30 s · clic/play/guardado coherentes · notificación abierta después de enviada |
| Recomendaciones | ninguna de una canción con like · 10 por usuario mientras haya canciones disponibles · todos los usuarios tienen recomendaciones |

Antes de las correcciones esta auditoría encontró **5 reglas en rojo** (G1, G2, G3 y G5 de CAMBIOS.md).

## Apartado 3 · Páginas de la app

| Prueba | Resultado |
|---|---|
| 🏠 Inicio, ✨ Para ti, 📡 Telemetría y 🗄️ Base de datos cargan sin excepciones ni errores | ✅ 4/4 |
| Las mismas 4 páginas y las 22 tablas y vistas con **base vacía** | ✅ 26/26 |

## Apartado 4 · ✨ Para ti

| Prueba | Resultado |
|---|---|
| Recorrer los **45 usuarios** uno por uno | ✅ |
| Filtros nueva / escuchada / guardada / descartada / Todas (incluyendo filtros sin resultados) | ✅ 5/5 |
| Regenerar las recomendaciones de un usuario sin historial (Ana) da 10 de `cold_start_popularity` | ✅ |
| Usuario con nombre vacío (pop-up de bienvenida) | ✅ |
| Regenerar cuando existe una canción sin artista ni género | ✅ |
| 0 razones contradictorias en los 45 usuarios | ✅ |

## Apartado 5 · 📡 Telemetría

| Prueba | Resultado |
|---|---|
| Las 8 pestañas se dibujan, también con base vacía | ✅ |
| Línea de tiempo de 5 usuarios distintos y de un usuario recién creado | ✅ |

## Apartado 6 · 🗄️ Base de datos: visor y buscador

| Prueba | Resultado |
|---|---|
| Abrir cada tabla y vista (7 principales, 12 de telemetría, 3 vistas) | ✅ 22/22 |
| Buscador con coincidencias («dora») y sin coincidencias | ✅ 2/2 |
| Columna Actividad en `users` | ✅ |

## Apartado 7 · Altas y modificaciones

| Prueba | Esperado | Resultado |
|---|---|---|
| Alta de usuario con nombre vacío | error «campos vacíos», no inserta | ✅ |
| Alta de usuario con nombre de solo espacios | error, no inserta | ✅ |
| Alta con fecha «31/12/2026» | error de formato | ✅ |
| Alta con fecha «2026-02-30 10:00:00» | error de formato | ✅ |
| Alta de 2 usuarios válidos (con espacios de sobra) | inserta 2 y quita los espacios | ✅ |
| Alta de canción sin artista | error | ✅ |
| Alta de canción válida (sin género) y una reproducción de ella | inserta | ✅ |
| Like que ya existe (usuario 1, canción 2) | error «ya le dio like» | ✅ |
| 2 likes iguales en el mismo formulario | error «repetidos» | ✅ |
| Like válido, playlist válida | inserta | ✅ |
| Alta Premium «Dúo Premium» | precio 179.00 y usuario → `premium` | ✅ |
| Altas en una tabla de telemetría | aviso de que no están disponibles | ✅ |
| Modificar sin escribir nada | aviso, no cambia nada | ✅ |
| Modificar solo el título de una canción | el artista se conserva | ✅ |
| Cambiar el plan a «Estudiantil Premium» | precio 75.00 | ✅ |
| Modificar una tabla no editable | aviso | ✅ |

## Apartado 8 · Pop-ups, verificados a mano en el navegador

`AppTest` de Streamlit no puede presionar botones dentro de `st.dialog`, así que estos flujos se probaron en el navegador con la app apuntando a la base de prueba.

| Prueba | Resultado |
|---|---|
| El pop-up de bienvenida aparece al abrir un usuario y «Ver todas mis recomendaciones» lo cierra | ✅ |
| «✨ Ver pop-up» lo vuelve a abrir | ✅ |
| «Detalles» abre el pop-up con la razón y las 4 barras de afinidad | ✅ |
| «▶ Escuchar»: toast, reproducciones 759 → 760, `ms_played` = duración de la canción y estado `escuchada` | ✅ |
| «❤ Me gusta» presionado **dos veces** en la misma canción: 1 solo like y estado `guardada` | ✅ |
| Bajas → «Cancelar»: no borra nada | ✅ |
| Bajas → «Sí, eliminar» en una suscripción: se borra y el usuario vuelve a `free` | ✅ |
| Bajas de un usuario con todo su historial (borra sus dependencias sin errores de llave foránea) | ✅ |
| Bajas de una canción con reproducciones y likes | ✅ |
