@echo off
title Mi Tienda

if not exist "venv\Scripts\activate.bat" (
    echo Creando entorno virtual...
    "C:\Program Files\Python313\python.exe" -m venv venv
)

call venv\Scripts\activate.bat

echo Instalando dependencias...
pip install fastapi uvicorn sqlalchemy python-multipart -q

echo Migrando base de datos...
python migrate.py

echo Preparando datos iniciales...
python seed.py

echo.
echo Servidor listo en http://localhost:8000
echo Para parar: Ctrl+C
echo.

start http://localhost:8000
python -m uvicorn main:app --host 0.0.0.0 --port 8000

pause
