"""
Main application runner for CV AI Assistant
"""
# Simple file interceptor for contract addresses
import builtins
from io import StringIO

# Store original open function
original_open = builtins.open

# Create straightforward interceptor
def safe_open(file, *args, **kwargs):
    """Prevent file not found errors with contract addresses"""
    if isinstance(file, str) and file.startswith("xion1"):
        print(f"🛡️ Prevented file access to: {file}")
        return StringIO("")
    return original_open(file, *args, **kwargs)

# Apply the patch
builtins.open = safe_open

# Standard imports
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )