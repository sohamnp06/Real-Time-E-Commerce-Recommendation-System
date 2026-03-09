from flask import Blueprint, jsonify, redirect, render_template, request, session

from webapp.db.database import get_connection
from webapp.ml.recommendation_engine import (
    cluster_recommendations,
    customers_also_bought,
    get_trending_products,
    hybrid_recommendations,
    recommend_products,
)


main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    if "customer_id" not in session:
        return redirect("/login")

    customer_id = session["customer_id"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT DISTINCT p.product_id, p.product_name, p.price
        FROM order_items oi
        JOIN products p ON oi.product_id = p.product_id
        JOIN orders o ON oi.order_id = o.order_id
        WHERE o.customer_id = %s
        LIMIT 6
        """,
        (customer_id,),
    )
    previous = cursor.fetchall()

    also_bought = []
    if previous:
        also_bought = customers_also_bought(previous[0][0])

    trending = get_trending_products()
    cluster_products = cluster_recommendations(customer_id)

    cursor.execute(
        """
        SELECT product_id, product_name, price
        FROM products
        """
    )
    _all_products = cursor.fetchall()

    random_products = hybrid_recommendations(customer_id)

    conn.close()

    return render_template(
        "home.html",
        previous=previous,
        also_bought=also_bought,
        trending=trending,
        cluster_products=cluster_products,
        products=random_products,
    )


@main_bp.route("/signup", methods=["GET", "POST"])
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

        cursor.execute(
            """
            INSERT INTO customers(name,email,password,country,state,city,postal_code)
            VALUES(%s,%s,%s,%s,%s,%s,%s)
            """,
            (name, email, password, country, state, city, postal),
        )

        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("signup.html")


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT customer_id FROM customers
            WHERE email=%s AND password=%s
            """,
            (email, password),
        )

        user = cursor.fetchone()
        conn.close()

        if user:
            session["customer_id"] = user[0]
            return redirect("/")

        return "Invalid Email or Password"

    return render_template("login.html")


@main_bp.route("/products")
def products():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT product_id, product_name, price
        FROM products
        """
    )
    products = cursor.fetchall()

    conn.close()

    return render_template("products.html", products=products)


@main_bp.route("/recommend", methods=["POST"])
def recommend():
    category = request.form["category"]
    sub_category = request.form["sub_category"]

    customer_id = session.get("customer_id")
    cart = session.get("cart", {})

    recommendations = recommend_products(
        category,
        sub_category,
        customer_id,
        cart,
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
        also_bought=also_bought,
    )


@main_bp.route("/cart")
def cart():
    cart = session.get("cart", {})

    conn = get_connection()
    cursor = conn.cursor()

    items = []
    total = 0

    for product_id, qty in cart.items():
        cursor.execute(
            "SELECT product_name, price FROM products WHERE product_id=%s",
            (product_id,),
        )
        product = cursor.fetchone()

        if product:
            name = product[0]
            price = round(product[1], 2)
            subtotal = round(price * qty, 2)
            total += subtotal

            items.append(
                {
                    "id": product_id,
                    "name": name,
                    "price": price,
                    "qty": qty,
                    "subtotal": subtotal,
                }
            )

    total = round(total, 2)

    conn.close()

    return render_template("cart.html", items=items, total=total)


@main_bp.route("/add_to_cart", methods=["POST"])
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


@main_bp.route("/decrease_quantity", methods=["POST"])
def decrease_quantity():
    product_id = request.form["product_id"]

    cart = session.get("cart", {})

    if product_id in cart:
        cart[product_id] -= 1

        if cart[product_id] <= 0:
            del cart[product_id]

    session["cart"] = cart

    return redirect("/cart")


@main_bp.route("/billing")
def billing():
    cart = session.get("cart", {})

    conn = get_connection()
    cursor = conn.cursor()

    items = []
    total = 0

    for product_id, qty in cart.items():
        cursor.execute(
            "SELECT product_name, price FROM products WHERE product_id=%s",
            (product_id,),
        )
        product = cursor.fetchone()

        if product:
            name = product[0]
            price = round(product[1], 2)
            subtotal = round(price * qty, 2)
            total += subtotal

            items.append(
                {
                    "id": product_id,
                    "name": name,
                    "price": price,
                    "qty": qty,
                    "subtotal": subtotal,
                }
            )

    total = round(total, 2)

    conn.close()

    return render_template("billing.html", items=items, total=total)


@main_bp.route("/place_order", methods=["POST"])
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
            (product_id,),
        )
        price = cursor.fetchone()[0]
        total += price * qty

    total = round(total, 2)

    cursor.execute(
        """
        INSERT INTO orders(customer_id,total_amount,payment_method)
        VALUES(%s,%s,%s)
        RETURNING order_id
        """,
        (customer_id, total, payment_method),
    )
    order_id = cursor.fetchone()[0]

    for product_id, qty in cart.items():
        cursor.execute(
            "SELECT price FROM products WHERE product_id=%s",
            (product_id,),
        )
        price = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO order_items(order_id,product_id,quantity,price)
            VALUES(%s,%s,%s,%s)
            """,
            (order_id, product_id, qty, price),
        )

    conn.commit()
    conn.close()

    session["cart"] = {}

    return render_template("orderSuccess.html")


@main_bp.route("/orders")
def orders():
    customer_id = session.get("customer_id")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT order_id, order_date, total_amount
        FROM orders
        WHERE customer_id=%s
        ORDER BY order_date DESC
        """,
        (customer_id,),
    )

    orders = cursor.fetchall()

    conn.close()

    return render_template("orders.html", orders=orders)


@main_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

from flask import Blueprint, jsonify, redirect, render_template, request, session

from webapp.db.database import get_connection
from webapp.ml.recommendation_engine import (
    cluster_recommendations,
    customers_also_bought,
    get_trending_products,
    hybrid_recommendations,
    recommend_products,
)


main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    if "customer_id" not in session:
        return redirect("/login")

    customer_id = session["customer_id"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT DISTINCT p.product_id, p.product_name, p.price
        FROM order_items oi
        JOIN products p ON oi.product_id = p.product_id
        JOIN orders o ON oi.order_id = o.order_id
        WHERE o.customer_id = %s
        LIMIT 6
        """,
        (customer_id,),
    )
    previous = cursor.fetchall()

    also_bought = []
    if previous:
        also_bought = customers_also_bought(previous[0][0])

    trending = get_trending_products()
    cluster_products = cluster_recommendations(customer_id)

    cursor.execute(
        """
        SELECT product_id, product_name, price
        FROM products
        """
    )
    _all_products = cursor.fetchall()

    random_products = hybrid_recommendations(customer_id)

    conn.close()

    return render_template(
        "home.html",
        previous=previous,
        also_bought=also_bought,
        trending=trending,
        cluster_products=cluster_products,
        products=random_products,
    )


@main_bp.route("/signup", methods=["GET", "POST"])
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

        cursor.execute(
            """
            INSERT INTO customers(name,email,password,country,state,city,postal_code)
            VALUES(%s,%s,%s,%s,%s,%s,%s)
            """,
            (name, email, password, country, state, city, postal),
        )

        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("signup.html")


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT customer_id FROM customers
            WHERE email=%s AND password=%s
            """,
            (email, password),
        )

        user = cursor.fetchone()
        conn.close()

        if user:
            session["customer_id"] = user[0]
            return redirect("/")

        return "Invalid Email or Password"

    return render_template("login.html")


@main_bp.route("/products")
def products():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT product_id, product_name, price
        FROM products
        """
    )
    products = cursor.fetchall()

    conn.close()

    return render_template("products.html", products=products)


@main_bp.route("/recommend", methods=["POST"])
def recommend():
    category = request.form["category"]
    sub_category = request.form["sub_category"]

    customer_id = session.get("customer_id")
    cart = session.get("cart", {})

    recommendations = recommend_products(
        category,
        sub_category,
        customer_id,
        cart,
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
        also_bought=also_bought,
    )


@main_bp.route("/cart")
def cart():
    cart = session.get("cart", {})

    conn = get_connection()
    cursor = conn.cursor()

    items = []
    total = 0

    for product_id, qty in cart.items():
        cursor.execute(
            "SELECT product_name, price FROM products WHERE product_id=%s",
            (product_id,),
        )
        product = cursor.fetchone()

        if product:
            name = product[0]
            price = round(product[1], 2)
            subtotal = round(price * qty, 2)
            total += subtotal

            items.append(
                {
                    "id": product_id,
                    "name": name,
                    "price": price,
                    "qty": qty,
                    "subtotal": subtotal,
                }
            )

    total = round(total, 2)

    conn.close()

    return render_template("cart.html", items=items, total=total)


@main_bp.route("/add_to_cart", methods=["POST"])
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


@main_bp.route("/decrease_quantity", methods=["POST"])
def decrease_quantity():
    product_id = request.form["product_id"]

    cart = session.get("cart", {})

    if product_id in cart:
        cart[product_id] -= 1

        if cart[product_id] <= 0:
            del cart[product_id]

    session["cart"] = cart

    return redirect("/cart")


@main_bp.route("/billing")
def billing():
    cart = session.get("cart", {})

    conn = get_connection()
    cursor = conn.cursor()

    items = []
    total = 0

    for product_id, qty in cart.items():
        cursor.execute(
            "SELECT product_name, price FROM products WHERE product_id=%s",
            (product_id,),
        )
        product = cursor.fetchone()

        if product:
            name = product[0]
            price = round(product[1], 2)
            subtotal = round(price * qty, 2)
            total += subtotal

            items.append(
                {
                    "id": product_id,
                    "name": name,
                    "price": price,
                    "qty": qty,
                    "subtotal": subtotal,
                }
            )

    total = round(total, 2)

    conn.close()

    return render_template("billing.html", items=items, total=total)


@main_bp.route("/place_order", methods=["POST"])
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
            (product_id,),
        )
        price = cursor.fetchone()[0]
        total += price * qty

    total = round(total, 2)

    cursor.execute(
        """
        INSERT INTO orders(customer_id,total_amount,payment_method)
        VALUES(%s,%s,%s)
        RETURNING order_id
        """,
        (customer_id, total, payment_method),
    )
    order_id = cursor.fetchone()[0]

    for product_id, qty in cart.items():
        cursor.execute(
            "SELECT price FROM products WHERE product_id=%s",
            (product_id,),
        )
        price = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO order_items(order_id,product_id,quantity,price)
            VALUES(%s,%s,%s,%s)
            """,
            (order_id, product_id, qty, price),
        )

    conn.commit()
    conn.close()

    session["cart"] = {}

    return render_template("orderSuccess.html")


@main_bp.route("/orders")
def orders():
    customer_id = session.get("customer_id")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT order_id, order_date, total_amount
        FROM orders
        WHERE customer_id=%s
        ORDER BY order_date DESC
        """,
        (customer_id,),
    )

    orders = cursor.fetchall()

    conn.close()

    return render_template("orders.html", orders=orders)


@main_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

