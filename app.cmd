@echo off
rem Windows entrypoint for local-recommender. Propagates arguments and exit code.
setlocal
python "%~dp0app" %*
exit /b %ERRORLEVEL%
