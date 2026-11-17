# Phase 1 Step 2: Scorecard

_Plain code, no model._

| Metric | Value |
|---|---|
| sources | 0 |
| voices | 0 |
| recent_voices | 0 |
| engagement | 0 |
| demand | 0 |
| fit | 12 |
| skill_hits | [] |
| competitors | 0 |
| max_competitor_stars | 0 |
| competition_level | 0 |

## Formulas
- **demand**: 6 x recent voices + 2 x older voices + min(20, recent engagement / 10), max 100
- **fit**: 40 if founder is a target user + 10 per matching skill (max 30) + 3 x hours/week (max 30)
- **competition_level**: 20 x log10(top competitor stars + 1)
