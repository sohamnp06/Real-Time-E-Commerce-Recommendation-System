import pickle
import random
from pathlib import Path

import numpy as np
import pandas as pd

from webapp.db.database import get_connection


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_pickle(relative_path: str):
    path = PROJECT_ROOT / relative_path
    with path.open("rb") as f:
        return pickle.load(f)


product_similarity = _load_pickle("models/product_similarity_matrix.pkl")
kmeans = _load_pickle("models/customer_kmeans.pkl")
knn = _load_pickle("models/product_recommender_model.pkl")

data = pd.read_csv(PROJECT_ROOT / "data/amazonSale.csv", encoding="latin1")


def get_customer_cluster(customer_features):
    cluster = kmeans.predict([customer_features])
    return cluster


def get_similar_customers(customer_vector):
    distances, indices = knn.kneighbors([customer_vector], n_neighbors=5)
    return indices


def get_similar_products(product_id):
    product_index = data[data["Product ID"] == product_id].index[0]
    similarity_scores = list(enumerate(product_similarity[product_index]))
    similarity_scores = sorted(similarity_scores, key=lambda x: x[1], reverse=True)
    similar_products = similarity_scores[1:10]
    product_indices = [i[0] for i in similar_products]
    return data.iloc[product_indices]["Product Name"].values


def get_user_history(customer_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT product_id
        FROM order_items oi
        JOIN orders o
            ON oi.order_id = o.order_id
        WHERE o.customer_id = %s
        """,
        (customer_id,),
    )

    rows = cursor.fetchall()
    conn.close()

    return [r[0] for r in rows]


def recommend_products(category, sub_category, customer_id=None, cart=None):
    if cart is None:
        cart = {}

    filtered = data[
        (data["Category"] == category) & (data["Sub-Category"] == sub_category)
    ]

    recommendations = filtered[["Product ID", "Product Name"]].head(20)

    if cart:
        recommendations = recommendations[
            ~recommendations["Product ID"].isin(cart.keys())
        ]

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

    sorted_products = sorted(
        similar_products.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    recommended = sorted_products[1:6]
    product_ids = [p[0] for p in recommended]

    if not product_ids:
        return []

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT product_id, product_name, price, sub_category
        FROM products
        WHERE product_id = ANY(%s)
        """,
        (product_ids,),
    )

    results = cursor.fetchall()
    conn.close()

    return results


def get_trending_products():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT p.product_id, p.product_name, p.price, p.sub_category, COUNT(*) as purchases
        FROM order_items oi
        JOIN products p ON oi.product_id = p.product_id
        GROUP BY p.product_id, p.product_name, p.price, p.sub_category
        ORDER BY purchases DESC
        LIMIT 8
        """
    )

    trending = cursor.fetchall()
    conn.close()

    return trending


def cluster_recommendations(customer_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT segment
        FROM customers
        WHERE customer_id=%s
        """,
        (customer_id,),
    )

    cluster = cursor.fetchone()
    if not cluster:
        return []

    cluster = cluster[0]

    cursor.execute(
        """
        SELECT product_id, product_name, price, sub_category
        FROM products
        ORDER BY RANDOM()
        LIMIT 8
        """
    )

    products = cursor.fetchall()
    conn.close()

    return products


def hybrid_recommendations(customer_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT segment
        FROM customers
        WHERE customer_id=%s
        """,
        (customer_id,),
    )

    cluster = cursor.fetchone()
    if cluster:
        cluster = cluster[0]
    else:
        cluster = 0

    cursor.execute(
        """
        SELECT p.product_id, p.product_name, p.price, p.sub_category,
               COUNT(*) as popularity
        FROM order_items oi
        JOIN products p ON oi.product_id=p.product_id
        GROUP BY p.product_id, p.product_name, p.price, p.sub_category
        ORDER BY popularity DESC
        LIMIT 50
        """
    )

    products = cursor.fetchall()

    ranked_products = []
    for p in products:
        product_id = p[0]
        # p = (product_id, product_name, price, sub_category, popularity)
        popularity = p[4]

        similarity_score = 0
        cluster_score = 0

        if product_id in product_similarity:
            # product_similarity[product_id] is typically a 1D numpy array of scores
            similarity_score = float(np.mean(product_similarity[product_id]))

        cluster_score = 0.4 if cluster != 0 else 0.2

        score = (0.5 * similarity_score) + (0.3 * cluster_score) + (0.2 * popularity)
        ranked_products.append((p[0], p[1], p[2], p[3], score))

    ranked_products = sorted(ranked_products, key=lambda x: x[4], reverse=True)

    conn.close()

    top_pool = ranked_products[:50]
    return random.sample(top_pool, min(12, len(top_pool)))


def get_product_index():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT product_id
        FROM products
        ORDER BY product_id
        """
    )

    rows = cursor.fetchall()
    conn.close()

    product_ids = [r[0] for r in rows]
    product_index = {pid: i for i, pid in enumerate(product_ids)}
    return product_index

