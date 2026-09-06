"""
Challenge App A — CRUD Application with Auth, Search, Pagination, and Validation.
Defects:
1. Delete on item 999 raises HTTP 500 (Functional)
2. Search page has horizontal overflow (+5000px) (UI)
3. Create form accepts negative price -100 without validation error (Validation)
"""
from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

app = FastAPI(title="Challenge CRUD App")

# In-memory database
items_db = [
    {"id": 1, "name": "Laptop Pro", "category": "Electronics", "price": 1200.0},
    {"id": 2, "name": "Wireless Mouse", "category": "Accessories", "price": 25.0},
    {"id": 3, "name": "Mechanical Keyboard", "category": "Accessories", "price": 95.0},
    {"id": 4, "name": "4K Monitor", "category": "Electronics", "price": 350.0},
]


@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>CRUD App - Login</title></head>
    <body>
        <h1>Inventory System Login</h1>
        <form action="/login" method="post">
            <label for="username">Username:</label>
            <input type="text" id="username" name="username" required /><br/>
            <label for="password">Password:</label>
            <input type="password" id="password" name="password" required /><br/>
            <button type="submit" id="login-btn">Login</button>
        </form>
        <p><a href="/items" id="guest-view">View Public Items</a></p>
    </body>
    </html>
    """


@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    if username == "admin" and password == "secret":
        return RedirectResponse(url="/dashboard", status_code=303)
    return HTMLResponse("<h3>Invalid Credentials</h3>", status_code=401)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>CRUD App - Dashboard</title></head>
    <body>
        <h1>Inventory Dashboard</h1>
        <nav>
            <a href="/items" id="nav-items">Items List</a> | 
            <a href="/items/create" id="nav-create">Create Item</a> | 
            <a href="/items/search" id="nav-search">Search Inventory</a>
        </nav>
        <p>Total Items Registered: 4</p>
    </body>
    </html>
    """


@app.get("/items", response_class=HTMLResponse)
def list_items(page: int = 1):
    rows = "".join([
        f"<tr><td>{item['id']}</td><td>{item['name']}</td><td>{item['category']}</td><td>${item['price']}</td>"
        f"<td><a href='/items/{item['id']}/edit'>Edit</a> | <a href='/items/{item['id']}/delete'>Delete</a></td></tr>"
        for item in items_db
    ])
    # Add a buggy link for item 999
    rows += "<tr><td>999</td><td>Broken Item</td><td>Buggy</td><td>$0</td><td><a href='/items/999/delete' id='del-999'>Delete Buggy Item</a></td></tr>"

    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>CRUD App - Items List</title></head>
    <body>
        <h1>Inventory Items (Page {page})</h1>
        <table border="1">
            <thead><tr><th>ID</th><th>Name</th><th>Category</th><th>Price</th><th>Actions</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
        <p><a href="/items/create" id="btn-add">Add New Item</a></p>
    </body>
    </html>
    """


@app.get("/items/create", response_class=HTMLResponse)
def create_item_form():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>CRUD App - Create Item</title></head>
    <body>
        <h1>Create Inventory Item</h1>
        <form action="/items/create" method="post">
            <label for="name">Item Name:</label>
            <input type="text" id="name" name="name" required /><br/>
            <label for="category">Category:</label>
            <input type="text" id="category" name="category" required /><br/>
            <label for="price">Price ($):</label>
            <input type="number" id="price" name="price" required /><br/>
            <button type="submit" id="save-item">Save Item</button>
        </form>
    </body>
    </html>
    """


@app.post("/items/create")
def create_item_submit(name: str = Form(...), category: str = Form(...), price: float = Form(...)):
    # DEFECT: Allows negative price without validation!
    new_id = len(items_db) + 1
    items_db.append({"id": new_id, "name": name, "category": category, "price": price})
    return RedirectResponse(url="/items", status_code=303)


@app.get("/items/{item_id}/delete")
def delete_item(item_id: int):
    # DEFECT: Deleting item 999 triggers an unhandled 500 error!
    if item_id == 999:
        raise HTTPException(status_code=500, detail="Database Constraint Failure: Hardcoded Bug in Item 999")
    global items_db
    items_db = [i for i in items_db if i["id"] != item_id]
    return RedirectResponse(url="/items", status_code=303)


@app.get("/items/search", response_class=HTMLResponse)
def search_items(q: str = ""):
    # DEFECT: Horizontal overflow element on search page
    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>CRUD App - Search</title></head>
    <body>
        <h1>Search Inventory</h1>
        <form action="/items/search" method="get">
            <input type="text" id="q" name="q" value="{q}" />
            <button type="submit" id="search-btn">Search</button>
        </form>
        <div style="width: 6000px; background: red; height: 30px;" id="overflow-box">
            Defect Overflow Element Stretching Page Width
        </div>
    </body>
    </html>
    """
