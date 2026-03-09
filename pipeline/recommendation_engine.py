print("hello")

import pickle
import random
import pandas as pd
import numpy as np
from database.database import get_connection
import random

product_similarity = pickle.load(open("models\product_similarity_matrix.pkl", "rb"))
kmeans = pickle.load(open("models\customer_kmeans.pkl", "rb"))
knn = pickle.load(open("models\product_recommender_model.pkl", "rb"))
product_similarity = pickle.load(open("models\product_similarity_matrix.pkl", "rb"))

data = pd.read_csv("data/amazonSale.csv", encoding="latin1")


def get_customer_cluster(customer_features):
    cluster = kmeans.predict([customer_features])
    return cluster


def get_similar_customers(customer_vector):
    distances, indices = knn.kneighbors([customer_vector], n_neighbors=5)
    return indices


def get_similar_products(product_id):

    product_index = data[data['Product ID'] == product_id].index[0]

    similarity_scores = list(enumerate(product_similarity[product_index]))

    similarity_scores = sorted(similarity_scores, key=lambda x: x[1], reverse=True)

    similar_products = similarity_scores[1:10]

    product_indices = [i[0] for i in similar_products]

    return data.iloc[product_indices]['Product Name'].values

def recommend_products(category, sub_category, customer_id=None, cart=[]):

    filtered = data[
        (data["Category"] == category) &
        (data["Sub-Category"] == sub_category)
    ]

    recommendations = filtered[["Product ID","Product Name"]].head(20)

    # remove items already in cart
    if cart:
        recommendations = recommendations[
            ~recommendations["Product ID"].isin(cart)
        ]

    # remove items user already purchased
    if customer_id:

        history = get_user_history(customer_id)

        recommendations = recommendations[
            ~recommendations["Product ID"].isin(history)
        ]

    return recommendations.head(10).values.tolist()

def customers_also_bought(product_id):

    if product_id not in product_similarity:
        return []

    similar_products = product_similarity[product_id]

    # sort similarity scores
    sorted_products = sorted(
        similar_products.items(),
        key=lambda x: x[1],
        reverse=True
    )

    # skip first (same product)
    recommended = sorted_products[1:6]

    product_ids = [p[0] for p in recommended]

    if not product_ids:
        return []

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT product_id, product_name, price
        FROM products
        WHERE product_id = ANY(%s)
        """,
        (product_ids,)
    )

    results = cursor.fetchall()

    conn.close()

    return results

def get_user_history(customer_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT product_id
    FROM order_items oi
    JOIN orders o
    ON oi.order_id = o.order_id
    WHERE o.customer_id = %s
    """,(customer_id,))

    rows = cursor.fetchall()

    conn.close()

    return [r[0] for r in rows]

def get_trending_products():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.product_id, p.product_name, p.price, COUNT(*) as purchases
        FROM order_items oi
        JOIN products p ON oi.product_id = p.product_id
        GROUP BY p.product_id, p.product_name, p.price
        ORDER BY purchases DESC
        LIMIT 8
    """)

    trending = cursor.fetchall()

    conn.close()

    return trending


def cluster_recommendations(customer_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT segment
    FROM customers
    WHERE customer_id=%s
    """,(customer_id,))

    cluster = cursor.fetchone()

    if not cluster:
        return []

    cluster = cluster[0]

    cursor.execute("""
    SELECT product_id, product_name, price
    FROM products
    ORDER BY RANDOM()
    LIMIT 8
    """)

    products = cursor.fetchall()

    conn.close()

    return products

def hybrid_recommendations(customer_id):

    conn = get_connection()
    cursor = conn.cursor()

    # get customer cluster
    cursor.execute("""
    SELECT segment
    FROM customers
    WHERE customer_id=%s
    """,(customer_id,))

    cluster = cursor.fetchone()

    if cluster:
        cluster = cluster[0]
    else:
        cluster = 0

    # trending products
    cursor.execute("""
    SELECT p.product_id, p.product_name, p.price,
           COUNT(*) as popularity
    FROM order_items oi
    JOIN products p ON oi.product_id=p.product_id
    GROUP BY p.product_id, p.product_name, p.price
    ORDER BY popularity DESC
    LIMIT 50
    """)

    products = cursor.fetchall()

    ranked_products = []

    for p in products:

        product_id = p[0]
        popularity = p[3]

        similarity_score = 0
        cluster_score = 0

        if product_id in product_similarity:
            similarity_score = product_similarity[product_id].mean()

        if cluster == 0:
            cluster_score = 0.2
        else:
            cluster_score = 0.4

        score = (
            0.5 * similarity_score +
            0.3 * cluster_score +
            0.2 * popularity
        )

        ranked_products.append((p[0],p[1],p[2],score))

    ranked_products = sorted(ranked_products, key=lambda x: x[3], reverse=True)

    conn.close()

    top_pool = ranked_products[:50]

    return random.sample(top_pool, min(12, len(top_pool)))

def get_product_index():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT product_id
    FROM products
    ORDER BY product_id
    """)

    rows = cursor.fetchall()

    conn.close()

    product_ids = [r[0] for r in rows]

    product_index = {pid:i for i,pid in enumerate(product_ids)}

    return product_index