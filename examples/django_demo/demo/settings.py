from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = "local-flowtoken-demo-only"
DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "py_flowtoken.adapters.django.apps.FlowTokenConfig",
]
ROOT_URLCONF = "demo.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "demo/templates"],
        "APP_DIRS": True,
    }
]
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / ".static"
FLOWTOKEN_ASSET_MODE = "route"
