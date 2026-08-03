import json
import os
import urllib.request

NC_URL = os.environ["NOCODB_URL"]
NC_TOKEN = os.environ["NOCODB_TOKEN"]
HROMADAS_TABLE = "mjtetfuixggp5lg"
TAGS_TABLE = "moee8ep5561zt76"

payload = {
    "Name": "Ніжинська міська територіальна громада",
    "Oblast": "Чернігівська область",
    "Type": "міська",
    "StrategyUrl": "https://data.gov.ua/dataset/0e6dcf9a-f240-4967-8cbf-9e2bffe8a79d",
    "StrategyYear": 2019,
    "StrategyPeriod": "до 2027 (9 років, ПЗР 2/3/4-річні цикли)",
    "Goals": (
        "Стратегічна ціль 1. Створення сприятливих умов для розвитку бізнесу, "
        "промисловості та залучення інвестицій\n"
        "Стратегічна ціль 2. Розвиток туристичного потенціалу громади\n"
        "Стратегічна ціль 3. Покращення комфорту проживання, безпеки та довкілля громади\n"
        "Стратегічна ціль 4. Розвиток соціального капіталу громади"
    ),
    "Projects": (
        '- Створення логістичного центру ("сухого порту") зі спільним використанням '
        "аеродрому [Транспорт/логістика, planned]\n"
        "- Розробка маркетингової стратегії громади та бренд-буку [Туризм, planned]\n"
        "- Створення регіонального енергетичного центру [Енергетика (ВДЕ), planned]\n"
        "- Впровадження концепції «Е-місто» + електронний реєстр жителів "
        "[IT/цифровізація, planned]\n"
        "- Розчищення русла річки Остер та водоймищ [Довкілля/екологія, planned]"
    ),
    "Strengths": (
        "- Вигідне транспортно-логістичне розташування (аеродром, всі види транспорту)\n"
        "- Значна історико-архітектурна спадщина, старовинне місто\n"
        "- Університетське місто зі значним студентським потенціалом\n"
        "- Чисте повітря, відсутність шкідливих підприємств, річка Остер"
    ),
    "Challenges": (
        "- Близькість до країни-агресора відлякує інвесторів\n"
        "- Скорочення сектора малого/мікробізнесу, відтік кадрів через низькі зарплати\n"
        "- Відсутність повноцінного туристичного бренду при наявній спадщині\n"
        "- Невпорядкованість пасажирських перевезень, брак безбар'єрності\n"
        "- Брак публічних просторів для молоді, хаотичний розвиток вуличного спорту"
    ),
    "PartnersMentioned": (
        "- Європейська Ініціатива «Угода мерів» (Дні Сталої Енергії)\n"
        "- Інструменти COSME та Горизонт-2020 (для МСП)"
    ),
    "MSSAgreements": (
        "ЯВНИЙ намір МСС у задачі 3.5.3: «Кооперація з іншими громадами у спільному "
        "вирішенні проблеми розчищення річки Остер» — громада сама формулює потребу в "
        "міжмуніципальній співпраці по річці, спільній для кількох громад басейну"
    ),
    "SourceQuality": "full-strategy",
    "ExtractedAt": "2026-07-21 00:00:00",
    "ConfidenceNotes": (
        "Документ побудований за стандартним держшаблоном Мінрегіону (профіль → SWOT → "
        "стратегічні цілі → оперативні цілі → завдання → заходи). Явна згадка МСС у "
        "тексті — сильний сигнал, що такі наміри можна витягувати автоматично навіть без "
        "окремого реєстру. PoC-запис для валідації пайплайна."
    ),
}


def nc(method, endpoint, body=None):
    req = urllib.request.Request(
        f"{NC_URL}{endpoint}",
        method=method,
        headers={"xc-token": NC_TOKEN, "Content-Type": "application/json"},
        data=json.dumps(body).encode("utf-8") if body is not None else None,
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


created = nc("POST", f"/api/v2/tables/{HROMADAS_TABLE}/records", payload)
print("Created hromada record:", created)
hromada_id = created["Id"] if isinstance(created, dict) else created[0]["Id"]

sector_names = [
    "Підприємництво / МСБ",
    "Інвестиції / інвестклімат",
    "Туризм",
    "Культура / спадщина",
    "Вода / каналізація (ЖКГ)",
    "Енергетика (ВДЕ)",
    "Транспорт / логістика",
    "Довкілля / екологія",
    "Безпека / ЦЗ",
    "IT / цифровізація",
    "Освіта",
    "Охорона здоровя",
]

tags = nc("GET", f"/api/v2/tables/{TAGS_TABLE}/records?limit=200&fields=Id,Name")
name_to_id = {r["Name"]: r["Id"] for r in tags["list"]}
sector_ids = [name_to_id[n] for n in sector_names if n in name_to_id]
missing = [n for n in sector_names if n not in name_to_id]
print("Sector tag ids to link:", sector_ids, "missing:", missing)

SECTORS_LINK_COL_ID = "c80rnrin54hrttm"
link_body = [{"Id": tid} for tid in sector_ids]
linked = nc(
    "POST",
    f"/api/v2/tables/{HROMADAS_TABLE}/links/{SECTORS_LINK_COL_ID}/records/{hromada_id}",
    link_body,
)
print("Linked sectors:", linked)
