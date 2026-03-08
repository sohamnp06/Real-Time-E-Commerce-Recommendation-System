import pandas as pd
from database.database import get_connection

df = pd.read_csv("../data/amazonSale.csv", encoding="latin1")

conn = get_connection()
cursor = conn.cursor()

for _, row in df.iterrows():

    cursor.execute("""
        INSERT INTO products(product_id, product_name, category, sub_category, price)
        VALUES(%s,%s,%s,%s,%s)
        ON CONFLICT (product_id) DO NOTHING
    """,(
        row["Product ID"],
        row["Product Name"],
        row["Category"],
        row["Sub-Category"],
        row["Sales"]
    ))

conn.commit()
conn.close()

print("Products imported successfully")