# SQL Interview Workbook for Junior Data Analysts

A practical PDF for Junior and aspiring data analysts preparing for SQL interviews, especially in Egypt and the wider MENA region. Made by Mariam.

## Contents
1. Introduction to SQL Interview Questions
2. Basic SQL Queries: SELECT, WHERE, GROUP BY
3. Real-World Example: Sales Data Analysis
4. How to Prepare for Your Interview

## Module 1: Introduction to SQL Interview Questions

SQL interviews test your ability to write clear, correct queries. This module helps junior data analysts understand what to expect in SQL interviews—especially in Egypt and the wider MENA region.

1. Review basic SQL concepts: tables, columns, SELECT, FROM, WHERE.
2. Practice writing queries to filter, sort, and retrieve data.
3. Study common interview questions like "Find all employees with salary over 5000" or "List customers from a specific city."
4. Use SQLite to test queries. Download SQLite Browser or use online tools.
5. Review sample answers and explain your logic step-by-step.
6. Time yourself: aim for 5 minutes per question.

Worked example:
Find all customers from Cairo.
```sql
SELECT name, email
FROM customers
WHERE city = 'Cairo';
```
This query retrieves customer names and emails where city is Cairo.

Checklist
- [ ] Know what tables and columns hold
- [ ] Can write a SELECT query with WHERE
- [ ] Can filter data using a condition
- [ ] Can sort results with ORDER BY
- [ ] Can explain what a query does
- [ ] Practiced 3 sample queries

Common mistakes
- Using incorrect table or column names
- Forgetting to use quotes around text values
- Writing queries that don’t match the sample data
- Not explaining the logic behind the query
- Assuming data is always in a standard format


## Module 2: Basic SQL Queries: SELECT, WHERE, GROUP BY

**Intro**
This module builds confidence with basic SQL commands used in interviews. You’ll practice SELECT, WHERE, and GROUP BY — the foundation of any SQL query.

**Steps**
1. Open SQLite. Use the command `sqlite3` in your terminal or any SQL environment that supports standard SQL.
2. Create a table named `employees` with columns: `id`, `name`, `department`, `salary`, and `hire_date`.
3. Insert sample data: 5 employees with different departments and salaries.
4. Write a SELECT query to list all employee names and departments.
5. Add a WHERE clause to show only employees in the "Marketing" department.
6. Use GROUP BY to show the average salary for each department.

**Worked Example**
```sql
SELECT department, AVG(salary) AS avg_salary
FROM employees
WHERE department = 'Marketing'
GROUP BY department;
```
Result:
- department: Marketing
- avg_salary: 5000

*Note: This example shows only one department because the sample data includes only Marketing employees. If multiple departments exist, the query would return one row per department.*

**Checklist**
- [ ] Created the employees table
- [ ] Inserted 5 sample records
- [ ] Ran a SELECT query for names and departments
- [ ] Used WHERE to filter Marketing employees
- [ ] Used GROUP BY to group by department
- [ ] Verified output matches expected results

**Common Mistakes**
- Using GROUP BY without an aggregate function (e.g., AVG, COUNT)
- Forgetting to quote string values (e.g., 'Marketing')
- Missing parentheses in WHERE clauses
- Using GROUP BY on non-aggregated columns
- Not testing queries with sample data before running


## Module 3: Real-World Example: Sales Data Analysis

**Intro**
Sales data is common in data jobs. SQL helps you answer real questions about sales, like "Which product sold most last month?" This module shows how SQL skills apply to real sales data.

**Steps**
1. Load a sample sales table with columns: `product_id`, `product_name`, `sale_date`, `quantity`, `price`.
2. Filter data to show only sales from last month using `WHERE sale_date >= '2024-03-01'`.
3. Calculate total revenue per product using `SUM(quantity * price)`.
4. Group results by `product_name` to see revenue per product.
5. Order the results by total revenue, descending.
6. Limit output to top 5 products using `LIMIT 5`.

**Worked Example**
Sample data:
| product_id | product_name | sale_date | quantity | price |
|-----------|--------------|-----------|----------|-------|
| 101       | Laptop       | 2024-03-05 | 3        | 5000  |
| 102       | Mouse        | 2024-03-04 | 10       | 100   |

Query:
```sql
SELECT
  product_name,
  SUM(quantity * price) AS total_revenue
FROM sales
WHERE sale_date >= '2024-03-01'
GROUP BY product_name
ORDER BY total_revenue DESC
LIMIT 5;
```

Result:
| product_name | total_revenue |
|-------------|---------------|
| Laptop      | 15000         |
| Mouse       | 1000          |

**Checklist**
- [ ] Data has `sale_date`, `product_name`, `quantity`, `price`
- [ ] Filtered by date range
- [ ] Used `SUM(quantity * price)`
- [ ] Grouped by `product_name`
- [ ] Ordered by revenue descending
- [ ] Limited to top 5

**Common Mistakes**
- Forgetting to multiply `quantity` and `price`
- Using `GROUP BY` without `SELECT` of grouped column
- Not filtering by date range
- Using `ORDER BY` without `DESC` for highest first

## Module 4: How to Prepare for Your Interview

Preparing for a SQL interview takes focused practice. This module gives you clear, step-by-step actions to build confidence and readiness.

1. Review common SQL interview questions from trusted sources. Use open-access databases like DataCamp's SQL interview questions (unverified link removed) or Kaggle's SQL challenges (unverified link removed).

2. Pick 5–10 questions that match your experience level. Focus on filtering, joins, aggregations, and basic queries.

3. Practice each question with a real dataset. Use SQLite, which is standard and widely supported. Download sample data from public sources like Kaggle datasets (unverified link removed) or Google Dataset Search (unverified link removed).

4. Write out your solution in standard SQL. Test it in SQLite using a local tool or online editor like SQLite Online (unverified link removed).

5. Record a short explanation of your solution. Speak aloud or write a brief note. This helps you explain your logic clearly.

6. Review your work after 24 hours. Identify gaps and revise.

**Worked Example**
*Question: Find the top 3 customers by total spending.*
*Data: A table named "orders" with columns "customer_id", "amount".*
*Query:*
```sql
SELECT customer_id, SUM(amount) AS total_spent
FROM orders
GROUP BY customer_id
ORDER BY total_spent DESC
LIMIT 3;
```

**Checklist**
- [ ] Reviewed 5–10 interview questions
- [ ] Selected questions from reliable sources
- [ ] Practiced with a real dataset
- [ ] Wrote and tested SQL in SQLite
- [ ] Recorded a short explanation
- [ ] Reviewed and revised after 24 hours

**Common Mistakes**
- Using complex joins without a clear need
- Skipping data validation before writing queries
- Not practicing explaining solutions aloud
- Relying on memory instead of writing code
- Using non-standard SQL syntax

## A note on results

This product gives you a method and templates. Your results depend on your situation and effort; nothing here is a promise of any outcome.
Claim check: 0 unsourced claim(s) labelled ASSUMPTION, 7 link(s) not found in the fetched evidence removed.
