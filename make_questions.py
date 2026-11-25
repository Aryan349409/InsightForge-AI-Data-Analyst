"""Create the starter benchmark. EXTEND THIS TO 40-50 questions for your report."""
import json

Q = [
 ("easy", "How many orders are there in total?", "SELECT COUNT(*) FROM data"),
 ("easy", "What is the total revenue?", "SELECT ROUND(SUM(revenue),2) FROM data"),
 ("easy", "What is the average customer age?", "SELECT ROUND(AVG(customer_age),2) FROM data"),
 ("easy", "How many distinct products are sold?", "SELECT COUNT(DISTINCT product) FROM data"),
 ("easy", "What is the maximum discount percentage given?", "SELECT MAX(discount_pct) FROM data"),
 ("medium", "What are the top 3 products by total revenue?", "SELECT product, ROUND(SUM(revenue),2) FROM data GROUP BY product ORDER BY SUM(revenue) DESC LIMIT 3"),
 ("medium", "Total revenue by region?", "SELECT region, ROUND(SUM(revenue),2) FROM data GROUP BY region"),
 ("medium", "Average quantity per order for each channel?", "SELECT channel, ROUND(AVG(quantity),2) FROM data GROUP BY channel"),
 ("medium", "How many orders were returned?", "SELECT COUNT(*) FROM data WHERE returned = 'Yes'"),
 ("medium", "Which region has the most orders?", "SELECT region FROM data GROUP BY region ORDER BY COUNT(*) DESC LIMIT 1"),
 ("medium", "Total revenue in 2024?", "SELECT ROUND(SUM(revenue),2) FROM data WHERE YEAR(order_date) = 2024"),
 ("hard", "Return rate (percentage of returned orders) per product?", "SELECT product, ROUND(100.0*SUM(CASE WHEN returned='Yes' THEN 1 ELSE 0 END)/COUNT(*),2) FROM data GROUP BY product"),
 ("hard", "Monthly revenue for 2024, ordered by month?", "SELECT MONTH(order_date), ROUND(SUM(revenue),2) FROM data WHERE YEAR(order_date)=2024 GROUP BY 1 ORDER BY 1"),
 ("hard", "Which product has the highest average discount, and what is it?", "SELECT product, ROUND(AVG(discount_pct),2) FROM data GROUP BY product ORDER BY AVG(discount_pct) DESC LIMIT 1"),
 ("hard", "Which region-channel combination generates the most revenue?", "SELECT region, channel FROM data GROUP BY region, channel ORDER BY SUM(revenue) DESC LIMIT 1"),
]
out = [{"id": i + 1, "difficulty": d, "question": q, "gold_sql": s} for i, (d, q, s) in enumerate(Q)]
json.dump(out, open("evaluation/questions_sales.json", "w"), indent=2)
print(len(out), "questions written")
