@echo off
REM This batch file starts both backend services and frontend development server.
REM It ensures proper sequencing and provides clear output about what's starting.

echo Starting Sentient Retail SaaS Platform...
echo.

REM Change to the directory where this batch file is located (project root)
cd /d %~dp0

echo [1/3] Starting backend services with Docker Compose...
docker-compose up -d
if %errorlevel% neq 0 (
    echo ERROR: Failed to start backend services. Please check Docker and docker-compose setup.
    pause
    exit /b 1
)
echo Backend services started successfully.
echo.

echo [2/3] Starting frontend development server...
cd frontend
npm install
npm run dev
if %errorlevel% neq 0 (
    echo ERROR: Failed to start frontend development server. Please check Node.js and npm setup.
    cd ..
    pause
    exit /b 1
)
echo Frontend development server started successfully.
echo.

echo [3/3] Opening application in default browser...
start http://localhost:8054
echo.

echo All services started successfully!
echo - Backend API Gateway: Running on ports defined in docker-compose.yml
echo - Frontend: http://localhost:3000
echo.
echo Press Ctrl+C to stop all services.
pause
