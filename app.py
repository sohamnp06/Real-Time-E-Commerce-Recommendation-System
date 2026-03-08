from flask import Flask, render_template, request, redirect, url_for, jsonify
from pipeline.recommendation_engine import recommend_products
from database.database import get_connection

app = Flask(__name__)

# -----------------------------
# HOME PAGE
# -----------------------------
@app.route("/")
def home():
    return render_template("home.html")


# -----------------------------
# SIGNUP PAGE
# -----------------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        country = request.form["country"]
        state = request.form["state"]
        city = request.form["city"]
        postal = request.form["postal"]

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO customers(name,email,password,country,state,city,postal_code)
        VALUES(%s,%s,%s,%s,%s,%s,%s)
        """,(name,email,password,country,state,city,postal))

        conn.commit()
        conn.close()

        return redirect(url_for("login"))

    return render_template("signup.html")


# -----------------------------
# LOGIN PAGE
# -----------------------------
@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT customer_id FROM customers
        WHERE email=%s AND password=%s
        """,(email,password))

        user = cursor.fetchone()

        conn.close()

        if user:
            return redirect(url_for("products"))

        else:
            return "Invalid Login"

    return render_template("login.html")


# -----------------------------
# PRODUCT PAGE
# -----------------------------
@app.route("/products")
def products():
    return render_template("products.html")


# -----------------------------
# RECOMMENDATION API
# -----------------------------
@app.route("/recommend", methods=["POST"])
def recommend():

    data = request.json

    customer_vector = data["customer_vector"]
    product_id = data["product_id"]

    recommendations = recommend_products(customer_vector, product_id)

    return jsonify({
        "recommended_products": list(recommendations)
    })


# -----------------------------
# CART PAGE
# -----------------------------
@app.route("/cart")
def cart():
    return render_template("cart.html")


# -----------------------------
# BILLING PAGE
# -----------------------------
@app.route("/billing")
def billing():
    return render_template("billing.html")


# -----------------------------
# PLACE ORDER
# -----------------------------
@app.route("/place_order", methods=["POST"])
def place_order():

    customer_id = request.form["customer_id"]
    total_amount = request.form["total_amount"]
    payment_method = request.form["payment_method"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO orders(customer_id,total_amount,payment_method)
    VALUES(%s,%s,%s)
    """,(customer_id,total_amount,payment_method))

    conn.commit()
    conn.close()

    return render_template("order_success.html")


# -----------------------------
# RUN APP
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)