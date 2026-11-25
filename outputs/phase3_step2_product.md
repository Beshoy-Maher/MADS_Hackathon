# SQL Interview Prep Workbook for Junior Analysts

A practical PDF workbook for Junior and aspiring data analysts preparing for SQL interviews, especially in Egypt and the wider MENA region. Made by Mariam.

## Contents
1. Get oriented: what good sql interview prep looks like
2. Step-by-step method for sql interview prep
3. Worked example
4. Checklists and worksheet

## Module 1: Get oriented: what good sql interview prep looks like

You’re preparing for SQL interviews as a junior analyst in Egypt or the wider MENA region. Good prep means focusing on real interview patterns, not just memorizing syntax. Many candidates fail because they skip practice with real-world scenarios. This module shows you how to build a solid foundation.

1. Review job postings from companies in Egypt and MENA to identify commonly mentioned SQL skills. Note which SQL skills are mentioned: filtering, grouping, joining, window functions.
2. Use free resources like SQLite.org to practice in a local environment. No cloud setup needed.
3. Focus on standard SQL syntax. Avoid vendor-specific features (e.g., `LIMIT` in MySQL vs. `LIMIT` in SQLite — use only what works in SQLite).
4. Practice with sample datasets from publicly available sources like Kaggle or data.gov.eg, ensuring they are relevant to real-world business scenarios.
5. Time yourself: solve one query in 10 minutes. Use a timer.
6. Review your code: does it return correct results? Is it readable? Can someone else understand it?

**Worked example**:
Given a table `sales` with columns `date`, `region`, `amount`, find total sales per region in January 2023.
```sql
SELECT region, SUM(amount) AS total_sales
FROM sales
WHERE date BETWEEN '2023-01-01' AND '2023-01-31'
GROUP BY region;
```

**Checklist**
- [ ] Used only standard SQL (SQLite-compatible)
- [ ] Tested query on sample data
- [ ] Verified output matches expected result
- [ ] Named columns clearly
- [ ] Avoided unnecessary complexity

**Common mistakes**
- Using `LIMIT` without `ORDER BY` (can return inconsistent results)
- Forgetting `GROUP BY` when using aggregate functions
- Assuming all companies use the same SQL dialect
- Skipping test data validation

## Module 2: Step-by-step method for sql interview prep

Start with one clear goal: practice SQL queries that match real interview questions. Use this method to build confidence and speed.

1. Pick one SQL topic (e.g., `SELECT`, `WHERE`, `GROUP BY`).
2. Find a real interview question from a trusted source (e.g., LeetCode, StrataScratch).
3. Write the query using only standard SQL (no vendor-specific syntax).
4. Test it in SQLite with sample data you create.
5. Check your answer against the expected output.
6. Repeat with a new topic or question.

**Worked example:**
*Question:* Find the total number of orders per customer from a table `orders` with columns `customer_id`, `order_date`, `amount`.
*Step-by-step:*
- `SELECT customer_id, SUM(amount) AS total FROM orders GROUP BY customer_id;`
- Run in SQLite:
  ```sql
  CREATE TABLE orders (customer_id INTEGER, order_date TEXT, amount REAL);
  INSERT INTO orders VALUES (1, '2023-01-01', 100), (1, '2023-01-02', 50), (2, '2023-01-01', 200);
  ```
- Query returns: `customer_id=1, total=150`, `customer_id=2, total=200`.

**Checklist:**
- [ ] Chose one SQL topic
- [ ] Found a real question from a public source
- [ ] Wrote query using only standard SQL
- [ ] Tested in SQLite with sample data
- [ ] Verified output matches expected result
- [ ] Moved to next topic

**Common mistakes:**
- Using non-standard SQL (e.g., `LIMIT 10` in a `SELECT` without `ORDER BY`)
- Forgetting to `GROUP BY` when using `SUM()`
- Not testing with real data
- Copying answers without understanding
- Skipping the verification step

## Module 3: Worked example

This module shows how to solve a real SQL interview question step by step. You’ll learn how to break down a problem, write clean queries, and think like an analyst. The example uses a realistic dataset common in MENA-region companies: employee records with department, salary, and hire date.

1. **Read the question carefully**
   Identify the key request. For example: “Find employees hired in 2023 who earn above the average salary in their department.”

2. **Break the problem into parts**
   - Step 1: Get average salary per department.
   - Step 2: Join this with employee data.
   - Step 3: Filter for hires in 2023 and salaries above department average.

3. **Write the query in stages**
   Start with a subquery to calculate average salary per department. Test it first. Then join it with the main table.

4. **Use standard SQL syntax**
   Use `SELECT`, `FROM`, `JOIN`, `WHERE`, `GROUP BY`, and `HAVING`. Avoid vendor-specific functions.

5. **Test with sample data**
   Run your query in SQLite. Check for syntax errors and logical issues.

6. **Review and simplify**
   Remove unnecessary columns. Use clear aliases. Ensure the output matches the question.

**Worked Example**
Given a table `employees` with columns: `id`, `name`, `department`, `salary`, `hire_date` (format: 'YYYY-MM-DD'):

```sql
SELECT e.name, e.department, e.salary
FROM employees e
JOIN (
  SELECT department, AVG(salary) AS avg_sal
  FROM employees
  GROUP BY department
) dept_avg ON e.department = dept_avg.department
WHERE e.hire_date LIKE '2023-%'
  AND e.salary > dept_avg.avg_sal;
```

**Checklist**
- [ ] Query uses standard SQL
- [ ] All columns referenced exist
- [ ] Date filter uses `LIKE '2023-%'`
- [ ] Subquery calculates average per department
- [ ] Final output matches the question

**Common mistakes**
- Using `WHERE` instead of `JOIN` for averages
- Forgetting to group by department
- Using `HAVING` on non-aggregated columns
- Misreading the date format or using incorrect comparison

## Module 4: Checklists and worksheet

This module helps you practice SQL interview questions using real-world templates. Use these checklists and worksheets to test your skills before an interview. All examples use standard SQL that works in SQLite.

1. Open a SQLite database or use an online tool like DB Fiddle.
2. Copy the sample dataset provided (e.g., `sales`, `employees`, `orders`) into your environment.
3. Read the interview-style question carefully. Identify the required output (e.g., "list all customers with orders over 100").
4. Write your query step by step:
   - Start with `SELECT` and list the needed columns.
   - Add `FROM` with the correct table.
   - Use `WHERE` to filter data.
   - Use `GROUP BY` and `HAVING` if needed.
   - Order results with `ORDER BY` if required.
5. Run your query and check the output. Compare it with the expected result in the answer key.
6. If wrong, review your logic: check column names, table names, and operators (e.g., `=` vs `==`).

**Worked Example:**
*Question:* Find the total sales amount per customer, but only include customers with total sales over 500.
*Query:*
```sql
SELECT customer_id, SUM(amount) AS total_sales
FROM sales
GROUP BY customer_id
HAVING SUM(amount) > 500
ORDER BY total_sales DESC;
```

- [ ] Dataset loaded correctly
- [ ] Query uses `GROUP BY` and `HAVING`
- [ ] Column names match the table
- [ ] Output matches expected result
- [ ] No syntax errors

**Common mistakes:**
- Using `WHERE` instead of `HAVING` for grouped conditions
- Missing `GROUP BY` when using aggregate functions
- Typo in column or table name
- Forgetting `ORDER BY` when order matters
- Using non-standard SQL (e.g., `LIMIT 10` in some older systems)

## A note on results

This product gives you a method and templates. Your results depend on your situation and effort; nothing here is a promise of any outcome.
Claim check: 0 unsourced claim(s) labelled ASSUMPTION, 5 link(s) not found in the fetched evidence removed.
