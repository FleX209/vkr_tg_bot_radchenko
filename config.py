import os


BASE_DIR = os.path.dirname(__file__)
IMAGE_FOLDER = os.path.join(BASE_DIR, 'images')
WORD_FOLDER  = os.path.join(BASE_DIR, 'documents', 'word')
PDF_FOLDER   = os.path.join(BASE_DIR, 'documents', 'pdf')
DB_FILE      = os.path.join(BASE_DIR, 'database.db')


TELEGRAM_TOKEN = '7931020579:AAHP-8DTdM3gHl0oaDgkPQlsLOCO6uSEKdA'

LANG_MAP = {
    'Русский': 'ru',
    'Английский': 'en',
    'Китайский': 'zh-CN',
    'Испанский': 'es',
    'Французский': 'fr',
    'Португальский': 'pt',
    'Немецкий': 'de'
}

