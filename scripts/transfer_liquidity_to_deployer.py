"""Transfer ALGO from liquidity wallet to deployer via the signing vault."""
import json, base64, os, socket
from algosdk.v2client import algod
from algosdk import transaction
from algosdk.encoding import msgpack_encode

LIQUIDITY = "CM4FNHTBOUEFH44IFHLQBZKV5WLYVGCDREB5JUEKHRKKS5T6MHJCTMNZYU"
DEPLOYER = "R7CLPM5L3CQ62PHF347KDIEHKUHIFJYTYVVG6JU6XNT5MFCQOK5V33XMWI"

client = algod.AlgodClient("", "https://mainnet-api.4160.nodely.dev")
info = client.account_info(LIQUIDITY)
print(f"Liquidity balance: {info['amount']/1e6} ALGO")

params = client.suggested_params()
txn = transaction.PaymentTxn(
    sender=LIQUIDITY,
    sp=params,
    receiver=DEPLOYER,
    amt=11_000_000_000,
    note=b"Transfer to deployer for DEX pool seeding",
)

encoded = msgpack_encode(txn)
if isinstance(encoded, str):
    encoded = base64.b64decode(encoded)
txn_b64 = base64.b64encode(encoded).decode()
SOCKET_PATH = os.environ.get("PURECORTEX_SIGNER_SOCKET_PATH", "/run/purecortex/socket/signer.sock")
TOKEN = os.environ.get("PURECORTEX_SIGNER_SHARED_TOKEN", "")

request = json.dumps({
    "action": "sign_transaction",
    "identity": "liquidityPool",
    "transaction_b64": txn_b64,
    "token": TOKEN,
}) + "\n"

print(f"Connecting to signer at {SOCKET_PATH}...")
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.settimeout(30)
sock.connect(SOCKET_PATH)
sock.sendall(request.encode())

response = b""
while True:
    chunk = sock.recv(4096)
    if not chunk:
        break
    response += chunk
    if b"\n" in response:
        break
sock.close()

resp = json.loads(response.decode().strip())
if resp.get("signed_transaction_b64"):
    signed = base64.b64decode(resp["signed_transaction_b64"])
    tx_id = client.send_raw_transaction(signed)
    print(f"TX submitted: {tx_id}")
    result = transaction.wait_for_confirmation(client, tx_id, 10)
    print(f"Confirmed round: {result.get('confirmed-round')}")
    print("SUCCESS")
elif resp.get("error"):
    print(f"Signer error: {resp['error']}")
else:
    print(f"Response: {json.dumps(resp)[:300]}")
