"""Read-only Campus Customs catalogue API.

First-time setup from hw4 (creates the virtual environment):
    python -m venv .venv
    .venv\\Scripts\\python -m pip install -r requirements.txt
    copy .env.example .env   (then fill in your values)

Run from hw4/backend:
    ..\\.venv\\Scripts\\python -m uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import json
import asyncio
import base64
import binascii
import hashlib
import hmac
import os
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from agent import choose_voice, run_chat
from models import CartResult, ChatHistory, ChatPageContext, ChatResponse, ChatTurn, ChatWelcome

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA_DIR = ROOT / "data"
DATABASE = DATA_DIR / "campus_customs.db"

app = FastAPI(title="Campus Customs Catalogue API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
app.mount("/images", StaticFiles(directory=DATA_DIR / "products"), name="images")

HASH_N = 2**14
HASH_R = 8
HASH_P = 1
HASH_LENGTH = 32
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "aihw516!")


class RegisterRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    user_email: EmailStr | None = None
    page_context: ChatPageContext | None = None
    previous_voice: str | None = Field(default=None, max_length=120)
    conversation_context: list[ChatTurn] = Field(default_factory=list, max_length=8)


class CartRequest(BaseModel):
    email: EmailStr
    product_id: str = Field(min_length=1, max_length=200)
    size: str = Field(min_length=1, max_length=20)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=HASH_N, r=HASH_R, p=HASH_P, dklen=HASH_LENGTH
    )
    encode = lambda value: base64.urlsafe_b64encode(value).decode("ascii")
    return f"scrypt${HASH_N}${HASH_R}${HASH_P}${encode(salt)}${encode(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        parts = stored.split("$")
        if parts[0] == "scrypt":
            _, n, r, p, salt_text, digest_text = parts
            salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
            expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
            actual = hashlib.scrypt(
                password.encode("utf-8"), salt=salt, n=int(n), r=int(r), p=int(p), dklen=len(expected)
            )
            return hmac.compare_digest(actual, expected)
        if parts[0] == "pbkdf2_sha256":
            _, rounds, salt_text, digest_text = parts
            expected = base64.b64decode(digest_text + "===")
            actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_text.encode("utf-8"), int(rounds), len(expected))
            return hmac.compare_digest(actual, expected)
        return False
    except (ValueError, TypeError, binascii.Error):
        return False


@contextmanager
def database():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


def ensure_chat_history_field() -> None:
    with sqlite3.connect(DATABASE) as connection:
        fields = {row[1] for row in connection.execute("PRAGMA table_info(users)")}
        if "chat_history" not in fields:
            connection.execute("ALTER TABLE users ADD COLUMN chat_history TEXT NOT NULL DEFAULT '[]'")
            connection.commit()


def ensure_cart_field() -> None:
    with sqlite3.connect(DATABASE) as connection:
        fields = {row[1] for row in connection.execute("PRAGMA table_info(users)")}
        if "cart" not in fields:
            connection.execute("ALTER TABLE users ADD COLUMN cart TEXT NOT NULL DEFAULT '[]'")
            connection.commit()


def material_texture_from_catalogue_text(description: str, tags: str) -> str:
    """Keep only material/texture terms that are already stated in catalogue text."""
    text = f"{description} {tags}".lower()
    terms = (
        ("fleece", ("fleece",)),
        ("double-knit", ("double-knit", "double knit")),
        ("tri-blend", ("tri-blend", "tri blend")),
        ("heathered", ("heathered",)),
        ("heavyweight", ("heavyweight",)),
        ("cotton-style", ("cotton-style",)),
    )
    return ", ".join(label for label, matches in terms if any(match in text for match in matches))


def ensure_material_texture_field() -> None:
    with sqlite3.connect(DATABASE) as connection:
        fields = {row[1] for row in connection.execute("PRAGMA table_info(catalogue)")}
        if "material_texture" not in fields:
            connection.execute("ALTER TABLE catalogue ADD COLUMN material_texture TEXT NOT NULL DEFAULT ''")
        rows = connection.execute("SELECT product_id, description, search_tags, material_texture FROM catalogue").fetchall()
        for product_id, description, tags, material_texture in rows:
            if not material_texture:
                connection.execute(
                    "UPDATE catalogue SET material_texture = ? WHERE product_id = ?",
                    (material_texture_from_catalogue_text(description or "", tags or ""), product_id),
                )
        connection.commit()


ensure_chat_history_field()
ensure_cart_field()
ensure_material_texture_field()


def serialize_product(row: sqlite3.Row, inventory: list[sqlite3.Row]) -> dict:
    product = dict(row)
    product["colors"] = json.loads(product["colors"])
    product["image_url"] = "/images/" + Path(product["image_file_path"]).name
    product["inventory"] = [{"size": item["size"], "quantity": item["quantity"]} for item in inventory]
    product["stock_total"] = sum(item["quantity"] for item in inventory)
    return product


def product_from_row(connection: sqlite3.Connection, row: sqlite3.Row) -> dict:
    inventory = connection.execute(
        "SELECT size, quantity FROM inventory WHERE product_id = ? ORDER BY size",
        (row["product_id"],),
    ).fetchall()
    return serialize_product(row, inventory)


@app.get("/api/health")
def health() -> dict:
    return {"ok": DATABASE.exists(), "database": DATABASE.name}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(body: ChatRequest) -> ChatResponse:
    try:
        return await asyncio.wait_for(run_chat(body.message, str(body.user_email) if body.user_email else None, body.page_context.model_dump(exclude_none=True) if body.page_context else None, body.previous_voice, [turn.model_dump() for turn in body.conversation_context]), timeout=60)
    except asyncio.TimeoutError:
        return ChatResponse(reply="Timeout - please reach out to campuscustomscustomerservice@campuscustoms.com to answer your request", intent="timeout", timeout=True)


@app.get("/api/chat/welcome", response_model=ChatWelcome)
def chat_welcome(previous_voice: str | None = Query(default=None, max_length=120)) -> ChatWelcome:
    """Choose a fresh Yale-alum persona whenever a chat panel is opened."""
    return choose_voice(previous_voice)


@app.get("/api/chat/history", response_model=ChatHistory)
def chat_history(email: EmailStr = Query(...)) -> ChatHistory:
    """Reload saved chat exchanges for the remembered logged-in account."""
    from tools import DrawHistory
    return DrawHistory(str(email))


def cart_products(email: str) -> CartResult:
    with database() as connection:
        user = connection.execute("SELECT cart FROM users WHERE lower(email) = lower(?)", (email,)).fetchone()
        if user is None:
            raise HTTPException(status_code=404, detail="Account not found")
        items = json.loads(user["cart"] or "[]")
        products = []
        for item in items:
            row = connection.execute("SELECT * FROM catalogue WHERE product_id = ?", (item["product_id"],)).fetchone()
            if row is not None:
                product = product_from_row(connection, row)
                product["selected_size"] = item.get("size")
                product["cart_quantity"] = item.get("quantity", 1)
                products.append(product)
    return CartResult(email=email, products=products)


@app.get("/api/cart", response_model=CartResult)
def get_cart(email: EmailStr = Query(...)) -> CartResult:
    return cart_products(str(email))


@app.post("/api/cart", response_model=CartResult)
def add_to_cart(body: CartRequest) -> CartResult:
    email = str(body.email).lower()
    size = body.size.strip().upper()
    with database() as connection:
        user = connection.execute("SELECT cart FROM users WHERE lower(email) = lower(?)", (email,)).fetchone()
        product = connection.execute("SELECT product_id FROM catalogue WHERE product_id = ?", (body.product_id,)).fetchone()
        inventory = connection.execute("SELECT quantity FROM inventory WHERE product_id = ? AND upper(size) = ?", (body.product_id, size)).fetchone()
        if user is None:
            raise HTTPException(status_code=404, detail="Account not found")
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        if inventory is None or inventory["quantity"] <= 0:
            raise HTTPException(status_code=400, detail=f"Selected size {size} is unavailable")
        items = json.loads(user["cart"] or "[]")
        existing = next((item for item in items if item["product_id"] == body.product_id and item.get("size") == size), None)
        if existing is None:
            items.append({"product_id": body.product_id, "size": size, "quantity": 1})
        else:
            existing["quantity"] += 1
        connection.execute("UPDATE users SET cart = ? WHERE lower(email) = lower(?)", (json.dumps(items), email))
        connection.commit()
    return cart_products(email)


@app.delete("/api/cart/{product_id}", response_model=CartResult)
def remove_from_cart(product_id: str, email: EmailStr = Query(...), size: str | None = Query(default=None, max_length=20)) -> CartResult:
    email_text = str(email).lower()
    with database() as connection:
        user = connection.execute("SELECT cart FROM users WHERE lower(email) = lower(?)", (email_text,)).fetchone()
        if user is None:
            raise HTTPException(status_code=404, detail="Account not found")
        normalized_size = size.strip().upper() if size else None
        items = [item for item in json.loads(user["cart"] or "[]") if not (item["product_id"] == product_id and (normalized_size is None or item.get("size") == normalized_size))]
        connection.execute("UPDATE users SET cart = ? WHERE lower(email) = lower(?)", (json.dumps(items), email_text))
        connection.commit()
    return cart_products(email_text)


@app.get("/api/products")
def list_products(q: str | None = Query(default=None)) -> dict:
    """Return all catalogue products, optionally filtered by product text."""
    with database() as connection:
        if q and q.strip():
            term = f"%{q.strip()}%"
            rows = connection.execute(
                """
                SELECT * FROM catalogue
                WHERE name LIKE ? OR garment_type LIKE ? OR description LIKE ? OR search_tags LIKE ?
                ORDER BY name
                """,
                (term, term, term, term),
            ).fetchall()
        else:
            rows = connection.execute("SELECT * FROM catalogue ORDER BY name").fetchall()
        products = [product_from_row(connection, row) for row in rows]
    return {"count": len(products), "products": products}


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> dict:
    with database() as connection:
        row = connection.execute(
            "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        return product_from_row(connection, row)


@app.post("/api/auth/register")
def register_user(body: RegisterRequest) -> dict:
    email = str(body.email).lower()
    with database() as connection:
        existing = connection.execute("SELECT id FROM users WHERE lower(email) = ?", (email,)).fetchone()
        if existing is not None:
            raise HTTPException(status_code=409, detail="An account with that email already exists")
        connection.execute(
            """
            INSERT INTO users (name, email, password_hash, first_name, last_name)
            VALUES (?, ?, ?, ?, ?)
            """,
            (f"{body.first_name} {body.last_name}", email, hash_password(body.password), body.first_name, body.last_name),
        )
        connection.commit()
    return {"ok": True, "message": "Account created"}


@app.post("/api/auth/login")
def login_user(body: LoginRequest) -> dict:
    email = str(body.email).lower()
    with database() as connection:
        user = connection.execute(
            "SELECT id, first_name, last_name, email, password_hash FROM users WHERE lower(email) = ?",
            (email,),
        ).fetchone()
    if user is None or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Account not found")
    return {
        "ok": True,
        "message": "Login successful",
        "user": {"id": user["id"], "first_name": user["first_name"], "last_name": user["last_name"], "email": user["email"]},
    }


@app.get("/api/admin/users")
def list_users_for_admin(x_admin_password: str | None = Header(default=None)) -> dict:
    """Protected user-management view; password hashes are never returned."""
    if x_admin_password is None or not secrets.compare_digest(x_admin_password, ADMIN_PASSWORD):
        raise HTTPException(status_code=403, detail="Admin authentication required")
    with database() as connection:
        users = connection.execute(
            "SELECT id, first_name, last_name, email, created_at FROM users ORDER BY id"
        ).fetchall()
    return {"users": [dict(user) for user in users]}
