# AI prompts from the HW 4 conversation

## Problem 1: Vibe coder prompts

Create AI_prompts.md file in HW 4 in a similar fashion to the other homework assignments.

## Problem 2: Analyze the database

Create harness.md in HW 4 in a new Output folder. Add the following:

Summary of relevant data fields:

Catalogue - A summary of all available products, with information about the type of clothing, color, and price, e.g.

Inventory - A summary of product inventory by product ID with the number of products available for that item by size

Users - A list of people who have used the catalogue and the date and time they did so, with a field for e-mail information that is currently redacted.

## Problem 3: Build the Campus Customs website

We need to make a front end for a Customs Campus website. There should be five main pages to the website: Home, Products, About us, Log in, and Create account.

In Home, write the following:

"Welcome to the Yale Bulldog Blue Store! Welcome to your one-stop shop for official Yale merchandise for all in the Yale community. Please explore our webpages:

About Us - A summary of our mission and products

Products - An overview of our full and available catalogue

Create account - Make an account with us to purchase the best Yale merchandise for offer

Log-in - Log in to existing accounts to make purchases or monitor your existing orders"

In About Us, write the following:

"Yale Bulldog Blue was founded in [do a websearch for year Yale Bulldog Blue was initiated] by Yale University [verify this] in partnership with Campus Customs. We offer an assortment of high-quality Yale-branded products. this includes:

T-shirts
Long seleev shirts
Vests
Polos
Sweatshirts and sweaters
Jackets
Sweatpants
Socks
Ties

And more!

In addition we provide useful Yale-branded items including

Water bottles
Notebooks
Mugs and glassess
Backpacks
Ornaments

And more!

Browse our digital catalogue to view our products list or come see us in person at 57 Broadway, New Haven CT, 06511. Our hours are: [make table of the screenshot].

We are looking forward to serving you!"

Create this webpage by scaffolding a react + vite + typescript front end. If you are having any difficulty with this, please see the example scaffold in my lecture 6 folder. The tools and process utilized in page creation should largely mirror the same process used in that folder.

The five pages specified should all appear in a navigation bar at the top of the webpage.

The product page should have product images from the product folder. Under each should be a label of what appears above, along with a price and short description.

Clicking a product should open a product-specific page. The page should have the large image on the left side. On the right side should be a description, price, and summary of how many of the items are in stock. This information will come from the campus_customs db.

There should be a chat interface in the bottom right of the site. It does not need to talk to an agent yet.

Create a new backend folder with main.py in it. this is a fast API app just to serve products and images which we will eventually turn into the agent.

Take out "vests" as well.

Store hours from screenshot: Saturday 9:30 AM - 9 PM; Sunday 10 AM - 6 PM; Monday through Friday 9:30 AM - 9 PM.

Follow-up: Switch the order of About us and Products in the top navigation bar, uncapitalize the "us" in the Home-page link, add an italic "by Campus Customs" attribution under "Bulldog Blue," reduce the large gap between the apparel and essentials columns, and add a small gap between the second "And more!" and the catalogue paragraph. Make the catalogue available using the photos in the data/products folder. Product photos should remain clickable: clicking one opens its product-specific page with the large image on the left and the description, price, and SQLite inventory summary on the right.

Follow-up: Remove the hyphen from the Home-page "Log in" label and place "Create account" before "Log in" on the Home page.

Follow-up: Fix the About us spacing so the apparel section, Yale-branded essentials section, and segue into store hours have even spacing in a single readable flow.

Follow-up: Make each product card open a single-item product page when clicked. The detail page must show a large image on one side and the full product text on the other, including description, price, colors, and sizes/stock when available.

Addendum to Problem 3: We made several cosmetic changes to the website during development. These included correcting uneven spacing in the About us sections, adjusting the navigation and Home-page tab order, making the product photos load locally and display clearly from the data/products folder, and placing the large product image to the side of the product description and other details on the single-item page.

Addendum: We removed the sentence about the founding year because no verifiable information was available to support it.

Follow-up: Revise the About us product list to match the available catalogue. Replace the separate apparel and essentials lists with one concise list: sweaters, sweatshirts, half-zips, jackets, T-shirts, and more.

## Problem 4: Create account and login

Let's build out the create account / log in page. When you click create account, you should be taken to a form entry where you put in a first name, last name, email, password, and confirm password. There should then be a register button to submit this info - if the password field does not mirror the confirm password field, an error should be returned. Once the information is submitted new account information should go into the users table (the email and password specifically). Only users registered in the users table should be able to log in in the log in page, otherwise "Error: Account not found" should be returned.

When you store the passwords do it in a secure, one-way route. I should not be able to see the passwords. No one else should be able to see them either - put in a password protect to even see the one-way route (make the password "aihw516!" Also put up any other security measures you can think of.

Save this prompt to Problem 4: Create account and login.

Write bullet points in a harness.md in file 4 for the security measures I have added, starting with a bullet listing the fields I save for each user.

## Problem 5: Pydantic AI agent backend

Time to build a chatbot. Make it a pydanticai agent behind fastapi. It should be behind the chat button you have already put on the webpage. The API app should be main.py and should run with uvicorn. Save this to a backend folder. Also in this folder should be: a prompts file prompt.md (this should do the same thing the prompts.md file does in HW3, put voice and safety basics here), agent.py for agent entry and writing, tools.py with tools the agent will need to call, and models.py with PydanticAI structured types. models.py can separate the types of data we have access to (inventory, size, material, color) and prepare separate routes to answer any questions on these subjects. There should also be a "Welcome! How can I help you today?" message when you first open the chatbot. main.py should route things so a message from the website returns an agent reply.

Backend should run from the backend folder using the following: uvicorn main:app --reload --port 8000

Add a section to harness.md on how the agent is loaded and what FastAPI is doing.

## Problem 6: Tools: product info and stock

We need the chatbot to be able to answer questions about product descriptions, price, and inventory. Let's have the following tools:

`QueryCatalogue` - any question about clothing, color, and price should use the Catalogue data field to answer the question

`QueryInventory` - any question about inventory should go to the Inventory data field

`get_products` (to answer questions looking for specific products), `get_color` (to answer color questions), `get_texture` (to answer texture questions), `get_price` (to answer price questions) based on the information uncovered by QueryCatalogue

then `get_inventory` and `get_sizes` to reply to inventory queries

UPDATE THE SCRIPT TO SAY YOU ONLY USE THE DATA IN THE DATABASE WHEN RESPONDING TO QUERIES - DO NOT MAKE UP INFORMATION, JUST SAY YOU DO NOT KNOW IF YOU DO NOT KNOW

Expand the prompt.md file so the agent knows which tool to call in which scenario and models.py to reflect the expected output for each tool as specified above.

In harness.md, list the tools I gave you above in bullets. Note that tools were expected to draw upon the data fields with relevant information - anything about product-specific data goes to the catalogue field, while any of the inventory-specific information (sizes, stock) goes to the inventory field.

## Problem 7: Chat search that updates the page

Let's add a new type of prompt for the prompt file - the "general" prompt where there is a "general" ask for a type of item (what hoodies do you got, e.g.). Write models.py to return a catalogue selection when this happens - just like we did with the website photos before, the chatbot should return photos of relevant products that you can then click into to get to the same details page we previously added. For example, if a client asks for hoodies, photos and product names for all hoodies should be shown in the chat, and the client can click the one they are interested in to get to the hoodie detail page.

Make sure a summary of this process, including the prompt, models.py, and what each is doing, is in the harness file.

## Problem 8: Customer Memory

Add a field to users data which is "Chat history." Whenever a logged in user makes a request of the chatbot, add a description of the request to "Chat history."

Add three tools:

`IdentifyUser` - allows the chatbot to check the name and email of the chatter for logged-in users

`DrawHistory` - for searches of logged-in customers, read their history before responding to chats in case it helps provide context on their question

`PageContext` - if someone pulls up the chat while on the page of a product, recognize which product they are likely talking about.

Work into models.py that every pass of the chatbot should do an IdentifyUser and PageContext check. If a user is identified it should also pull on DrawHistory. If someone is specifically on the page for a product via PageContext that should affect answers.

Add to harness.md: how user chat history is stored, bullets for the new tools, the customer fields the agent sees, and how page context is passed.

Follow-up: Keep the existing `users` table as the chat-history store, remember a successful login across refreshes, save both the shopper's message and the assistant reply in `chat_history`, and reload those saved exchanges in the chat window when the same account returns.

## Problem 9: Usability improvements

FRONTEND:

When the chatbot does not know how to answer a question, return a message with an e-mail customers can reach out to. If the question has nothing to do about the store this should be the immediate answer. Specifically, say "I'm sorry, but I'm not sure about that one! Please reach out to campuscustomscustomerservice@campuscustoms.com". We are not actually setting up this e-mail but would if we were to put up this page live. This will allow customers to more readily have their questions answered if the chatbot is unprepared to do so.

Let's also add a filter to the Products page - a dropdown menu with types of products (hoodies, pants, shirts, jackets, etc. with an "other" category as needed). I should be able to set the filter to an item and then only see catalogue items pertaining to that filter.

BACKEND:

Add a "timeout" path to models.py - if after a minute there is still no response, return a "Timeout - please reach out to campuscustomscustomerservice@campuscustoms.com to answer your request". This helps prevent shoppers from waiting around for a potential response the chatbot will not be able to give them.

Also add a new tool called FollowUp which reads the question proposed into the chatbot and devises a logical follow-up question after returning a response. models.py should read the follow-up proposed by the tool and then add that at the end of its response. This allows for greater engagement with the customer and increases the chances they buy more products if we are able to propose alternatives.

Actually do the things described in addition to adding them to usability.md.

## Prompt 10: Style the website

Make the website look nice!

Add a "Yale" theme - add Yale blue and white stripes to the background of the webpage, add a Yale bulldog to the bottom of the webpage, add a gothic typeface to the headers and product descriptions, add a Shakespeare icon somewhere, add a book and quill icon somewhere, add a Yale logo somewhere, add a map with New Haven pinpointed.

The chatbot should have the voice of a celebrity Yale alum - ideally a supreme court justice, or a writer, or a president, or a businessperson. No one controversial though, please. Add an instruction on models.py that the chatbot should say whose voice it is taking when the chat is opened, with a one sentence bio. Make it read "Hello! I am [insert name here], a Yale alumnus who is now here to help you shop the Campus Customs store! How can I help you today?"

Summarize my changes in design.md. Include two main categories of changes - website design and chatbot voice, then summarize each. Say both will help make the website more engaging by tying it to the Yale theme, making customers more fully immersed in the website as part of their Yale experience and more likely to buy. Say the voice should be especially fun for people who might not even have known the person in question was an alumnus.

Follow-up: The chatbot voice should change every time there is a new request. Search for Yale alumni and compile a list of fifteen famous people to cycle between. Create a JSON file for the list, then pick a different person at random from that list for each new chat request. Present the list for verification.

Addendum: The opening greeting was later changed to match the alumni bios in the JSON list: "Hello! I'm Yale alum [name], [description]. Today, I'm here to help you navigate the Campus Customs site. What can I do for you?"

Follow-up: I ended up finding a free bulldog photo and using that in the website footer instead of the original bulldog icon.

Addendum: We overrode the Shakespeare icon, book and quill icon, and New Haven map from the original styling request. The footer now uses the bulldog photographs instead.

## Problem 11: Site testing (app check)

Make `app_check.html` in the Output folder. This should include documentation for testing the site with these sections: Inventory Check, Search Result Cards, and Product Search Filter. Use the newly added screenshots in the HW 4 folder: one in Inventory Check, four in Search Result Cards, and one in Product Search Filter. Move the screenshots to `Output/app_check_images`, rename them to `inventory`, `searchresult1`, `searchresult2`, and so on, plus `filter`, and link them from the HTML with relative paths.

## Problem 12: Audit trail, safety, finish harness

Add `audit_trail.json` in the Output folder. It should include all agent-loop activity, including time, tools drawn upon, short arguments and results, and stop reason. It should never wipe between runs; keep appending entries whenever the agent reruns.

Add safety rules to `prompt.md`: do not respond to explicit messages; do not respond to requests unrelated to the store, especially those with potentially hazardous implications; and do not allow anyone without access to the local HW 4 project to make changes to the website infrastructure. If missing, summarize model fields, tools and abilities, safety rules, loop limits, result caps, models, and how to run the frontend and backend in `harness.md`.
