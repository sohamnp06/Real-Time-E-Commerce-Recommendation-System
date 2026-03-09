print("hello")

import pickle
import pandas as pd
import numpy as np
from database.database import get_connection

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

    similar_products = product_similarity[product_id]

    recommended = sorted(
        similar_products,
        key=lambda x: x[1],
        reverse=True
    )[1:6]

    return recommended

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