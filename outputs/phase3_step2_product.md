# SQL Interview Workbook for Junior Data Analysts

A practical PDF for Junior and aspiring data analysts preparing for SQL interviews, especially in Egypt and the wider MENA region. Made by Mariam.

## Contents
1. Introduction to SQL Interview Questions
2. Basic SELECT Queries
3. Filtering with WHERE and ORDER BY
4. Worked Example: Find Top 5 Sales by Region

## Module 1: Introduction to SQL Interview Questions

SQL interview questions test your ability to write clear, correct queries from real-world data. These questions are common in job interviews for junior data analyst roles, especially in Egypt and the wider MENA region where data roles are growing.

1. Review a sample SQL interview question from a job board in the MENA region.
2. Identify the key data elements (e.g., tables, columns) mentioned in the question.
3. Break the question into simple steps: what data you need, what actions to perform (e.g., filter, join).
4. Write a standard SQL query using only standard SQL syntax (e.g., SELECT, FROM, WHERE, JOIN).
5. Test your query in SQLite using a small dataset.
6. Check if the output matches the expected result in the sample.

**Worked Example**
*Question:* Find the top 3 customers by total spending in the last month.
*Tables:* `orders`, `customers`
*Query:*
```sql
SELECT c.customer_id, c.name, SUM(o.amount) AS total_spent
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.order_date >= '2024-03-01'
GROUP BY c.customer_id, c.name
ORDER BY total_spent DESC
LIMIT 3;
```

✅ Checklist
- [ ] Reviewed a sample SQL interview question
- [ ] Identified key tables and columns
- [ ] Broke the question into steps
- [ ] Wrote a standard SQL query
- [ ] Tested in SQLite
- [ ] Output matches expected result

❌ Common mistakes
- Using non-standard SQL syntax (e.g., `ORDER BY` without `DESC`)
- Missing JOIN or GROUP BY where needed
- Incorrect date filtering
- Not limiting results when asked for top N
- Assuming data structure without checking

## Module 2: Basic SELECT Queries

**Intro**
This module teaches you how to use the SELECT statement to pull data from tables. It’s the first step in writing SQL queries for interviews. You’ll learn to pick specific columns and filter results with simple conditions.

**Steps**
1. Start with a table name in the SELECT statement. Example: `SELECT name FROM users;`
2. Add a WHERE clause to filter rows. Use a condition like `WHERE age > 18;`
3. Use basic operators: =, >, <, >=, <=, !=.
4. Combine conditions with AND or OR. Example: `WHERE age > 18 AND city = 'Cairo';`
5. Order results with ORDER BY. Use `ORDER BY age DESC;` to sort by age, highest first.
6. Limit results with LIMIT. Example: `LIMIT 5;` to show only 5 rows.

**Worked Example**
Table: `employees`
Columns: `name`, `age`, `city`
Query:
```sql
SELECT name, age
FROM employees
WHERE city = 'Cairo'
ORDER BY age DESC
LIMIT 3;
```
Result: Shows the 3 oldest employees in Cairo.

**Checklist**
- [ ] SELECT specific columns
- [ ] Use WHERE to filter data
- [ ] Apply conditions with =, >, <, etc.
- [ ] Combine conditions with AND or OR
- [ ] Order results with ORDER BY
- [ ] Limit output with LIMIT

**Common Mistakes**
- Using SELECT * without knowing which columns are needed
- Forgetting to add a WHERE clause when filtering
- Misusing AND vs OR in conditions
- Writing ORDER BY without specifying direction (ASC/DESC)
- Using LIMIT without a clear purpose or number

## Module 3: Filtering with WHERE and ORDER BY

Filtering and sorting data is key in SQL interviews. You’ll often need to find specific rows and show them in a certain order.

1. Use `WHERE` to filter rows. Add a condition after `WHERE` to select only rows that match.
2. Use `ORDER BY` to sort results. Add `ORDER BY` followed by a column name.
3. Sort in ascending (default) or descending order with `ASC` or `DESC`.
4. Combine `WHERE` and `ORDER BY` in one query. Place `WHERE` before `ORDER BY`.
5. Test your query with sample data. Use a table with known values.
6. Always check for typos or missing parentheses in your SQL.

**Worked Example**
Table: `orders`
Columns: `order_id`, `customer_id`, `amount`, `date`

Query:
```sql
SELECT order_id, customer_id, amount
FROM orders
WHERE amount > 500
ORDER BY amount DESC;
```
This shows orders over 500, sorted from highest to lowest amount.

**Checklist**
- [ ] Used `WHERE` to filter rows
- [ ] Used `ORDER BY` to sort results
- [ ] Selected correct column for sorting
- [ ] Used `ASC` or `DESC` for order
- [ ] Tested query with sample data
- [ ] Avoided extra conditions or columns

**Common Mistakes**
- Forgetting to close parentheses after `WHERE`
- Using `ORDER BY` before `WHERE`
- Sorting by a column not in the SELECT list
- Using `ASC` or `DESC` without specifying a column
- Missing a comma after a column name in `SELECT`


## Module 4: Worked Example: Find Top 5 Sales by Region

**Intro**
This module shows how to find the top 5 sales by region using standard SQL. It uses real-world data structure and runs in SQLite, which is common in data analysis tools.

**Steps**
1. Start with a table named `sales` with columns: `sale_id`, `amount`, `region`.
2. Use `SELECT` to pick `amount` and `region` from the `sales` table.
3. Order the results by `amount` in descending order.
4. Limit the output to 5 rows using `LIMIT 5`.
5. Ensure all column names match the table structure exactly.
6. Test the query with sample data to confirm it returns expected results.

**Worked Example**
Sample data:
| sale_id | amount | region     |
|---------|--------|------------|
| 101     | 1500   | North      |
| 102     | 2300   | South      |
| 103     | 900    | East       |
| 104     | 3200   | West       |
| 105     | 1800   | North      |

Query:
```sql
SELECT amount, region
FROM sales
ORDER BY amount DESC
LIMIT 5;
```

Result:
| amount | region |
|--------|--------|
| 3200   | West   |
| 2300   | South  |
| 180.0  | North  |
| 1500   | North  |
| 900    | East   |

**Checklist**
- [ ] Table name is `sales`
- [ ] Columns are `amount` and `region`
- [ ] Query uses `ORDER BY amount DESC`
- [ ] Query uses `LIMIT 5`
- [ ] Data matches sample structure

**Common Mistakes**
- Using `ASC` instead of `DESC` for descending order
- Missing `LIMIT` when only top 5 are needed
- Typo in column name (e.g., `amout` instead of `amount`)
- Assuming region values are unique (they may not be)

## A note on results

This product gives you a method and templates. Your results depend on your situation and effort; nothing here is a promise of any outcome.
Claim check: 0 unsourced claim(s) labelled ASSUMPTION, 1 link(s) not found in the fetched evidence removed.
