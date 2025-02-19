@echo off
setlocal
set "vision_point_env_name=%KAYA_VISION_POINT_APP_PATH%"
set "vision_point_exe=%vision_point_env_name%\VisionPoint.exe
rem get current directory
set "script_dir=%~dp0"
rem get JS file
set "case_path=case_2851.js"
"%vision_point_exe%" --guiscript "%script_dir%\%case_path%" --guiscriptParameters "--deviceIndex 1 "