"""
Проверка данных от Telegram Login Widget (https://core.telegram.org/widgets/login).
Сайт subboy отправляет сюда данные после нажатия "Login with Telegram".
"""
import hashlib
import hmac
from config import config


def verify_telegram_login(hash_from_telegram: str, **data) -> bool:
    """
    Проверяет, что данные действительно пришли от Telegram.
    hash_from_telegram — поле 'hash' из ответа виджета.
    data — остальные поля: id, first_name, last_name, username, auth_date и т.д.
    """
    if not hash_from_telegram or "auth_date" not in data:
        return False
    # Строка для проверки: ключи в алфавитном порядке, формат key=value через \n
    data_check_parts = [f"{k}={v}" for k, v in sorted(data.items()) if v is not None]
    data_check_string = "\n".join(data_check_parts)
    secret_key = hashlib.sha256(config.BOT_TOKEN.get_secret_value().encode()).digest()
    computed = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(computed, hash_from_telegram)
