from __future__ import annotations

import json
import re
import shutil
import sqlite3
import threading
from contextvars import ContextVar, Token
from functools import wraps
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from models import CatalogueQueryResult, CatalogueSelection, ChatHistory, ChatHistoryEntry, ColorResult, FollowUpResult, InventoryAnswer, InventoryItem, InventoryQueryResult, MaterialAnswer, PageContextResult, PriceResult, ProductAnswer, ProductListResult, SizeAnswer, TextureResult, UserIdentity

ROOT = Path(__file__).resolve().parent.parent
DATABASE = ROOT / "data" / "campus_customs.db"


# --- Audit trail: persistent, local records of each agent run and its tool calls ---

AUDIT_PATH = ROOT / "output" / "audit_trail.json"
_CURRENT_RUN: ContextVar[dict[str, Any] | None] = ContextVar("campus_customs_audit_run", default=None)
_LOCK = threading.Lock()


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _short(value: Any, limit: int = 700) -> str:
    """Return a compact, JSON-safe representation without retaining full payloads."""
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    try:
        text = json.dumps(value, default=str, ensure_ascii=False)
    except (TypeError, ValueError):
        text = str(value)
    return text if len(text) <= limit else f"{text[:limit]}…"


def start_agent_run(message: str, user_email: str | None, page_context: dict | None) -> Token:
    record = {
        "run_id": str(uuid4()),
        "started_at": _timestamp(),
        "request": message[:500],
        "logged_in": bool(user_email),
        "page_context": _short(page_context or {}, 250),
        "tools": [],
    }
    return _CURRENT_RUN.set(record)


def record_tool_call(name: str, args: tuple[Any, ...], kwargs: dict[str, Any], result: Any = None, error: Exception | None = None) -> None:
    run = _CURRENT_RUN.get()
    if run is None:
        return
    activity = {
        "time": _timestamp(),
        "tool": name,
        "args": _short({"args": args, "kwargs": kwargs}, 400),
    }
    if error is None:
        activity["result"] = _short(result)
    else:
        activity["error"] = f"{type(error).__name__}: {error}"[:700]
    run["tools"].append(activity)


def finish_agent_run(token: Token, stop_reason: str, error: BaseException | None = None) -> None:
    run = _CURRENT_RUN.get()
    if run is None:
        return
    run["finished_at"] = _timestamp()
    run["stop_reason"] = stop_reason
    if error is not None:
        run["error"] = f"{type(error).__name__}: {error}"[:700]
    with _LOCK:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        if AUDIT_PATH.exists():
            try:
                entries = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
                if not isinstance(entries, list):
                    raise ValueError("audit trail root is not a list")
            except (json.JSONDecodeError, OSError, ValueError):
                backup = AUDIT_PATH.with_name(f"{AUDIT_PATH.stem}.corrupt-{datetime.now():%Y%m%d%H%M%S}.json")
                shutil.copy2(AUDIT_PATH, backup)
                entries = []
        else:
            entries = []
        entries.append(run)
        AUDIT_PATH.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _CURRENT_RUN.reset(token)


# --- Catalogue and user tools ---


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def _product(row: sqlite3.Row, connection: sqlite3.Connection) -> ProductAnswer:
    inventory = connection.execute("SELECT quantity FROM inventory WHERE product_id = ?", (row["product_id"],)).fetchall()
    return ProductAnswer(
        product_id=row["product_id"], name=row["name"], garment_type=row["garment_type"],
        description=row["description"], price=row["price"], colors=json.loads(row["colors"]),
        material_texture=row["material_texture"] if "material_texture" in row.keys() else "",
        stock_total=sum(item["quantity"] for item in inventory),
        image_url="/images/" + Path(row["image_file_path"]).name,
    )


def search_products(query: str, limit: int = 8) -> list[ProductAnswer]:
    """Search the catalogue by product name, garment type, description, color, or tags."""
    connection = _connection()
    try:
        # Prefer a forgiving word-level search for conversational requests such
        # as "similar T-shirts" rather than requiring an exact database phrase.
        aliases = {"ben": "benjamin", "tee": "t", "tees": "t"}
        ignored = {"similar", "products", "product", "catalogue", "show", "me", "please", "pls", "what", "which", "do", "you", "have", "got", "any", "the", "a", "an", "for", "of", "with", "in", "to"}
        terms = []
        for raw_term in re.findall(r"[a-z0-9]+", query.lower()):
            term = aliases.get(raw_term, raw_term)
            if term.endswith("s") and len(term) > 3:
                term = term[:-1]
            if term not in ignored:
                terms.append(term)
        all_rows = connection.execute("SELECT * FROM catalogue ORDER BY name").fetchall()
        if terms:
            rows = []
            for row in all_rows:
                searchable = " ".join(str(row[field] or "") for field in ("product_id", "name", "garment_type", "description", "colors", "search_tags", "material_texture"))
                searchable_terms = set(re.findall(r"[a-z0-9]+", searchable.lower()))
                normalized_searchable = {word[:-1] if word.endswith("s") and len(word) > 3 else word for word in searchable_terms}
                if all(term in normalized_searchable for term in terms):
                    rows.append(row)
        else:
            rows = all_rows
        return [_product(row, connection) for row in rows[:limit]]
    finally:
        connection.close()


def get_product_by_id(product_id: str) -> ProductAnswer | None:
    """Return one complete catalogue record for a product page context."""
    connection = _connection()
    try:
        row = connection.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
        return _product(row, connection) if row is not None else None
    finally:
        connection.close()


def general_catalogue_selection(message: str) -> CatalogueSelection | None:
    """Return product cards for broad category requests before an LLM response is needed."""
    text = message.lower()
    categories = (
        ("hoodies", ("hoodie", "hooded")),
        ("sweatshirts and sweaters", ("sweatshirt", "sweater", "crewneck", "pullover", "quarter-zip", "1-4 zip", "1/4 zip")),
        ("shirts", ("t-shirt", "shirt", "tee", "long sleeve")),
        ("jackets", ("jacket", "bomber")),
        ("pants", ("pants", "sweatpants")),
    )
    general_markers = ("what", "which", "show", "browse", "do you have", "have you got", "got any")
    for label, keywords in categories:
        is_category_request = any(keyword in text for keyword in keywords)
        is_general = any(marker in text for marker in general_markers) or any(f"{keyword}s" in text for keyword in keywords)
        if not (is_category_request and is_general):
            continue
        clauses = " OR ".join("(lower(name) LIKE ? OR lower(garment_type) LIKE ? OR lower(description) LIKE ? OR lower(search_tags) LIKE ?)" for _ in keywords)
        params = [f"%{keyword}%" for keyword in keywords for _ in range(4)]
        connection = _connection()
        try:
            rows = connection.execute(f"SELECT * FROM catalogue WHERE {clauses} ORDER BY name", params).fetchall()
            products = [_product(row, connection) for row in rows]
        finally:
            connection.close()
        return CatalogueSelection(products=products, summary=f"{len(products)} {label} found")
    return None


def attribute_catalogue_selection(message: str) -> CatalogueSelection | None:
    """Return clickable cards when a customer asks for a known colour or material/texture."""
    text = message.lower()
    connection = _connection()
    try:
        rows = connection.execute("SELECT colors, material_texture FROM catalogue").fetchall()
    finally:
        connection.close()
    colors = {color.lower() for row in rows for color in json.loads(row["colors"])}
    materials = {term.lower() for row in rows for term in (row["material_texture"] or "").split(", ") if term}
    for attribute in sorted(colors | materials, key=len, reverse=True):
        if attribute and attribute in text:
            products = search_products(attribute, limit=102)
            label = "color" if attribute in colors else "material or texture"
            return CatalogueSelection(products=products, summary=f"{len(products)} products with {label} '{attribute}' found")
    return None


def get_inventory(product_query: str) -> InventoryAnswer:
    """Find inventory quantities by product and size for a named product or product ID."""
    connection = _connection()
    try:
        # Customer wording often differs from the catalogue: for example,
        # "Ben Franklin T-shirt" is stored as "Benjamin Franklin T Shirt".
        # Normalize those harmless wording differences before matching, while
        # still selecting the actual catalogue rows as the source of truth.
        aliases = {"ben": "benjamin", "tee": "t"}
        ignored = {"how", "many", "is", "are", "available", "availability", "in", "stock", "inventory", "size", "sizes", "large", "larges", "medium", "mediums", "small", "smalls", "extra", "xlarge", "xl", "xs", "xxl", "the", "a", "an", "for", "of", "does", "do", "you", "have", "got"}
        query_terms = [aliases.get(term, term) for term in re.findall(r"[a-z0-9]+", product_query.lower()) if term not in ignored]
        catalogue_rows = connection.execute("SELECT product_id, name, garment_type, description, search_tags FROM catalogue").fetchall()
        matches = []
        for catalogue_row in catalogue_rows:
            searchable = " ".join(str(catalogue_row[field] or "") for field in ("product_id", "name", "garment_type", "description", "search_tags"))
            searchable_terms = set(re.findall(r"[a-z0-9]+", searchable.lower()))
            if query_terms and all(term in searchable_terms for term in query_terms):
                matches.append(catalogue_row["product_id"])
        if not matches:
            matches = [product_query.strip()]
        placeholders = ",".join("?" for _ in matches)
        rows = connection.execute(
            f"""SELECT c.product_id, c.name, i.size, i.quantity FROM catalogue c JOIN inventory i ON i.product_id = c.product_id WHERE c.product_id IN ({placeholders}) ORDER BY c.name, i.size""",
            matches,
        ).fetchall()
        items = [InventoryItem(product_id=row["product_id"], product_name=row["name"], size=row["size"], quantity=row["quantity"]) for row in rows]
        summary = "No matching inventory was found." if not items else f"Found {len(items)} size inventory records."
        return InventoryAnswer(items=items, summary=summary)
    finally:
        connection.close()


def get_sizes(product_query: str) -> SizeAnswer:
    """Return available quantities grouped by size for a named product or product ID."""
    inventory = get_inventory(product_query)
    name = inventory.items[0].product_name if inventory.items else product_query
    return SizeAnswer(product_name=name, sizes={item.size: item.quantity for item in inventory.items}, summary=inventory.summary)


def find_by_material(material: str) -> MaterialAnswer:
    """Find products whose catalogue description or tags mention a material."""
    products = search_products(material, limit=20)
    return MaterialAnswer(products=[product.name for product in products], summary=f"Found {len(products)} products mentioning {material}.")


def find_by_color(color: str) -> ColorResult:
    """Find products associated with a color and return their catalogue colors."""
    products = search_products(color, limit=20)
    colors = sorted({item for product in products for item in product.colors})
    return ColorResult(products=[product.name for product in products], colors=colors, summary=f"Found {len(products)} products associated with {color}.")


def QueryCatalogue(question: str) -> CatalogueQueryResult:
    """Use the catalogue field for clothing, color, price, description, texture, and other product questions."""
    products = search_products(question, limit=50)
    return CatalogueQueryResult(products=products, summary=f"Found {len(products)} catalogue products matching the question.")


def QueryInventory(question: str) -> InventoryQueryResult:
    """Use the inventory field for stock, availability, and quantity questions."""
    result = get_inventory(question)
    return InventoryQueryResult(items=result.items, summary=result.summary)


def get_products(product_query: str) -> ProductListResult:
    """Use catalogue data to answer requests for specific products."""
    products = search_products(product_query, limit=50)
    return ProductListResult(products=products, summary=f"Found {len(products)} matching products.")


def get_color(color_or_product: str) -> ColorResult:
    """Use catalogue data to answer color questions."""
    return find_by_color(color_or_product)


def get_texture(texture_or_product: str) -> TextureResult:
    """Use catalogue descriptions and tags to answer texture or material questions; never infer unlisted attributes."""
    products = search_products(texture_or_product, limit=20)
    evidence = [f"{product.name}: {product.description}" for product in products]
    return TextureResult(products=[product.name for product in products], evidence=evidence, summary=f"Found {len(products)} products with catalogue text related to {texture_or_product}.")


def get_price(product_or_query: str) -> PriceResult:
    """Use catalogue data to answer product price questions."""
    products = search_products(product_or_query, limit=12)
    prices = {product.name: product.price for product in products}
    return PriceResult(products=prices, summary=f"Found prices for {len(prices)} matching products.")


def IdentifyUser(email: str | None) -> UserIdentity:
    """Identify a logged-in chatter by the verified email supplied by the website."""
    if not email:
        return UserIdentity(identified=False)
    connection = _connection()
    try:
        user = connection.execute("SELECT first_name, last_name, email FROM users WHERE lower(email) = lower(?)", (email,)).fetchone()
        if user is None:
            return UserIdentity(identified=False)
        return UserIdentity(identified=True, first_name=user["first_name"], last_name=user["last_name"], email=user["email"])
    finally:
        connection.close()


def DrawHistory(email: str) -> ChatHistory:
    """Read the recognized logged-in user's prior chatbot requests for context."""
    connection = _connection()
    try:
        user = connection.execute("SELECT email, chat_history FROM users WHERE lower(email) = lower(?)", (email,)).fetchone()
        if user is None:
            return ChatHistory(email=email, entries=[])
        raw = json.loads(user["chat_history"] or "[]")
        return ChatHistory(email=user["email"], entries=[ChatHistoryEntry(**entry) for entry in raw[-20:]])
    finally:
        connection.close()


def PageContext(product_id: str | None = None, product_name: str | None = None) -> PageContextResult:
    """Resolve the product page currently open in the website, if one was supplied."""
    connection = _connection()
    try:
        row = None
        if product_id:
            row = connection.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
        elif product_name:
            row = connection.execute("SELECT * FROM catalogue WHERE name LIKE ? ORDER BY name LIMIT 1", (f"%{product_name}%",)).fetchone()
        if row is None:
            return PageContextResult()
        stock = connection.execute("SELECT COALESCE(SUM(quantity), 0) AS total FROM inventory WHERE product_id = ?", (row["product_id"],)).fetchone()["total"]
        return PageContextResult(product_id=row["product_id"], product_name=row["name"], description=row["description"], price=row["price"], stock_total=stock)
    finally:
        connection.close()


def record_chat_request(email: str, request: str, reply: str | None = None) -> None:
    """Append one customer message and its assistant reply to a user's chat history."""
    connection = _connection()
    try:
        user = connection.execute("SELECT chat_history FROM users WHERE lower(email) = lower(?)", (email,)).fetchone()
        if user is None:
            return
        history = json.loads(user["chat_history"] or "[]")
        history.append({"timestamp": datetime.now(timezone.utc).isoformat(), "request": request[:500], "reply": reply[:4000] if reply else None})
        connection.execute("UPDATE users SET chat_history = ? WHERE lower(email) = lower(?)", (json.dumps(history[-50:]), email))
        connection.commit()
    finally:
        connection.close()


def FollowUp(question: str, response: str) -> FollowUpResult:
    """Create one concise, catalogue-related follow-up question after an answer."""
    if "stock" in response.lower() or "inventory" in response.lower():
        next_question = "Would you like to see other colors or similar styles that are currently in stock?"
    elif "price" in response.lower() or "$" in response:
        next_question = "Would you like to compare this with products at a different price point?"
    else:
        next_question = "Would you like to see similar products from the catalogue?"
    return FollowUpResult(question=next_question)


def _audited_tool(name: str, function):
    """Keep PydanticAI tool signatures while recording concise local audit data."""
    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            result = function(*args, **kwargs)
        except Exception as error:
            record_tool_call(name, args, kwargs, error=error)
            raise
        record_tool_call(name, args, kwargs, result=result)
        return result
    return wrapped


for _tool_name in (
    "QueryCatalogue", "QueryInventory", "get_products", "get_color", "get_texture",
    "get_price", "get_inventory", "get_sizes", "IdentifyUser", "DrawHistory",
    "PageContext", "FollowUp", "get_product_by_id", "general_catalogue_selection",
    "attribute_catalogue_selection",
):
    globals()[_tool_name] = _audited_tool(_tool_name, globals()[_tool_name])
