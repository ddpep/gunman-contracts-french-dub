@echo off
rem ===========================================================================
rem  Gunman Contracts FR - installer launcher
rem
rem  Prepares everything the installer needs, then launches it:
rem    1. finds a Python 3.9+ interpreter (or offers to install one)
rem    2. creates a private virtual environment in .venv
rem    3. installs the dependencies listed in requirements.txt
rem    4. runs app.py
rem
rem  Nothing is installed system-wide, and no administrator rights are needed
rem  at this stage. The installer itself asks for elevation only when it has to
rem  write into the game folder (usually Program Files).
rem ===========================================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title Gunman Contracts FR - preparation

echo.
echo  ==========================================================
echo    Gunman Contracts - Stand Alone : doublage francais
echo    Preparation de l'environnement
echo  ==========================================================
echo.

rem ---------------------------------------------------------------- Python ---
rem Test each candidate on its own: inside a for-loop, errorlevel reflects the
rem last command run, not the interpreter that actually answered.
set "PYEXE="
call :try_python py
if not defined PYEXE call :try_python python
if not defined PYEXE call :try_python python3

if not defined PYEXE (
    echo  Python 3.9 ou plus recent est introuvable sur cet ordinateur.
    echo.
    where winget >nul 2>&1
    if !errorlevel! equ 0 (
        echo  winget peut l'installer pour toi, sans droits administrateur.
        set /p "ANSWER= Installer Python maintenant ? [O/n] "
        if /i not "!ANSWER!"=="n" (
            echo.
            echo  Installation de Python en cours, cela peut prendre une minute...
            winget install --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
            echo.
            echo  Python installe. Ferme cette fenetre et relance INSTALLER.bat.
            pause
            exit /b 0
        )
    ) else (
        echo  winget n'est pas disponible sur ce systeme.
    )
    echo.
    echo  Installe Python toi-meme : voir INSTALLATION.md, section "A la main".
    echo  Pense a cocher "Add python.exe to PATH" pendant l'installation.
    echo.
    pause
    exit /b 1
)

echo  Python trouve : %PYEXE%
%PYEXE% -c "import sys;print('  version', sys.version.split()[0])"

rem ------------------------------------------------------------------ venv ---
rem A .venv folder can exist while its interpreter is broken (interrupted run,
rem Python uninstalled, antivirus quarantine): test it, rebuild it if it fails.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import sys" >nul 2>&1
    if errorlevel 1 (
        echo.
        echo  Environnement .venv invalide : reconstruction...
        rmdir /s /q ".venv"
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo  Creation de l'environnement isole .venv ...
    %PYEXE% -m venv .venv
    if errorlevel 1 (
        echo.
        echo  ECHEC : impossible de creer .venv
        echo  Cause la plus frequente : Python installe depuis le Microsoft Store,
        echo  qui ne permet pas de creer un environnement virtuel.
        echo  Solution : winget install Python.Python.3.12 --scope user
        pause
        exit /b 1
    )
) else (
    echo.
    echo  Environnement .venv deja present.
)

set "VPY=.venv\Scripts\python.exe"

rem ---------------------------------------------------------- dependencies ---
"%VPY%" -c "import UnityPy" >nul 2>&1
if errorlevel 1 (
    echo.
    echo  Installation des dependances ^(UnityPy, une seule ligne^)...
    "%VPY%" -m pip install --upgrade pip --quiet --disable-pip-version-check
    "%VPY%" -m pip install -r requirements.txt --disable-pip-version-check
    if errorlevel 1 (
        echo.
        echo  ECHEC de l'installation des dependances.
        echo  Verifie ta connexion internet, puis relance ce fichier.
        pause
        exit /b 1
    )
) else (
    echo  Dependances deja installees.
)

rem --------------------------------------------------------------- launch ---
echo.
echo  Lancement de l'installeur...
echo.
"%VPY%" app.py
set "RC=%errorlevel%"

if not "%RC%"=="0" (
    echo.
    echo  L'installeur s'est termine avec le code %RC%.
    pause
)
exit /b %RC%

rem ---------------------------------------------------------------------------
:try_python
rem Reject the Microsoft Store alias: it opens the Store instead of running, and
rem cannot create a virtual environment.
where %1 >nul 2>&1
if errorlevel 1 exit /b 1
for /f "delims=" %%P in ('where %1 2^>nul') do (
    echo %%~P | find /i "WindowsApps" >nul
    if errorlevel 1 (
        %1 -c "import sys;raise SystemExit(0 if sys.version_info>=(3,9) else 1)" >nul 2>&1
        if not errorlevel 1 (
            set "PYEXE=%1"
            exit /b 0
        )
    )
)
exit /b 1
