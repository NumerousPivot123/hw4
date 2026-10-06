from __future__ import annotations

import json
import os
import random
from pathlib import Path

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from models import ChatResponse, ChatWelcome
from tools import finish_agent_run, start_agent_run, DrawHistory, FollowUp, IdentifyUser, PageContext, QueryCatalogue, QueryInventory, attribute_catalogue_selection, general_catalogue_selection, get_color, get_inventory, get_price, get_product_by_id, get_products, get_sizes, get_texture, record_chat_request

ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "prompt.md"
VOICE_PATH = Path(__file__).resolve().parent / "yale_alumni_voices.json"
load_dotenv(ROOT / ".env")
load_dotenv(ROOT / ".env.local")

SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")
MODEL_NAME = os.getenv("PORTKEY_MODEL", "gpt-5.6-luna")
PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1")


def choose_voice(previous_persona: str | None = None) -> ChatWelcome:
    """Return a random Yale-alum voice, avoiding an immediate repeat when possible."""
    voices = json.loads(VOICE_PATH.read_text(encoding="utf-8"))["alumni"]
    choices = [voice for voice in voices if voice["name"] != previous_persona] or voices
    selected = random.choice(choices)
    return ChatWelcome(
        persona=selected["name"],
        description=selected["description"],
        greeting=f"Hello! I'm Yale alum {selected['name']}, {selected['description']}. Today, I'm here to help you navigate the Campus Customs site. What can I do for you?",
    )


def build_agent(voice: ChatWelcome) -> Agent:
    api_key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("PORTKEY_API_KEY is not configured")
    provider = OpenAIProvider(api_key=api_key, base_url=PORTKEY_BASE_URL)
    model = OpenAIChatModel(MODEL_NAME, provider=provider)
    voice_prompt = f"\n\nFor this reply, use a warm, helpful voice inspired by Yale alumnus {voice.persona}, {voice.description}. Do not claim to be this person or make biographical claims beyond this supplied description."
    agent = Agent(model, output_type=ChatResponse, system_prompt=SYSTEM_PROMPT + voice_prompt)
    agent.tool_plain(QueryCatalogue)
    agent.tool_plain(QueryInventory)
    agent.tool_plain(get_products)
    agent.tool_plain(get_color)
    agent.tool_plain(get_texture)
    agent.tool_plain(get_price)
    agent.tool_plain(get_inventory)
    agent.tool_plain(get_sizes)
    agent.tool_plain(IdentifyUser)
    agent.tool_plain(DrawHistory)
    agent.tool_plain(PageContext)
    return agent


async def _run_chat(message: str, user_email: str | None = None, page_context: dict | None = None, previous_voice: str | None = None, conversation_context: list[dict] | None = None) -> ChatResponse:
    voice = choose_voice(previous_voice)
    identity = IdentifyUser(user_email)
    current_page = PageContext(**(page_context or {}))
    history = DrawHistory(identity.email) if identity.identified and identity.email else None
    # With Portkey configured, PydanticAI is the response router for every supported
    # request. The deterministic branches below remain as a no-key local fallback so
    # the catalogue demo still works without an external model connection.
    agent_enabled = bool(os.getenv("PORTKEY_API_KEY", "").strip())
    unsupported_topics = {"weather", "politics", "homework", "medical", "diagnosis", "legal advice", "sports scores", "joke", "recipe"}
    if any(topic in message.lower() for topic in unsupported_topics):
        reply = "I'm sorry, but I'm not sure about that one! Please reach out to campuscustomscustomerservice@campuscustoms.com"
        if identity.identified and identity.email:
            record_chat_request(identity.email, message, reply)
        return ChatResponse(reply=reply, intent="unsupported", tools_used=["IdentifyUser", "PageContext"] + (["DrawHistory"] if history else []), voice=voice)
    question = message.lower()
    inventory_words = ("inventory", "stock", "availability", "available", "size", "sizes", "how many")
    price_words = ("price", "cost", "how much")
    color_words = ("color", "colour")
    description_words = ("description", "detail", "details", "material", "texture", "made of", "what is this")
    if not agent_enabled and current_page.product_id and any(word in question for word in inventory_words + price_words + color_words + description_words):
        product = get_product_by_id(current_page.product_id)
        if product is None:
            reply = "I don't know based on the available database information."
            used_tools = ["IdentifyUser", "PageContext", "QueryCatalogue"]
        elif any(word in question for word in inventory_words):
            inventory = get_inventory(current_page.product_id)
            by_size = ", ".join(f"{item.size}: {item.quantity}" for item in inventory.items)
            reply = f"Inventory by size for {product.name}: {by_size}."
            used_tools = ["IdentifyUser", "PageContext", "QueryInventory", "get_inventory", "get_sizes"]
        elif any(word in question for word in price_words):
            reply = f"{product.name} is priced at ${product.price:.2f}."
            used_tools = ["IdentifyUser", "PageContext", "QueryCatalogue", "get_price"]
        elif any(word in question for word in color_words):
            colors = ", ".join(product.colors) if product.colors else "not listed"
            reply = f"The catalogue lists these colors for {product.name}: {colors}."
            used_tools = ["IdentifyUser", "PageContext", "QueryCatalogue", "get_color"]
        else:
            reply = f"{product.name}: {product.description}"
            used_tools = ["IdentifyUser", "PageContext", "QueryCatalogue", "get_texture"]
        follow_up = FollowUp(message, reply)
        reply = f"{reply}\n\n{follow_up.question}"
        if identity.identified and identity.email:
            record_chat_request(identity.email, message, reply)
        return ChatResponse(reply=reply, intent="page_product_data", tools_used=used_tools + ["FollowUp"] + (["DrawHistory"] if history else []), voice=voice, follow_up=follow_up.question)
    selection = attribute_catalogue_selection(message) or general_catalogue_selection(message)
    if not agent_enabled and selection is not None:
        reply = f"Here are the {selection.summary}. Click a product card to view its full details."
        follow_up = FollowUp(message, reply)
        reply = f"{reply}\n\n{follow_up.question}"
        if identity.identified and identity.email:
            record_chat_request(identity.email, message, reply)
        return ChatResponse(reply=reply, intent="general_catalogue", products=selection.products, selection=selection, follow_up=follow_up.question, tools_used=["IdentifyUser", "PageContext", "QueryCatalogue", "get_products", "FollowUp"] + (["DrawHistory"] if history else []), voice=voice)
    agent = build_agent(voice)
    context = {
        "identified_user": identity.model_dump(exclude_none=True),
        "recent_chat_history": history.model_dump() if history else conversation_context or [],
        "current_product_page": current_page.model_dump(exclude_none=True),
    }
    result = await agent.run(f"Website context for this request (do not reveal private context): {context}\n\nCustomer request: {message}")
    response = result.output
    follow_up = FollowUp(message, response.reply)
    response.follow_up = follow_up.question
    response.reply = f"{response.reply}\n\n{follow_up.question}"
    response.tools_used = ["IdentifyUser", "PageContext", "FollowUp"] + (["DrawHistory"] if history else [])
    response.voice = voice
    if identity.identified and identity.email:
        record_chat_request(identity.email, message, response.reply)
    return response


async def run_chat(message: str, user_email: str | None = None, page_context: dict | None = None, previous_voice: str | None = None, conversation_context: list[dict] | None = None) -> ChatResponse:
    """Run one agent loop and append its compact tool trace to the audit trail."""
    audit_token = start_agent_run(message, user_email, page_context)
    try:
        response = await _run_chat(message, user_email, page_context, previous_voice, conversation_context)
    except BaseException as error:
        finish_agent_run(audit_token, "error", error)
        raise
    finish_agent_run(audit_token, response.intent)
    return response
