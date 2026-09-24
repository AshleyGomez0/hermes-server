@echo off
REM Launch the durable Orca adapter (v2) with full Python path so nohup cannot accidentally
REM invoke the in-memory old server.

setlocal
set "ROOT=C:\hermes-server"
set "PY=C:\Users\ashley\AppData\Local\hermes\hermes-agent\venv\Scripts\pythonw.exe"
set "SRV=%ROOT%\bin\orca-adapter\server.py"
set "DB=%ROOT%\factory\kanban.db"
set "LOG=%ROOT%\state\durable_callbacks\orca_adapter_v2_persistent.stdout.log"

REM Kill any prior instances on :8788 only if they are running the OLD server.py.
REM We do this by port and process-name match.
powershell -NoProfile -Command "(Get-NetTCPConnection -State Listen -LocalPort 8788 -EA SilentlyContinue).OwningProcess | ForEach-Object { Get-CimInstance Win32_Process -Filter ('ProcessId='+$_) | ForEach-Object { $cmd = $_.CommandLine; if ($cmd -notmatch 'bin\\orca-adapter\\server\.py') { try { Stop-Process -Id $_.ProcessId -Force } catch {} } } }"

"\"%PY%\" -u "%SRV%" --port 8788 --host 127.0.0.1 --db "%DB%" > "%LOG%" 2>&1
endlocal
