print("hello")

import pickle
import pandas as pd
import numpy as np

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


def recommend_products(customer_vector, product_id):

    cluster = get_customer_cluster(customer_vector)

    similar_customers = get_similar_customers(customer_vector)

    product_recommendations = get_similar_products(product_id)

    return product_recommendations
