import os
from pathlib import Path
from ssl import CERT_REQUIRED
from urllib.parse import parse_qs, parse_qsl, unquote, urlencode, urlsplit, urlunsplit

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


def _load_local_env():
    """Load project-local secrets for Django and Celery when not already exported."""
    env_file = BASE_DIR / '.env'
    if not env_file.is_file():
        return
    for raw_line in env_file.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        name, value = line.split('=', 1)
        name, value = name.strip(), value.strip()
        if value[:1] == value[-1:] and value[:1] in ('"', "'"):
            value = value[1:-1]
        if name and not os.environ.get(name):
            os.environ[name] = value


_load_local_env()

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-local-development-key')
DEBUG = True
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'media_engine',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core_server.urls'
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.debug',
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ]},
}]
WSGI_APPLICATION = 'core_server.wsgi.application'
database_url = os.environ.get('DATABASE_URL', '').strip()
if database_url.startswith(('postgres://', 'postgresql://', 'postgresql+psycopg://')):
    parsed_database = urlsplit(database_url.replace('postgresql+psycopg://', 'postgresql://', 1))
    database_options = parse_qs(parsed_database.query)
    DATABASES = {'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': unquote(parsed_database.path.lstrip('/')),
        'USER': unquote(parsed_database.username or ''),
        'PASSWORD': unquote(parsed_database.password or ''),
        'HOST': parsed_database.hostname or '',
        'PORT': parsed_database.port or '',
        'OPTIONS': {key: values[-1] for key, values in database_options.items()},
    }}
else:
    sqlite_path = database_url.removeprefix('sqlite:///') if database_url else str(BASE_DIR / 'db.sqlite3')
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': sqlite_path}}
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Configure these environment variables with a real Redis URL to enable background jobs.
# Leaving them unset keeps the site usable and lets uploads report that setup is needed.
def _require_tls_verification(redis_url):
    """Add Celery's required TLS verification parameter to rediss URLs."""
    if not redis_url or urlsplit(redis_url).scheme != 'rediss':
        return redis_url
    parsed = urlsplit(redis_url)
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key != 'ssl_cert_reqs'
    ]
    query.append(('ssl_cert_reqs', 'required'))
    return urlunsplit(parsed._replace(query=urlencode(query)))


CELERY_BROKER_URL = _require_tls_verification(
    os.environ.get('CELERY_BROKER_URL', '').strip()
)
CELERY_RESULT_BACKEND = _require_tls_verification(
    os.environ.get('CELERY_RESULT_BACKEND', CELERY_BROKER_URL).strip()
)

# Required SSL configuration for secure cloud brokers like Upstash Redis
CELERY_BROKER_USE_SSL = {'ssl_cert_reqs': CERT_REQUIRED} if CELERY_BROKER_URL.startswith('rediss://') else None
CELERY_REDIS_BACKEND_USE_SSL = {'ssl_cert_reqs': CERT_REQUIRED} if CELERY_RESULT_BACKEND.startswith('rediss://') else None

# Serialization and Timezone settings
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Kolkata'
