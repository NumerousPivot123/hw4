from __future__ import annotations

from pydantic import BaseModel, Field


class InventoryItem(BaseModel):
    product_id: str
    product_name: str
    size: str
    quantity: int


class InventoryAnswer(BaseModel):
    items: list[InventoryItem] = Field(default_factory=list)
    summary: str


class SizeAnswer(BaseModel):
    product_name: str
    sizes: dict[str, int] = Field(default_factory=dict)
    summary: str


class MaterialAnswer(BaseModel):
    products: list[str] = Field(default_factory=list)
    summary: str


class ColorAnswer(BaseModel):
    products: list[str] = Field(default_factory=list)
    colors: list[str] = Field(default_factory=list)
    summary: str


class ProductAnswer(BaseModel):
    product_id: str
    name: str
    garment_type: str
    description: str
    price: float
    colors: list[str] = Field(default_factory=list)
    material_texture: str = ""
    stock_total: int
    image_url: str


class CatalogueQueryResult(BaseModel):
    products: list[ProductAnswer] = Field(default_factory=list)
    summary: str


class InventoryQueryResult(BaseModel):
    items: list[InventoryItem] = Field(default_factory=list)
    summary: str


class ProductListResult(BaseModel):
    products: list[ProductAnswer] = Field(default_factory=list)
    summary: str


class ColorResult(BaseModel):
    products: list[str] = Field(default_factory=list)
    colors: list[str] = Field(default_factory=list)
    summary: str


class TextureResult(BaseModel):
    products: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    summary: str


class PriceResult(BaseModel):
    products: dict[str, float] = Field(default_factory=dict)
    summary: str


class CatalogueSelection(BaseModel):
    products: list[ProductAnswer] = Field(default_factory=list)
    summary: str


class ChatResponse(BaseModel):
    reply: str
    intent: str = "catalogue"
    products: list[ProductAnswer] = Field(default_factory=list)
    selection: CatalogueSelection | None = None
    follow_up: str | None = None
    timeout: bool = False
    voice: "ChatWelcome | None" = None
    tools_used: list[str] = Field(default_factory=list)


class ChatWelcome(BaseModel):
    persona: str
    description: str
    greeting: str


class TimeoutResponse(BaseModel):
    timeout: bool = True
    message: str


class FollowUpResult(BaseModel):
    question: str
    tools_used: list[str] = Field(default_factory=list)


class UserIdentity(BaseModel):
    identified: bool
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None


class ChatHistoryEntry(BaseModel):
    timestamp: str
    request: str
    reply: str | None = None


class ChatTurn(BaseModel):
    role: str
    text: str


class ChatHistory(BaseModel):
    email: str
    entries: list[ChatHistoryEntry] = Field(default_factory=list)


class PageContextResult(BaseModel):
    product_id: str | None = None
    product_name: str | None = None
    description: str | None = None
    price: float | None = None
    stock_total: int | None = None


class ChatPageContext(BaseModel):
    product_id: str | None = None
    product_name: str | None = None


class CartItem(BaseModel):
    product_id: str
    size: str | None = None
    quantity: int = 1


class CartProduct(ProductAnswer):
    selected_size: str | None = None
    cart_quantity: int = 1


class CartResult(BaseModel):
    email: str
    products: list[CartProduct] = Field(default_factory=list)
