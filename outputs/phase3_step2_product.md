# SQL Interview Prep Workbook for Junior Analysts

A practical PDF workbook for Junior and aspiring data analysts preparing for SQL interviews, especially in Egypt and the wider MENA region. Made by Mariam.

## Contents
1. Get oriented: what good sql interview prep looks like
2. Step-by-step method for sql interview prep
3. Worked example
4. Checklists and worksheet

## Module 1: Get oriented: what good sql interview prep looks like

Preparing for a SQL interview means showing you can write correct, readable queries that solve real problems. This module helps you understand what interviewers look for and how to avoid common errors.

1. Know the typical interview format: Most junior analyst interviews include 1–2 coding questions on a shared screen or whiteboard. ASSUMPTION You’ll be asked to write SQL to answer a business question using sample data.

2. Use standard SQL: Stick to basic syntax that works in SQLite (e.g., `SELECT`, `FROM`, `WHERE`, `GROUP BY`, `ORDER BY`). Avoid database-specific features like `LIMIT` with offset or window functions unless asked.

3. Read the question carefully: Identify the table(s), columns, and what you’re being asked to calculate (e.g., count, average, filter). Highlight key terms like “active users” or “last 30 days.”

4. Write step-by-step: Break the query into parts. First, select the data. Then filter. Then group or aggregate. Test each step as you go.

5. Check for correctness: Run your query in a tool like DB Fiddle or SQLite online. Ensure it returns expected results and handles edge cases (e.g., NULL values).

6. Explain your logic: Even if the query is correct, interviewers want to hear your thinking. Say why you chose a `JOIN`, or how you handled duplicates.

**Worked example**:
*Question:* Find the number of unique users who made a purchase in January 2024.
*Table:* `sales` (columns: `user_id`, `purchase_date`)
*Query:*
```sql
SELECT COUNT(DISTINCT user_id)
FROM sales
WHERE purchase_date >= '2024-01-01'
  AND purchase_date < '2024-02-01';
```

- [ ] Read the question fully
- [ ] Use only standard SQL
- [ ] Test with sample data
- [ ] Handle NULLs and edge cases
- [ ] Explain your approach

**Common mistakes**:
- Using `LIKE` when `=` is enough
- Forgetting `DISTINCT` when counting unique values
- Assuming data is clean (e.g., no NULLs)
- Writing complex queries without testing step-by-step

## Module 2: Step-by-step method for sql interview prep

Start with a clear plan. Break SQL interview prep into repeatable steps. This method works for standard SQL in SQLite, which is widely supported.

1. **List common SQL interview topics**
   Focus on: `SELECT`, `WHERE`, `GROUP BY`, `HAVING`, `JOIN`, `UNION`, `ORDER BY`, and basic window functions. Use free resources like SQLZoo (unverified link removed) or Mode Analytics SQL Tutorial (unverified link removed) for practice.

2. **Pick one topic per day**
   Choose one topic. Write 3–5 practice queries using real data. Use sample datasets like `sales`, `employees`, or `orders` from SQLite.

3. **Write queries by hand first**
   Type each query without copying. This builds memory and logic. Test it in a SQLite environment (e.g., DB Fiddle or SQLite Online).

4. **Review and refactor**
   After running, check for errors. Simplify complex `JOIN`s. Use aliases for clarity. Avoid `SELECT *`.

5. **Time yourself**
   Set a 10-minute limit per query. Simulate interview pressure. Track speed and accuracy.

6. **Document your progress**
   Keep a log: date, topic, query, errors, fixes. Review weekly.

**Worked Example**
Topic: `JOIN`
Dataset: `employees` (id, name, dept_id), `departments` (id, name)
Goal: List all employees with their department names.
Query:
```sql
SELECT e.name, d.name AS dept_name
FROM employees e
JOIN departments d ON e.dept_id = d.id;
```

**Checklist**
- [ ] Used standard SQL (no vendor-specific syntax)
- [ ] Tested in SQLite
- [ ] Wrote queries by hand
- [ ] Used aliases for tables
- [ ] Avoided `SELECT *`
- [ ] Timed each query

**Common mistakes**
- Forgetting `ON` in `JOIN`
- Using `WHERE` instead of `ON` for join conditions
- Mixing up `HAVING` and `WHERE`
- Not aliasing tables in complex queries
- Copying code instead of typing it

## Module 3: Worked example

This module shows how to solve a real SQL interview question step by step. You’ll learn how to break down a problem, write clean queries, and think through edge cases—just like in a real interview.

1. **Read the question carefully**
   Identify the goal: what data are you retrieving? What conditions apply?
   Example: “Find the top 3 customers by total order value in 2023.”

2. **List the required columns and filters**
   Decide what to select: customer name, total order value, etc.
   Note: Only include what the question asks for.

3. **Use `GROUP BY` for aggregation**
   Group by customer to sum their order values.
   Use `SUM()` with `WHERE` to filter by year.

4. **Sort and limit results**
   Use `ORDER BY SUM(value) DESC` to rank by highest total.
   Add `LIMIT 3` to return only the top 3.

5. **Test your query**
   Run it in SQLite. Check for syntax errors.
   Verify output matches expected logic.

6. **Review for edge cases**
   Consider: Are there null values? What if two customers tie for 3rd place?
   Adjust if needed—e.g., use `LIMIT 3` only if ties are acceptable.

**Worked Example**
Given a table `orders` with columns `customer_id`, `order_date`, and `amount`:
```sql
SELECT customer_id, SUM(amount) AS total_value
FROM orders
WHERE order_date LIKE '2023%'
GROUP BY customer_id
ORDER BY total_value DESC
LIMIT 3;
```

**Checklist**
- [ ] Query uses `SUM()` for total value
- [ ] `GROUP BY` matches the selected non-aggregated column
- [ ] `WHERE` filters by year 2023
- [ ] Results sorted descending
- [ ] `LIMIT 3` applied
- [ ] No unnecessary columns selected

**Common mistakes**
- Forgetting `GROUP BY` when using `SUM()`
- Using `ORDER BY` without `GROUP BY`
- Applying `LIMIT` before `ORDER BY`
- Including extra columns not in the question
- Not filtering by year before aggregation

## Module 4: Checklists and worksheet

This module helps you practice SQL interview questions using real-world templates. Use these checklists and worksheets to test your skills before interviews. All examples use standard SQL that works in SQLite.

1. Open a SQLite database or use an online tool like DB Fiddle.
2. Copy the sample dataset provided (e.g., `sales`, `employees`, `orders`) into your environment.
3. Read the question carefully. Identify the required output (e.g., “list all employees in Cairo”).
4. Write your query step by step:
   - Start with `SELECT`
   - Add `FROM` with the correct table
   - Use `WHERE` to filter data
   - Use `ORDER BY` if needed
   - Test each part before finalizing
5. Run your query and check results against expected output.
6. Save your query in a text file with a `.sql` extension.

**Worked Example:**
*Question:* Find all employees in the "Sales" department, sorted by hire date (newest first).
*Query:*
```sql
SELECT name, hire_date
FROM employees
WHERE department = 'Sales'
ORDER BY hire_date DESC;
```

**Checklist:**
- [ ] Dataset loaded correctly
- [ ] Query uses standard SQL
- [ ] `SELECT` lists only needed columns
- [ ] `WHERE` filters match the question
- [ ] `ORDER BY` is used if sorting is required
- [ ] Query runs without errors in SQLite

**Common mistakes:**
- Using `=` instead of `LIKE` for partial matches
- Forgetting to escape quotes in strings
- Missing `FROM` clause
- Using `ORDER BY` without `SELECT`
- Not testing small parts of the query step by step

## A note on results

This product gives you a method and templates. Your results depend on your situation and effort; nothing here is a promise of any outcome.
Claim check: 0 unsourced claim(s) labelled ASSUMPTION, 2 link(s) not found in the fetched evidence removed.
