import os

APP_NAME = os.getenv("APP_NAME", "sitedown")
APP_PORT = int(os.getenv("APP_PORT", "8004"))
APP_TITLE = "SiteDown"
APP_SUBTITLE = "IT Operations"
DD_SERVICE = os.getenv("DD_SERVICE", "sitedown")
DD_ENV = os.getenv("DD_ENV", "proving-grounds")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
FAULT_STATE_FILE = os.getenv("FAULT_STATE_FILE", "/app/data/faults.json")
