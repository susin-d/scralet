@echo off
REM This batch file starts the services in the background and opens the frontend in the default browser.
REM It ensures the working directory is set to the project root where docker-compose.yml is located.

REM Change to the directory where this batch file is located (project root)
cd /d %~dp0

REM Start all services defined in docker-compose.yml in detached mode
docker-compose up -d

REM Open the frontend in the default web browser
start http://localhost