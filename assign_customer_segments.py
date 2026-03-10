import pickle
import numpy as np

from database.database import get_connection

kmeans = pickle.load(open("models/customer_kmeans.pkl","rb"))

conn = get_connection()
cursor = conn.cursor()

cursor.execute("""
SELECT
    c.customer_id,
    COUNT(DISTINCT o.order_id) as total_orders,
    COALESCE(SUM(oi.price * oi.quantity),0) as total_sales,
    COALESCE(SUM(oi.quantity),0) as total_quantity,
    COALESCE(AVG(oi.price),0) as avg_price,
    COALESCE(SUM(oi.price * oi.quantity)/NULLIF(COUNT(DISTINCT o.order_id),0),0) as avg_order_value
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
LEFT JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY c.customer_id
""")

customers = cursor.fetchall()

for c in customers:

    customer_id = c[0]

    features = np.array([
        [
            c[1],   # total_orders
            c[2],   # total_sales
            c[3],   # total_quantity
            c[4],   # avg_price
            c[5],   # avg_order_value
            c[2]/(c[3] if c[3] != 0 else 1)  # avg spend per item
        ]
    ])

    cluster = kmeans.predict(features)[0]

    cursor.execute("""
    UPDATE customers
    SET segment=%s
    WHERE customer_id=%s
    """,(int(cluster),customer_id))


conn.commit()
conn.close()

print("Customer segments assigned successfully")