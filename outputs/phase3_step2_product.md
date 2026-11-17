# SQL Interview Prep Workbook for Junior Analysts

A practical PDF workbook for Junior and aspiring data analysts preparing for SQL interviews, especially in Egypt and the wider MENA region. Made by Mariam.

## Contents
1. Get oriented: what good sql interview prep looks like
2. Step-by-step method for sql interview prep
3. Worked example
4. Checklists and worksheet

## Module 1: Get oriented: what good sql interview prep looks like

Preparing for a SQL interview means knowing what interviewers expect and avoiding common pitfalls. This module helps you understand the structure of real SQL interviews and how to practice effectively.

1. Review job postings from companies in Egypt and the MENA region (e.g., from LinkedIn (unverified link removed) or Wuzzuf (unverified link removed)) to identify common SQL skills required.
2. Focus on core SQL operations: `SELECT`, `WHERE`, `GROUP BY`, `HAVING`, `JOIN`, and `ORDER BY`. Use only standard SQL syntax compatible with SQLite.
3. Practice writing queries that solve real business questions—like counting users by region or finding top-performing products—using sample datasets.
4. Test each query in a local SQLite environment or online tool like DB Fiddle (unverified link removed). Verify results match expected outcomes.
5. Time yourself: aim to write and test a query in under 10 minutes.
6. Review your mistakes and rework them without looking at answers first.

**Worked Example**:
*Problem*: Find the number of unique customers who made purchases in Cairo in 2023.
*Query*:
```sql
SELECT COUNT(DISTINCT customer_id)
FROM sales
WHERE city = 'Cairo'
  AND order_date BETWEEN '2023-01-01' AND '2023-12-31';
```

**Checklist**
- [ ] Used only standard SQL
- [ ] Tested query in SQLite
- [ ] Verified output matches expected result
- [ ] Practiced under time limit
- [ ] Reviewed mistakes without copying answers

**Common mistakes**
- Using non-standard syntax (e.g., `LIMIT 10` in some systems, but not always supported)
- Forgetting `DISTINCT` when counting unique values
- Misplacing `WHERE` vs `HAVING`
- Assuming all date formats are the same across datasets
- Skipping test runs and relying on intuition

## Module 2: Step-by-step method for sql interview prep

Start your SQL interview prep with a clear, repeatable method. This approach works for junior analysts in Egypt and the wider MENA region. Use real interview questions from job postings on platforms like LinkedIn and Wuzzuf. Focus on standard SQL that runs in SQLite.

1. **Find 5 real SQL interview questions** from job posts on LinkedIn or Wuzzuf. Look for roles like “Junior Data Analyst” or “Data Analyst Intern.”
2. **Break each question into parts**. Identify the table(s), required columns, filters (WHERE), grouping (GROUP BY), and sorting (ORDER BY).
3. **Write the query step by step**. Start with SELECT, then add FROM, then WHERE, then GROUP BY, then ORDER BY. Test each step in SQLite.
4. **Check your answer**. Run it in SQLite. Verify it returns expected results. If not, fix one part at a time.
5. **Repeat with 3 more questions**. Use different tables and scenarios. Practice until you can write a query in under 10 minutes.
6. **Review your mistakes**. Keep a log of errors (e.g., missing commas, wrong column names). Revisit them weekly.

*Worked example:*
Question: “Find the top 3 cities with the most active users in the last 30 days.”
Steps:
- SELECT city, COUNT(*)
- FROM users
- WHERE last_login >= DATE('now', '-30 days')
- GROUP BY city
- ORDER BY COUNT(*) DESC
- LIMIT 3

Checklist:
- [ ] Found 5 real questions
- [ ] Identified table and columns
- [ ] Wrote query step by step
- [ ] Tested in SQLite
- [ ] Fixed errors
- [ ] Practiced 3 more questions

Common mistakes:
- Using non-standard SQL (e.g., LIMIT in MySQL without LIMIT)
- Forgetting to GROUP BY when using aggregate functions
- Misplacing WHERE and HAVING
- Not testing in SQLite before claiming it works

## Module 3: Worked example

This module walks you through solving a full problem step by step using standard SQL in SQLite.

1. **Read the question carefully**
   Identify the goal: What data are you retrieving? What conditions apply?
   Example: “Find the top 3 cities by total sales in the last 30 days.”

2. **List the required columns**
   Write down exactly which columns you need in the output (e.g., `city`, `total_sales`).

3. **Filter the data**
   Use `WHERE` to limit rows by date (`date >= date('now', '-30 days')`) and other conditions.

4. **Group and aggregate**
   Use `GROUP BY` on the city column. Apply `SUM()` to calculate total sales per city.

5. **Sort and limit results**
   Use `ORDER BY total_sales DESC` and `LIMIT 3` to get the top 3.

6. **Test your query**
   Run it in SQLite. Check for syntax errors and verify output matches expectations.

**Worked Example**
Given a table `sales` with columns: `id`, `city`, `amount`, `date`.
Query:
```sql
SELECT city, SUM(amount) AS total_sales
FROM sales
WHERE date >= date('now', '-30 days')
GROUP BY city
ORDER BY total_sales DESC
LIMIT 3;
```

**Checklist**
- [ ] Query uses standard SQL (SQLite-compatible)
- [ ] All column names match the table
- [ ] `WHERE` filters only recent data
- [ ] `GROUP BY` matches the selected non-aggregated column
- [ ] `ORDER BY` sorts by total sales descending
- [ ] `LIMIT 3` restricts output to top 3 results

**Common mistakes**
- Forgetting `GROUP BY` when using `SUM()`
- Using `ORDER BY` on a column not in the `SELECT` list
- Applying `LIMIT` before `ORDER BY`
- Using incorrect date syntax (e.g., `NOW()` instead of `date('now', '-30 days')`)

## Module 4: Checklists and worksheet

This module helps you practice SQL interview questions using real-world templates. Use these checklists and worksheets to test your skills before interviews. The examples use standard SQL that works in SQLite.

1. Open a SQLite database or use an online tool like DB Fiddle.
2. Copy the sample dataset provided (e.g., `sales`, `employees`, `products`) into your environment.
3. Read the interview-style question carefully. Identify the required output (e.g., “list all customers with orders over $100”).
4. Write your SQL query step by step:
   - Start with `SELECT`
   - Add `FROM` with the correct table
   - Use `WHERE` for filtering
   - Use `GROUP BY` and `HAVING` if needed
   - Order results with `ORDER BY`
5. Run your query and check if the output matches the expected result.
6. Refactor your query to make it cleaner and more efficient.

**Worked Example**:
*Question*: Find the total sales per product category, but only for categories with more than 5 orders.
*Query*:
```sql
SELECT
  category,
  SUM(sales_amount) AS total_sales
FROM sales
GROUP BY category
HAVING COUNT(*) > 5
ORDER BY total_sales DESC;
```

**Checklist**
- [ ] Dataset loaded correctly
- [ ] Query uses standard SQL syntax
- [ ] All required columns are selected
- [ ] Filters are applied with `WHERE` or `HAVING`
- [ ] Results are ordered as needed
- [ ] Query runs without errors

**Common mistakes**
- Using `WHERE` instead of `HAVING` for grouped conditions
- Forgetting `GROUP BY` when using aggregate functions
- Typing column names incorrectly (e.g., `sales_amount` vs `salesamount`)
- Not testing the query with sample data before finalizing

## A note on results

This product gives you a method and templates. Your results depend on your situation and effort; nothing here is a promise of any outcome.
Claim check: 0 unsourced claim(s) labelled ASSUMPTION, 3 link(s) not found in the fetched evidence removed.
