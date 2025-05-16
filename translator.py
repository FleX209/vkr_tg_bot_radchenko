from deep_translator import GoogleTranslator
from config import LANG_MAP
from image_processing import postprocess_text


def translate(text, target):
    code = LANG_MAP[target]
    return GoogleTranslator(source='auto', target=code).translate(text)

