"""
Translation component: DeepL-based sync translation for use from async code via run_in_executor.
"""
import os
from typing import Optional

from deepl import Translator
from deepl.exceptions import DeepLException

# Load env so DEEPL_* are available when this module is imported
def _load_env() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass


_load_env()

DEEPL_AUTH_KEY: Optional[str] = os.getenv("DEEPL_AUTH_KEY")
DEEPL_SOURCE_LANG: Optional[str] = os.getenv("DEEPL_SOURCE_LANG")  # e.g. "EN", or None for auto-detect
DEEPL_TARGET_LANG: str = os.getenv("DEEPL_TARGET_LANG", "ES").upper()  # e.g. "ES", "DE", "EN"

_translator: Optional[Translator] = None


def get_translator() -> Translator:
    """Return the shared DeepL Translator instance. Raises if auth key is missing."""
    global _translator
    if not DEEPL_AUTH_KEY:
        raise ValueError("DEEPL_AUTH_KEY not set in environment")
    if _translator is None:
        _translator = Translator(DEEPL_AUTH_KEY)
    return _translator


def translate_text_sync(text: str) -> str:
    """
    Synchronous translation: call from a thread (e.g. via run_in_executor).
    Returns translated string. On failure, raises DeepLException or returns original text
    depending on configuration; here we raise so the caller can decide (e.g. send original).
    """
    if not text or not text.strip():
        return text
    translator = get_translator()
    result = translator.translate_text(
        text,
        source_lang=DEEPL_SOURCE_LANG or None,  # None => auto-detect
        target_lang=DEEPL_TARGET_LANG,
    )
    return result.text
