#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
METAR / SPECI / TAF Decoder (RU)
Полное покрытие кодов и грамматическая обработка для естественных фраз.
"""

import re

# ==============================
# СЛОВАРИ: грамматика и явления
# ==============================
# WEATHER_GRAMMAR: (род, число) — для выбора формы при согласовании
WEATHER_GRAMMAR = {
    'морось': ('ж', 'ед'),
    'дождь': ('м', 'ед'),
    'снег': ('м', 'ед'),
    'снежные зерна': ('мн', 'мн'),
    'ледяные иглы': ('мн', 'мн'),
    'ледяные шарики': ('мн', 'мн'),
    'град': ('м', 'ед'),
    'мелкий град/снежная крупа': ('м', 'ед'),
    'неопределенные осадки': ('мн', 'мн'),
    'дымка': ('ж', 'ед'),
    'туман': ('м', 'ед'),
    'дым': ('м', 'ед'),
    'вулканический пепел': ('м', 'ед'),
    'пыль': ('ж', 'ед'),
    'песок': ('м', 'ед'),
    'мгла': ('ж', 'ед'),
    'водяная пыль': ('ж', 'ед'),
    'пыльные/песчаные вихри': ('мн', 'мн'),
    'шквал': ('м', 'ед'),
    'пыльная буря': ('ж', 'ед'),
    'песчаная буря': ('ж', 'ед'),
    'гроза': ('ж', 'ед'),
}

# INTENSITY_FORMS: формы для интенсивности (по роду/числу)
INTENSITY_FORMS = {
    '+': {'м':'сильный','ж':'сильная','ср':'сильное','мн':'сильные'},
    '-': {'м':'слабый','ж':'слабая','ср':'слабое','мн':'слабые'},
    '':  {'м':'умеренный','ж':'умеренная','ср':'умеренное','мн':'умеренные'},
}

# DESCRIPTORS (основная форма) -> согласованные формы в DESCR_FORMS ниже
DESCRIPTORS = {
    'MI': 'тонкий', 'BC': 'клочья', 'PR': 'частичный', 'DR': 'поземок',
    'BL': 'низовая метель', 'SH': 'ливневой', 'TS': 'гроза', 'FZ': 'переохлажденный',
    'VC': 'вблизи', 'RE': 'недавний'
}

DESCR_FORMS = {
    'тонкий':      {'м':'тонкий','ж':'тонкая','ср':'тонкое','мн':'тонкие'},
    'клочья':      {'м':'клочковый','ж':'клочковая','ср':'клочковое','мн':'клочковые'},
    'частичный':   {'м':'частичный','ж':'частичная','ср':'частичное','мн':'частичные'},
    'поземок':     {'м':'поземный','ж':'поземная','ср':'поземное','мн':'поземные'},
    'низовая метель': {'м':'низовой','ж':'низовая','ср':'низовое','мн':'низовые'},
    'ливневой':    {'м':'ливневый','ж':'ливневая','ср':'ливневое','мн':'ливневые'},
    'переохлажденный': {'м':'переохлажденный','ж':'переохлажденная','ср':'переохлажденное','мн':'переохлажденные'},
    'недавний':    {'м':'недавний','ж':'недавняя','ср':'недавнее','мн':'недавние'},
    'вблизи':      {'м':'вблизи','ж':'вблизи','ср':'вблизи','мн':'вблизи'},
}

# WEATHER код -> текст
WEATHER = {
    'DZ': 'морось','RA': 'дождь','SN': 'снег','SG': 'снежные зерна','IC': 'ледяные иглы',
    'PL': 'ледяные шарики','GR': 'град','GS': 'мелкий град/снежная крупа','UP': 'неопределенные осадки',
    'BR': 'дымка','FG': 'туман','FU': 'дым','VA': 'вулканический пепел','DU': 'пыль','SA': 'песок',
    'HZ': 'мгла','PY': 'водяная пыль','PO': 'пыльные/песчаные вихри','SQ': 'шквал','DS': 'пыльная буря','SS': 'песчаная буря'
}

# инструментальные формы (для "X со Y" — второе явление в творительном падеже)
WEATHER_INSTR = {
    'дождь': 'дождём','снег': 'снегом','морось': 'моросью',
    'снежные зерна': 'снежными зёрнами','ледяные иглы': 'ледяными иглами','ледяные шарики': 'ледяными шариками',
    'град': 'градом','мелкий град/снежная крупа': 'мелким градом/снежной крупой',
    'неопределенные осадки': 'неопределёнными осадками','дымка': 'дымкой','туман': 'туманом','дым': 'дымом',
    'вулканический пепел': 'вулканическим пеплом','пыль': 'пылью','песок': 'песком','мгла': 'мглой',
    'водяная пыль': 'водяной пылью','пыльные/песчаные вихри': 'пыльными/песчаными вихрями',
    'шквал': 'шквалом','пыльная буря': 'пыльной бурей','песчаная буря': 'песчаной бурей'
}

# облачные слова
CLOUDS = {
    'FEW': 'мало (1–2/8)','SCT': 'рассеянные (3–4/8)','BKN': 'значительная (5–7/8)','OVC': 'сплошная (8/8)',
    'NSC': 'нет значимых облаков','SKC': 'ясно (sky clear)','CLR': 'ясно (clear)',
    'CAVOK': 'CAVOK (видимость ≥10 км, без облаков и явлений)'
}

CLOUD_TYPES = {
    'CB': 'кучево-дождевые (CB)',
    'TCU': 'мощные кучевые (TCU)'
}

# Вспомогательный набор явлений, которые считаем "осадками" (для выражений типа "гроза с дождём")
PRECIPITATION_LIKE = {
    'дождь','морось','снег','град','снежные зерна','ледяные иглы','ледяные шарики','мелкий град/снежная крупа',
    'неопределенные осадки'
}

# покрытие ВПП
RUNWAY_TYPE = {
    '0': 'сухо','1': 'влажно','2': 'мокро/лужи','3': 'иней/изморозь','4': 'сухой снег',
    '5': 'мокрый снег','6': 'слякоть','7': 'лед','8': 'укатанный снег','9': 'замерзшая/неровная поверхность','/': 'нет данных'
}
RUNWAY_COVER = {'1': '<10%','2': '11–25%','5': '26–50%','9': '51–100%','/': 'нет данных'}
BRAKING = {
    '95': 'хорошая (≥0.40)','94': 'средне-хорошая (0.36–0.39)','93': 'средняя (0.30–0.35)',
    '92': 'плохо-средняя (0.26–0.29)','91': 'плохая (≤0.25)','99': 'ненадежно','//': 'нет данных'
}

# ==============================
# REGEX
# ==============================
RE_STATION = re.compile(r'^[A-Z]{4}$')
RE_TIME = re.compile(r'^\d{6}Z$')
RE_WIND = re.compile(r'^(?P<dir>\d{3}|VRB|000)(?P<spd>\d{2,3})(G(?P<gust>\d{2,3}))?(?P<unit>KT|MPS|KMH)?$')
RE_VARWIND = re.compile(r'^(?P<from>\d{3})V(?P<to>\d{3})$')
RE_VIS = re.compile(r'^(?P<vis>\d{4})(?P<dir>[NSEW]{1,2})?$')
RE_RVR = re.compile(r'^R(?P<rwy>\d{2}[LRC]?)/(?P<val>[PM]?\d{4})(V(?P<max>\d{4}))?(?P<trend>[UDN])?$')
# CLOUD: allow digits or /// for unknown base
RE_CLOUD = re.compile(r'^(FEW|SCT|BKN|OVC|NSC|SKC|CLR|CAVOK)(\d{3}|///)?(CB|TCU)?$')
RE_VV = re.compile(r'^VV(\d{3}|///)$')
RE_TEMP = re.compile(r'^(M?\d{2}|//)/(M?\d{2}|//)$')
RE_Q = re.compile(r'^Q(\d{4})$')
RE_A = re.compile(r'^A(\d{4})$')
RE_TREND = re.compile(r'^(BECMG|TEMPO|NOSIG|FM\d*|TL\d*|AT\d*)$')
RE_RUNWAY6 = re.compile(r'^R(?P<rwy>\d{2}|88|99)/(?P<digits>\d{6})$')
RE_RUNWAY_VAR = re.compile(r'^R(?P<rwy>\d{2}[LRC]?|88|99)/(?P<body>[0-9/]{4,6})$')

# погодные явления (интенсивность + дескрипторы + >=1 явление (возможны несколько))
RE_WEATHER = re.compile(
    r'^(?:\+|-|VC)?'
    r'(?:MI|BC|PR|DR|BL|SH|TS|FZ|RE){0,3}'
    r'(?:DZ|RA|SN|SG|IC|PL|GR|GS|UP|'
    r'BR|FG|FU|VA|DU|SA|HZ|PY|PO|SQ|DS|SS)+$'
)

# ==============================
# ФУНКЦИИ-помощники для грамматики
# ==============================
def grammatical_gender_number(word):
    """Возвращает (род, число) для заданного погодного слова, если известно."""
    return WEATHER_GRAMMAR.get(word, ('м','ед'))  # default masculine singular

def intensity_word_for(sign, gender='м', number='ед'):
    """Возвращает слово интенсивности по sign ('+','-','') и грамм.форме."""
    forms = INTENSITY_FORMS.get(sign, INTENSITY_FORMS[''])
    # если множественное — используем ключ 'мн'
    key = number if number in ('мн',) else gender
    return forms.get(key, forms.get('м'))

def descr_form(descr_text, gender='м', number='ед'):
    """Возвращает согласованную форму дескриптора (например 'ливневой'/'ливневая')."""
    forms = DESCR_FORMS.get(descr_text)
    if not forms:
        return descr_text
    key = number if number in ('мн',) else gender
    return forms.get(key, forms.get('м'))

# ==============================
# Склейка и генерация естественных фраз для погодных явлений
# ==============================
def join_weather_events(events, descriptors, sign):
    """
    events: список (строк) основных явлений в нормальной форме, напр. ['дождь', 'снег']
    descriptors: список дескрипторов (в нормальной форме), напр. ['ливневой', 'недавний']
    sign: '+', '-' или '' (интенсивность)
    Возвращает естественную русскую фразу, грамматически согласованную.
    """

    if not events and not descriptors:
        return ""

    # Если есть дескриптор 'гроза' (TS) — особая логика: предпочитаем "гроза" и затем "с ...".
    # Но если в дескрипторах есть слова, которые не являются погодой (например 'низовая метель'),
    # мы выводим их как отдельную фразу перед основными явлениями (чтобы не получилось "низовая метель снегом").
    # Поэтому разделим descriptors на "атрибутные" (описательные, не превращаемые в 'с X') и 'TS' обработку.
    # Для упрощения: если дескриптор равен 'гроза' — помечаем.
    has_ts = any(d == 'гроза' for d in descriptors)

    # Первично — возьмём основные события (events). Для грамматики определим род/число по первому событию.
    # Если нет основных событий, но есть дескрипторы (напр. 'низовая метель' без явлений) — просто выведем дескрипторы.
    if events:
        # основной элемент для согласования:
        main = events[0]
        gender, number = grammatical_gender_number(main)
    else:
        # согласование по первому дескриптору
        d0 = descriptors[0] if descriptors else ''
        gender, number = grammatical_gender_number(d0)

    # Формируем словосочетание дескрипторов (кроме 'гроза' — её обрабатываем отдельно):
    descr_out = []
    for d in descriptors:
        if d == 'гроза':
            continue
        # если descriptor — «вблизи», просто используем слово
        if d == 'вблизи':
            descr_out.append('вблизи')
            continue
        # согласуем по грамматической форме
        descr_out.append(descr_form(d, gender, number))

    # Формируем интенсивность слово, согласованное по роду/числу (для тех слов, где это имеет смысл)
    intensity = intensity_word_for(sign, gender, number)

    # Специальная логика для грозы:
    if has_ts:
        # если есть гроза и одновременно есть осадки — формируем "гроза с дождём" или "сильная гроза с дождём"
        prec = [e for e in events if e in PRECIPITATION_LIKE]
        if prec:
            base = 'гроза'
            # если есть интенсивность — ставим перед 'гроза' слово интенсивности (в женском роде)
            # intensity_word_for уже учитывает род/число
            if sign:
                # интенсивность для 'гроза' (женский)
                int_for_ts = intensity_word_for(sign, 'ж', 'ед')
                base = f"{int_for_ts} гроза"
            # второе явление — инструментальная форма
            ev = prec[0]
            ev_instr = WEATHER_INSTR.get(ev, ev)
            return " ".join(filter(None, descr_out + [base + " с " + ev_instr]))
        else:
            # просто "гроза" (с интенсивностью, если есть)
            base = 'гроза'
            if sign:
                base = f"{intensity_word_for(sign, 'ж', 'ед')} {base}"
            return " ".join(filter(None, descr_out + [base]))

    # Если нет TS — стандартное склеивание для событий + дескрипторов.
    # Сначала событие(я)
    if events:
        if len(events) == 1:
            ev_phrase = events[0]
        elif len(events) == 2:
            # второе — в инструментале, если возможно
            first, second = events
            second_instr = WEATHER_INSTR.get(second, second)
            # выбирать 'с' или 'со' по начальной букве инструментальной формы
            prep = 'со' if second_instr and second_instr[0] in 'сш' else 'с'
            ev_phrase = f"{first} {prep} {second_instr}"
        else:
            ev_phrase = ", ".join(events[:-1]) + " и " + events[-1]
    else:
        ev_phrase = ""

    # Если есть дескрипторы-описания (например 'ливневой') — ставим их перед событием
    # Но если descriptor — 'вблизи', уже включили его в descr_out
    if descr_out:
        # соединяем дескр. словами через пробел
        descr_part = " ".join(descr_out)
        # если есть и событие — "ливневой дождь" (т.е. descr + ev)
        if ev_phrase:
            # иногда descr_out может содержать несколько слов — просто ставим перед
            phrase = f"{descr_part} {ev_phrase}"
        else:
            phrase = descr_part
    else:
        phrase = ev_phrase

    # прикрепим интенсивность (для не-TS случаев): "сильный ливневой дождь" или "сильный дождь с ...", если intensity задан
    if sign and phrase:
        # если первым словом уже стоит 'вблизи' — не вставляем интенсивность перед 'вблизи'
        if phrase.startswith('вблизи '):
            return phrase
        # вставляем интенсивность перед фразой
        phrase = f"{intensity} {phrase}"

    return phrase.strip()

# ==============================
# Регулярные помощники и декодеры (облака, ВПП и пр.)
# ==============================
def decode_cloud(tok: str) -> str:
    """Обработка облачности, поддержка FEW/// (нет данных основания)."""
    m = RE_CLOUD.match(tok)
    if not m:
        return tok
    grp, hhh, extra = m.groups()
    desc = CLOUDS.get(grp, grp)
    if grp == 'CAVOK':
        return desc
    # базовое основание: если hhh == '///' или содержит '/', то показываем «основание: нет данных»
    if hhh:
        if '/' in hhh:
            base = " основание: нет данных"
        else:
            try:
                base = f" основание ~{int(hhh)*30} м ({int(hhh)*100} ft)"
            except:
                base = " основание: нет данных"
    else:
        base = ""
    cloud_type = f" {CLOUD_TYPES.get(extra, extra)}" if extra else ""
    return f"{desc}{base}{cloud_type}"

def decode_braking(brake):
    if brake in BRAKING:
        return f"  Сцепление: {BRAKING[brake]}"
    try:
        val = int(brake) / 100.0
        return f"  Сцепление: коэффициент ≈ {val:.2f}"
    except:
        return f"  Сцепление: код {brake}"

def runway_header(rwy: str) -> str:
    if rwy == "88":
        return "Состояние всех ВПП:"
    elif rwy == "99":
        return "Состояние ВПП: повтор из предыдущего сообщения"
    else:
        return f"Состояние ВПП {rwy}:"

def decode_runway_digits(rwy, d):
    Er, Cr, thick, brake = d[0], d[1], d[2:4], d[4:6]
    res = [runway_header(rwy)]
    res.append(f"  Тип покрытия: {RUNWAY_TYPE.get(Er, Er)}")
    res.append(f"  Степень покрытия: {RUNWAY_COVER.get(Cr, Cr)}")
    if thick == '//':
        res.append("  Толщина: нет данных")
    else:
        try:
            iv = int(thick)
            if iv == 0:
                res.append("  Толщина: <1 мм")
            elif 1 <= iv <= 90:
                res.append(f"  Толщина: {iv} мм")
            elif iv == 92:
                res.append("  Толщина: 10 см")
            elif iv == 93:
                res.append("  Толщина: 15 см")
            elif iv == 94:
                res.append("  Толщина: 20 см")
            elif iv == 98:
                res.append("  Толщина: 40 см")
            elif iv == 99:
                res.append("  Толщина: ВПП не работает")
            else:
                res.append(f"  Толщина: код {thick}")
        except:
            res.append("  Толщина: нет данных")
    res.append(decode_braking(brake))
    return "\n".join(res)

def decode_runway_body(rwy, body):
    res = [runway_header(rwy)]
    if len(body) >= 4:
        brake = body[-2:]; core = body[:-2]
        if core and core[0].isdigit():
            res.append(f"  Тип покрытия: {RUNWAY_TYPE.get(core[0], core[0])}")
        if len(core) > 1 and core[1].isdigit():
            res.append(f"  Степень покрытия: {RUNWAY_COVER.get(core[1], core[1])}")
        if "//" in core:
            res.append("  Толщина: нет данных")
        elif len(core) >= 3 and core[2:].isdigit():
            res.append(f"  Толщина: {int(core[2:])} мм")
        res.append(decode_braking(brake))
    else:
        res.append(f"  Код состояния: {body}")
    return "\n".join(res)

def decode_runway(tok: str):
    if tok.startswith("R") and "CLRD" in tok:
        return f"Состояние ВПП {tok[1:3]}: очищена"
    if tok.startswith("R") and "CLSD" in tok:
        return f"Состояние ВПП {tok[1:3]}: закрыта"
    if "SNOCLO" in tok:
        return "Аэродром закрыт снегом"
    if "RRRR" in tok and "99" in tok:
        return "ВПП закрыта на чистку"
    m = RE_RUNWAY6.match(tok)
    if m:
        return decode_runway_digits(m.group('rwy'), m.group('digits'))
    m = RE_RUNWAY_VAR.match(tok)
    if m:
        return decode_runway_body(m.group('rwy'), m.group('body'))
    return None

# ==============================
# Основной декодер METAR
# ==============================
def decode_weather_token(tok: str) -> str:
    """
    Парсит токен погоды (например '-SHRASN' или '+TSRA') и возвращает человекопонятную фразу (без 'Явления:')
    """
    if not tok:
        return ''
    sign = ''
    if tok[0] in ('+', '-'):
        sign = tok[0]
        tok = tok[1:]
    # поддерживаем маркер 'VC' как дескриптор «вблизи»
    descriptors = []
    events = []
    # проход по токену по 2 буквы
    i = 0
    while i < len(tok):
        code = tok[i:i+2]
        if code == 'VC':
            descriptors.append('вблизи')
            i += 2
            continue
        if code in DESCRIPTORS:
            descriptors.append(DESCRIPTORS[code])
            i += 2
            continue
        if code in WEATHER:
            events.append(WEATHER[code])
            i += 2
            continue
        # неожиданный символ — сдвигаем на 1
        i += 1

    # Теперь формируем фразу, используя join_weather_events
    phrase = join_weather_events(events, descriptors, sign)
    return phrase

def decode_metar(metar: str) -> str:
    tokens = metar.replace("=", "").split()
    out = []
    i = 0
    while i < len(tokens):
        t = tokens[i]

        # Станция
        if RE_STATION.match(t) and (i == 1 or (i > 0 and tokens[i-1] in ["METAR", "SPECI"])):
            out.append(f"Аэродром: {t}")

        # Время
        elif RE_TIME.match(t):
            out.append(f"Время наблюдения: {t} UTC")

        # Ветер
        elif RE_WIND.match(t):
            m = RE_WIND.match(t)
            d = m.group('dir'); s = int(m.group('spd')); g = m.group('gust'); u = (m.group('unit') or 'KT').upper()
            unit_ru = 'м/с' if u == 'MPS' else 'км/ч' if u == 'KMH' else 'уз.'
            if d == '000':
                wind = f"Штиль, {s} {unit_ru}"
            elif d == 'VRB':
                wind = f"Ветер переменный {s} {unit_ru}"
            else:
                wind = f"Ветер {int(d)}° {s} {unit_ru}"
            if g:
                wind += f", порывы {int(g)} {unit_ru}"
            out.append(wind)

        # Вариабельность ветра
        elif RE_VARWIND.match(t):
            m = RE_VARWIND.match(t)
            out.append(f"Вариабельность ветра: {m.group('from')}°–{m.group('to')}°")

        # Видимость
        elif RE_VIS.match(t):
            m = RE_VIS.match(t); vis = int(m.group('vis')); dir_ = m.group('dir') or ''
            if vis == 9999:
                out.append("Видимость ≥10 км")
            else:
                if out and out[-1].startswith("Видимость"):
                    # если уже есть видимость — корректируем/дополняем
                    if dir_:
                        out[-1] += f", в направлении {dir_} — {vis} м"
                    else:
                        out[-1] = f"Видимость минимальная {vis} м"
                else:
                    if dir_:
                        out.append(f"Видимость {vis} м {dir_}")
                    else:
                        out.append(f"Видимость минимальная {vis} м")

        # RVR
        elif RE_RVR.match(t):
            m = RE_RVR.match(t)
            val = m.group('val')
            if val.startswith('P'):
                val_txt = f">{val[1:]} м"
            elif val.startswith('M'):
                val_txt = f"<{val[1:]} м"
            else:
                val_txt = f"{int(val)} м"
            trend_map = {'U':'улучшалась','D':'ухудшалась','N':'без изменений'}
            trend = trend_map.get(m.group('trend'),'')
            out.append(f"RVR ВПП {m.group('rwy')}: {val_txt} {trend}".strip())

        # Облачность
        elif RE_CLOUD.match(t):
            out.append("Облачность: " + decode_cloud(t))

        # Вертикальная видимость
        elif RE_VV.match(t):
            vv = RE_VV.match(t).group(1)
            out.append("Вертикальная видимость: нет данных" if vv == "///" else f"Вертикальная видимость {int(vv)*30} м")

        # Температура и точка росы
        elif RE_TEMP.match(t):
            m = RE_TEMP.match(t)
            T, Td = m.group(1), m.group(2)
            T_val = "нет данных" if T == "//" else f"{T.replace('M','-')}°C"
            Td_val = "нет данных" if Td == "//" else f"{Td.replace('M','-')}°C"
            out.append(f"Температура {T_val}, точка росы {Td_val}")

        # Давление QNH
        elif RE_Q.match(t):
            out.append(f"Давление QNH {int(RE_Q.match(t).group(1))} гПа")

        # Давление inHg A
        elif RE_A.match(t):
            val = int(RE_A.match(t).group(1)) / 100.0
            out.append(f"Давление {val:.2f} inHg")

        # Тренд
        elif RE_TREND.match(t):
            out.append(f"Тренд {t}")

        # Состояние ВПП (R..., CLRD/CLSD/SNOCLO/RRRR)
        elif t.startswith("R") and (RE_RUNWAY6.match(t) or RE_RUNWAY_VAR.match(t) or any(x in t for x in ["CLRD","CLSD","SNOCLO","RRRR"])):
            r = decode_runway(t)
            if r:
                out.append(r)
            else:
                out.append(f"(неизвестно) {t}")

        # Погодные явления
        elif RE_WEATHER.match(t):
            phrase = decode_weather_token(t)
            if phrase:
                out.append("Явления: " + phrase)

        # NSW — no significant weather (в прогнозе или в наблюдении)
        elif t == "NSW":
            if out and out[-1].startswith("Тренд"):
                out.append("В прогнозе: без значимых явлений")
            else:
                out.append("Явления: без значимых явлений")

        # WS — windshear
        elif t == "WS":
            if i+2 < len(tokens) and tokens[i+1] == "ALL" and tokens[i+2] == "RWY":
                out.append("Сдвиг ветра: на всех ВПП"); i += 2
            elif i+1 < len(tokens) and tokens[i+1].startswith("RWY"):
                out.append(f"Сдвиг ветра: на {tokens[i+1]}"); i += 1
            else:
                out.append("Сдвиг ветра (WS)")

        # RMK — ремарки: обрабатываем все, поддерживая QFE/ QBB / OBST / MT / OBSC / ICE / TURB
        elif t == 'RMK':
            remark_tokens = tokens[i+1:]
            for rt in remark_tokens:
                if rt.startswith("QFE"):
                    val = rt[3:]
                    if "/" in val:
                        a, b = val.split("/", 1)
                        out.append(f"Ремарка: Давление QFE {a} мм рт.ст. (доп. {b})")
                    else:
                        out.append(f"Ремарка: Давление QFE {val} мм рт.ст.")
                elif rt.startswith("QBB"):
                    out.append(f"Ремарка: Нижняя граница облаков {rt[3:]} м")
                elif rt == "OBST" and "OBSC" in remark_tokens:
                    out.append("Ремарка: Препятствия закрыты облаками")
                elif rt == "MT" and "OBSC" in remark_tokens:
                    out.append("Ремарка: Горы закрыты облаками")
                elif rt == "OBSC":
                    continue
                elif rt.startswith("ICE"):
                    out.append("Ремарка: Обледенение")
                elif rt.startswith("TURB"):
                    out.append("Ремарка: Турбулентность")
                else:
                    out.append("Ремарка: " + rt)
            break

        # иначе — неизвестный токен
        else:
            out.append(f"(неизвестно) {t}")

        i += 1

    return "\n".join(out)


# ==============================
# Простой демонстрационный блок (можно расширять/менять примеры)
# ==============================
if __name__ == "__main__":
    samples = [
        "METAR ULMM 261330Z 22005G12MPS 180V250 9999 -SHRASN BKN028CB 03/M02 Q1000 R13/290051 NOSIG RMK QFE744=",
        "METAR ULLI 101330Z 23002MPS 5000 -SHSN SCT006 BKN020CB OVC036 M01/M01 Q1009 RESHSN R28L/550539 R28R/590537 TEMPO 0800 +SHSN FZRA BKN004 BKN016CB RMK OBST OBSC=",
        "METAR URKA 190130Z 06007MPS 5000 -SHRA FEW/// BKN044CB 15/15 Q1006 RESHRA R21/290155 TEMPO 0500 +TSRA SCT003 BKN016CB RMK QFE749/0999=",
        "METAR ULLI 191700Z 29008MPS 2200 0900SE R28L/1900U R28R/2000U +SHSN BLSN SCT011 BKN019CB OVC033 M06/M07 Q0996 R28L/452030 R28R/490535 BECMG 6000 NSW="
    ]
    for s in samples:
        print("==== RAW ====")
        print(s)
        print("==== DECODED ====")
        print(decode_metar(s))
        print()
