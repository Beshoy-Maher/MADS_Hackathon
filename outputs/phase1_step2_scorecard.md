# Phase 1, step 2: Scorecard (idea vs. alternatives)

| Candidate | Relevant sources | Independent voices | Platforms | Pain posts | Demand | Pay signals | Competition | Founder fit | **Total** |
|---|---|---|---|---|---|---|---|---|---|
| Founder idea: SQL Interview Prep Workbook for Junior Analysts | 25 | 11 | 2 | 5 | 89.6 | 50.0 | 100.0 | 100.0 | **73.4** |
| Alt 1: Daily SQL Challenges for Aspiring Analysts | 14 | 5 | 2 | 3 | 48.0 | 0.0 | 0.0 | 95.5 | **62.8** |
| Alt 2: SQL Query Debugging Guide for Beginners | 9 | 8 | 2 | 4 | 47.6 | 0.0 | 0.0 | 97.8 | **63.4** |

## Why

- **SQL Interview Prep Workbook for Junior Analysts**: Mariam’s SQL and mentoring skills directly match the workbook format. (skill match 1.0)
- **Daily SQL Challenges for Aspiring Analysts**: Daily challenges require content scheduling and engagement—less aligned with her skills. (skill match 0.9)
- **SQL Query Debugging Guide for Beginners**: Her debugging experience and technical writing cover the guide’s needs well. (skill match 0.95)

## Evidence behind each candidate

### Founder idea: SQL Interview Prep Workbook for Junior Analysts

People describing the problem (11):
- [Ask HN: Are there any good resources to practice SQL?](https://news.ycombinator.com/item?id=7357954) (hackernews, 2014-03-07, 1 pts/stars, 2 comments)
- [Ask HN: SQL interview in 2 weeks, how to best prepare?](https://news.ycombinator.com/item?id=24659490) (hackernews, 2020-10-02, 1 pts/stars, 1 comments)
- [Show HN: DataLemur – Ace the SQL Interview!](https://news.ycombinator.com/item?id=32584550) (hackernews, 2022-08-24, 16 pts/stars, 5 comments)
- [SQL Interview Questions for Aspiring Data Scientist – The Histogram](https://news.ycombinator.com/item?id=18389273) (hackernews, 2018-11-06, 6 pts/stars, 0 comments)

Existing solutions (14):
- [Repository sanketrs/sql-interview-preparation-questions-with-answers: Designed as a comprehensive resource for](https://github.com/sanketrs/sql-interview-preparation-questions-with-answers) (github, 2024-12-29, 24 pts/stars, 0 comments)
- [Repository Aafreen29/SQL-Interview-Prep-Question: This repository is for everyone who is preparing for Data Sc](https://github.com/Aafreen29/SQL-Interview-Prep-Question) (github, 2019-05-18, 475 pts/stars, 6 comments)
- [Repository rohanmistry231/SQL-Interview-Preparation: A comprehensive resource for SQL interview preparation, f](https://github.com/rohanmistry231/SQL-Interview-Preparation) (github, 2025-04-15, 42 pts/stars, 0 comments)
- [Repository shawlu95/Beyond-LeetCode-SQL: Analysis of SQL Leetcode and classic interview questions, common pitf](https://github.com/shawlu95/Beyond-LeetCode-SQL) (github, 2019-03-02, 1345 pts/stars, 2 comments)

### Alt 1: Daily SQL Challenges for Aspiring Analysts

People describing the problem (6):
- [Issue: Security: daily_challenges grants the anon role full write access and has no RLS](https://github.com/AnmolS99/voyage/issues/151) (github, 2026-11-11, 0 pts/stars, 0 comments)
- [Issue: SkateQuest sessions, challenges and media regression QA](https://github.com/treesus6/SkateQuest-Mobile/issues/344) (github, 2026-10-22, 0 pts/stars, 15 comments)
- [Show HN: Vertis – The simplest way to orchestrate SQL pipelines](https://news.ycombinator.com/item?id=36763504) (hackernews, 2023-07-17, 2 pts/stars, 0 comments)
- [State of the art for Database CI/CD multi-customer with complex config](https://news.ycombinator.com/item?id=29305709) (hackernews, 2021-11-22, 1 pts/stars, 0 comments)

Existing solutions (8):
- [Repository Srimathy-S/21Days-SQL_Challenge-by_IDC: A day-by-day documentation of my 21 Days Journey to master ](https://github.com/Srimathy-S/21Days-SQL_Challenge-by_IDC) (github, 2025-11-04, 2 pts/stars, 0 comments)
- [Repository mahirtantod/30-Days-of-SQL:  📊 30 Days of SQL is a daily challenge guiding you from SQL basics to a](https://github.com/mahirtantod/30-Days-of-SQL) (github, 2024-12-27, 70 pts/stars, 0 comments)
- [Repository Prakhar-002/LEETCODE: 📜 LeetCode Solution Hub 🔥 | Get all solutions 🧩 for daily challenges and spec](https://github.com/Prakhar-002/LEETCODE) (github, 2024-05-24, 5 pts/stars, 0 comments)
- [Repository pzoladkiewicz/SQL-Prep-Daily-Challenges: ](https://github.com/pzoladkiewicz/SQL-Prep-Daily-Challenges) (github, 2017-04-27, 4 pts/stars, 0 comments)

### Alt 2: SQL Query Debugging Guide for Beginners

People describing the problem (8):
- [Show HN: Beyond "chat with your database" – agentic data exploration](https://news.ycombinator.com/item?id=49910856) (hackernews, 2026-09-30, 2 pts/stars, 0 comments)
- [Ask HN: SQL Query Generators?](https://news.ycombinator.com/item?id=25324429) (hackernews, 2020-12-06, 2 pts/stars, 0 comments)
- [Issue: [Enhancement]: aws_cloudwatch_query_definition: support query_language and parameters](https://github.com/hashicorp/terraform-provider-aws/issues/50937) (github, 2026-11-12, 1 pts/stars, 1 comments)
- [Show HN: Web-based SQL Server Query Plan Viewer](https://news.ycombinator.com/item?id=7382527) (hackernews, 2014-03-11, 1 pts/stars, 0 comments)

Existing solutions (1):
- [Repository CaptainEFFF/burger: # Node Express Handlebars  ### Overview  In this assignment, you'll create a bu](https://github.com/CaptainEFFF/burger) (github, 2019-06-27, 4 pts/stars, 4 comments)

## How the scores are calculated

demand = 0.5 x engagement(log-scaled points/stars/comments; posts older than 2 years count half, older than 5 years a quarter) + 10 x min(pain posts, 5); independent voices = distinct authors or communities among discussion posts (repositories excluded); willingness_to_pay = 25 x posts mentioning paying/price (max 100); competition = 20 x existing solutions with 500+ stars/points (max 100); founder_fit = 45 x skill match + 30 x min(1, hours/8) + 25 x min(1, budget/$50); total = 0.40 demand + 0.15 willingness_to_pay + 0.30 founder_fit + 0.15 x (100 - competition)

Founder fit uses the brief: skills, 10 hours/week, $50 budget. Engagement counts are public numbers from the linked sources; they show interest, not guaranteed buyers (ASSUMPTION that interest relates to demand).

---
Generated by the pipeline. Model: `qwen3:30b-a3b-instruct-2507-q4_K_M` (local open-weight model). Cost: $0.00.
Sources cited: 21. Claims without a source are marked ASSUMPTION.
Claim check: every statistic or citation above links to fetched evidence.
