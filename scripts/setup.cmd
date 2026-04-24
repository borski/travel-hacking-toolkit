@echo off
REM Travel Hacking Toolkit - Windows setup launcher.
REM Invokes setup.ps1 with an ExecutionPolicy bypass so users don't have to fiddle with policy.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1" %*
