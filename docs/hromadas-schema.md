# Hromadas — extraction schema & pipeline draft

Draft for the "collect громада strategies → analyze for collaborations" pilot.
Pilot scope: 30–50 громад tied to Civic Tech Lab / Digital Democracy Lab participants + neighbors.
Two-layer output graph: громада↔громада + громада↔W3I ecosystem.

## NocoDB table: `Hromadas`

| Field | Type | Notes |
|-------|------|-------|
| Name | SingleLineText | Офіційна назва громади |
| Koatuu / Katottg | SingleLineText | Код КАТОТТГ — стабильный ключ для дедупликации/джойнов |
| Oblast | SingleSelect | Область |
| Rayon | SingleLineText | Район |
| Type | SingleSelect | міська / селищна / сільська |
| Population | Number | Населення |
| StrategyUrl | URL | Ссылка на PDF/страницу стратегии |
| StrategyYear | Number | Горизонт/год принятия стратегии |
| StrategyPeriod | SingleLineText | напр. 2021–2027 |
| Goals | LongText | 3–5 стратегічних цілей (извлечено LLM) |
| Sectors | LinkToTags | Контролируемый словарь секторов (связь с Tags) |
| Projects | LongText | Конкретні проєкти из стратегии + ДФРР/Prozorro |
| Strengths | LongText | Сильні сторони / ресурси |
| Challenges | LongText | Проблеми / виклики |
| PartnersMentioned | LongText | Донори, сусідні громади, згадані в стратегії |
| DonorsPrograms | MultiSelect / CSV | Контрольований словник програм (DOBRE, DECIDE, GIZ, U-LEAD, …). У публічному JSON — масив рядків. Відсутність ≠ «немає програми» (підлога покриття). |
| MSSAgreements | LongText | Існуючі договори МСС (если найдены) |
| SourceQuality | SingleSelect | full-strategy / dfrr-proxy / partial / none |
| ExtractedAt | DateTime | Когда прогнали extraction |
| RawTextRef | URL/Attachment | Ссылка на исходный PDF/текст |

## Controlled sector vocabulary (draft — теги Category=Hromada Sector)

Энергетика (ВДЕ) · Туризм · Сільське господарство / АПК · Промисловість ·
IT / цифровізація · Освіта · Охорона здоров'я · Транспорт / логістика ·
Вода / каналізація (ЖКГ) · Довкілля / екологія · Культура / спадщина ·
Соціальні послуги · Безпека / ЦЗ · Відновлення / реконструкція ·
Підприємництво / МСБ · Інвестиції / інвестклімат

(финализировать после первых 5–10 стратегий — словарь всегда растёт)
Update after PoC (Ніжинська громада): добавить "Просторове планування / урбаністика", "Е-врядування".

## Extraction prompt (v0)

SYSTEM:
Ты аналитик локального развития. На входе — текст «Стратегії розвитку громади»
(Украина). Извлеки строго факты из документа, не додумывай. Верни JSON по схеме.
Если поля нет в документе — null. Секторы выбирай ТОЛЬКО из controlled vocabulary
(список ниже); если сектор не подходит ни к одному — добавь в поле `sectors_new`.

USER (шаблон):
{
  "hromada_name": "...",
  "katottg": "...",
  "goals": ["...", "..."],            // 3–5 дословно/сжато
  "sectors": ["Енергетика (ВДЕ)"],    // из vocabulary
  "sectors_new": [],                  // кандидаты вне словаря
  "projects": [{"name":"...","sector":"...","status":"planned|ongoing"}],
  "strengths": ["..."],
  "challenges": ["..."],
  "partners_mentioned": ["..."],
  "mss_agreements": ["..."],
  "strategy_period": "2021-2027",
  "confidence_notes": "что было неоднозначно"
}

CONTROLLED VOCABULARY: <inject sector list>

## Collaboration analysis (Фаза 3)

Edge types:
1. shared-priority — cosine(goals_embedding) high OR sector overlap ≥2 → joint grant / procurement / peer-exchange
2. complementary — strength(A) matches challenge(B) via rule table
3. geo-cluster — соседние (adjacency by oblast/rayon) + sector overlap → МСС candidate
Layer 2 (громада↔W3I): match громада sectors/goals vs W3I services, RxC, Lab themes, донори.
Render into react-force-graph; each edge carries a "why" explanation string.

## Verified sources (confirmed live 2026-07-21)

- **data.gov.ua CKAN API** — works. `package_search?q=стратегія+розвитку+громади` → 123 datasets. Endpoint: `https://data.gov.ua/api/3/action/package_search`. License CC-BY 4.0.
- **DREAM public API** — works. Base `https://public-api.dream.gov.ua`, endpoint `/marketplace/public/dream/ideas` returns live project records (JSON, id/code/timestamps). Full schema: https://open-contracting.github.io/dream-api-docs/ (raw spec at github raw openapi.yaml). Confirmed ~87% hromada coverage per secondary source (unverified count, but API itself is real and live).
- **MCC (МСС) registry** — dataset `912c1ea4-38ea-4648-8306-59fc1df8b51b` on data.gov.ua, XLSX format, no API beyond CKAN metadata — download the file directly.
- No centralized machine-readable strategy-text repository exists (Мінрозвитку's own catalogue has none) — data.gov.ua CKAN search is the best aggregator, but full coverage requires supplementing with individual hromada websites.

## PoC extraction run — Ніжинська громада (real strategy, 143pp PDF)

Downloaded via CKAN resource link, extracted text with `pypdf`, ran the v0 extraction prompt manually against the real "Стратегічні цілі" section (pages 59–78).
Result: [poc-extraction.json](poc-extraction.json)

Key confirmations:
- Document structure matches the hypothesized state template exactly: Профіль громади → SWOT → Стратегічне бачення → Цілі (стратегічні → оперативні → завдання → заходи). This means the extraction prompt can rely on structural anchors ("СТРАТЕГІЧНА ЦІЛЬ N", "Оперативна ціль N.M") instead of freeform parsing.
- Found an EXPLICIT inter-municipal cooperation signal inside the text itself (task 3.5.3: "Кооперація з іншими громадами у спільному вирішенні проблеми розчищення річки Остер") — hromadas sometimes state collaboration intent directly, which the extraction prompt should capture even without a formal МСС agreement existing yet. This is a real-world case for the "shared-priority becomes explicit ask" edge type.
- Sector vocabulary needed 2 additions after just 1 document (Просторове планування/урбаністика, Е-врядування) — confirms vocabulary will keep growing through the pilot; the `sectors_new` escape valve in the prompt works as intended.

## Open questions still unresolved
- U-LEAD/DESPRO/АМУ internal databases — not confirmed to exist publicly; likely internal-only (donor-facing), worth a direct outreach ask rather than more searching.
- DREAM's exact hromada-coverage % and whether `ideas` endpoint carries geographic/sector metadata sufficient for matching — needs one more live pull with a populated project record (the sample above only returned internal IDs, not full project bodies).
