# PyInstaller Build Guide for MCP Client

> [!NOTE]
> The issue encountered during build is not related to `stdio`, but rather module importing. Always check `error.log` for details.

> [!TIP] Final Solution
> Run the following command from the `client` directory:
> ```bash
> ..\python_env\python.exe -m PyInstaller --noconfirm --onefile --clean --copy-metadata fastmcp --copy-metadata pydantic --collect-data fakeredis --hidden-import=lupa --hidden-import=lupa.lua51 .\mcp_client.py
> ```

## Issue: Silent Dependency Failure

When building a **fastmcp** server executable with **PyInstaller**, the application may crash at runtime. This happens because **fakeredis** (a dependency) conditionally imports **lupa** for Lua scripting support. PyInstaller's static analysis fails to detect this dynamic import.

### Solution: Force Inclusion of Hidden Imports

#### Option 1: Command Line
Explicitly include the missing modules:
```bash
pyinstaller --hidden-import=lupa --hidden-import=lupa.lua51 your_script.py
```

#### Option 2: Spec File (Recommended)
Add the modules to the `hiddenimports` list in your `.spec` file:
```python
a = Analysis(
    # ... existing settings
    hiddenimports=['lupa', 'lupa.lua51'],
    # ... existing settings
)
```

This ensures the required modules (including OS-specific binaries) are bundled, preventing runtime errors.
