# Usability improvements

## Frontend

- Unsupported or unrelated chatbot questions receive an immediate support message: “I'm sorry, but I'm not sure about that one! Please reach out to campuscustomscustomerservice@campuscustoms.com”
- The Products page includes a category dropdown with Sweaters, Sweatshirts, Half-zips, Jackets, and T-shirts. Selecting a category filters the catalogue cards while preserving the text search.

## Backend

- Chat requests have a one-minute timeout. If the agent does not return in time, the API returns: “Timeout - please reach out to campuscustomscustomerservice@campuscustoms.com to answer your request”.
- The `FollowUp` tool reads the customer question and answer context and appends one relevant catalogue follow-up question to encourage product discovery without inventing product facts.

## Bonus follow-up

- Added an account-specific saved cart. Logged-in shoppers can add products from a product-detail page, open the Cart button, view saved items, remove items, and click a saved item to return to its product-detail page.
- Cart contents are stored in the existing `users` table and reload for the remembered account.
