# Harness Summary

## Summary of relevant data fields

### Catalogue

A summary of all available products, with information about the type of clothing, color, price, and the normalized `material_texture` field.

### Inventory

A summary of product inventory by product ID with the number of products available for that item by size.

### Users

A list of people who have used the catalogue and the date and time they did so, with a field for e-mail information that is currently redacted.

## Account security measures

- Fields saved for each user: first name, last name, email, password hash, and account creation timestamp. The database also retains the existing user ID.
- Passwords are never stored as plaintext. They are hashed with salted, one-way `scrypt` hashing and a per-user random salt.
- Login compares the submitted password to the stored hash using a constant-time comparison and returns only a safe user summary.
- Password confirmation is checked in the frontend before registration is submitted.
- Duplicate email addresses are rejected during registration.
- Passwords must be at least eight characters long and are never placed in response bodies, logs, or the frontend catalogue.
- The protected admin user view requires the configured `X-Admin-Password` header and uses `aihw516!` for the local assignment configuration. It returns no password hashes.
- The admin view is intentionally read-only and does not expose the one-way password values; production deployments should move the admin password to a secret environment variable.
- The API uses parameterized SQL queries and does not expose the SQLite database file directly.
- Login failures use the requested `Error: Account not found` response and do not reveal whether an email or password was incorrect.

## PydanticAI agent and FastAPI

- `backend/main.py` creates the FastAPI app, serves the existing product/image and authentication routes, and exposes `POST /api/chat` for chatbot messages.
- `backend/agent.py` loads `backend/prompts/prompt.md`, configures the Portkey OpenAI-compatible provider with the `gpt-5.6-luna` model, constructs the PydanticAI agent, and returns the structured `ChatResponse` model.
- `backend/tools.py` provides read-only SQLite tools for product search, inventory, sizes, material, and color questions.
- `backend/models.py` defines the structured inventory, size, material, color, product, and chat response types used by the agent.
- The React chat button sends each message to FastAPI and displays the rotating Yale-alumnus greeting and agent reply when the panel opens.
- FastAPI validates request and response shapes, handles CORS for the Vite development ports, and keeps the database/tool calls on the server.
- The agent uses only the supplied database tools and follows the voice and safety rules loaded from `prompt.md`.

## Chatbot catalogue and stock tools

- `QueryCatalogue` — handles questions about clothing, color, product descriptions, texture wording, and price using the `catalogue` data field.
- `QueryInventory` — handles inventory, stock, availability, and quantity questions using the `inventory` data field.
- `get_products` — answers requests for specific products using catalogue data.
- `get_color` — answers color questions using catalogue data.
- `get_texture` — answers texture or material questions only when the information appears in catalogue descriptions or tags.
- `get_price` — answers price questions using catalogue data.
- `get_inventory` — returns inventory records for a product using the inventory data field.
- `get_sizes` — returns size-level quantities using the inventory data field.

The tool routing is deliberate: product-specific information always goes to the `catalogue` field, while inventory-specific information—including sizes and stock—goes to the `inventory` field. The prompt instructs the agent to use only database information and say it does not know when the database does not contain an answer.

The catalogue also stores normalized material and texture terms in `material_texture`; material searches use that field while retaining the original description and tag evidence.

## General catalogue search and clickable selections

- The general catalogue prompt handles broad item requests such as “What hoodies do you have?”
- `models.py` defines `CatalogueSelection`, which contains the matching structured product records and a summary.
- `ProductAnswer` includes the product ID, name, image URL, description, price, colors, and stock total so the frontend can render useful selection cards.
- `prompt.md` tells the agent to use `QueryCatalogue` and `get_products` for general item searches and to return a `CatalogueSelection` rather than inventing a text-only result.
- The chat widget displays returned product photos, names, and prices in clickable cards.
- Clicking a chatbot product looks up the full static catalogue record and reuses the existing product detail page, preserving the large image, description, price, colors, and size-by-size inventory view.

## Customer memory and page context

- A `chat_history` field was added to the `users` table. It stores a JSON array of timestamped customer requests and assistant replies, retaining the most recent 50 exchanges.
- Chat history is written after a recognized logged-in user receives a chatbot response; anonymous requests are not stored in a user record.
- `IdentifyUser` checks the logged-in user's email against the `users` table and exposes only the user's name and email to the agent.
- `DrawHistory` reads recent request summaries for an identified user so the agent can use prior context when relevant.
- `PageContext` receives the current product ID and name from the frontend, resolves that product against SQLite, and provides its description, price, and stock as likely context.
- The frontend remembers the logged-in email in browser storage, reloads saved exchanges through `/api/chat/history`, and passes the logged-in email and current product-page context with every chatbot request. The agent performs IdentifyUser and PageContext on every pass, and DrawHistory whenever IdentifyUser succeeds.
- Passwords, password hashes, and unrelated private user fields are never included in chat context or chat history.

## Usability improvements

- Unrelated chatbot questions receive the immediate support message: `I'm sorry, but I'm not sure about that one! Please reach out to campuscustomscustomerservice@campuscustoms.com`.
- The Products page has a category dropdown for Sweaters, Sweatshirts, Half-zips, Jackets, and T-shirts, plus an All products default; the selected category filters the catalogue while text search still works.
- FastAPI wraps agent requests in a one-minute timeout and returns `Timeout - please reach out to campuscustomscustomerservice@campuscustoms.com to answer your request` if the agent takes too long.
- `FollowUp` reads the question and response context and adds one relevant catalogue follow-up question to the final chatbot reply.

## Agent models, fields, and limits

- `ProductAnswer` carries the product ID, name, garment type, description, price, colors, normalized material/texture, stock total, and image URL. `InventoryItem` carries product ID, product name, size, and quantity.
- `ChatResponse` contains the reply, intent, optional structured product selection, follow-up, selected Yale-alumnus voice, timeout status, and the tools used. `ChatPageContext` carries an optional product ID and product name.
- `UserIdentity` exposes only a recognized customer's first name, last name, and email to the agent. `ChatHistory` contains timestamped request/reply entries; passwords, hashes, and cart data are never sent to the agent.
- Each request is limited to 2,000 characters. The frontend sends at most eight recent visible conversation turns, the database retains the most recent 50 saved exchanges, and `DrawHistory` reads the latest 20 exchanges.
- Catalogue search returns a limited, structured result set: the general search helper defaults to 8 items, material/texture lookups return up to 20, and named product/catalogue queries return up to 50. Broad selectable catalogue results can return the full current catalogue when needed.
- The Portkey OpenAI-compatible PydanticAI model is `gpt-5.6-luna`. FastAPI applies a 60-second agent timeout before returning the documented support message.

## Safety and scope rules

- The agent uses only supplied read-only database tools for store facts and says it does not know when the database cannot answer.
- Explicit or sexual messages are declined. Unrelated requests, particularly those with hazardous, illegal, self-harm, medical, or other harmful implications, receive the Campus Customs support message.
- The agent cannot modify the website, source code, database, infrastructure, deployment, or model configuration. It has no write tools and does not provide access-control bypass instructions.
- The agent never handles passwords, password hashes, payment details, or private user data, and does not claim to perform purchases, account changes, or external communications.

## Audit trail

- `output/audit_trail.json` is a persistent JSON array. Every completed chatbot run appends a new record; earlier run records are retained.
- Each record includes a run ID, start/finish times, a shortened request, whether the shopper was logged in, page context, a list of tool calls, and the final stop reason.
- Each tool call records its time, tool name, shortened arguments, and a shortened result or error. If an audit file is corrupted, it is copied to a timestamped recovery file before a new valid trail is written.

## Running the local application

- Start the backend from `hw4/backend` with `..\\.venv\\Scripts\\python.exe -m uvicorn main:app --reload --port 8000`.
- Start the frontend from `hw4/frontend` with `npm.cmd run dev` and open `http://localhost:5173`.
- The frontend defaults to the backend at `http://127.0.0.1:8000`. A configured `PORTKEY_API_KEY` is required for the Portkey-backed PydanticAI chat model.
