' STOCK UNDO! Silent Windows Background Launcher
WScript.Sleep 3000
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "A:\Stock Undoo\backend"
WshShell.Run """A:\Stock Undoo\backend\.venv\Scripts\python.exe"" -m uvicorn app.main:app --host 0.0.0.0 --port 8000", 0, False
