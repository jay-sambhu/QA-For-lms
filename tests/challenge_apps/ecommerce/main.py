"""
Challenge App B — E-Commerce Application with Catalog, Cart, Discounts, and Checkout.
Defects:
1. POST /checkout with item 404 throws HTTP 500 (API/Functional)
2. Quantity update JS error on /cart (JavaScript uncaught TypeError)
3. Discount OFF50 increases cart total price instead of deducting 50% (Calculation)
"""
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI(title="Challenge E-Commerce App")

products = [
    {"id": 101, "title": "Wireless Earbuds", "price": 49.99, "stock": 15},
    {"id": 102, "title": "Smart Watch", "price": 199.99, "stock": 8},
    {"id": 404, "title": "Defective Gadget", "price": 9.99, "stock": 99},
]

cart = [{"id": 101, "title": "Wireless Earbuds", "price": 49.99, "qty": 1}]


@app.get("/", response_class=HTMLResponse)
def catalog():
    prods_html = "".join([
        f"<div class='product'><h3>{p['title']}</h3><p>Price: ${p['price']}</p>"
        f"<a href='/product/{p['id']}'>Details</a> | "
        f"<a href='/cart/add/{p['id']}' id='add-{p['id']}'>Add to Cart</a></div>"
        for p in products
    ])
    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>ShopSphere - Catalog</title></head>
    <body>
        <h1>ShopSphere Products</h1>
        <p><a href="/cart" id="view-cart">View Cart ({len(cart)} items)</a></p>
        <div id="catalog">{prods_html}</div>
    </body>
    </html>
    """


@app.get("/product/{prod_id}", response_class=HTMLResponse)
def product_details(prod_id: int):
    prod = next((p for p in products if p["id"] == prod_id), None)
    if not prod:
        return HTMLResponse("<h1>Product Not Found</h1>", status_code=404)
    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>{prod['title']} - Details</title></head>
    <body>
        <h1>{prod['title']}</h1>
        <p>Price: ${prod['price']}</p>
        <p>Stock: {prod['stock']} units available</p>
        <a href="/cart/add/{prod['id']}" id="add-to-cart">Add to Cart</a> | 
        <a href="/">Back to Shop</a>
    </body>
    </html>
    """


@app.get("/cart", response_class=HTMLResponse)
def view_cart():
    items_html = "".join([
        f"<tr><td>{i['title']}</td><td>${i['price']}</td><td>{i['qty']}</td>"
        f"<td><button onclick='updateQtyNullError()' id='update-qty-{i['id']}'>Update Qty</button></td></tr>"
        for i in cart
    ])
    subtotal = sum(i['price'] * i['qty'] for i in cart)
    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>ShopSphere - Cart</title></head>
    <body>
        <h1>Shopping Cart</h1>
        <table border="1">
            <thead><tr><th>Product</th><th>Price</th><th>Qty</th><th>Action</th></tr></thead>
            <tbody>{items_html}</tbody>
        </table>
        <h3>Total: $<span id="total-price">{subtotal:.2f}</span></h3>
        <form action="/cart/discount" method="post">
            <input type="text" id="coupon" name="coupon" placeholder="Discount Code (OFF50)" />
            <button type="submit" id="apply-discount">Apply Coupon</button>
        </form>
        <br/>
        <form action="/checkout" method="post">
            <button type="submit" id="btn-checkout">Proceed to Checkout</button>
        </form>

        <script>
        function updateQtyNullError() {{
            // DEFECT: Uncaught TypeError when update button clicked!
            var obj = null;
            console.log(obj.quantity);
        }}
        </script>
    </body>
    </html>
    """


@app.get("/cart/add/{prod_id}")
def add_to_cart(prod_id: int):
    prod = next((p for p in products if p["id"] == prod_id), None)
    if prod:
        cart.append({"id": prod["id"], "title": prod["title"], "price": prod["price"], "qty": 1})
    return RedirectResponse(url="/cart", status_code=303)


@app.post("/cart/discount", response_class=HTMLResponse)
def apply_discount(coupon: str = Form(...)):
    # DEFECT: Coupon OFF50 doubles the price instead of deducting 50%!
    subtotal = sum(i['price'] * i['qty'] for i in cart)
    if coupon == "OFF50":
        new_total = subtotal * 1.5  # Calculation Defect!
    else:
        new_total = subtotal

    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>ShopSphere - Cart</title></head>
    <body>
        <h1>Shopping Cart</h1>
        <h2>Discount Applied: {coupon}</h2>
        <h3>Total: $<span id="total-price">{new_total:.2f}</span> (Original: ${subtotal:.2f})</h3>
        <a href="/cart">Back to Cart</a>
    </body>
    </html>
    """


@app.post("/checkout")
def checkout():
    # DEFECT: If cart contains defective item 404, throw 500 error!
    if any(i["id"] == 404 for i in cart):
        raise HTTPException(status_code=500, detail="Checkout Failed: Payment Gateway Failure for Item 404")
    cart.clear()
    return HTMLResponse("<h1>Checkout Successful! Order #8812</h1>", status_code=200)
