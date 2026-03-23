@echo off
cd /d "%~dp0"

lualatex main.tex && biber main && lualatex main.tex && lualatex main.tex

if exist "..\tex.zip" del /f /q "..\tex.zip"

tar -a -c -f "..\tex.zip" ^
  main.tex ^
  build.bat ^
  .gitignore ^
  bib ^
  sections ^
  images

pause