# Phase 1 Step 2: Scorecard

_Plain code, no model._

| Metric | Value |
|---|---|
| sources | 48 |
| voices | 29 |
| recent_voices | 8 |
| engagement | 762 |
| demand | 100 |
| fit | 90 |
| skill_hits | ['release', 'changelog'] |
| competitors | 19 |
| max_competitor_stars | 24180 |
| competition_level | 88 |

## Formulas
- **demand**: 6 x recent voices + 2 x older voices + min(20, recent engagement / 10), max 100
- **fit**: 40 if founder is a target user + 10 per matching skill (max 30) + 3 x hours/week (max 30)
- **competition_level**: 20 x log10(top competitor stars + 1)
