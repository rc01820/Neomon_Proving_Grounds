import os

APP_NAME = os.getenv("APP_NAME", "blackledger")
APP_PORT = int(os.getenv("APP_PORT", "8003"))
APP_TITLE = "BlackLedger"
APP_SUBTITLE = "Financial Operations"
DD_SERVICE = os.getenv("DD_SERVICE", "blackledger")
DD_ENV = os.getenv("DD_ENV", "proving-grounds")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
FAULT_STATE_FILE = os.getenv("FAULT_STATE_FILE", "/app/data/faults.json")
