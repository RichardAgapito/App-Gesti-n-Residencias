@echo off
echo ===================================================
echo   REINICIANDO BASE DE DATOS - DEMO GESTION RESIDENCIAL
echo ===================================================
echo.

REM 1. Eliminar Base de Datos Anterior
if exist db.sqlite3 (
    echo [1/5] Eliminando db.sqlite3 antigua...
    del db.sqlite3
) else (
    echo [1/5] No existe db.sqlite3, continuando...
)

REM 2. Migraciones
echo.
echo [2/5] Creando tablas (Migrate)...
python manage.py migrate
if %errorlevel% neq 0 (
    echo ERROR: Fallo al ejecutar migraciones. Asegurate de tener el entorno virtual activado.
    pause
    exit /b %errorlevel%
)

REM 3. Llenado de Datos (Usuarios, Complejos, Facturas Noviembre)
echo.
echo [3/5] Poblando datos de prueba (Demo Data)...
python manage.py populate_demo_data

REM 4. Calculo de Mora
echo.
echo [4/5] Calculando moras e intereses...
python manage.py update_financial_status

echo.
echo ===================================================
echo   PROCESO TERMINADO CON EXITO
echo ===================================================
echo.
echo Ya puedes ejecutar: python manage.py runserver
echo.
pause
