import os
from dotenv import load_dotenv

# Force reload environment variables
load_dotenv(override=True)

print("=== XION Environment Variables ===")
for key, value in os.environ.items():
    if key.startswith("XION"):
        # Hide mnemonic but show other variables
        if "MNEMONIC" in key:
            print(f"{key}: [HIDDEN]")
        else:
            print(f"{key}: {value}")