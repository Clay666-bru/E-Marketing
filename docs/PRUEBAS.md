# Plan y resultados de pruebas

**Fecha:** 9 de noviembre de 2026 · **Entorno:** Windows 11, Python 3.10.3, MariaDB 10.4.32 (XAMPP), Streamlit 1.64.0, pandas 2.3.3

**Base de datos:** todas las pruebas se corrieron sobre la **base original `spotify_uadeo_db`**. No se usó ninguna base falsa ni de prueba.

**Resultado final: ✅ todo en verde.** El generador corre sin errores, las 39 reglas de integridad dan 0 y pasan las 64 pruebas de la app (63 funcionales más la verificación de restauración, además del recorrido de los 45 usuarios). Los pop-ups se verificaron a mano en el navegador y, al terminar, la base quedó **idéntica** a como estaba antes de las pruebas (`CHECKSUM TABLE` en las 19 tablas).

Los errores encontrados durante estas pruebas y su corrección están en [CAMBIOS.md](CAMBIOS.md).

## Cómo repetir las pruebas

```bash
python "base de datos.py"            # apartado 1: genera la base original
python pruebas/auditoria_datos.py    # apartado 2: solo lectura
python pruebas/test_app.py           # apartados 3 a 7
```

**¿Cómo se prueba sobre la original sin ensuciarla?** `test_app.py` da de alta, modifica y borra registros, así que antes de empezar toma una **foto** de la base (`pruebas/respaldo.py`) y al final, pase lo que pase, la **restaura**:

1. Borra los registros nuevos (los que tienen un ID mayor al de la foto), primero los hijos y luego los padres.
2. Regresa los valores originales de `users`, `songs`, `playlist_created` y `premium_subscribed`, y repone completa `user_recommendations`.
3. Regresa los contadores `AUTO_INCREMENT`.
4. Compara `CHECKSUM TABLE` de las 19 tablas contra la foto. Si alguna no coincide, la prueba falla.

Para las pruebas manuales del apartado 8 se usa lo mismo desde la terminal:

```bash
python pruebas/respaldo.py foto
# ... probar en el navegador ...
python pruebas/respaldo.py restaurar
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
| 🏠 Inicio, 📺 En vivo, 📈 Marketing, 🧠 Recomendaciones, 📡 Telemetría y 🗄️ Base de datos cargan sin excepciones ni errores | ✅ 6/6 |
| Tablas vacías: la app conserva las columnas aunque una consulta no devuelva filas (error A1 de CAMBIOS.md) | ✅ (filtros sin resultados, buscador sin coincidencias, usuario sin historial) |

## Apartado 3b · 📈 Marketing

Los resultados de la app se compararon con consultas SQL hechas por separado y con un cálculo estadístico independiente (`statistics.NormalDist`).

| Prueba | Resultado |
|---|---|
| La página y sus 5 pestañas cargan sin errores | ✅ |
| Cada página tiene su guía «ℹ️ ¿Cómo leer esta página?» | ✅ |
| KPI de usuarios con Aha! = 20, igual que la consulta de `base de datos.py` | ✅ |
| Retención días 8-30: con Aha! 100% contra sin Aha! 80% (15 elegibles por grupo). Premium: 55% contra 12% | ✅ igual al cálculo independiente |
| KPI MRR = $1,497 = `SUM(price_mxn)` de las suscripciones activas | ✅ |
| Prueba A/B: CTR A 21.93%, B 23.74%, z = 2.92, p = 0.0036, igual que `NormalDist` | ✅ |
| Conclusiones automáticas («la hipótesis se cumple», «diferencia significativa») | ✅ |
| Revisión visual en el navegador de las 5 pestañas; se corrigieron 6 detalles de diseño (ver CAMBIOS.md, M7–M12) | ✅ |

## Apartado 4 · 🧠 Recomendaciones (antes «✨ Para ti»)

El panel es del **administrador**: la página dejó de simular al usuario (sin pop-up de bienvenida ni botones de escuchar / me gusta) y ahora es un inspector.

| Prueba | Resultado |
|---|---|
| Recorrer **todos los usuarios** uno por uno | ✅ |
| Filtros por resultado: nueva / escuchada / saltada / guardada / descartada / Todas (incluyendo filtros sin resultados) | ✅ 6/6 |
| Regenerar las recomendaciones de un usuario sin historial (Ana) da 10 de `cold_start_popularity` | ✅ |
| Regenerar con el motor en vivo guarda las recomendaciones con `telemetry_live_learning` | ✅ |
| El panel no tiene botones para escuchar o dar me gusta en nombre del usuario | ✅ |
| Usuario con nombre vacío | ✅ |
| Regenerar cuando existe una canción sin artista ni género | ✅ |
| 0 razones contradictorias | ✅ |

## Apartado 5 · 📡 Telemetría

| Prueba | Resultado |
|---|---|
| Las 8 pestañas se dibujan | ✅ |
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

> Las cinco primeras filas (pop-ups de «Para ti») corresponden a la versión anterior del panel: esos pop-ups se quitaron porque escuchar y dar me gusta ahora se hace en la app de usuario «Mi Spotify» (ver apartado 9).

`AppTest` de Streamlit no puede presionar botones dentro de `st.dialog`, así que estos flujos se probaron en el navegador con la app conectada a la **base original**, entre `respaldo.py foto` y `respaldo.py restaurar`. Para las bajas se creó un usuario temporal (#46, «ZZ Prueba Bajas») con reproducción, like, playlist y suscripción; así no se borró ningún dato real.

| Prueba | Resultado |
|---|---|
| El pop-up de bienvenida aparece al abrir a Dora y «Ver todas mis recomendaciones» lo cierra | ✅ |
| «Detalles» abre el pop-up con la razón y las 4 barras de afinidad | ✅ |
| «▶ Escuchar» en *Me Porto Bonito*: toast, reproducción con `ms_played` = 178,000 (duración completa) y estado `escuchada` | ✅ |
| «❤ Me gusta» presionado **dos veces** en *Perro Negro*: 1 solo like y estado `guardada` | ✅ |
| «🚫 No me interesa» en *AMG*: estado `descartada` | ✅ |
| Bajas → «Sí, eliminar» en la suscripción 15: se borra y el usuario 46 pasa de `premium` a `free` | ✅ |
| Bajas → «Cancelar» (usuario 46): no borra nada | ✅ |
| Bajas → «Sí, eliminar» del usuario 46: se borran el usuario y su reproducción, like, playlist y suscripción, sin errores de llave foránea | ✅ |
| `respaldo.py restaurar`: las 19 tablas quedan idénticas a la foto y la auditoría da 0 | ✅ |

## Apartado 0 · Acceso de administrador (`test_app.py`)

| Prueba | Resultado |
|---|---|
| Sin sesión, el panel solo muestra el formulario de usuario y contraseña | ✅ |
| Contraseña incorrecta: «Usuario o contraseña incorrectos» y no entra | ✅ |
| Contraseña correcta: aparece el menú | ✅ |

## Apartado 9 · App de usuario «Mi Spotify» (`pruebas/test_usuario.py`)

Corre sobre la base original entre foto y restauración, igual que `test_app.py`.

| Prueba | Resultado |
|---|---|
| Registro: usuario `free` con `signup_source = 'app_en_vivo'` y sesión abierta | ✅ |
| Onboarding con 3 artistas → 3 `artist_follows`, 10 recomendaciones y 10 impresiones | ✅ |
| El usuario no ve datos internos (% de match ni el nombre de la base) | ✅ |
| Canción terminada → `trackdone`, la recomendación queda reproducida y completada | ✅ |
| ⏭ antes de 30 s → `fwdbtn`, `skipped = 1` | ✅ |
| Anuncio después de 3 canciones (impresión y `complete`) y la música sigue | ✅ |
| Límite de 6 saltos por hora con `paywall_view` (`skip_limit_reached`) | ✅ |
| Me gusta / quitar me gusta / no me interesa; lo que te gusta o descartaste ya no se recomienda | ✅ |
| Búsqueda con clic guardado (resultado, posición y tiempo) | ✅ |
| Crear playlist (se abre sola), página de artista, dejar de seguir y Tu perfil | ✅ |
| 7 reglas de integridad (plays dentro de su sesión, `tracks_played`, skips < 30 s, guardadas con play, etc.) | ✅ |
| Restauración: las 19 tablas idénticas a la foto | ✅ |

Revisión en el navegador: reproductor en tiempo real y Autoplay, anuncio de al menos 5 s, oferta Premium que no se cierra al cambiar de canción, prueba gratis de Premium (sin anuncios) y la página «📺 En vivo» del administrador mostrando al usuario en línea.
