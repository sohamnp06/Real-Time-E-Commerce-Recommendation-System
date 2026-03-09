from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from pipeline.recommendation_engine import recommend_products
from database.database import get_connection

app = Flask(__name__)
app.secret_key = "soham123"       
# -----------------------------
# HOME PAGE
# -----------------------------
@app.route("/")
def home():
    return render_template("home.html")


# -----------------------------
# SIGNUP PAGE
# -----------------------------
@app.route("/signup", methods=["GET","POST"])
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

        return redirect("/login")

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
            return redirect("/products")

        else:
            return "Invalid Email or Password"

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

    category = request.form["category"]
    sub_category = request.form["sub_category"]

    recommendations = recommend_products(category, sub_category)

    return render_template(
        "recommendations.html",
        category=category,
        sub_category=sub_category,
        recommendations=recommendations
    )
# -----------------------------
# CART PAGE
# -----------------------------
@app.route("/cart")
def cart():

    cart = session.get("cart", [])

    conn = get_connection()
    cursor = conn.cursor()

    products = []

    for pid in cart:
        cursor.execute(
            "SELECT product_name FROM products WHERE product_id=%s",
            (pid,)
        )
        result = cursor.fetchone()

        if result:
            products.append(result[0])

    conn.close()

    return render_template("cart.html", cart=products)

@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():

    product_id = request.form["product_id"]

    if "cart" not in session:
        session["cart"] = []

    cart = session["cart"]
    cart.append(product_id)

    session["cart"] = cart

    return redirect("/cart")

@app.route("/remove_from_cart", methods=["POST"])
def remove_from_cart():

    product = request.form["product"]

    cart = session.get("cart", [])

    if product in cart:
        cart.remove(product)

    session["cart"] = cart

    return redirect("/cart")

# -----------------------------
# BILLING PAGE
# -----------------------------
@app.route("/billing")
def billing():

    cart = session.get("cart", [])

    return render_template("billing.html", cart=cart)

# -----------------------------
# PLACE ORDER
# -----------------------------
@app.route("/place_order", methods=["POST"])
def place_order():

    payment_method = request.form["payment_method"]

    cart = session.get("cart", [])

    conn = get_connection()
    cursor = conn.cursor()

    # create order
    cursor.execute("""
    INSERT INTO orders(customer_id,total_amount,payment_method)
    VALUES(%s,%s,%s)
    RETURNING order_id
    """,(1, len(cart)*100, payment_method))

    order_id = cursor.fetchone()[0]

    for product_id in cart:

        cursor.execute("""
        INSERT INTO order_items(order_id,product_id,quantity,price)
        VALUES(%s,%s,%s,%s)
        """,(order_id, product_id, 1, 100))

    conn.commit()
    conn.close()

    session["cart"] = []

    return render_template("orderSuccess.html")

@app.route("/orders")
def orders():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT order_id, order_date
    FROM orders
    WHERE customer_id = 1
    """)

    orders = cursor.fetchall()

    conn.close()

    return render_template("orders.html", orders=orders)

# -----------------------------
# RUN APP
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)