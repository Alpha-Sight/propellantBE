import os
import sys
from dotenv import load_dotenv
from cosmpy.aerial.client import LedgerClient, NetworkConfig
from cosmpy.aerial.wallet import LocalWallet
from cosmpy.aerial.contract import LedgerContract

# Force reload environment variables
load_dotenv(override=True)

# Directly access environment variables
print("=== Environment Variables ===")
contract_address = os.environ["XION_CONTRACT_ADDRESS"]
rpc_url = os.environ["XION_RPC_URL"]
chain_id = os.environ["XION_CHAIN_ID"]
mnemonic = os.environ["XION_ADMIN_MNEMONIC"]

print(f"Contract address: {contract_address}")
print(f"RPC URL: {rpc_url}")
print(f"Chain ID: {chain_id}")

# Format RPC URL
if rpc_url.startswith("https://"):
    formatted_rpc = f"rest+{rpc_url}"
elif rpc_url.startswith("http://"):
    formatted_rpc = f"rest+{rpc_url}"
else:
    formatted_rpc = rpc_url
    
# Network configuration - removed unsupported parameters
cfg = NetworkConfig(
    chain_id=chain_id,
    url=formatted_rpc,
    fee_minimum_gas_price=0.025,
    fee_denomination="uxion",
    staking_denomination="uxion",
    # query_timeout_seconds=30
)

# Create client and wallet
print("\n=== Creating Client and Wallet ===")
try:
    client = LedgerClient(cfg)
    wallet = LocalWallet.from_mnemonic(mnemonic, prefix="xion")
    address = wallet.address()
    print(f"Admin address: {address}")
except Exception as e:
    print(f"Error creating client/wallet: {e}")
    sys.exit(1)

# Try blockchain connection
print("\n=== Testing Blockchain Connection ===")
try:
    height = client.query_height()
    print(f"Connected! Current block height: {height}")
except Exception as e:
    print(f"Error connecting to blockchain: {e}")
    print("Try an alternative RPC endpoint.")
    sys.exit(1)

# Create contract instance
print(f"\n=== Creating Contract Instance ===")
try:
    contract = LedgerContract(contract_address, client)
    print("Contract instance created!")
    
    # Try a basic query
    print("\n=== Testing Contract Query ===")
    # Try different query types that your contract might support
    queries = [
        {"config": {}},
        {"get_config": {}},
        {"state": {}},
        {"owner": {}}
    ]
    
    success = False
    for query in queries:
        try:
            print(f"Trying query: {query}")
            result = contract.query(query)
            print(f"Success! Result: {result}")
            success = True
            break
        except Exception as e:
            print(f"Query failed: {e}")
    
    if not success:
        print("\nAll queries failed. Please check your contract's supported queries.")
        print("You may need to ask your contract developer for the correct query message format.")
        
except Exception as e:
    print(f"Error creating contract instance: {e}")