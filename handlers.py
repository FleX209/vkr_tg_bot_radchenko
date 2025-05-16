import os
import logging
import re
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from config import IMAGE_FOLDER, LANG_MAP, WORD_FOLDER, PDF_FOLDER
from db_utils import init_db, insert_record, record_exists, fetch_history, fetch_record_by_id, delete_record
from image_processing import extract_text
from translator import translate
from file_savers import save_word, save_pdf

logger = logging.getLogger(__name__)

user_temp = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    init_db()
    welcome = (
        "Привет! 👋\n\n"
        "Я — бот, который поможет тебе распознать текст с изображения 📸, "
        "перевести его на нужный язык 🌍 и сохранить в твоей личной истории 🗂.\n\n"
        "Что я умею:\n"
        "• Принимать изображения\n"
        "• Распознавать текст\n"
        "• Переводить на разные языки\n"
        "• Сохранять переводы в Word и PDF\n"
        "• Показывать историю переводов по запросу\n\n"
    )
    await update.message.reply_text(welcome)
    await reset_to_main_menu(update)


async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    photo = await update.effective_message.photo[-1].get_file()
    folder = os.path.join(IMAGE_FOLDER, str(user_id))
    os.makedirs(folder, exist_ok=True)
    filename = f"{user_id}_{update.effective_message.message_id}.jpg"
    path = os.path.join(folder, filename)
    await photo.download_to_drive(path)

    user_temp[user_id] = {'file_path': path}
    context.user_data['awaiting_source_lang'] = True

    keyboard = [
        ['Русский', 'Английский'],
        ['Китайский', 'Испанский'],
        ['Французский', 'Португальский'],
        ['Немецкий']
    ]
    await update.effective_message.reply_text(
        'Выберите язык текста на фото:',
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    txt = update.effective_message.text

    if txt == 'Загрузить фото':
        await update.effective_message.reply_text('Пожалуйста, отправьте изображение.')
        return
    if txt == 'Просмотр истории':
        await show_history(update, context)
        return
    if txt == 'Очистить историю':
        await clear_history(update, context)
        return

    if context.user_data.get('awaiting_source_lang') and txt in LANG_MAP:
        info = user_temp.get(user_id, {})
        path = info.get('file_path')
        extracted = extract_text(path, LANG_MAP[txt])
        if not extracted or extracted.startswith(('Текст не найден', 'Не удалось')):
            os.remove(path)
            enhanced = re.sub(r"\.jpg$", "_enhanced.jpg", path)
            if os.path.exists(enhanced): os.remove(enhanced)
            await update.effective_message.reply_text('Текст на изображении не найден.')
            user_temp.pop(user_id, None)
            await reset_to_main_menu(update)
            return
        user_temp[user_id]['extracted'] = extracted
        context.user_data.pop('awaiting_source_lang', None)
        context.user_data['awaiting_target_lang'] = True
        await update.effective_message.reply_text(
            'На какой язык перевести?',
            reply_markup=ReplyKeyboardMarkup(
                [['Русский','Английский'], ['Китайский','Испанский'], ['Французский','Португальский'], ['Немецкий']],
                resize_keyboard=True, one_time_keyboard=True
            )
        )
        return

    if context.user_data.get('awaiting_target_lang') and txt in LANG_MAP:
        extracted = user_temp[user_id]['extracted']
        translated = translate(extracted, txt)
        if not translated:
            await update.effective_message.reply_text('Не удалось перевести текст')
            user_temp.pop(user_id, None)
            await reset_to_main_menu(update)
            return
        user_temp[user_id]['translated'] = translated
        context.user_data.pop('awaiting_target_lang', None)
        await update.effective_message.reply_text(f'Перевод:\n{translated}')
        await update.effective_message.reply_text(
            'Хотите сохранить перевод?',
            reply_markup=ReplyKeyboardMarkup([['Сохранить','Не сохранять']], resize_keyboard=True, one_time_keyboard=True)
        )
        return

    if txt == 'Не сохранять':
        # удаляем временные файлы
        info = user_temp.pop(user_id, {})
        fp = info.get('file_path')
        if fp and os.path.exists(fp):
            os.remove(fp)
        enhanced = re.sub(r'(\.jpg)$', r'_enhanced\1', fp) if fp else None
        if enhanced and os.path.exists(enhanced):
            os.remove(enhanced)
        # ответ и возврат в меню
        await update.effective_message.reply_text('Перевод и файлы не сохранены.')
        await reset_to_main_menu(update)
        return

    if txt == 'Сохранить':
        context.user_data['awaiting_name'] = True
        await update.effective_message.reply_text('Введите имя для сохранения:')
        return

    if context.user_data.get('awaiting_name'):
        name = txt.strip()
        context.user_data['name'] = name
        if record_exists(user_id, name):
            await update.effective_message.reply_text(
                f"Запись '{name}' уже существует. Перезаписать или другое имя?",
                reply_markup=ReplyKeyboardMarkup(
                    [['Перезаписать','Новое имя']], resize_keyboard=True, one_time_keyboard=True
                )
            )
        else:
            await update.effective_message.reply_text(
                'Выберите формат для сохранения:',
                reply_markup=ReplyKeyboardMarkup(
                    [['Word','PDF'], ['Не сохранять в файл']],
                    resize_keyboard=True, one_time_keyboard=True
                )
            )
        context.user_data.pop('awaiting_name', None)
        return

    if txt in ('Перезаписать','Новое имя'):
        if txt == 'Новое имя':
            context.user_data['awaiting_name'] = True
            await update.effective_message.reply_text('Введите новое имя:')
            return
        name = context.user_data.get('name')
        info = user_temp.pop(user_id, {})
        fp, ex, tr = info['file_path'], info['extracted'], info['translated']
        path = save_word(user_id, name, ex, tr)
        with open(path, 'rb') as doc:
            await update.effective_message.reply_document(doc)
        insert_record(user_id, fp, name, ex, tr, path)
        await update.effective_message.reply_text(f"Запись '{name}' перезаписана.")
        await reset_to_main_menu(update)
        return

    if txt in ('Word','PDF'):
        name = context.user_data.get('name')
        info = user_temp.pop(user_id, {})
        fp, ex, tr = info['file_path'], info['extracted'], info['translated']
        path = save_word(user_id, name, ex, tr) if txt == 'Word' else save_pdf(user_id, name, ex, tr)
        with open(path, 'rb') as doc:
            await update.effective_message.reply_document(doc)
        insert_record(user_id, fp, name, ex, tr, path)
        await update.effective_message.reply_text(f"Перевод '{name}' сохранён.")
        await reset_to_main_menu(update)
        return

    if txt == 'Не сохранять в файл':
        info = user_temp.pop(user_id, {})
        name = context.user_data.get('name', 'Без названия')
        insert_record(user_id, info['file_path'], name, info['extracted'], info['translated'], None)
        await update.effective_message.reply_text('Перевод сохранён в истории без файла.')
        await reset_to_main_menu(update)
        return

    if context.user_data.get('awaiting_source_lang'):
        await update.effective_message.reply_text(
            'Нужно выбрать язык исходного текста кнопками ниже.'
        )
        return

    if context.user_data.get('awaiting_target_lang'):
        await update.effective_message.reply_text(
            'Нужно выбрать язык для перевода кнопками ниже.'
        )
        return

    if context.user_data.get('awaiting_name'):
        await update.effective_message.reply_text(
            'Пожалуйста, введите имя для сохранения (или выберите «Перезаписать/Новое имя»).'
        )
        return

    await update.effective_message.reply_text('Пожалуйста, используйте кнопки меню.')


async def reset_to_main_menu(update: Update) -> None:
    markup = ReplyKeyboardMarkup(
        [['Загрузить фото'], ['Просмотр истории','Очистить историю']],
        resize_keyboard=True
    )
    await update.effective_message.reply_text('Выберите действие:', reply_markup=markup)


async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    rows = fetch_history(user_id)
    if not rows:
        await update.effective_message.reply_text('История пуста.')
        return
    buttons = []
    for rec in rows:
        pid = rec['id']
        buttons.append([
            InlineKeyboardButton(rec['photo_name'], callback_data=f"show_{pid}"),
            InlineKeyboardButton("Удалить", callback_data=f"del_{pid}")
        ])
    await update.effective_message.reply_text(
        'Выберите запись:',
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    rows = fetch_history(user_id)
    for rec in rows:
        fp = rec['file_path']
        if fp and os.path.exists(fp):
            os.remove(fp)
            enhanced = re.sub(r"(\.jpg)$", r"_enhanced\1", fp)
            if os.path.exists(enhanced):
                os.remove(enhanced)
        sp = rec['saved_file_path']
        if sp and os.path.exists(sp):
            os.remove(sp)
    delete_record(user_id)

    for folder in (IMAGE_FOLDER, WORD_FOLDER, PDF_FOLDER):
        user_folder = os.path.join(folder, str(user_id))
        try:
            if os.path.isdir(user_folder) and not os.listdir(user_folder):
                os.rmdir(user_folder)
        except OSError:
            logger.warning(f"Не удалось удалить папку {user_folder}")
    await update.effective_message.reply_text('История очищена.')
    await reset_to_main_menu(update)


async def handle_photo_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    if data.startswith('show_'):
        pid = int(data.split('_')[1])
        rec = fetch_record_by_id(pid)
        if not rec:
            await query.message.reply_text('Запись не найдена.')
            return

        file_path = rec.get('file_path')
        if file_path and os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                await query.message.reply_photo(f, caption=f"Фото из записи '{rec['photo_name']}'")

        text_parts = [
            f"Название: {rec['photo_name']}",
            f"Дата: {rec['timestamp']}",
            f"\nРаспознанный текст:\n{rec['extracted_text']}",
            f"\nПереведённый текст:\n{rec['translated_text']}"
        ]
        await query.message.reply_text('\n'.join(text_parts))

        # Отправка файла (если есть)
        doc_path = rec.get('saved_file_path')
        if doc_path and os.path.exists(doc_path):
            with open(doc_path, 'rb') as f:
                await query.message.reply_document(f)
        await show_history(update, context)
    elif data.startswith('del_'):
        pid = int(data.split('_')[1])
        rec = fetch_record_by_id(pid)
        if rec:
            # Удаляем оригинал и его enhanced
            fp = rec['file_path']
            if fp and os.path.exists(fp):
                os.remove(fp)
                enhanced = re.sub(r"(\.jpg)$", r"_enhanced\1", fp)
                if os.path.exists(enhanced): os.remove(enhanced)
            sp = rec['saved_file_path']
            if sp and os.path.exists(sp): os.remove(sp)
        delete_record(user_id, pid)
        await query.message.reply_text('Запись удалена.')
        # Чистим пустые директории
        for folder in (IMAGE_FOLDER, WORD_FOLDER, PDF_FOLDER):
            user_folder = os.path.join(folder, str(user_id))
            try:
                if os.path.isdir(user_folder) and not os.listdir(user_folder):
                    os.rmdir(user_folder)
            except OSError:
                logger.warning(f"Не удалось удалить папку {user_folder}")

        await show_history(update, context)
