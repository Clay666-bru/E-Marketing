@echo off
REM ==============================================================
REM  Mi Spotify (app de usuario) - E-Marketing UAdeO
REM  Abre la app con doble clic o desde cualquier terminal:
REM      iniciar_usuario.bat
REM  No depende de que "streamlit" este en el PATH.
REM  Antes enciende MySQL en el panel de XAMPP.
REM  Puerto 8502: puede correr al mismo tiempo que la otra app.
REM ==============================================================
chcp 65001 >nul
cd /d "%~dp0consu"

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] No se encontro Python. Instala Python 3.10 o superior y marca "Add to PATH".
    pause
    exit /b 1
)

python -c "import streamlit, mysql.connector, pandas, altair" >nul 2>nul
if errorlevel 1 (
    echo Instalando dependencias por primera vez...
    python -m pip install -r "%~dp0requirements.txt"
)

echo.
echo  Abriendo Mi Spotify (app de usuario) en http://localhost:8502
echo  Si el navegador no se abre solo, entra a esa direccion.
echo  Para cerrarla presiona Ctrl + C en esta ventana.
echo.
REM La configuracion usa headless = true, asi que Streamlit no abre el navegador:
REM se abre aqui unos segundos despues, cuando el servidor ya esta listo.
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep 6; Start-Process 'http://localhost:8502'"
python -m streamlit run app_usuario.py --server.port 8502
pause
