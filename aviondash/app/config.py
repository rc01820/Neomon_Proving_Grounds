import os

APP_NAME = os.getenv("APP_NAME", "aviondash")
APP_PORT = int(os.getenv("APP_PORT", "8001"))
APP_TITLE = "AvionDash"
APP_SUBTITLE = "Aviation Operations"
DD_SERVICE = os.getenv("DD_SERVICE", "aviondash")
DD_ENV = os.getenv("DD_ENV", "proving-grounds")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
FAULT_STATE_FILE = os.getenv("FAULT_STATE_FILE", "/app/data/faults.json")
