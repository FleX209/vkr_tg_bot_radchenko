import cv2
import time
import logging
from functools import wraps
from config import IMAGE_FOLDER
import os
import re
import easyocr

logger = logging.getLogger(__name__)


def timeit(label):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            duration = time.perf_counter() - start
            logger.info(f"[{label}] {func.__name__}: {duration:.3f} сек")
            return result
        return wrapper
    return decorator


def postprocess_text(text):
    return re.sub(r'([:;])(?=\s|$)', '.', text)


@timeit("PREPROC")
def enhance_image(path):
    img = cv2.imread(path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    up = cv2.resize(thresh, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    out = path.replace('.jpg', '_enhanced.jpg')
    cv2.imwrite(out, up)
    return out


@timeit("OCR")
def extract_text(image_path, lang_code):
    enhanced = enhance_image(image_path)
    ocr_lang = 'ch_sim' if lang_code == 'zh-CN' else lang_code
    langs = [ocr_lang, 'en'] if ocr_lang == 'ch_sim' else [ocr_lang]
    try:
        reader = easyocr.Reader(langs, gpu=True)
        result = reader.readtext(enhanced, detail=0, paragraph=True)
        text = '\n'.join(result) if result else 'Текст не найден.'
    except Exception as e:
        logger.error(f'OCR error: {e}')
        text = 'Не удалось распознать текст.'
    return postprocess_text(text)

