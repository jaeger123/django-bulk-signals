"""Settings for the test suite.

The database backend is selected with DB_BACKEND=sqlite|postgres|mysql so the
same suite can run against every backend in CI.
"""

import os

BACKEND = os.environ.get("DB_BACKEND", "sqlite")

if BACKEND == "mysql":  # pure-python driver, no system libs needed
    import pymysql

    pymysql.install_as_MySQLdb()

DATABASES = {
    "default": {
        "sqlite": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        },
        "postgres": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("PG_NAME", "bulksig"),
            "USER": os.environ.get("PG_USER", "bulksig"),
            "PASSWORD": os.environ.get("PG_PASSWORD", "bulksig"),
            "HOST": os.environ.get("PG_HOST", "127.0.0.1"),
            "PORT": os.environ.get("PG_PORT", "5432"),
        },
        "mysql": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.environ.get("MY_NAME", "bulksig"),
            "USER": os.environ.get("MY_USER", "root"),
            "PASSWORD": os.environ.get("MY_PASSWORD", "bulksig"),
            "HOST": os.environ.get("MY_HOST", "127.0.0.1"),
            "PORT": os.environ.get("MY_PORT", "3306"),
        },
    }[BACKEND]
}

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "tests",
]

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
USE_TZ = True
SECRET_KEY = "test-only-not-a-secret"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
