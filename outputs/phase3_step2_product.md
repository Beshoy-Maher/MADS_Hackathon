# SQL Interview Prep Workbook for Junior Analysts

A practical PDF workbook for Junior and aspiring data analysts preparing for SQL interviews, especially in Egypt and the wider MENA region. Made by Mariam.

## Contents
1. Get oriented: what good sql interview prep looks like
2. Step-by-step method for sql interview prep
3. Worked example
4. Checklists and worksheet

## Module 1: Get oriented: what good sql interview prep looks like

Preparing for a SQL interview means knowing what interviewers expect and avoiding common pitfalls. This module helps you start with clarity and focus.

1. **Review job postings from companies in Egypt and the MENA region** (e.g., from LinkedIn, Wuzzuf, or Bayt.com). Look for recurring SQL skills like `SELECT`, `JOIN`, `GROUP BY`, and filtering with `WHERE`.
2. **Use free resources like SQLZoo or Mode Analytics’ SQL tutorial** to confirm you understand basic syntax. Practice writing queries that match the job descriptions.
3. **Avoid memorizing answers**. Instead, learn how to break down questions: identify the goal, data sources, and required operations.
4. **Practice with real-world datasets**. Use sample data like sales records or user activity logs. Write queries that answer typical questions (e.g., “Find the top 5 customers by order count”).
5. **Time your practice**. Simulate interview conditions: 10–15 minutes per question.
6. **Review your queries**. Check for correct syntax, proper table joins, and accurate filtering.

**Worked example**:
*Question*: “List all customers who made more than 3 purchases in 2023.”
*Steps*:
- Use `SELECT customer_id` from `orders`
- Filter with `WHERE order_date BETWEEN '2023-01-01' AND '2023-12-31'`
- Group by `customer_id`
- Use `HAVING COUNT(*) > 3`
- Order by count descending

```sql
SELECT customer_id, COUNT(*) AS order_count
FROM orders
WHERE order_date BETWEEN '2023-01-01' AND '2023-12-31'
GROUP BY customer_id
HAVING COUNT(*) > 3
ORDER BY order_count DESC;
```

- [ ] Reviewed 3 job posts from MENA region
- [ ] Practiced 5 basic queries on SQLZoo
- [ ] Wrote and tested 1 query under time limit
- [ ] Checked syntax and logic in query

**Common mistakes**:
- Using `WHERE` instead of `HAVING` for grouped data
- Forgetting `GROUP BY` when using aggregate functions
- Misplacing parentheses or quotes in date filters

## Module 2: Step-by-step method for sql interview prep

Start with a clear plan. Use this method to prepare for SQL interviews step by step. It works for junior analysts in Egypt and the wider MENA region. Follow these steps to build confidence and clarity.

1. **Pick one SQL topic** – Choose a core skill like `SELECT`, `JOIN`, or `GROUP BY`. Focus on one at a time.
2. **Find a real-world dataset** – Use public data from sources like Kaggle or open data platforms to find datasets. Avoid private or internal data.
3. **Write 3 practice queries** – For each topic, write simple queries using standard SQL. Test them in SQLite. Example: `SELECT name FROM users WHERE age > 25;`
4. **Explain your logic aloud** – Say out loud why you wrote each part. This builds communication skills for interviews.
5. **Review and refactor** – Check if your query is clean. Use `AS` for aliases, avoid `SELECT *`, and order results with `ORDER BY`.
6. **Repeat with a new topic** – Move to the next skill after mastering one. Track progress in a notebook.

**Worked example**:
Topic: `JOIN`
Dataset: Two tables – `employees` (id, name, department_id) and `departments` (id, name).
Query:
```sql
SELECT e.name, d.name AS department
FROM employees e
JOIN departments d ON e.department_id = d.id;
```
This shows employee names and their departments.

- [ ] Chose one SQL topic
- [ ] Found a public dataset
- [ ] Wrote 3 queries
- [ ] Explained each step aloud
- [ ] Refactored for clarity
- [ ] Moved to next topic

**Common mistakes**:
- Using `SELECT *` instead of naming columns
- Forgetting `ON` in `JOIN` clauses
- Not testing queries in SQLite first
- Skipping explanation practice
- Trying to learn too many topics at once

## Module 3: Worked example

This module walks you through solving a real-world SQL interview question step by step. You’ll practice writing queries using standard SQL that works in SQLite. The example is based on common data patterns seen in job postings and company datasets ASSUMPTION.

1. **Understand the question**
   Read the problem carefully. Identify the key data needed: which tables, what conditions, and what output is expected.

2. **List the required columns**
   Decide which columns to select. Only include what’s asked—no extra data.

3. **Apply filtering conditions**
   Use `WHERE` to narrow down rows. Be specific: filter by date, region, or job type if needed.

4. **Group or sort data if required**
   Use `GROUP BY` for counts or summaries. Use `ORDER BY` to sort results by a column.

5. **Test your query**
   Run it in a SQLite environment. Check for syntax errors and logical issues.

6. **Review the output**
   Ensure results match the expected format and answer the question.

**Worked Example**
*Question:* Find the number of data analyst jobs posted in Egypt in 2023, grouped by month, sorted by month.

```sql
SELECT
  strftime('%m', posted_date) AS month,
  COUNT(*) AS job_count
FROM job_postings
WHERE
  country = 'Egypt'
  AND job_title LIKE '%analyst%'
  AND posted_date BETWEEN '2023-01-01' AND '2023-12-31'
GROUP BY month
ORDER BY month;
```

**Checklist**
- [ ] Query uses standard SQL
- [ ] Runs in SQLite
- [ ] Filters by country and job title
- [ ] Groups by month
- [ ] Orders by month
- [ ] Returns only needed columns

**Common mistakes**
- Using `GROUP BY` without `SELECT`ing the grouped column
- Forgetting to filter by year
- Using `LIKE` with `%` without proper context
- Not testing in a real environment before submitting

## Module 4: Checklists and worksheet

This module helps you practice SQL interview questions using real-world templates. You’ll apply what you’ve learned in earlier modules to write queries that solve common analyst tasks. Use these worksheets to test your skills before interviews.

1. Open your SQL environment (like SQLite or a web-based tool).
2. Copy the sample dataset structure below into your database:
   ```sql
   CREATE TABLE sales (
     id INTEGER,
     date DATE,
     region TEXT,
     amount DECIMAL(10,2)
   );
   INSERT INTO sales VALUES
     (1, '2023-01-05', 'Cairo', 120.50),
     (2, '2023-01-06', 'Alexandria', 95.00),
     (3, '2023-01-07', 'Cairo', 200.00);
   ```
3. Read each question in the worksheet. For each, write a query using standard SQL.
4. Run your query and check the output. Compare it to the expected result shown in the answer key.
5. If wrong, revise your query. Focus on syntax, column names, and filtering logic.
6. Save your final version in a file named `sql_interview_worksheet.sql`.

**Worked Example:**
*Question:* Find total sales in Cairo.
*Your Query:*
```sql
SELECT SUM(amount) AS total_cairo_sales
FROM sales
WHERE region = 'Cairo';
```
*Expected Output:* 320.50

**Checklist**
- [ ] Dataset created and loaded
- [ ] Query uses standard SQL (no vendor-specific syntax)
- [ ] All column names match the table exactly
- [ ] `WHERE` clause filters correctly
- [ ] `SUM()` used for totals
- [ ] Query runs without errors

**Common mistakes**
- Typo in column name (e.g., `regin` instead of `region`)
- Missing `FROM` clause
- Using `= 'Cairo'` instead of `= 'Cairo'` (case-sensitive in some systems)
- Forgetting `GROUP BY` when using aggregate functions with non-aggregated columns

## A note on results

This product gives you a method and templates. Your results depend on your situation and effort; nothing here is a promise of any outcome.
Claim check: 0 unsourced claim(s) labelled ASSUMPTION, 2 link(s) not found in the fetched evidence removed.
