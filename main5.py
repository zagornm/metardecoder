#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
METAR / SPECI / TAF Decoder (RU)
Полное покрытие кодов и грамматическая обработка для естественных фраз.
--- REFACTORED VERSION ---
"""

import re
import json # Добавлен импорт для красивого вывода словаря

# ==============================
# ЦЕНТРАЛИЗОВАННЫЕ СЛОВАРИ ДАННЫХ
# ==============================

# ### NEW: Единый словарь для всех данных о погодных явлениях ###
# Структура: {КОД: {'name': Название, 'gender': род, 'number': число, 'instr': творительный падеж}}
WEATHER_DATA = {
    # Осадки
    'DZ': {'name': 'морось', 'gender': 'ж', 'number': 'ед', 'instr': 'моросью'},
    'RA': {'name': 'дождь', 'gender': 'м', 'number': 'ед', 'instr': 'дождём'},
    'SN': {'name': 'снег', 'gender': 'м', 'number': 'ед', 'instr': 'снегом'},
    'SG': {'name': 'снежные зерна', 'gender': 'мн', 'number': 'мн', 'instr': 'снежными зёрнами'},
    'IC': {'name': 'ледяные иглы', 'gender': 'мн', 'number': 'мн', 'instr': 'ледяными иглами'},
    'PL': {'name': 'ледяные шарики', 'gender': 'мн', 'number': 'мн', 'instr': 'ледяными шариками'},
    'GR': {'name': 'град', 'gender': 'м', 'number': 'ед', 'instr': 'градом'},
    'GS': {'name': 'мелкий град/снежная крупа', 'gender': 'м', 'number': 'ед', 'instr': 'мелким градом/снежной крупой'},
    'UP': {'name': 'неопределенные осадки', 'gender': 'мн', 'number': 'мн', 'instr': 'неопределёнными осадками'},
    # Явления, ухудшающие видимость
    'BR': {'name': 'дымка', 'gender': 'ж', 'number': 'ед', 'instr': 'дымкой'},
    'FG': {'name': 'туман', 'gender': 'м', 'number': 'ед', 'instr': 'туманом'},
    'FU': {'name': 'дым', 'gender': 'м', 'number': 'ед', 'instr': 'дымом'},
    'VA': {'name': 'вулканический пепел', 'gender': 'м', 'number': 'ед', 'instr': 'вулканическим пеплом'},
    'DU': {'name': 'пыль', 'gender': 'ж', 'number': 'ед', 'instr': 'пылью'},
    'SA': {'name': 'песок', 'gender': 'м', 'number': 'ед', 'instr': 'песком'},
    'HZ': {'name': 'мгла', 'gender': 'ж', 'number': 'ед', 'instr': 'мглой'},
    'PY': {'name': 'водяная пыль', 'gender': 'ж', 'number': 'ед', 'instr': 'водяной пылью'},
    # Другие явления
    'PO': {'name': 'пыльные/песчаные вихри', 'gender': 'мн', 'number': 'мн', 'instr': 'пыльными/песчаными вихрями'},
    'SQ': {'name': 'шквал', 'gender': 'м', 'number': 'ед', 'instr': 'шквалом'},
    'DS': {'name': 'пыльная буря', 'gender': 'ж', 'number': 'ед', 'instr': 'пыльной бурей'},
    'SS': {'name': 'песчаная буря', 'gender': 'ж', 'number': 'ед', 'instr': 'песчаной бурей'},
    # Составные явления (обрабатываются отдельно, но хранятся здесь для полноты)
    'DRSN': {'name': 'поземок', 'gender': 'м', 'number': 'ед', 'instr': 'поземком'},
    'BLSN': {'name': 'низовая метель', 'gender': 'ж', 'number': 'ед', 'instr': 'низовой метелью'},
    'TS': {'name': 'гроза', 'gender': 'ж', 'number': 'ед', 'instr': 'грозой'}, # Гроза как явление
}

# ### NEW: Единый словарь для дескрипторов ###
DESCRIPTORS_DATA = {
    'MI': {'name': 'тонкий', 'forms': {'м':'тонкий','ж':'тонкая','ср':'тонкое','мн':'тонкие'}},
    'BC': {'name': 'клочья', 'forms': {'м':'клочковый','ж':'клочковая','ср':'клочковое','мн':'клочковые'}},
    'PR': {'name': 'частичный', 'forms': {'м':'частичный','ж':'частичная','ср':'частичное','мн':'частичные'}},
    'DR': {'name': 'поземок', 'forms': {'м':'поземный','ж':'поземная','ср':'поземное','мн':'поземные'}},
    'BL': {'name': 'низовая метель', 'forms': {'м':'низовой','ж':'низовая','ср':'низовое','мн':'низовые'}},
    'SH': {'name': 'ливневой', 'forms': {'м':'ливневый','ж':'ливневая','ср':'ливневое','мн':'ливневые'}},
    'TS': {'name': 'гроза', 'forms': {}}, # Гроза как дескриптор, сама становится явлением
    'FZ': {'name': 'переохлажденный', 'forms': {'м':'переохлажденный','ж':'переохлажденная','ср':'переохлажденное','мн':'переохлажденные'}},
    'VC': {'name': 'вблизи', 'forms': {'м':'вблизи','ж':'вблизи','ср':'вблизи','мн':'вблизи'}},
    'RE': {'name': 'недавний', 'forms': {'м':'недавний','ж':'недавняя','ср':'недавнее','мн':'недавние'}},
}

# ### NEW: Автоматически создаваемый "обратный" словарь для грамматики ###
# Для получения грамматической информации по названию явления, а не по коду.
WEATHER_GRAMMAR_BY_NAME = {v['name']: v for v in WEATHER_DATA.values()}

# Вспомогательный набор названий явлений, которые считаются осадками
PRECIPITATION_LIKE = {
    'морось', 'дождь', 'снег', 'снежные зерна', 'ледяные иглы', 'ледяные шарики',
    'град', 'мелкий град/снежная крупа', 'неопределенные осадки'
}

# Остальные словари без изменений
INTENSITY_FORMS = {
    '+': {'м':'сильный','ж':'сильная','ср':'сильное','мн':'сильные'},
    '-': {'м':'слабый','ж':'слабая','ср':'слабое','мн':'слабые'},
    '':  {'м':'умеренный','ж':'умеренная','ср':'умеренное','мн':'умеренные'},
}
CLOUDS = {
    'FEW': 'мало (1–2/8)','SCT': 'рассеянные (3–4/8)','BKN': 'значительная (5–7/8)','OVC': 'сплошная (8/8)',
    'NSC': 'нет значимых облаков','SKC': 'ясно (sky clear)','CLR': 'ясно (clear)',
    'CAVOK': 'CAVOK (видимость ≥10 км, без облаков и явлений)'
}
CLOUD_TYPES = {'CB': 'кучево-дождевые (CB)', 'TCU': 'мощные кучевые (TCU)'}
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
# REGEX (без изменений)
# ==============================
RE_STATION = re.compile(r'^[A-Z]{4}$')
RE_TIME = re.compile(r'^\d{6}Z$')
RE_WIND = re.compile(r'^(?P<dir>\d{3}|VRB|000)(?P<spd>\d{2,3})(G(?P<gust>\d{2,3}))?(?P<unit>KT|MPS|KMH)?$')
RE_VARWIND = re.compile(r'^(?P<from>\d{3})V(?P<to>\d{3})$')
RE_VIS = re.compile(r'^(?P<vis>\d{4})(?P<dir>[NSEW]{1,2})?$')
RE_RVR = re.compile(r'^R(?P<rwy>\d{2}[LRC]?)/(?P<val>[PM]?\d{4})(V(?P<max>\d{4}))?(?P<trend>[UDN])?$')
RE_CLOUD = re.compile(r'^(FEW|SCT|BKN|OVC|NSC|SKC|CLR|CAVOK)(\d{3}|///)?(CB|TCU)?$')
RE_VV = re.compile(r'^VV(\d{3}|///)$')
RE_TEMP = re.compile(r'^(M?\d{2}|//)/(M?\d{2}|//)$')
RE_Q = re.compile(r'^Q(\d{4})$')
RE_A = re.compile(r'^A(\d{4})$')
RE_TREND = re.compile(r'^(BECMG|TEMPO|NOSIG|FM\d*|TL\d*|AT\d*)$')
RE_RUNWAY6 = re.compile(r'^R(?P<rwy>\d{2}|88|99)/(?P<digits>\d{6})$')
RE_RUNWAY_VAR = re.compile(r'^R(?P<rwy>\d{2}[LRC]?|88|99)/(?P<body>[0-9/]{4,6})$')
RE_WEATHER = re.compile(
    r'^(?:\+|-|VC)?'
    r'((?:MI|BC|PR|DR|BL|SH|TS|FZ|RE)|(?:DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PY|PO|SQ|DS|SS))+$'
)

# ==============================
# ФУНКЦИИ-помощники для грамматики (адаптированы под новую структуру)
# ==============================
def grammatical_gender_number(word):
    """Возвращает (род, число) для заданного погодного слова."""
    # Используем новый "обратный" словарь
    return (WEATHER_GRAMMAR_BY_NAME.get(word, {}).get('gender', 'м'),
            WEATHER_GRAMMAR_BY_NAME.get(word, {}).get('number', 'ед'))

def intensity_word_for(sign, gender='м', number='ед'):
    """Возвращает слово интенсивности по sign ('+','-','') и грамм.форме."""
    forms = INTENSITY_FORMS.get(sign, INTENSITY_FORMS[''])
    key = 'мн' if number == 'мн' else gender
    return forms.get(key, forms.get('м'))

def descr_form(descr_text, gender='м', number='ед'):
    """Возвращает согласованную форму дескриптора."""
    # Ищем дескриптор по названию в новой структуре
    for data in DESCRIPTORS_DATA.values():
        if data['name'] == descr_text:
            forms = data.get('forms')
            if not forms: return descr_text
            key = 'мн' if number == 'мн' else gender
            return forms.get(key, forms.get('м'))
    return descr_text

# ==============================
# Склейка и генерация естественных фраз (с исправлением бага)
# ==============================
def join_weather_events(events, descriptors, sign):
    """
    Создает естественную русскую фразу, грамматически согласованную.
    """
    if not events and not descriptors:
        return ""

    # Дескриптор 'TS' (гроза) всегда становится главным явлением
    if 'гроза' in descriptors:
        events.insert(0, 'гроза')
        descriptors.remove('гроза')
    
    has_ts = 'гроза' in events

    # Определяем главное слово для согласования
    main_word = events[0] if events else descriptors[0]
    gender, number = grammatical_gender_number(main_word)

    # Формируем список согласованных дескрипторов
    descr_out = [descr_form(d, gender, number) for d in descriptors]

    # ### FIXED: Логика для грозы с несколькими видами осадков ###
    if has_ts:
        prec = [e for e in events if e in PRECIPITATION_LIKE]
        base = 'гроза'
        if sign:
            int_for_ts = intensity_word_for(sign, 'ж', 'ед')
            base = f"{int_for_ts} {base}"

        if prec:
            # Собираем все осадки в творительном падеже
            instr_prec = [WEATHER_GRAMMAR_BY_NAME.get(p, {}).get('instr', p) for p in prec]
            
            # Соединяем их в красивую строку: "с дождём, снегом и градом"
            if len(instr_prec) == 1:
                prec_phrase = instr_prec[0]
            else:
                prec_phrase = ", ".join(instr_prec[:-1]) + " и " + instr_prec[-1]

            # Определяем предлог 'с' или 'со'
            first_word = instr_prec[0]
            prep = 'со' if first_word and first_word[0] in 'сш' else 'с'
            
            return " ".join(filter(None, descr_out + [f"{base} {prep} {prec_phrase}"]))
        else: # Гроза без осадков
            return " ".join(filter(None, descr_out + [base]))

    # Логика для обычных явлений
    if not events:
        ev_phrase = ""
    elif len(events) == 1:
        ev_phrase = events[0]
    elif len(events) == 2:
        first, second = events
        second_instr = WEATHER_GRAMMAR_BY_NAME.get(second, {}).get('instr', second)
        prep = 'со' if second_instr and second_instr[0] in 'сш' else 'с'
        ev_phrase = f"{first} {prep} {second_instr}"
    else: # 3 и более явления
        ev_phrase = ", ".join(events[:-1]) + " и " + events[-1]

    # Собираем финальную фразу
    intensity = intensity_word_for(sign, gender, number)
    
    # Не добавляем "умеренный"
    if sign not in ('+', '-'):
        intensity = ""
        
    full_phrase = " ".join(filter(None, [intensity] + descr_out + [ev_phrase]))
    
    return full_phrase.strip()


# ==============================
# ### REFACTORED: Основной декодер токена погоды ###
# ==============================
def decode_weather_token(tok: str) -> str:
    """
    Парсит токен погоды (например '-SHRASN') с помощью regex, без ручного перебора.
    """
    if not tok:
        return ''

    sign = ''
    if tok.startswith(('+', '-')):
        sign = tok[0]
        tok = tok[1:]

    events = []
    descriptors = []

    # 1. Обрабатываем составные коды, которые могут быть неверно разделены
    if 'BLSN' in tok:
        events.append(WEATHER_DATA['BLSN']['name'])
        tok = tok.replace('BLSN', '')
    if 'DRSN' in tok:
        events.append(WEATHER_DATA['DRSN']['name'])
        tok = tok.replace('DRSN', '')

    # 2. Используем findall для извлечения всех кодов
    codes = re.findall(r'[A-Z]{2}', tok)
    
    for code in codes:
        if code in DESCRIPTORS_DATA:
            descriptors.append(DESCRIPTORS_DATA[code]['name'])
        elif code in WEATHER_DATA:
            events.append(WEATHER_DATA[code]['name'])

    return join_weather_events(events, descriptors, sign)

# ==============================
# Функции-декодеры ВПП и облаков (без изменений)
# ==============================
def decode_cloud(tok: str) -> str:
    m = RE_CLOUD.match(tok)
    if not m: return tok
    grp, hhh, extra = m.groups()
    desc = CLOUDS.get(grp, grp)
    if grp == 'CAVOK': return desc
    if hhh:
        base = " основание: нет данных" if '/' in hhh else f" основание ~{int(hhh)*30} м ({int(hhh)*100} ft)"
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
    if rwy == "88": return "Состояние всех ВПП:"
    if rwy == "99": return "Состояние ВПП: повтор из предыдущего сообщения"
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
            if iv == 0: res.append("  Толщина: <1 мм")
            elif 1 <= iv <= 90: res.append(f"  Толщина: {iv} мм")
            elif iv == 92: res.append("  Толщина: 10 см")
            elif iv == 93: res.append("  Толщина: 15 см")
            elif iv == 94: res.append("  Толщина: 20 см")
            elif iv == 98: res.append("  Толщина: 40 см")
            elif iv == 99: res.append("  Толщина: ВПП не работает")
            else: res.append(f"  Толщина: код {thick}")
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
    if tok.startswith("R") and "CLRD" in tok: return f"Состояние ВПП {tok[1:3]}: очищена"
    if tok.startswith("R") and "CLSD" in tok: return f"Состояние ВПП {tok[1:3]}: закрыта"
    if "SNOCLO" in tok: return "Аэродром закрыт снегом"
    if "RRRR" in tok and "99" in tok: return "ВПП закрыта на чистку"
    m = RE_RUNWAY6.match(tok)
    if m: return decode_runway_digits(m.group('rwy'), m.group('digits'))
    m = RE_RUNWAY_VAR.match(tok)
    if m: return decode_runway_body(m.group('rwy'), m.group('body'))
    return None

# ==============================
# Основной декодер METAR
# ==============================
def decode_metar(metar: str) -> tuple[str, dict]: # ИЗМЕНЕНО: Тип возвращаемого значения
    tokens = metar.replace("=", "").split()
    out = []
    # НОВОЕ: Инициализация словаря для структурированных данных
    metar_data = {}
    i = 0
    while i < len(tokens):
        t = tokens[i]
        
        # Станция
        if RE_STATION.match(t) and (i == 1 or (i > 0 and tokens[i-1] in ["METAR", "SPECI"])):
            out.append(f"Аэродром: {t}")
            # НОВОЕ: Добавление в словарь
            metar_data['station'] = {'code': t}

        # Время
        elif RE_TIME.match(t):
            out.append(f"Время наблюдения: {t} UTC")
            # НОВОЕ: Добавление в словарь
            metar_data['time'] = {
                'raw': t,
                'day': int(t[0:2]),
                'hour': int(t[2:4]),
                'minute': int(t[4:6])
            }

        # Ветер
        elif RE_WIND.match(t):
            m = RE_WIND.match(t)
            d, s, g, u = m.group('dir'), int(m.group('spd')), m.group('gust'), (m.group('unit') or 'KT').upper()
            unit_ru = 'м/с' if u == 'MPS' else 'км/ч' if u == 'KMH' else 'уз.'
            if d == '000': wind = f"Штиль, {s} {unit_ru}"
            elif d == 'VRB': wind = f"Ветер переменный {s} {unit_ru}"
            else: wind = f"Ветер {int(d)}° {s} {unit_ru}"
            if g: wind += f", порывы {int(g)} {unit_ru}"
            out.append(wind)
            # НОВОЕ: Добавление в словарь
            metar_data['wind'] = {
                'raw': t,
                'direction': d if d == 'VRB' else int(d),
                'speed': s,
                'gust': int(g) if g else None,
                'unit': u
            }

        # Вариабельность ветра
        elif RE_VARWIND.match(t):
            m = RE_VARWIND.match(t)
            out.append(f"Вариабельность ветра: {m.group('from')}°–{m.group('to')}°")
            # НОВОЕ: Добавление в словарь
            if 'wind' not in metar_data: metar_data['wind'] = {}
            metar_data['wind']['variability'] = {
                'raw': t,
                'from': int(m.group('from')),
                'to': int(m.group('to'))
            }

        # Видимость
        elif RE_VIS.match(t):
            m = RE_VIS.match(t)
            vis, dir_ = int(m.group('vis')), m.group('dir') or ''
            if vis == 9999:
                out.append("Видимость ≥10 км")
            else:
                if out and out[-1].startswith("Видимость"):
                    if dir_: out[-1] += f", в направлении {dir_} — {vis} м"
                    else: out[-1] = f"Видимость минимальная {vis} м"
                else:
                    if dir_: out.append(f"Видимость {vis} м {dir_}")
                    else: out.append(f"Видимость минимальная {vis} м")
            # НОВОЕ: Добавление в словарь
            if 'visibility' not in metar_data: metar_data['visibility'] = []
            vis_data = {'raw': t, 'meters': vis}
            if dir_: vis_data['direction'] = dir_
            metar_data['visibility'].append(vis_data)


        # RVR
        elif RE_RVR.match(t):
            m = RE_RVR.match(t)
            val = m.group('val')
            if val.startswith('P'): val_txt = f">{val[1:]} м"
            elif val.startswith('M'): val_txt = f"<{val[1:]} м"
            else: val_txt = f"{int(val)} м"
            trend_map = {'U': 'улучшалась', 'D': 'ухудшалась', 'N': 'без изменений'}
            trend = trend_map.get(m.group('trend'), '')
            out.append(f"RVR ВПП {m.group('rwy')}: {val_txt} {trend}".strip())
            # НОВОЕ: Добавление в словарь
            if 'rvr' not in metar_data: metar_data['rvr'] = []
            metar_data['rvr'].append({
                'raw': t,
                'runway': m.group('rwy'),
                'value_raw': m.group('val'),
                'value_max': m.group('max'),
                'trend': m.group('trend')
            })

        # Облачность
        elif RE_CLOUD.match(t):
            decoded_cloud_text = decode_cloud(t)
            out.append("Облачность: " + decoded_cloud_text)
            # НОВОЕ: Добавление в словарь
            if 'clouds' not in metar_data: metar_data['clouds'] = []
            m = RE_CLOUD.match(t)
            grp, hhh, extra = m.groups()
            metar_data['clouds'].append({
                'raw': t,
                'code': grp,
                'height_ft': int(hhh) * 100 if hhh and hhh.isdigit() else None,
                'type': extra,
                'decoded_text': decoded_cloud_text
            })

        # Вертикальная видимость
        elif RE_VV.match(t):
            vv = RE_VV.match(t).group(1)
            out.append("Вертикальная видимость: нет данных" if vv == "///" else f"Вертикальная видимость {int(vv)*30} м")
            # НОВОЕ: Добавление в словарь
            metar_data['vertical_visibility'] = {
                'raw': t,
                'height_m': int(vv) * 30 if vv.isdigit() else None
            }

        # Температура и точка росы
        elif RE_TEMP.match(t):
            T, Td = t.split('/')
            T_val = "нет данных" if T == "//" else f"{T.replace('M','-')}°C"
            Td_val = "нет данных" if Td == "//" else f"{Td.replace('M','-')}°C"
            out.append(f"Температура {T_val}, точка росы {Td_val}")
            # НОВОЕ: Добавление в словарь
            metar_data['temperature'] = {
                'raw': t,
                'air_celsius': int(T.replace('M', '-')) if T != '//' else None,
                'dew_point_celsius': int(Td.replace('M', '-')) if Td != '//' else None
            }

        # Давление
        elif RE_Q.match(t):
            pressure_hpa = int(RE_Q.match(t).group(1))
            out.append(f"Давление QNH {pressure_hpa} гПа")
            # НОВОЕ: Добавление в словарь
            metar_data['pressure'] = {'raw': t, 'qnh_hpa': pressure_hpa}
        elif RE_A.match(t):
            pressure_inhg = int(RE_A.match(t).group(1)) / 100.0
            out.append(f"Давление {pressure_inhg:.2f} inHg")
            # НОВОЕ: Добавление в словарь
            metar_data['pressure'] = {'raw': t, 'altimeter_inhg': pressure_inhg}

        # Тренд
        elif RE_TREND.match(t):
            out.append(f"Тренд {t}")
            # НОВОЕ: Добавление в словарь
            if 'trend' not in metar_data: metar_data['trend'] = []
            metar_data['trend'].append({'code': t})


        # Состояние ВПП
        elif t.startswith("R") and (RE_RUNWAY6.match(t) or RE_RUNWAY_VAR.match(t) or any(x in t for x in ["CLRD","CLSD","SNOCLO","RRRR"])):
            r = decode_runway(t)
            out.append(r if r else f"(неизвестно) {t}")
            # НОВОЕ: Добавление в словарь
            if 'runway_state' not in metar_data: metar_data['runway_state'] = []
            metar_data['runway_state'].append({'raw': t, 'decoded_text': r})

        # Погодные явления
        elif RE_WEATHER.match(t):
            phrase = decode_weather_token(t)
            if phrase:
                out.append("Явления: " + phrase)
                # НОВОЕ: Добавление в словарь
                if 'weather' not in metar_data: metar_data['weather'] = []
                metar_data['weather'].append({'raw': t, 'decoded_text': phrase})

        # NSW
        elif t == "NSW":
            out.append("В прогнозе: без значимых явлений" if out and out[-1].startswith("Тренд") else "Явления: без значимых явлений")
            # НОВОЕ: Добавление в словарь
            if 'weather' not in metar_data: metar_data['weather'] = []
            metar_data['weather'].append({'raw': t, 'decoded_text': 'Без значимых явлений'})


        # WS
        elif t == "WS":
            ws_info = "Сдвиг ветра (WS)"
            ws_dict = {'raw': [t]}
            if i + 2 < len(tokens) and tokens[i + 1] == "ALL" and tokens[i + 2] == "RWY":
                ws_info = "Сдвиг ветра: на всех ВПП"
                ws_dict['runways'] = 'ALL'
                ws_dict['raw'].extend(["ALL", "RWY"])
                i += 2
            elif i + 1 < len(tokens) and tokens[i + 1].startswith("RWY"):
                ws_info = f"Сдвиг ветра: на {tokens[i + 1]}"
                ws_dict['runways'] = tokens[i + 1]
                ws_dict['raw'].append(tokens[i + 1])
                i += 1
            out.append(ws_info)
            # НОВОЕ: Добавление в словарь
            if 'wind_shear' not in metar_data: metar_data['wind_shear'] = []
            metar_data['wind_shear'].append(ws_dict)

        # RMK (С НОВЫМ ИСПРАВЛЕННЫМ БЛОКОМ)
        elif t == 'RMK':
            remark_tokens = tokens[i+1:]
            # Добавляем один общий заголовок для всех ремарок
            if remark_tokens:
                out.append("Ремарки:")
                # НОВОЕ: Добавление в словарь
                metar_data['remarks'] = {'raw': ' '.join(remark_tokens), 'decoded': []}

            j = 0
            while j < len(remark_tokens):
                rt = remark_tokens[j]
                decoded_remark_text = None
                decoded_remark_dict = {}
                
                # --- НОВАЯ ЛОГИКА: Проверяем фразы из двух слов ---
                # Проверяем, что мы не выходим за границы списка
                if j + 1 < len(remark_tokens):
                    phrase = f"{rt} {remark_tokens[j+1]}"
                    if phrase == "MT OBSC":
                        decoded_remark_text = "  - Горы закрыты облачностью/осадками"
                        decoded_remark_dict = {'code': phrase, 'description': 'Горы закрыты облачностью/осадками'}
                        out.append(decoded_remark_text)
                        metar_data['remarks']['decoded'].append(decoded_remark_dict)
                        j += 2  # Перескакиваем через 2 токена
                        continue
                    if phrase == "OBST OBSC":
                        decoded_remark_text = "  - Препятствия закрыты облачностью/осадками"
                        decoded_remark_dict = {'code': phrase, 'description': 'Препятствия закрыты облачностью/осадками'}
                        out.append(decoded_remark_text)
                        metar_data['remarks']['decoded'].append(decoded_remark_dict)
                        j += 2  # Перескакиваем через 2 токена
                        continue
                
                # --- СТАРАЯ ЛОГИКА для одиночных токенов ---
                if rt.startswith("QFE"):
                    val = rt[3:]
                    decoded_remark_text = f"  - Давление QFE {val.replace('/', ' мм рт.ст. (доп. ')} мм рт.ст."
                    decoded_remark_dict = {'code': rt, 'description': 'Давление QFE', 'value': val}
                    out.append(decoded_remark_text)
                elif rt.startswith("QBB"):
                    decoded_remark_text = f"  - Нижняя граница облаков {rt[3:]} м"
                    decoded_remark_dict = {'code': rt, 'description': 'Нижняя граница облаков', 'value_m': rt[3:]}
                    out.append(decoded_remark_text)
                else: # Обработка остальных, теперь как неизвестных
                    decoded_remark_text = f"  - (неизвестная ремарка) {rt}"
                    decoded_remark_dict = {'code': rt, 'description': 'Неизвестная ремарка'}
                    out.append(decoded_remark_text)
                
                # НОВОЕ: Добавление в словарь
                if decoded_remark_dict:
                     metar_data['remarks']['decoded'].append(decoded_remark_dict)

                j += 1 # Сдвигаемся на 1 токен

            break # Выходим из основного цикла, т.к. ремарки всегда в конце
            
        # иначе — неизвестный токен
        else:
            if t not in ["METAR", "SPECI", "TAF"]:
                out.append(f"(неизвестно) {t}")
                # НОВОЕ: Добавление в словарь
                if 'unknown' not in metar_data: metar_data['unknown'] = []
                metar_data['unknown'].append(t)

        i += 1

    # ИЗМЕНЕНО: Возвращаем и текст, и словарь
    return "\n".join(out), metar_data

# ==============================
# Демонстрационный блок с новым тест-кейсом
# ==============================
if __name__ == "__main__":
    samples = [
        "METAR ULMM 261330Z 22005G12MPS 180V250 9999 -SHRASN BKN028CB 03/M02 Q1000 R13/290051 NOSIG RMK QFE744=",
        "METAR ULLI 101330Z 23002MPS 5000 -SHSN SCT006 BKN020CB OVC036 M01/M01 Q1009 RESHSN R28L/550539 R28R/590537 TEMPO 0800 +SHSN FZRA BKN004 BKN016CB RMK OBST OBSC=",
        "METAR ULLI 191700Z 29008MPS 2200 0900SE R28L/1900U R28R/2000U +SHSN BLSN SCT011 BKN019CB OVC033 M06/M07 Q0996 R28L/452030 R28R/490535 BECMG 6000 NSW=",
        "METAR ULLI 200930Z 32005MPS 9999 VCTS -SHRA BKN029CB 17/14 Q1000 R88/290050 TEMPO VRB13MPS 1000 SHRA SQ BKN016CB=",
        "METAR UUUU 201000Z 24015G25KT 2000 +TSRASNGR BKN015CB 01/00 Q0998",
        # ### НОВЫЙ ТЕСТ-КЕЙС ДЛЯ РЕМАРОК ###
        "METAR URMM 021630Z 11005MPS 4400 -SHRA BR BKN004 OVC021CB 12/11 Q1023 R11/190060 TEMPO 0300 -SHRA FG BKN002 BKN030CB RMK MT OBSC OBST OBSC QFE739/0986"
    ]
    for s in samples:
        print("==== RAW ====")
        print(s)
        # ИЗМЕНЕНО: Обработка нового формата вывода
        print("\n==== DECODED (Human-Readable) ====")
        try:
            # Получаем оба результата
            decoded_text, decoded_dict = decode_metar(s)
            print(decoded_text)
            print("\n---- DECODED (Dict/JSON) ----")
            # Выводим словарь в отформатированном виде
            print(json.dumps(decoded_dict, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"ERROR!\n{e}")
        print("\n" + "="*40 + "\n")
