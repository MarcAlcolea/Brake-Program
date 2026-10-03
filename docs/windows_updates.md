# Keeping the Windows application current

The repository and the downloaded executable are separate copies of the program.
Saving Python files, committing, or pulling Git changes does not update an already
installed executable. Rebuild and install it, or launch `run.bat` from this checkout
to run the current source.

On Lucas's computer, the source checkout is
`C:\Users\Lucas\OneDrive\Documents\GitHub\Brake-Program` (`main`).
The application folder is
`C:\Users\Lucas\Rice\ZD- Rice Racing\Brake Design Studio`.
The old executable in that folder lacked PURPLE and the custom-component library,
although both were already committed in the source and on `origin/main`.
An earlier updated build also existed in the September 26 Codex work folder.

After saving and reviewing source changes, run the tests, commit, and push to the
authorized branch. Build from that same checkout using a Python environment with
the project's dependencies and PyInstaller installed:

```powershell
./packaging/build_windows.ps1 -Python 'path/to/python.exe' -InstallDirectory 'C:/Users/Lucas/Rice/ZD- Rice Racing/Brake Design Studio'
```

This builds the current files, records the source revision and whether it has
uncommitted changes in `build-info.json`, and checks two independent launches.
Close the installed app first. Its previous folder is retained as a timestamped
backup before installing the new build. No saved user configurations or custom
components are replaced. If installation fails, the backup remains available.

Use the application in the Rice folder or its desktop shortcut consistently.
Executables extracted into Downloads or old Codex output folders remain at their
original version. Check `build-info.json` beside the executable when identifying
which source revision it contains.

Vehicle inputs require **Save** or **Save As** in the application. Custom parts
require **Save** in Manage components. They persist under
`%APPDATA%\Brake Design Studio\configs` and `components`, respectively.
Source changes require saving the actual repository files and rebuilding the app.
Keep backups of these user folders when moving computers; Git tracks application
source, not your personal saved vehicle setups.
