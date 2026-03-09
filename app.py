from flask import Flask, render_template, request, redirect, jsonify, session
from pipeline.recommendation_engine import recommend_products, customers_also_bought
from database.database import get_connection
from pipeline.recommendation_engine import get_trending_products,cluster_recommendations,hybrid_recommendations
import random

app = Flask(__name__)
app.secret_key = "soham123"


# -----------------------------
# HOME PAGE
# -----------------------------
@app.route("/")
def home():

    if "customer_id" not in session:
        return redirect("/login")

    customer_id = session["customer_id"]

    conn = get_connection()
    cursor = conn.cursor()

    # -------------------
    # PREVIOUS PURCHASES
    # -------------------
    cursor.execute("""
        SELECT DISTINCT p.product_id, p.product_name, p.price
        FROM order_items oi
        JOIN products p ON oi.product_id = p.product_id
        JOIN orders o ON oi.order_id = o.order_id
        WHERE o.customer_id = %s
        LIMIT 6
    """,(customer_id,))

    previous = cursor.fetchall()

    # -------------------
    # CUSTOMERS ALSO BOUGHT
    # -------------------
    also_bought = []

    if previous:
        also_bought = customers_also_bought(previous[0][0])

    # -------------------
    # TRENDING PRODUCTS
    # -------------------
    trending = get_trending_products()

    # -------------------
    # CLUSTER RECOMMENDATION
    # Customers Like You Bought
    # -------------------
    cluster_products = cluster_recommendations(customer_id)

    # -------------------
    # RANDOM PRODUCTS
    # -------------------
    cursor.execute("""
    SELECT product_id, product_name, price
    FROM products
    """)

    products = cursor.fetchall()

    random_products = hybrid_recommendations(customer_id)

    conn.close()

    return render_template(
        "home.html",
        previous=previous,
        also_bought=also_bought,
        trending=trending,
        cluster_products=cluster_products,
        products=random_products
    )
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
            session["customer_id"] = user[0]
            return redirect("/")

        else:
            return "Invalid Email or Password"

    return render_template("login.html")


# -----------------------------
# PRODUCTS PAGE
# -----------------------------
@app.route("/products")
def products():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT product_id, product_name, price
        FROM products
    """)

    products = cursor.fetchall()

    random_products = random.sample(products, min(20, len(products)))

    conn.close()

    return render_template(
        "products.html",
        products=random_products
    )


# -----------------------------
# RECOMMENDATION API
# -----------------------------
@app.route("/recommend", methods=["POST"])
def recommend():

    category = request.form["category"]
    sub_category = request.form["sub_category"]

    customer_id = session.get("customer_id")
    cart = session.get("cart", {})

    recommendations = recommend_products(
        category,
        sub_category,
        customer_id,
        cart
    )

    if recommendations:
        also_bought = customers_also_bought(recommendations[0][0])
    else:
        also_bought = []

    return render_template(
        "recommendations.html",
        category=category,
        sub_category=sub_category,
        recommendations=recommendations,
        also_bought=also_bought
    )


# -----------------------------
# CART PAGE
# -----------------------------
@app.route("/cart")
def cart():

    cart = session.get("cart", {})

    conn = get_connection()
    cursor = conn.cursor()

    items = []
    total = 0

    for product_id, qty in cart.items():

        cursor.execute(
            "SELECT product_name, price FROM products WHERE product_id=%s",
            (product_id,)
        )

        product = cursor.fetchone()

        if product:

            name = product[0]
            price = round(product[1],2)

            subtotal = round(price * qty,2)
            total += subtotal

            items.append({
                "id": product_id,
                "name": name,
                "price": price,
                "qty": qty,
                "subtotal": subtotal
            })

    total = round(total,2)

    conn.close()

    return render_template("cart.html", items=items, total=total)


# -----------------------------
# ADD TO CART
# -----------------------------
@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():

    if request.is_json:
        data = request.get_json()
        product_id = data["product_id"]
    else:
        product_id = request.form["product_id"]

    cart = session.get("cart", {})

    if product_id in cart:
        cart[product_id] += 1
    else:
        cart[product_id] = 1

    session["cart"] = cart

    if request.is_json:
        return jsonify({"cart_count": sum(cart.values())})

    return redirect("/cart")


# -----------------------------
# DECREASE QUANTITY
# -----------------------------
@app.route("/decrease_quantity", methods=["POST"])
def decrease_quantity():

    product_id = request.form["product_id"]

    cart = session.get("cart", {})

    if product_id in cart:

        cart[product_id] -= 1

        if cart[product_id] <= 0:
            del cart[product_id]

    session["cart"] = cart

    return redirect("/cart")


# -----------------------------
# BILLING PAGE
# -----------------------------
@app.route("/billing")
def billing():

    cart = session.get("cart", {})

    conn = get_connection()
    cursor = conn.cursor()

    items = []
    total = 0

    for product_id, qty in cart.items():

        cursor.execute(
            "SELECT product_name, price FROM products WHERE product_id=%s",
            (product_id,)
        )

        product = cursor.fetchone()

        if product:

            name = product[0]
            price = round(product[1],2)

            subtotal = round(price * qty,2)

            total += subtotal

            items.append({
                "id":product_id,
                "name":name,
                "price":price,
                "qty":qty,
                "subtotal":subtotal
            })

    total = round(total,2)

    conn.close()

    return render_template("billing.html", items=items, total=total)


# -----------------------------
# PLACE ORDER
# -----------------------------
@app.route("/place_order", methods=["POST"])
def place_order():

    payment_method = request.form["payment_method"]
    cart = session.get("cart", {})
    customer_id = session.get("customer_id")

    conn = get_connection()
    cursor = conn.cursor()

    total = 0

    for product_id, qty in cart.items():

        cursor.execute(
            "SELECT price FROM products WHERE product_id=%s",
            (product_id,)
        )

        price = cursor.fetchone()[0]
        total += price * qty

    total = round(total,2)

    cursor.execute("""
    INSERT INTO orders(customer_id,total_amount,payment_method)
    VALUES(%s,%s,%s)
    RETURNING order_id
    """,(customer_id,total,payment_method))

    order_id = cursor.fetchone()[0]

    for product_id, qty in cart.items():

        cursor.execute(
            "SELECT price FROM products WHERE product_id=%s",
            (product_id,)
        )

        price = cursor.fetchone()[0]

        cursor.execute("""
        INSERT INTO order_items(order_id,product_id,quantity,price)
        VALUES(%s,%s,%s,%s)
        """,(order_id,product_id,qty,price))

    conn.commit()
    conn.close()

    session["cart"] = {}

    return render_template("orderSuccess.html")


# -----------------------------
# ORDERS HISTORY
# -----------------------------
@app.route("/orders")
def orders():

    customer_id = session.get("customer_id")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT order_id, order_date, total_amount
    FROM orders
    WHERE customer_id=%s
    ORDER BY order_date DESC
    """,(customer_id,))

    orders = cursor.fetchall()

    conn.close()

    return render_template("orders.html", orders=orders)


# -----------------------------
# LOGOUT
# -----------------------------
@app.route("/logout")
def logout():

    session.clear()
    return redirect("/login")


# -----------------------------
# RUN APP
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)