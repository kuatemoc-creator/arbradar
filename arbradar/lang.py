"""A cheap language guess for feed items that do not say what language they are in.

Function words give a language away in a sentence or two; scripts give the rest
away in a word. Anything the guess is unsure about is English, which is the safe
default: an English item is never damped as unverified foreign copy.
"""
import re
from typing import Dict

_STOP: Dict[str, set] = {
    "es": set("el la de los las en por para con una del que se su al es lo más como sus ha sobre".split()),
    "fr": set("le la les des du une pour dans sur avec est qui que au aux ce cette par ne pas plus été".split()),
    "de": set("der die das und den dem mit für von ist nicht eine ein auf sich des zu im hat wird auch".split()),
    "pt": set("o a e os as de do da dos das em para com uma não que é ao pelo pela foi são mais sua seu".split()),
    "it": set("il di che per con del della una un non sono gli le nel alla dei ha più anche stato".split()),
    "nl": set("het een van en op met voor dat zijn niet aan ook door bij naar heeft worden werd".split()),
    "tr": set("ve bir bu için ile olarak olan tarafından gibi daha en da de ancak sonra karşı".split()),
    "pl": set("się nie jest że przez dla od po jako oraz który została został".split()),
    "id": set("dan yang di untuk dengan dari ini itu pada akan telah tidak oleh dalam".split()),
    "en": set("the and of to in is for on with that by as has its from was were been are will".split()),
}
_SCRIPTS = (
    (re.compile(r"[؀-ۿ]"), "ar"),
    (re.compile(r"[԰-֏]"), "hy"),
    (re.compile(r"[Ⴀ-ჿ]"), "ka"),
    (re.compile(r"[֐-׿]"), "he"),
    (re.compile(r"[一-鿿]"), "zh"),
    (re.compile(r"[぀-ヿ]"), "ja"),
    (re.compile(r"[가-힯]"), "ko"),
    (re.compile(r"[฀-๿]"), "th"),
)


def guess(text: str, default: str = "en") -> str:
    t = text or ""
    if not t.strip():
        return default
    letters = re.findall(r"[^\W\d_]", t)
    if not letters:
        return default
    for pat, code in _SCRIPTS:
        if len(pat.findall(t)) >= 0.3 * len(letters):
            return code
    cyr = re.findall(r"[Ѐ-ӿ]", t)
    if len(cyr) >= 0.3 * len(letters):
        if re.search(r"[іїєґ]", t.lower()):
            return "uk"
        if re.search(r"[ыэъё]", t.lower()) or not re.search(r"[іїє]", t.lower()):
            return "ru"
        return "uk"
    words = re.findall(r"[^\W\d_]+", t.lower())
    if len(words) < 3:
        return default
    best, best_n = default, 0
    en = sum(1 for w in words if w in _STOP["en"])
    for code, stop in _STOP.items():
        if code == "en":
            continue
        n = sum(1 for w in words if w in stop)
        if n > best_n:
            best, best_n = code, n
    if best_n >= 2 and best_n > en:
        return best
    return default
