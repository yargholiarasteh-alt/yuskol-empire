# -*- coding: utf-8 -*-
import random
import json
import os
import time
import shutil

from kivy.app import App
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.progressbar import ProgressBar

Window.clearcolor = (0.06, 0.08, 0.13, 1)

# Persian-capable font selection.
# Prefer a bundled Vazirmatn font; otherwise try Android's Arabic-capable fonts.
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_FONT_CANDIDATES = [
    os.path.join(_BASE_DIR, "Vazirmatn-Regular.ttf"),
    "/system/fonts/NotoNaskhArabic-Regular.ttf",
    "/system/fonts/NotoSansArabic-Regular.ttf",
    "/system/fonts/NotoSansArabicUI-Regular.ttf",
]
FONT_PATH = next((path for path in _FONT_CANDIDATES if os.path.isfile(path)), None)
if FONT_PATH:
    try:
        LabelBase.register(name="PersianFont", fn_regular=FONT_PATH)
        FONT_NAME = "PersianFont"
    except Exception:
        FONT_NAME = "Roboto"
else:
    FONT_NAME = "Roboto"


# Persian RTL support. The optional libraries give the most reliable rendering.
# If they are not installed, the built-in shaping fallback below is used.
import re
try:
    import arabic_reshaper as _arabic_reshaper
    from bidi.algorithm import get_display as _bidi_get_display
    _HAS_RTL_LIBS = True
except ImportError:
    _HAS_RTL_LIBS = False

# Presentation forms: isolated, final, initial, medial. None means unavailable.
_PERSIAN_FORMS = {
    'ا': (0xFE8D, 0xFE8E, None, None), 'آ': (0xFE81, 0xFE82, None, None),
    'ب': (0xFE8F, 0xFE90, 0xFE91, 0xFE92), 'پ': (0xFB56, 0xFB57, 0xFB58, 0xFB59),
    'ت': (0xFE95, 0xFE96, 0xFE97, 0xFE98), 'ث': (0xFE99, 0xFE9A, 0xFE9B, 0xFE9C),
    'ج': (0xFE9D, 0xFE9E, 0xFE9F, 0xFEA0), 'چ': (0xFB7A, 0xFB7B, 0xFB7C, 0xFB7D),
    'ح': (0xFEA1, 0xFEA2, 0xFEA3, 0xFEA4), 'خ': (0xFEA5, 0xFEA6, 0xFEA7, 0xFEA8),
    'د': (0xFEA9, 0xFEAA, None, None), 'ذ': (0xFEAB, 0xFEAC, None, None),
    'ر': (0xFEAD, 0xFEAE, None, None), 'ز': (0xFEAF, 0xFEB0, None, None),
    'ژ': (0xFB8A, 0xFB8B, None, None), 'س': (0xFEB1, 0xFEB2, 0xFEB3, 0xFEB4),
    'ش': (0xFEB5, 0xFEB6, 0xFEB7, 0xFEB8), 'ص': (0xFEB9, 0xFEBA, 0xFEBB, 0xFEBC),
    'ض': (0xFEBD, 0xFEBE, 0xFEBF, 0xFEC0), 'ط': (0xFEC1, 0xFEC2, 0xFEC3, 0xFEC4),
    'ظ': (0xFEC5, 0xFEC6, 0xFEC7, 0xFEC8), 'ع': (0xFEC9, 0xFECA, 0xFECB, 0xFECC),
    'غ': (0xFECD, 0xFECE, 0xFECF, 0xFED0), 'ف': (0xFED1, 0xFED2, 0xFED3, 0xFED4),
    'ق': (0xFED5, 0xFED6, 0xFED7, 0xFED8), 'ک': (0xFB8E, 0xFB8F, 0xFB90, 0xFB91),
    'گ': (0xFB92, 0xFB93, 0xFB94, 0xFB95), 'ل': (0xFEDD, 0xFEDE, 0xFEDF, 0xFEE0),
    'م': (0xFEE1, 0xFEE2, 0xFEE3, 0xFEE4), 'ن': (0xFEE5, 0xFEE6, 0xFEE7, 0xFEE8),
    'و': (0xFEED, 0xFEEE, None, None), 'ه': (0xFEE9, 0xFEEA, 0xFEEB, 0xFEEC),
    'ی': (0xFBFC, 0xFBFD, 0xFBFE, 0xFBFF), 'ء': (0xFE80, None, None, None),
    'ئ': (0xFE89, 0xFE8A, 0xFE8B, 0xFE8C), 'ؤ': (0xFE85, 0xFE86, None, None),
    'أ': (0xFE83, 0xFE84, None, None), 'إ': (0xFE87, 0xFE88, None, None),
    'ة': (0xFE93, 0xFE94, None, None), 'ى': (0xFEEF, 0xFEF0, None, None),
}
_ARABIC_CHARS = set(_PERSIAN_FORMS)
_MARKUP_RE = re.compile(r'(\[[^\]]+\])')

def _shape_word(word):
    chars = list(word)
    out = []
    for i, ch in enumerate(chars):
        forms = _PERSIAN_FORMS.get(ch)
        if not forms:
            out.append(ch)
            continue
        prev = chars[i - 1] if i > 0 else ''
        nxt = chars[i + 1] if i + 1 < len(chars) else ''
        pf = _PERSIAN_FORMS.get(prev)
        nf = _PERSIAN_FORMS.get(nxt)
        joins_prev = bool(pf and pf[2] is not None and forms[1] is not None)
        joins_next = bool(nf and forms[2] is not None and nf[1] is not None)
        if joins_prev and joins_next and forms[3] is not None:
            code = forms[3]
        elif joins_prev:
            code = forms[1] if forms[1] is not None else forms[0]
        elif joins_next and forms[2] is not None:
            code = forms[2]
        else:
            code = forms[0]
        out.append(chr(code))
    return ''.join(reversed(out))

def _rtl_segment(text):
    # Reverse word order for Kivy's left-to-right renderer; shape Persian words.
    words = text.split(' ')
    words = [(_shape_word(w) if any(c in _ARABIC_CHARS for c in w) else w) for w in words]
    return ' '.join(reversed(words))

def rtl_text(text):
    if not isinstance(text, str) or not any(c in _ARABIC_CHARS for c in text):
        return text

    # Preferred path: proper Arabic shaping + Unicode bidirectional algorithm.
    # Markup tags are kept intact so Kivy can still render [b], [i], etc.
    if _HAS_RTL_LIBS:
        parts = re.split(r'(\[/?[a-zA-Z][^\]]*\])', text)
        return ''.join(
            part if part.startswith('[') and part.endswith(']')
            else '\n'.join(
                _bidi_get_display(_arabic_reshaper.reshape(line))
                for line in part.split('\n')
            )
            for part in parts
        )

    # Dependency-free fallback for Pydroid installations without those modules.
    parts = _MARKUP_RE.split(text)
    return ''.join(
        part if part.startswith('[') and part.endswith(']')
        else '\n'.join(_rtl_segment(line) for line in part.split('\n'))
        for part in parts
    )

# Transform widget text at creation time without adding dependencies.
_KivyLabel = Label
_KivyButton = Button
class Label(_KivyLabel):
    def __init__(self, **kwargs):
        kwargs.setdefault('font_name', FONT_NAME)
        if 'text' in kwargs:
            kwargs['text'] = rtl_text(kwargs['text'])
        super().__init__(**kwargs)

class Button(_KivyButton):
    def __init__(self, **kwargs):
        kwargs.setdefault('font_name', FONT_NAME)
        if 'text' in kwargs:
            kwargs['text'] = rtl_text(kwargs['text'])
        super().__init__(**kwargs)


CITIES = [
    "یوسکول‌شهر",
    "باتری‌آباد",
    "نوکیاستان",
    "آنتن‌آباد",
    "Snake City",
    "مرز اپل"
]

# شهرهای تازه‌ای که هنوز تصرف نشده‌اند
FRONTIER_CITIES = {
    "ربات‌آباد": 25,
    "پردازش‌گر": 40,
    "قلعهٔ سیب": 60,
    "دژ هوش مصنوعی": 80,
}


class YuskolGame(App):

    def build(self):
        self.title = "امپراتوری یوسکول"

        self.money = 500
        self.army = 20
        self.health = 100
        self.battery = 100
        self.score = 0
        self.enemy = 80
        self.cities = {city: 1 for city in CITIES}
        self.boss_health = 250

        # امکانات نسخهٔ جدید
        self.gems = 0
        self.last_daily_reward = ""
        self.achievements = []
        self.defense = 0
        self.elite_troops = 0
        self.frontier = dict(FRONTIER_CITIES)
        self.claimed_missions = []

        root = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(8)
        )

        title = Label(
            text="[b]امپراتوری یوسکول[/b]",
            markup=True,
            font_name=FONT_NAME,
            font_size=sp(23),
            size_hint_y=None,
            height=dp(48)
        )
        root.add_widget(title)

        self.status = Label(
            text="",
            markup=True,
            font_name=FONT_NAME,
            font_size=sp(14),
            size_hint_y=None,
            height=dp(112),
            halign="center",
            valign="middle"
        )
        root.add_widget(self.status)

        self.area = BoxLayout(
            orientation="vertical",
            spacing=dp(7)
        )
        root.add_widget(self.area)

        self.refresh()
        self.home()
        return root

    def _save_path(self):
        return os.path.join(self.user_data_dir, "yuskol_save.json")

    def _write_save(self):
        """Save safely; preserve the previous valid save as a backup."""
        data = {
            "money": self.money,
            "army": self.army,
            "health": self.health,
            "battery": self.battery,
            "score": self.score,
            "enemy": self.enemy,
            "cities": self.cities,
            "boss_health": self.boss_health,
            "gems": self.gems,
            "last_daily_reward": self.last_daily_reward,
            "achievements": self.achievements,
            "defense": self.defense,
            "elite_troops": self.elite_troops,
            "frontier": self.frontier,
            "claimed_missions": self.claimed_missions,
        }
        path = self._save_path()
        temp_path = path + ".tmp"
        backup_path = path + ".bak"
        os.makedirs(self.user_data_dir, exist_ok=True)
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        if os.path.exists(path):
            try:
                shutil.copy2(path, backup_path)
            except OSError:
                pass
        os.replace(temp_path, path)

    def button(self, text, action, height=48):
        b = Button(
            text=text,
            font_name=FONT_NAME,
            font_size=sp(16),
            size_hint_y=None,
            height=dp(height),
            background_normal="",
            background_color=(0.12, 0.30, 0.48, 1)
        )
        def run_action_and_autosave(*args):
            action(*args)
            try:
                self._write_save()
            except Exception:
                # A failed automatic save should not crash the game.
                pass

        b.bind(on_release=run_action_and_autosave)
        return b

    def refresh(self):
        self.status.text = rtl_text(
            f" پول: {self.money}    جواهر: {self.gems}\n"
            f" ارتش: {self.army}    دفاع: {self.defense}\n"
            f" سلامتی: {self.health}    باتری: {self.battery}%\n"
            f" امتیاز: {self.score}    دشمن: {self.enemy}"
        )

    def clear(self):
        self.area.clear_widgets()

    def message(self, title, text):
        box = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(10)
        )
        label = Label(
            text=text,
            font_name=FONT_NAME,
            font_size=sp(16),
            halign="center",
            valign="middle"
        )
        box.add_widget(label)

        popup = Popup(
            title=rtl_text(title),
            title_font=FONT_NAME,
            content=box,
            size_hint=(0.88, 0.45)
        )
        box.add_widget(
            self.button("باشه", lambda *_: popup.dismiss(), 42)
        )
        popup.open()

    def home(self, *_):
        self.clear()
        self.area.add_widget(
            Label(
                text=" پادشاه امپراتوری یوسکول هستی!\n"
                     "امپراتوری را گسترش بده و دشمن را شکست بده.",
                font_name=FONT_NAME,
                font_size=sp(16),
                halign="center",
                valign="middle"
            )
        )

        options = [
            (" نقشه", self.show_map),
            (" شهرها و ارتقا", self.show_cities),
            (" دریافت درآمد", self.earn),
            (" استخدام سرباز", self.recruit),
            (" فروشگاه سکه", self.shop),
            (" فروشگاه جواهر", self.gem_shop),
            (" جایزهٔ روزانه", self.daily_reward),
            (" دستاوردها و مأموریت‌ها", self.show_achievements),
            (" تصرف شهرهای جدید", self.show_conquest),
            (" نبرد عادی", self.battle),
            (" نبرد نهایی", self.final_battle),
            (" ذخیرهٔ بازی", self.save),
            (" بارگذاری بازی", self.load),
        ]

        scroll = ScrollView()
        grid = GridLayout(
            cols=1,
            spacing=dp(6),
            size_hint_y=None
        )
        grid.bind(minimum_height=grid.setter("height"))

        for text, action in options:
            grid.add_widget(self.button(text, action))

        scroll.add_widget(grid)
        self.area.add_widget(scroll)
        self.refresh()

    def show_map(self, *_):
        self.clear()
        map_text = (
            "[b] نقشهٔ امپراتوری یوسکول[/b]\n\n"
            " کوهستان شارژ\n"
            "        │\n"
            " نوکیاستان\n"
            "        │\n"
            " آنتن‌آباد ─  یوسکول‌شهر ─  Snake City\n"
            "        │\n"
            " باتری‌آباد\n"
            "        │\n"
            " مرز اپل"
        )
        self.area.add_widget(
            Label(
                text=map_text,
                markup=True,
                font_name=FONT_NAME,
                font_size=sp(16),
                halign="center",
                valign="middle"
            )
        )
        self.area.add_widget(self.button("بازگشت", self.home))

    def show_cities(self, *_):
        self.clear()
        scroll = ScrollView()
        grid = GridLayout(
            cols=1,
            spacing=dp(6),
            size_hint_y=None
        )
        grid.bind(minimum_height=grid.setter("height"))

        for city, level in self.cities.items():
            price = level * 150
            grid.add_widget(
                self.button(
                    f"{city} | سطح {level} | هزینه {price}",
                    lambda btn, c=city: self.upgrade(c)
                )
            )

        grid.add_widget(self.button("بازگشت", self.home))
        scroll.add_widget(grid)
        self.area.add_widget(scroll)

    def earn(self, *_):
        income = sum(self.cities.values()) * 20
        self.money += income
        self.refresh()
        self.message("درآمد امپراتوری", f" {income} سکه درآمد کسب کردی!")

    def recruit(self, *_):
        if self.money < 50:
            self.message("خطا", "۵۰ سکه لازم داری.")
            return
        self.money -= 50
        self.army += 10
        self.refresh()
        self.message("ارتش", " ده سرباز جدید استخدام شدند!")

    def upgrade(self, city):
        price = self.cities[city] * 150
        if self.money < price:
            self.message("خطا", "پول کافی نداری.")
            return
        self.money -= price
        self.cities[city] += 1
        self.refresh()
        self.show_cities()

    def shop(self, *_):
        self.clear()
        self.area.add_widget(
            Label(text=" فروشگاه یوسکول", font_name=FONT_NAME, font_size=sp(20))
        )
        self.area.add_widget(
            self.button(" شارژ باتری | ۱۰۰ سکه", lambda *_: self.buy_item("battery"))
        )
        self.area.add_widget(
            self.button(" تعمیر سلامتی | ۱۵۰ سکه", lambda *_: self.buy_item("health"))
        )
        self.area.add_widget(
            self.button(" زره یوسکول | ۲۰۰ سکه", lambda *_: self.buy_item("armor"))
        )
        self.area.add_widget(
            self.button(" سرباز ویژه | ۱۵۰ سکه", lambda *_: self.buy_item("elite"))
        )
        self.area.add_widget(
            self.button(" ارتقای دفاع | ۲۵۰ سکه", lambda *_: self.buy_item("defense"))
        )
        self.area.add_widget(self.button("نیروی سنگین | ۳۰۰ سکه", lambda *_: self.buy_item("heavy")))
        self.area.add_widget(self.button("بازگشت", self.home))

    def buy_item(self, item):
        prices = {
            "battery": 100, "health": 150, "armor": 200,
            "elite": 150, "defense": 250, "heavy": 300
        }
        price = prices[item]
        if self.money < price:
            self.message("فروشگاه", "پول کافی نداری.")
            return
        self.money -= price
        if item == "battery":
            self.battery = 100
            text = "باتری کاملاً شارژ شد."
        elif item == "health":
            self.health = 100
            text = "سلامتی کامل شد."
        elif item == "armor":
            self.health = min(100, self.health + 30)
            text = "زره یوسکول نصب شد و ۳۰ واحد سلامتی بازیابی شد."
        elif item == "elite":
            self.elite_troops += 5
            text = "۵ سرباز ویژه به ارتشت اضافه شدند. آسیب نبرد بیشتر شد."
        elif item == "heavy":
            self.army += 15
            self.defense += 1
            text = "۱۵ سرباز سنگین اضافه شد و دفاع ۱ سطح افزایش یافت."
        else:
            self.defense += 1
            text = f"دفاع امپراتوری به سطح {self.defense} رسید."
        self.refresh()
        self.message("فروشگاه", text)
        self.check_achievements()

    def gem_shop(self, *_):
        self.clear()
        self.area.add_widget(
            Label(
                text=f" فروشگاه جواهر | موجودی: {self.gems}",
                font_name=FONT_NAME, font_size=sp(18)
            )
        )
        self.area.add_widget(self.button(
            " ۱۰ سرباز عادی | ۵ جواهر",
            lambda *_: self.buy_gem_item("army")
        ))
        self.area.add_widget(self.button(
            " ۵۰۰ سکه | ۳ جواهر",
            lambda *_: self.buy_gem_item("money")
        ))
        self.area.add_widget(self.button(
            " بازیابی ۳۰ سلامتی | ۴ جواهر",
            lambda *_: self.buy_gem_item("health")
        ))
        self.area.add_widget(self.button("بازگشت", self.home))

    def buy_gem_item(self, item):
        costs = {"army": 5, "money": 3, "health": 4}
        cost = costs[item]
        if self.gems < cost:
            self.message("جواهر کافی نیست", "برای این خرید جواهر بیشتری لازم داری.")
            return
        self.gems -= cost
        if item == "army":
            self.army += 10
            text = "۱۰ سرباز به ارتشت اضافه شد."
        elif item == "money":
            self.money += 500
            text = "۵۰۰ سکه دریافت کردی."
        else:
            self.health = min(100, self.health + 30)
            text = "۳۰ واحد سلامتی بازیابی شد."
        self.refresh()
        self.message("خرید موفق", text)
        self.gem_shop()

    def daily_reward(self, *_):
        today = time.strftime("%Y-%m-%d")
        if self.last_daily_reward == today:
            self.message("جایزهٔ روزانه", "جایزهٔ امروز را قبلاً گرفته‌ای. فردا دوباره بیا!")
            return
        self.last_daily_reward = today
        self.money += 300
        self.gems += 5
        self.refresh()
        self.message("جایزهٔ روزانه", " ۳۰۰ سکه و ۵ جواهر گرفتی!")
        self.check_achievements()

    def show_conquest(self, *_):
        self.clear()
        self.area.add_widget(Label(
            text=" شهرهای آزاد را تصرف کن؛ پیروزی به ارتش تو بستگی دارد.",
            font_name=FONT_NAME, font_size=sp(16),
            halign="center", valign="middle"
        ))
        if not self.frontier:
            self.area.add_widget(Label(
                text="همهٔ شهرهای جدید را تصرف کرده‌ای!",
                font_name=FONT_NAME, font_size=sp(16)
            ))
        else:
            for city, power in list(self.frontier.items()):
                self.area.add_widget(self.button(
                    f" {city} | قدرت دشمن: {power}",
                    lambda *_args, c=city: self.conquer_city(c)
                ))
        self.area.add_widget(self.button("بازگشت", self.home))

    def conquer_city(self, city):
        if city not in self.frontier:
            return
        enemy_power = self.frontier[city]
        if self.army < enemy_power:
            self.message(
                "ارتش کافی نیست",
                f"برای حمله به {city} دست‌کم {enemy_power} سرباز لازم داری."
            )
            return
        losses = random.randint(max(1, enemy_power // 8), max(2, enemy_power // 4))
        losses = max(1, losses - self.defense // 2)
        self.army = max(0, self.army - losses)
        self.cities[city] = 1
        del self.frontier[city]
        reward = enemy_power * 8
        self.money += reward
        self.score += 150
        self.gems += 2
        self.refresh()
        self.check_achievements()
        self.message(
            "شهر تصرف شد!",
            f" {city} به امپراتوری پیوست.\n"
            f"سرباز ازدست‌رفته: {losses}\n"
            f"پاداش: {reward} سکه و ۲ جواهر"
        )
        self.show_conquest()

    def show_achievements(self, *_):
        self.clear()
        self.area.add_widget(Label(
            text=f"دستاوردها و مأموریت‌ها\\nجواهر: {self.gems}",
            font_name=FONT_NAME, font_size=sp(19),
            halign="center", valign="middle",
            size_hint_y=None, height=dp(58)
        ))

        missions = [
            ("army100", "ارتش صدنفره", self.army >= 100, 5,
             "ارتش را به ۱۰۰ سرباز برسان."),
            ("score1000", "قهرمان امپراتوری", self.score >= 1000, 10,
             "۱۰۰۰ امتیاز کسب کن."),
            ("conquer1", "فاتح شهر", len(self.cities) > len(CITIES), 5,
             "حداقل یک شهر جدید تصرف کن."),
            ("rich2000", "ثروتمند", self.money >= 2000, 5,
             "موجودی پولت را به ۲۰۰۰ سکه برسان."),
            ("elite10", "نیروی ویژه", self.elite_troops >= 10, 4,
             "۱۰ سرباز ویژه استخدام کن."),
            ("defense3", "دژ مستحکم", self.defense >= 3, 4,
             "دفاع امپراتوری را به سطح ۳ برسان."),
        ]

        scroll = ScrollView()
        grid = GridLayout(cols=1, spacing=dp(7), padding=dp(4),
                          size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        for key, title, completed, reward, description in missions:
            if key in self.claimed_missions:
                label = f"✓ {title} | جایزه دریافت شده"
                action = lambda *_: self.message("مأموریت", "جایزهٔ این مأموریت قبلاً دریافت شده است.")
            elif completed:
                label = f"🎁 دریافت {reward} جواهر | {title}"
                action = lambda *_args, k=key, r=reward: self.claim_mission(k, r)
            else:
                label = f"🔒 {title} | جایزه: {reward} جواهر"
                action = lambda *_: self.message("مأموریت", "هنوز شرایط این مأموریت کامل نشده است.")

            grid.add_widget(self.button(label, action, height=58))
            grid.add_widget(Label(
                text=description, font_name=FONT_NAME, font_size=sp(13),
                size_hint_y=None, height=dp(26),
                halign="center", valign="middle"
            ))

        grid.add_widget(self.button("بازگشت", self.home))
        scroll.add_widget(grid)
        self.area.add_widget(scroll)

    def claim_mission(self, key, reward):
        if key in self.claimed_missions:
            self.message("مأموریت", "این جایزه را قبلاً گرفته‌ای.")
            return

        checks = {
            "army100": self.army >= 100,
            "score1000": self.score >= 1000,
            "conquer1": len(self.cities) > len(CITIES),
            "rich2000": self.money >= 2000,
            "elite10": self.elite_troops >= 10,
            "defense3": self.defense >= 3,
        }
        if not checks.get(key, False):
            self.message("مأموریت", "شرایط این مأموریت دیگر برقرار نیست.")
            return

        self.claimed_missions.append(key)
        self.gems += reward
        self.refresh()
        try:
            self._write_save()
        except Exception:
            pass
        self.message("جایزه دریافت شد", f"{reward} جواهر به دست آوردی!")
        self.show_achievements()

    def check_achievements(self):
        goals = [
            ("اولین امتیاز", self.score >= 100, 3),
            ("ارتش صدنفره", self.army >= 100, 5),
            ("ثروتمند", self.money >= 2000, 5),
            ("فاتح شهر", len(self.cities) > len(CITIES), 5),
            ("قهرمان امپراتوری", self.score >= 1000, 10),
        ]
        unlocked = []
        for name, condition, reward in goals:
            if condition and name not in self.achievements:
                self.achievements.append(name)
                self.gems += reward
                unlocked.append(f"{name}: {reward} جواهر")
        if unlocked:
            self.refresh()
            self.message("دستاورد جدید!", "\n".join(unlocked))

    def battle(self, *_):
        if self.health <= 0:
            self.message("پایان بازی", "امپراتوری شکست خورده است.")
            return
        if self.battery < 5:
            self.message("باتری", "ابتدا باتری را شارژ کن.")
            return
        if self.enemy <= 0:
            self.enemy = 80

        damage = random.randint(5, 15) + self.elite_troops * 2
        retaliation = max(1, random.randint(3, 12) - self.defense)
        self.enemy -= damage
        self.army = max(0, self.army - retaliation)
        self.battery -= 5

        result = (
            f" آسیب واردشده: {damage}\n"
            f" سرباز ازدست‌رفته: {retaliation}"
        )
        if self.enemy <= 0:
            reward = random.randint(200, 500)
            self.money += reward
            self.score += 100
            self.enemy = min(180, 80 + self.score // 20)
            result += (
                f"\n\n پیروزی!\n"
                f" پاداش: {reward} سکه\n"
                f" ۱۰۰ امتیاز کسب کردی."
            )

        if self.army == 0:
            self.health = max(0, self.health - 30)
            result += "\nارتشت شکست خورد!"

        self.refresh()
        self.check_achievements()
        self.message("گزارش نبرد", result)

    def final_battle(self, *_):
        if self.army < 50 or self.score < 200:
            self.message(
                "هنوز آماده نیستی",
                "حداقل ۵۰ سرباز و ۲۰۰ امتیاز لازم داری."
            )
            return
        if self.health <= 0:
            self.message("خطا", "ابتدا سلامتی را بازیابی کن.")
            return
        self.boss_health = 250
        self.boss_screen()

    def boss_screen(self):
        self.clear()
        self.area.add_widget(
            Label(
                text=f" آیفون ۱۸ پرو\nسلامتی دشمن: {self.boss_health}",
                font_name=FONT_NAME,
                font_size=sp(20),
                halign="center",
                valign="middle"
            )
        )
        bar = ProgressBar(
            max=250,
            value=max(0, self.boss_health),
            size_hint_y=None,
            height=dp(25)
        )
        self.area.add_widget(bar)
        self.area.add_widget(
            self.button(" حمله", lambda *_: self.boss_turn("attack"))
        )
        self.area.add_widget(
            self.button(" حملهٔ ویژهٔ Snake", lambda *_: self.boss_turn("snake"))
        )
        self.area.add_widget(
            self.button(" شارژ باتری", lambda *_: self.boss_turn("charge"))
        )
        self.area.add_widget(self.button("عقب‌نشینی", self.home))

    def boss_turn(self, action):
        if action == "attack":
            damage = random.randint(15, 30) + self.elite_troops
            self.boss_health -= damage
        elif action == "snake":
            if self.battery < 20:
                self.message("باتری", "حداقل ۲۰٪ باتری لازم داری.")
                return
            damage = random.randint(30, 60) + self.elite_troops * 2
            self.boss_health -= damage
            self.battery -= 20
        else:
            self.battery = min(100, self.battery + 30)
            damage = 0

        result = f"آسیب واردشده: {damage}"
        if self.boss_health > 0:
            enemy_damage = max(2, random.randint(10, 25) - self.defense)
            self.health = max(0, self.health - enemy_damage)
            result += f"\nآسیب آیفون: {enemy_damage}"

        if self.boss_health <= 0:
            self.score += 1000
            self.money += 2000
            self.refresh()
            self.check_achievements()
            self.home()
            self.message(
                " پیروزی بزرگ!",
                "امپراتوری یوسکول برنده شد!\n\n"
                "«دوربین خوبه، ولی آنتن مهم‌تره!»\n\n"
                f"امتیاز نهایی: {self.score}\n"
                f"ثروت نهایی: {self.money}"
            )
            return

        if self.health <= 0:
            self.refresh()
            self.home()
            self.message(" شکست", "امپراتوری یوسکول سقوط کرد.")
            return

        self.refresh()
        self.message("نبرد نهایی", result)
        self.boss_screen()

    def save(self, *_):
        try:
            self._write_save()
            self.message("ذخیره", "بازی ذخیره شد و نسخهٔ پشتیبان هم نگه‌داری شد.")
        except Exception as exc:
            self.message("خطای ذخیره", f"ذخیره انجام نشد: {exc}")

    def load(self, *_):
        path = os.path.join(self.user_data_dir, "yuskol_save.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.money = data["money"]
            self.army = data["army"]
            self.health = data["health"]
            self.battery = data["battery"]
            self.score = data["score"]
            self.enemy = data.get("enemy", 80)
            self.boss_health = data.get("boss_health", 250)
            self.cities = data.get("cities", {city: 1 for city in CITIES})
            self.gems = data.get("gems", 0)
            self.last_daily_reward = data.get("last_daily_reward", "")
            self.achievements = data.get("achievements", [])
            self.defense = data.get("defense", 0)
            self.elite_troops = data.get("elite_troops", 0)
            self.frontier = data.get("frontier", dict(FRONTIER_CITIES))
            self.claimed_missions = data.get("claimed_missions", [])
            self.refresh()
            self.message("بارگذاری", "بازی قبلی بازیابی شد.")
        except FileNotFoundError:
            self.message("ذخیره‌ای نیست", "هنوز بازی ذخیره نشده است.")


if __name__ == "__main__":
    YuskolGame().run()
