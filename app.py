"""
VoicePay — app.py  (Member 3 — Financial Backend)
==================================================
Flask API that handles wallet transactions and PIN verification.

INSTALL:
    pip install flask

RUN:
    python app.py

TEST with Postman  →  POST http://localhost:5000/process
TEST with curl     →  see examples at bottom of file

ENDPOINTS:
    POST /process   — send money or check balance
    GET  /          — health check
    GET  /wallets   — view all balances (demo/debug only)
"""
import os           

account_sid = os.getenv("TWILIO_SID")
auth_token = os.getenv("TWILIO_AUTH")
from flask import Flask, request, jsonify

app = Flask(__name__)


# ══════════════════════════════════════════════════════
#  MOCK WALLET DATABASE (in-memory)
#  In production: replace with a real DB (SQLite / PostgreSQL)
# ══════════════════════════════════════════════════════
wallets = {
    "ahmad": {"balance": 2000, "pin": "1234"},
    "ali":   {"balance": 1000, "pin": "0000"},
    "aslam": {"balance": 5000, "pin": "4321"},
    "sara":  {"balance": 3000, "pin": "1111"},
}


# ══════════════════════════════════════════════════════
#  VALIDATION HELPERS
# ══════════════════════════════════════════════════════

def user_exists(username: str) -> bool:
    return username.lower() in wallets


def verify_pin(username: str, pin: str) -> bool:
    return wallets[username.lower()]["pin"] == str(pin)


def has_sufficient_balance(username: str, amount: float) -> bool:
    return wallets[username.lower()]["balance"] >= amount


# ══════════════════════════════════════════════════════
#  CORE TRANSACTION FUNCTIONS
# ══════════════════════════════════════════════════════

def send_money(sender: str, recipient: str, amount: float, pin: str) -> tuple[str, int]:
    """
    Transfer `amount` rupees from sender → recipient.
    Returns (message, http_status_code).
    """
    sender    = sender.lower()
    recipient = recipient.lower()

    if not user_exists(sender):
        return "Invalid user", 404

    if not verify_pin(sender, pin):
        return "Incorrect PIN", 401

    if amount <= 0:
        return "Invalid amount — must be greater than zero", 400

    if not user_exists(recipient):
        return "Recipient not found", 404

    if sender == recipient:
        return "Cannot send money to yourself", 400

    if not has_sufficient_balance(sender, amount):
        current = wallets[sender]["balance"]
        return f"Insufficient balance — you have {int(current)} rupees", 400

    # ── Execute transfer ──────────────────────────────
    wallets[sender]["balance"]    -= amount
    wallets[recipient]["balance"] += amount

    new_balance = int(wallets[sender]["balance"])
    return (
        f"{int(amount)} rupees sent to {recipient.capitalize()} successfully. "
        f"Your new balance is {new_balance} rupees.",
        200
    )


def check_balance(sender: str, pin: str) -> tuple[str, int]:
    """
    Return the balance of sender's wallet.
    Returns (message, http_status_code).
    """
    sender = sender.lower()

    if not user_exists(sender):
        return "Invalid user", 404

    if not verify_pin(sender, pin):
        return "Incorrect PIN", 401

    balance = wallets[sender]["balance"]
    return f"Your balance is {int(balance)} rupees", 200


# ══════════════════════════════════════════════════════
#  MAIN ENDPOINT — POST /process
# ══════════════════════════════════════════════════════

@app.route("/process", methods=["POST"])
def process():
    """
    Expected JSON body:
    {
        "action":    "send" | "balance",
        "sender":    "ahmed",
        "pin":       "1234",
        "recipient": "ali",      ← required for "send" only
        "amount":    500         ← required for "send" only
    }
    """
    data = request.get_json(silent=True)

    if not data:
        return "Invalid request — send JSON body", 400, {"Content-Type": "text/plain"}

    action = str(data.get("action", "")).lower().strip()
    sender = str(data.get("sender", "")).lower().strip()
    pin    = str(data.get("pin",    "")).strip()

    # ── Validate required fields ──────────────────────
    if not sender:
        return "Missing field: sender", 400, {"Content-Type": "text/plain"}
    if not pin:
        return "Missing field: pin", 400, {"Content-Type": "text/plain"}
    if not action:
        return "Missing field: action", 400, {"Content-Type": "text/plain"}

    # ── Route by action ───────────────────────────────
    if action == "send":
        recipient  = str(data.get("recipient", "")).lower().strip()
        amount_raw = data.get("amount")

        if not recipient:
            return "Missing field: recipient", 400, {"Content-Type": "text/plain"}
        if amount_raw is None:
            return "Missing field: amount — speak the amount clearly", 400, {"Content-Type": "text/plain"}

        try:
            amount = float(amount_raw)
        except (ValueError, TypeError):
            return "Invalid amount — must be a number", 400, {"Content-Type": "text/plain"}

        result, status = send_money(sender, recipient, amount, pin)

    elif action == "balance":
        result, status = check_balance(sender, pin)

    else:
        result, status = "Unknown action — say 'send' or 'balance'", 400

    return result, status, {"Content-Type": "text/plain"}


# ══════════════════════════════════════════════════════
#  DEBUG ENDPOINT — GET /wallets  (remove before production)
# ══════════════════════════════════════════════════════

@app.route("/wallets", methods=["GET"])
def show_wallets():
    """Show all wallet balances (for demo/testing only — no PINs exposed)."""
    safe = {user: {"balance": info["balance"]} for user, info in wallets.items()}
    return jsonify(safe), 200


# ══════════════════════════════════════════════════════
#  HEALTH CHECK — GET /
# ══════════════════════════════════════════════════════

@app.route("/", methods=["GET"])
def health():
    return "VoicePay Financial Backend is running.", 200, {"Content-Type": "text/plain"}


# ══════════════════════════════════════════════════════
#  RUN
# ══════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "═" * 52)
    print("  💳  VoicePay — Financial Backend")
    print("═" * 52)
    print("  URL:      http://localhost:5000")
    print("  Health:   http://localhost:5000/")
    print("  Wallets:  http://localhost:5000/wallets")
    print("  Process:  POST http://localhost:5000/process")
    print("─" * 52)
    print("  Registered users: ahmed (PIN:1234), ali (PIN:0000)")
    print("                    aslam (PIN:4321), sara (PIN:1111)")
    print("═" * 52 + "\n")
    app.run(debug=True, port=5000)


# ══════════════════════════════════════════════════════
#  CURL QUICK-TEST EXAMPLES
# ══════════════════════════════════════════════════════
# Send money:
#   curl -X POST http://localhost:5000/process \
#        -H "Content-Type: application/json" \
#        -d "{\"action\":\"send\",\"sender\":\"ahmed\",\"pin\":\"1234\",\"recipient\":\"ali\",\"amount\":500}"
#
# Check balance:
#   curl -X POST http://localhost:5000/process \
#        -H "Content-Type: application/json" \
#        -d "{\"action\":\"balance\",\"sender\":\"ahmed\",\"pin\":\"1234\"}"
