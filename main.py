from webapp import create_app


app = create_app()


if __name__ == "__main__":
    # For local development. In production, use a WSGI/ASGI server.
    app.run(debug=True)
