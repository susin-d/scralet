@echo off
REM This batch file starts both the frontend and backend servers by running docker-compose up.
REM It ensures the working directory is set to the project root where docker-compose.yml is located.

REM Change to the directory where this batch file is located (project root)
cd /d %~dp0

REM Start all services defined in docker-compose.yml
docker-compose up