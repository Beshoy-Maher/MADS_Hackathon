# SQL Interview Prep Workbook for Junior Analysts

A practical PDF workbook for Junior and aspiring data analysts preparing for SQL interviews, especially in Egypt and the wider MENA region. Made by Mariam.

## Contents
1. Get oriented: what good sql interview prep looks like
2. Step-by-step method for sql interview prep
3. Worked example
4. Checklists and worksheet

## Module 1: Get oriented: what good sql interview prep looks like

Preparing for a SQL interview means showing you can write clean, correct queries that solve real data problems. This module helps you understand what good prep looks like—so you avoid common pitfalls.

1. **Know the interview format**: Most junior analyst interviews include 2–3 SQL questions (ASSUMPTION) You’ll write queries on a whiteboard or in an online editor. Time is limited, so focus on clarity and correctness.

2. **Use standard SQL**: Stick to basic syntax like `SELECT`, `FROM`, `WHERE`, `GROUP BY`, `HAVING`, and `JOIN`. Avoid database-specific features (e.g., `LIMIT` in PostgreSQL vs. `LIMIT` in SQLite—use only what works in SQLite).

3. **Start with the question**: Read the prompt carefully. Identify the goal (e.g., “Find the top 3 customers by revenue”) and the data source (e.g., `sales` table).

4. **Write step-by-step**: Break the query into parts. First, pick the columns. Then filter with `WHERE`. Group with `GROUP BY` if needed. Order results with `ORDER BY`.

5. **Test your logic**: Run your query in SQLite. Check for syntax errors and logical flaws. For example, did you include `GROUP BY` when using an aggregate like `SUM()`?

6. **Review for clarity**: Use aliases (`AS`) to name columns clearly. Avoid `SELECT *`. Only include needed data.

**Worked example**:
*Goal: Find total sales per customer, ordered by highest sales first.*
```sql
SELECT customer_id, SUM(amount) AS total_sales
FROM sales
GROUP BY customer_id
ORDER BY total_sales DESC;
```

**Checklist**
- [ ] Query uses only standard SQL
- [ ] All column names are explicit
- [ ] `GROUP BY` is used with aggregates
- [ ] Results are ordered as expected
- [ ] No `SELECT *` used

**Common mistakes**
- Forgetting `GROUP BY` when using `SUM()`
- Using `ORDER BY` without `GROUP BY`
- Writing `LIMIT` without `ORDER BY`
- Not testing the query in a real environment

## Module 2: Step-by-step method for sql interview prep

Start your SQL interview prep with a clear, repeatable method. This approach works for any interview question, whether you're in Cairo, Riyadh, or Dubai. Use it every time.

1. **Read the question slowly.** Identify the key request: What data do you need? What filters apply? What output format is expected?
2. **List the required columns.** Write them down before writing code. Example: `user_id`, `order_date`, `total_amount`.
3. **Identify the tables involved.** Check the schema. Use `PRAGMA table_info(table_name)` in SQLite to see column names and types.
4. **Build the query step by step.** Start with `SELECT * FROM table` to check data. Then add `WHERE` filters, `JOIN` conditions, and `GROUP BY` clauses.
5. **Test each step.** Run the query after each change. Fix errors early.
6. **Review the final output.** Does it match the expected result? Are all filters applied? Are duplicates removed?

**Worked example:**
*Question:* Find the total sales per customer in January 2023.
- Tables: `orders` (order_id, customer_id, order_date, amount), `customers` (customer_id, name)
- Steps:
  - `SELECT customer_id, SUM(amount) FROM orders WHERE order_date LIKE '2023-01-%' GROUP BY customer_id`
  - Join with `customers` to get names: `JOIN customers ON orders.customer_id = customers.customer_id`
  - Final: `SELECT c.name, SUM(o.amount) FROM orders o JOIN customers c ON o.customer_id = c.customer_id WHERE o.order_date LIKE '2023-01-%' GROUP BY c.name`

- [ ] Read the question fully
- [ ] List required columns
- [ ] Identify tables and relationships
- [ ] Build query step by step
- [ ] Test each part
- [ ] Verify output matches the goal

**Common mistakes:**
- Skipping `GROUP BY` when using `SUM()`
- Using `=` instead of `LIKE '2023-01-%'` for date filtering
- Forgetting to join tables when needed
- Not testing intermediate steps
- Assuming data is clean (e.g., missing values, typos)

## Module 3: Worked example

This module walks you through solving a full problem step by step, using actual data patterns seen in job interviews.

1. Read the question carefully. Identify the key tables and required output.
2. List the columns you need from each table. Use `SELECT` with only necessary columns.
3. Join tables using `JOIN` on matching keys (e.g., `user_id`, `order_id`). Use `INNER JOIN` unless the question says otherwise.
4. Apply filters with `WHERE` to narrow results. Use `AND` for multiple conditions.
5. Group data with `GROUP BY` if you need counts, sums, or averages.
6. Order results with `ORDER BY` if required. Use `LIMIT` only if the question asks for top N.

**Worked Example:**
*Find the top 5 cities by total order value in January 2024, where each order has a value > 100.*

```sql
SELECT
    c.city,
    SUM(o.order_value) AS total_value
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
WHERE o.order_date >= '2024-01-01'
  AND o.order_date < '2024-02-01'
  AND o.order_value > 100
GROUP BY c.city
ORDER BY total_value DESC
LIMIT 5;
```

**Checklist**
- [ ] Used `INNER JOIN` for related tables
- [ ] Selected only needed columns
- [ ] Filtered by date range using `>=` and `<`
- [ ] Applied `GROUP BY` after `WHERE`
- [ ] Ordered by total value descending
- [ ] Used `LIMIT 5` as required

**Common mistakes**
- Using `LIKE` or `IN` when `=` or `BETWEEN` is better
- Placing `GROUP BY` before `WHERE`
- Forgetting to include `GROUP BY` when using aggregate functions
- Using `ORDER BY` without `LIMIT` when only top results are needed
- Joining on incorrect or missing keys (e.g., `user_id` vs `customer_id`)

## Module 4: Checklists and worksheet

This module helps you practice SQL interview questions using real-world templates. Use these checklists and worksheets to test your skills before interviews. All examples use standard SQL that works in SQLite.

1. Open a SQLite database or use an online tool like DB Fiddle.
2. Copy the sample dataset (e.g., `sales`, `employees`, `products`) provided in the workbook.
3. Write your query step by step using the template:
   - Start with `SELECT`
   - Add `FROM` and table name
   - Use `WHERE` for filters
   - Use `GROUP BY` if aggregating
   - Use `ORDER BY` to sort results
4. Run your query and check if it returns expected rows and columns.
5. Compare your result with the solution in the answer key.
6. Rewrite the query using a different approach (e.g., use `HAVING` instead of `WHERE` if filtering groups).

**Worked Example:**
*Find the total sales per region, showing only regions with sales over 1000.*
```sql
SELECT region, SUM(sales) AS total_sales
FROM sales
GROUP BY region
HAVING SUM(sales) > 1000;
```

**Checklist:**
- [ ] Query uses `SELECT`, `FROM`, and `GROUP BY`
- [ ] `HAVING` is used instead of `WHERE` for grouped conditions
- [ ] Column names match the sample data
- [ ] No syntax errors (e.g., missing commas or semicolons)
- [ ] Result matches expected output

**Common mistakes:**
- Using `WHERE` instead of `HAVING` when filtering grouped data
- Forgetting `GROUP BY` when using aggregate functions like `SUM()`
- Typo in table or column names
- Missing parentheses or quotes in string filters
- Not testing with sample data before finalizing

## A note on results

This product gives you a method and templates. Your results depend on your situation and effort; nothing here is a promise of any outcome.