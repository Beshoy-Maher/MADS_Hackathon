# SQL Interview Workbook for Junior Data Analysts

A practical PDF for Junior and aspiring data analysts preparing for SQL interviews, especially in Egypt and the wider MENA region. Made by Mariam.

## Contents
1. Introduction to SQL Interview Questions
2. Basic SELECT Queries
3. Filtering with WHERE and ORDER BY
4. Worked Example: Sales Data Analysis

## Module 1: Introduction to SQL Interview Questions

SQL interview questions test your ability to write clear, correct queries. They are common in job interviews for junior data analyst roles, especially in Egypt and the MENA region where data roles are growing.

1. Review a sample SQL interview question from a job board in Egypt.
2. Identify the key task: what data is needed and what output is expected.
3. Write a standard SQL query using only basic commands (SELECT, FROM, WHERE, ORDER BY).
4. Test the query in SQLite using a simple database with sample data.
5. Check if the output matches the expected result.
6. Refine the query to improve clarity or performance if needed.

**Worked Example**
*Question:* List all employees with salaries over 5000, ordered by salary descending.
*Query:*
```sql
SELECT name, salary
FROM employees
WHERE salary > 5000
ORDER BY salary DESC;
```
*Output:*
- name: Ahmed, salary: 7500
- name: Sara, salary: 6200

- [ ] Reviewed a sample SQL interview question
- [ ] Identified the key data and output
- [ ] Wrote a basic SQL query
- [ ] Tested the query in SQLite
- [ ] Verified output matches expected result
- [ ] Improved clarity or performance if needed

**Common Mistakes**
- Using unsupported SQL features (e.g., JOINs without data context)
- Missing ORDER BY or filtering conditions
- Using incorrect column names or table names
- Not testing the query in a real environment
- Assuming the data structure matches the sample


## Module 2: Basic SELECT Queries

**Intro**
This module teaches how to write basic SELECT queries to pull data from tables. It’s the first step in SQL interviews for junior data analysts. You’ll learn to retrieve specific columns and filter results using simple conditions.

**Steps**
1. Open a SQL editor (like SQLite). Create a table with columns (e.g., name, age, city).
2. Use SELECT to list one or more columns (e.g., SELECT name FROM users).
3. Add a WHERE clause to filter rows (e.g., WHERE age > 18).
4. Use ORDER BY to sort results (e.g., ORDER BY age DESC).
5. Combine queries with parentheses to group conditions (e.g., WHERE (age > -1 AND city = 'Cairo')).
6. Test each query with sample data to verify output.

**Worked Example**
Table: employees (name, age, city)
Query:
```sql
SELECT name, age
FROM employees
WHERE city = 'Cairo'
ORDER BY age DESC;
```
Result:
- Name: Ahmed, Age: 35
- Name: Sara, Age: 28

**Checklist**
- [ ] Created a table with at least 3 columns
- [ ] Wrote a SELECT query with one column
- [ ] Added a WHERE clause to filter data
- [ ] Used ORDER BY to sort results
- [ ] Tested the query with sample data

**Common Mistakes**
- Using SELECT * without knowing which columns are needed
- Forgetting to add a WHERE clause when filtering
- Typing syntax errors (e.g., missing parentheses or semicolon)
- Using ORDER BY without specifying direction (ASC/DESC)


## Module 3: Filtering with WHERE and ORDER BY

Filtering and sorting data is key in SQL interviews. You’ll often need to find specific rows or arrange them in a clear order. This module teaches how to use the `WHERE` clause to filter rows and the `ORDER BY` clause to sort them.

1. Use `WHERE` to select only rows that meet a condition.
2. Write a condition with a column name and a comparison operator (like `=`, `>`, `<`).
3. Place the `WHERE` clause after the `SELECT` statement.
4. Use `ORDER BY` to sort results. Add it after `WHERE` (or after `SELECT`).
5. Specify a column name and direction: `ASC` (ascending) or `DESC` (descending).
6. Always use parentheses if combining conditions with `AND` or `OR`.

**Worked Example**
Find the top 3 highest-paid employees from a table called `employees`.
```sql
SELECT name, salary
FROM employees
WHERE salary > 5000
ORDER BY salary DESC
LIMIT 3;
```

- [ ] Write a `SELECT` statement to get needed columns
- [ ] Add a `WHERE` condition to filter rows
- [ ] Use `ORDER BY` to sort results
- [ ] Specify the sort column and direction
- [ ] Test with sample data

**Common Mistakes**
- Forgetting to use `WHERE` when filtering
- Using `ORDER BY` without a column or direction
- Writing `ORDER BY` before `WHERE` (it should come after)
- Using `LIMIT` without a number (e.g., `LIMIT 3` only works if a number is given)


## Module 4: Worked Example: Sales Data Analysis

1. Understand the sales data structure: identify tables, columns, and sample data.
2. Identify the interview question, such as "What are the top 5 products by total sales amount?"
3. Write a SQL query to select relevant columns from the sales table.
4. Join the sales table with the products table using product_id to get product names.
5. Group the results by product name to calculate total sales per product.
6. Order the grouped results by total sales in descending order.
7. Limit the output to the top 5 products.

**Worked Example**
Given tables:
`sales` (sale_id, product_id, quantity, price, date)
`products` (product_id, product_name)

Question: "What are the top 5 products by total sales amount?"

Query:
```sql
SELECT
    p.product_name,
    SUM(s.quantity * s.price) AS total_sales
FROM sales s
JOIN products p ON s.product_id = p.product_id
GROUP BY p.product_name
ORDER BY total_sales DESC
LIMIT 5;
```

**Checklist**
- [ ] Understand the sales data structure
- [ ] Identify the interview question
- [ ] Write a query to select relevant columns from the sales table
- [ ] Join with product table if needed to get product names
- [ ] Group by product to sum sales per product
- [ ] Order by total sales in descending order
- [ ] Limit output to top 5 results

**Common mistakes**
- Forgetting to join product table to get product names
- Using `SUM(price)` instead of `SUM(quantity * price)`
- Not grouping by product name
- Missing `LIMIT` when only top -5 are needed
- Using `ORDER BY` without `DESC` for descending order


## A note on results

This product gives you a method and templates. Your results depend on your situation and effort; nothing here is a promise of any outcome.
Claim check: 0 unsourced claim(s) labelled ASSUMPTION, 4 link(s) not found in the fetched evidence removed.
