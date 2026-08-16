import os

APP_NAME = os.getenv("APP_NAME", "codeblue")
APP_PORT = int(os.getenv("APP_PORT", "8002"))
APP_TITLE = "CodeBlue"
APP_SUBTITLE = "Healthcare Operations"
DD_SERVICE = os.getenv("DD_SERVICE", "codeblue")
DD_ENV = os.getenv("DD_ENV", "proving-grounds")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
FAULT_STATE_FILE = os.getenv("FAULT_STATE_FILE", "/app/data/faults.json")
