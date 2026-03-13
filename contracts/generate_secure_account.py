import algosdk
from google.cloud import secretmanager
import os

PROJECT_ID = "purecortexai"
SECRET_NAME = "PURECORTEX_DEPLOYER_MNEMONIC"

def create_hardened_account():
    # 1. Generate Secure Account in memory
    private_key, address = algosdk.account.generate_account()
    mnemonic = algosdk.mnemonic.from_private_key(private_key)
    
    # 2. Push to GCP Secret Manager
    client = secretmanager.SecretManagerServiceClient()
    parent = f"projects/{PROJECT_ID}"
    
    # Create the secret if it doesn't exist
    try:
        client.create_secret(
            request={
                "parent": parent,
                "secret_id": SECRET_NAME,
                "secret": {"replication": {"automatic": {}}},
            }
        )
    except Exception:
        # Secret already exists
        pass
        
    # Add the mnemonic as the first version
    secret_path = client.secret_path(PROJECT_ID, SECRET_NAME)
    client.add_secret_version(
        request={"parent": secret_path, "payload": {"data": mnemonic.encode("UTF-8")}}
    )
    
    # 3. Secure output: Print ADDRESS ONLY
    print(f"✅ HARDENED ACCOUNT GENERATED & SECURED.")
    print(f"Address: {address}")
    print(f"Secret Name: {SECRET_NAME} (v1)")
    print("Mnemonic is now encrypted and stored in GCP Secret Manager.")

if __name__ == "__main__":
    create_hardened_account()
