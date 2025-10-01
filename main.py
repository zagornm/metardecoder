#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
METAR / SPECI / TAF Decoder (RU)
Полное покрытие кодов на основе методичек.
"""

import re

# ==============================
# СЛОВАРИ
# ==============================
INTENSITY = {'+': 'сильный', '-': 'слабый', '': 'умеренный'}

DESCRIPTORS = {
    'MI': 'тонкий', 'BC': 'клочья', 'PR': 'частичный', 'DR': 'поземок',
    'BL': 'низовая метель', 'SH': 'ливневый', 'TS': 'гроза', 'FZ': 'переохлажденный',
    'VC': 'вблизи', 'RE': 'недавний'
}

WEATHER = {
    'DZ': 'морось','RA': 'дождь','SN': 'снег','SG': 'снежные зерна','IC': 'ледяные иглы',
    'PL': 'ледяные шарики','GR': 'град','GS': 'мелкий град/снежная крупа','UP': 'неопределенные осадки',
    'BR': 'дымка','FG': 'туман','FU': 'дым','VA': 'вулканический пепел','DU': 'пыль','SA': 'песок',
    'HZ': 'мгла','PY': 'водяная пыль','PO': 'пыльные/песчаные вихри','SQ': 'шквал','DS': 'пыльная буря','SS': 'песчаная буря'
}

# инструментальные формы (для "X со Y" — второе явление в творительном падеже)
WEATHER_INSTR = {
    'морось': 'моросью',
    'дождь': 'дождём',
    'снег': 'снегом',
    'снежные зерна': 'снежными зёрнами',
    'ледяные иглы': 'ледяными иглами',
    'ледяные шарики': 'ледяными шариками',
    'град': 'градом',
    'мелкий град/снежная крупа': 'мелким градом/снежной крупой',
    'неопределенные осадки': 'неопределёнными осадками',
    'дымка': 'дымкой',
    'туман': 'туманом',
    'дым': 'дымом',
    'вулканический пепел': 'вулканическим пеплом',
    'пыль': 'пылью',
    'песок': 'песком',
    'мгла': 'мглой',
    'водяная пыль': 'водяной пылью',
    'пыльные/песчаные вихри': 'пыльными/песчаными вихрями',
    'шквал': 'шквалом',
    'пыльная буря': 'пыльной бурей',
    'песчаная буря': 'песчаной бурей'
}

CLOUDS = {
    'FEW': 'мало (1–2/8)','SCT': 'рассеянные (3–4/8)','BKN': 'значительная (5–7/8)','OVC': 'сплошная (8/8)',
    'NSC': 'нет значимых облаков','SKC': 'ясно (sky clear)','CLR': 'ясно (clear)',
    'CAVOK': 'CAVOK (видимость ≥10 км, без облаков и явлений)'
}

# типы кучевых облаков
CLOUD_TYPES = {
    'CB': 'кучево-дождевые (CB)',
    'TCU': 'мощные кучевые (TCU)'
}

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
RE_CLOUD = re.compile(r'^(FEW|SCT|BKN|OVC|NSC|SKC|CLR|CAVOK)(\d{3})?(CB|TCU)?$')
RE_VV = re.compile(r'^VV(\d{3}|///)$')
RE_TEMP = re.compile(r'^(M?\d{2}|//)/(M?\d{2}|//)$')
RE_Q = re.compile(r'^Q(\d{4})$')
RE_A = re.compile(r'^A(\d{4})$')
RE_TREND = re.compile(r'^(BECMG|TEMPO|NOSIG|FM\d*|TL\d*|AT\d*)$')
RE_RUNWAY6 = re.compile(r'^R(?P<rwy>\d{2}|88|99)/(?P<digits>\d{6})$')
RE_RUNWAY_VAR = re.compile(r'^R(?P<rwy>\d{2}[LRC]?|88|99)/(?P<body>[0-9/]{4,6})$')

# погодные явления
RE_WEATHER = re.compile(
    r'^(?:\+|-|VC)?'
    r'(?:MI|BC|PR|DR|BL|SH|TS|FZ|RE){0,3}'
    r'(?:DZ|RA|SN|SG|IC|PL|GR|GS|UP|'
    r'BR|FG|FU|VA|DU|SA|HZ|PY|PO|SQ|DS|SS)+$'
)

# ==============================
# ФУНКЦИИ
# ==============================
def join_weather_events(events):
    """Склеивает погодные явления в естественный вид (поддержка 1-2 элементов лучше всего)."""
    if not events:
        return ""
    if len(events) == 1:
        return events[0]
    if len(events) == 2:
        first, second = events[0], events[1]
        second_instr = WEATHER_INSTR.get(second)
        if second_instr:
            # выбираем 'с' или 'со' в зависимости от первой буквы инструментальной формы
            prep = 'со' if second_instr and second_instr[0] in 'сш' else 'с'
            return f"{first} {prep} {second_instr}"
        else:
            # fallback: просто 'с X'
            prep = 'со' if second and second[0] in 'сш' else 'с'
            return f"{first} {prep} {second}"
    # >2 — перечисление (в простом виде)
    return ", ".join(events[:-1]) + " и " + events[-1]

def decode_weather(tok: str) -> str:
    """Разбирает токен погоды, возвращает текст (без префикса 'Явления:' )."""
    if not tok:
        return ''
    intensity = ''
    if tok[0] in ['+', '-']:
        intensity = INTENSITY.get(tok[0], '')
        tok = tok[1:]
    elif tok.startswith('VC'):
        intensity = 'вблизи'
        tok = tok[2:]

    descriptors = []
    events = []
    # парсим по 2 буквы — DESCRIPTORS и WEATHER состоят из 2 букв
    while tok:
        code = tok[:2]
        if code in DESCRIPTORS:
            descriptors.append(DESCRIPTORS[code])
            tok = tok[2:]
        elif code in WEATHER:
            events.append(WEATHER[code])
            tok = tok[2:]
        else:
            # если первые 2 буквы не узнали — срезаем 1 символ чтобы сдвинуться
            tok = tok[1:]

    weather_text = join_weather_events(events) if events else ""
    # собираем: интенсивность + дескрипторы + явления
    parts = []
    if intensity: parts.append(intensity)
    if descriptors: parts.extend(descriptors)
    if weather_text: parts.append(weather_text)
    return " ".join(parts).strip()

def decode_cloud(tok: str) -> str:
    m = RE_CLOUD.match(tok)
    if not m:
        return tok
    grp, hhh, extra = m.groups()
    desc = CLOUDS.get(grp, grp)
    if grp == 'CAVOK':
        return desc
    base = f" основание ~{int(hhh)*30} м ({int(hhh)*100} ft)" if hhh else ""
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
        iv = int(thick)
        if iv == 0: res.append("  Толщина: <1 мм")
        elif 1 <= iv <= 90: res.append(f"  Толщина: {iv} мм")
        elif iv == 92: res.append("  Толщина: 10 см")
        elif iv == 93: res.append("  Толщина: 15 см")
        elif iv == 94: res.append("  Толщина: 20 см")
        elif iv == 98: res.append("  Толщина: 40 см")
        elif iv == 99: res.append("  Толщина: ВПП не работает")
        else: res.append(f"  Толщина: код {thick}")
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
    if m: return decode_runway_digits(m.group('rwy'), m.group('digits'))
    m = RE_RUNWAY_VAR.match(tok)
    if m: return decode_runway_body(m.group('rwy'), m.group('body'))
    return None

# ==============================
# ОСНОВНОЙ ДЕКОДЕР
# ==============================
def decode_metar(metar: str) -> str:
    tokens = metar.replace("=", "").split()
    out, i = [], 0
    while i < len(tokens):
        t = tokens[i]

        if RE_STATION.match(t) and (i == 1 or tokens[i-1] in ["METAR", "SPECI"]):
            out.append(f"Аэродром: {t}")

        elif RE_TIME.match(t):
            out.append(f"Время наблюдения: {t} UTC")

        elif RE_WIND.match(t):
            m = RE_WIND.match(t)
            d, s, g, u = m.group('dir'), int(m.group('spd')), m.group('gust'), (m.group('unit') or 'KT').upper()
            unit_ru = 'м/с' if u == 'MPS' else 'км/ч' if u == 'KMH' else 'уз.'
            if d == '000': wind = f"Штиль, {s} {unit_ru}"
            elif d == 'VRB': wind = f"Ветер переменный {s} {unit_ru}"
            else: wind = f"Ветер {int(d)}° {s} {unit_ru}"
            if g: wind += f", порывы {int(g)} {unit_ru}"
            out.append(wind)

        elif RE_VARWIND.match(t):
            m = RE_VARWIND.match(t)
            out.append(f"Вариабельность ветра: {m.group('from')}°–{m.group('to')}°")

        elif RE_VIS.match(t):
            m = RE_VIS.match(t); vis = int(m.group('vis')); dir_ = m.group('dir') or ''
            if vis == 9999:
                out.append("Видимость ≥10 км")
            else:
                if out and out[-1].startswith("Видимость"):
                    if dir_: out[-1] += f", в направлении {dir_} — {vis} м"
                    else: out[-1] = f"Видимость минимальная {vis} м"
                else:
                    if dir_: out.append(f"Видимость {vis} м {dir_}")
                    else: out.append(f"Видимость минимальная {vis} м")

        elif RE_RVR.match(t):
            m = RE_RVR.match(t); val = m.group('val')
            if val.startswith('P'): val = f">{val[1:]} м"
            elif val.startswith('M'): val = f"<{val[1:]} м"
            else: val = f"{int(val)} м"
            trend = {'U':'улучшалась','D':'ухудшалась','N':'без изменений'}.get(m.group('trend'),'')
            out.append(f"RVR ВПП {m.group('rwy')}: {val} {trend}".strip())

        elif RE_CLOUD.match(t):
            out.append("Облачность: " + decode_cloud(t))

        elif RE_VV.match(t):
            vv = RE_VV.match(t).group(1)
            out.append("Вертикальная видимость: нет данных" if vv=="///" else f"Вертикальная видимость {int(vv)*30} м")

        elif RE_TEMP.match(t):
            m = RE_TEMP.match(t)
            T, Td = m.group(1), m.group(2)
            T_val = "нет данных" if T=="//" else f"{T.replace('M','-')}°C"
            Td_val = "нет данных" if Td=="//" else f"{Td.replace('M','-')}°C"
            out.append(f"Температура {T_val}, точка росы {Td_val}")

        elif RE_Q.match(t):
            out.append(f"Давление QNH {int(RE_Q.match(t).group(1))} гПа")

        elif RE_A.match(t):
            val = int(RE_A.match(t).group(1)) / 100.0
            out.append(f"Давление {val:.2f} inHg")

        elif RE_TREND.match(t):
            out.append(f"Тренд {t}")

        elif t.startswith("R") and (RE_RUNWAY6.match(t) or RE_RUNWAY_VAR.match(t) or any(x in t for x in ["CLRD","CLSD","SNOCLO","RRRR"])):
            out.append(decode_runway(t))

        elif RE_WEATHER.match(t):
            dw = decode_weather(t)
            if dw:
                out.append("Явления: " + dw)

        elif t == "NSW":
            if out and out[-1].startswith("Тренд"):
                out.append("В прогнозе: без значимых явлений")
            else:
                out.append("Явления: без значимых явлений")

        elif t == "WS":
            if i+2 < len(tokens) and tokens[i+1]=="ALL" and tokens[i+2]=="RWY":
                out.append("Сдвиг ветра: на всех ВПП"); i+=2
            elif i+1 < len(tokens) and tokens[i+1].startswith("RWY"):
                out.append(f"Сдвиг ветра: на {tokens[i+1]}"); i+=1
            else:
                out.append("Сдвиг ветра (WS)")

        elif t == 'RMK':
            remark_tokens = tokens[i+1:]
            for rt in remark_tokens:
                if rt.startswith("QFE"): out.append(f"Ремарка: Давление QFE {rt[3:]} мм рт.ст.")
                elif rt.startswith("QBB"): out.append(f"Ремарка: Нижняя граница облаков {rt[3:]} м")
                elif rt == "OBST" and "OBSC" in remark_tokens: out.append("Ремарка: Препятствия закрыты облаками")
                elif rt == "MT" and "OBSC" in remark_tokens: out.append("Ремарка: Горы закрыты облаками")
                elif rt == "OBSC": continue
                elif rt.startswith("ICE"): out.append("Ремарка: Обледенение")
                elif rt.startswith("TURB"): out.append("Ремарка: Турбулентность")
                else: out.append("Ремарка: " + rt)
            break

        else:
            out.append(f"(неизвестно) {t}")

        i += 1
    return "\n".join(out)

# ==============================
# ДЕМО
# ==============================
if __name__ == "__main__":
    samples = [
        "METAR ULMM 261330Z 22005G12MPS 180V250 9999 -SHRASN BKN028CB 03/M02 Q1000 R13/290051 NOSIG RMK QFE744=",
        "METAR ULLI 101330Z 23002MPS 5000 -SHSN SCT006 BKN020CB OVC036 M01/M01 Q1009 RESHSN R28L/550539 R28R/590537 TEMPO 0800 +SHSN FZRA BKN004 BKN016CB RMK OBST OBSC=",
    ]
    for s in samples:
        print("==== RAW ===="); print(s)
        print("==== DECODED ===="); print(decode_metar(s)); print()
