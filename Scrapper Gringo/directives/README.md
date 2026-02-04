# Scrapper Gringo – Directives

Diese Directives definieren die SOPs (Standard Operating Procedures) für Scrapper Gringo.

## Verfügbare Directives

| Directive | Beschreibung | Script |
|-----------|-------------|--------|
| `scrape_url.md` | Einzelne URL scrapen | `scrape_url.py` |
| `deep_scrape.md` | Zweistufiges Scraping (Liste → Details) | `deep_scrape.py` |
| `scrape_gmb_listings.md` | Google Places API | `scrape_gmb.py` |
| `enrich_leads.md` | Lead-Anreicherung | `enrich_leads.py` |
| `export_to_sheets.md` | Google Sheets Export | `export_to_sheets.py` |

## DOE Workflow

```
┌────────────────────────────────────────────────────────────────┐
│                        DOE LOOP                                │
├────────────────────────────────────────────────────────────────┤
│  DIRECTIVE     →     ORCHESTRATION     →     EXECUTION         │
│  (directives/)       (AI Agent)              (execution/)      │
│                                                                │
│  Was soll               Wie wird            Deterministische   │
│  getan werden?          entschieden?        Scripts führen aus │
└────────────────────────────────────────────────────────────────┘
```

## Nutzung

Die AI liest zuerst die relevante Directive, dann führt sie das entsprechende Script aus.

Beispiel:
1. User: "Scrape alle Tutorials von snipki.de"
2. AI liest: `deep_scrape.md`
3. AI führt aus: `python execution/deep_scrape.py --url "..." --stage2 "..."`
4. Ergebnis: JSON in `.tmp/`, optional Sheets-Export

## Living Documents

Directives werden kontinuierlich verbessert:
- Neue Learnings dokumentiert
- Edge Cases hinzugefügt
- Fehlerbehandlung aktualisiert

---

*Letzte Aktualisierung: 2026-02-04*
