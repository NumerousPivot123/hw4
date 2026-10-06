import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { productImage, type CartProduct, type Product } from "./api";
import { catalogue } from "./catalogue";
import { addToCart, getCart, getChatHistory, getChatWelcome, loginUser, registerUser, removeFromCart, sendChat } from "./api";

type Page = "home" | "products" | "about" | "login" | "create" | "detail";
const nav: Array<[Exclude<Page, "detail">, string]> = [["home", "Home"], ["about", "About us"], ["products", "Products"], ["login", "Log in"], ["create", "Create account"]];
const money = (value: number) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value);
const productCategory = (product: Product) => { const type = product.garment_type.toLowerCase(); const name = product.name.toLowerCase(); if (type.includes("quarter-zip") || type.includes("half-zip")) return "Half-zips"; if (type.includes("sweater") || name.includes("sweater")) return "Sweaters"; if (type.includes("jacket") || type.includes("bomber") || type.includes("fleece")) return "Jackets"; if (type.includes("t-shirt") || type.includes("shirt")) return "T-shirts"; return "Sweatshirts"; };

function ProductCard({ product, open }: { product: Product; open: (p: Product) => void }) {
  return <article className="product-card" role="link" tabIndex={0} onClick={() => open(product)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); open(product); } }}><button className="product-image" onClick={() => open(product)} aria-label={`View ${product.name}`}><img src={productImage(product.image_url)} alt={product.name} /></button><div className="product-body"><p className="eyebrow">{product.garment_type}</p><h3>{product.name}</h3><p className="description">{product.description}</p><div className="product-footer"><strong>{money(product.price)}</strong><button className="text-button" onClick={() => open(product)}>View product →</button></div></div></article>;
}

function Chat({ openProduct, userEmail, pageContext }: { openProduct: (product: Product) => void; userEmail: string | null; pageContext: Product | null }) {
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [previousVoice, setPreviousVoice] = useState<string | null>(null);
  const [messages, setMessages] = useState<Array<{ role: "user" | "assistant"; text: string; products?: import("./api").ChatProduct[] }>>([
    { role: "assistant", text: "Hello! I am David McCullough, a Yale alumnus who is now here to help you shop the Campus Customs store! How can I help you today?" },
  ]);
  useEffect(() => {
    if (!open) return;
    Promise.all([getChatWelcome(previousVoice), userEmail ? getChatHistory(userEmail) : Promise.resolve(null)]).then(([voice, history]) => {
      setPreviousVoice(voice.persona);
      const saved = history?.entries.flatMap((entry) => [{ role: "user" as const, text: entry.request }, ...(entry.reply ? [{ role: "assistant" as const, text: entry.reply }] : [])]) ?? [];
      setMessages([{ role: "assistant", text: voice.greeting }, ...saved]);
    }).catch(() => undefined);
  }, [open, userEmail]);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const text = message.trim();
    if (!text || busy) return;
    setMessage(""); setBusy(true);
    setMessages((all) => [...all, { role: "user", text }]);
    try {
      const conversationContext = messages.slice(-8).map(({ role, text: priorText }) => ({ role, text: priorText }));
      const response = await sendChat(text, userEmail, pageContext, previousVoice, conversationContext);
      const products = response.selection?.products ?? response.products;
      if (response.voice) setPreviousVoice(response.voice.persona);
      setMessages((all) => [...all, { role: "assistant", text: response.reply, products }]);
    } catch (error) {
      setMessages((all) => [...all, { role: "assistant", text: error instanceof Error ? `Sorry, I couldn't connect to the catalogue assistant: ${error.message}` : "Sorry, I couldn't connect to the catalogue assistant." }]);
    } finally { setBusy(false); }
  };
  const openChatProduct = (productId: string) => {
    const product = catalogue.find((item) => item.product_id === productId);
    if (product) { setOpen(false); openProduct(product); }
  };
  return <aside className="chat" aria-label="Store chat">{open ? <div className="chat-panel"><header><div><strong>Campus Customs</strong><small>Catalogue assistant</small></div><button className="chat-close" onClick={() => setOpen(false)} aria-label="Close chat" title="Close chat">×</button></header><div className="chat-thread">{messages.map((item, index) => <div key={`${item.role}-${index}`}><p className={item.role === "user" ? "chat-user-message" : "chat-assistant-message"}>{item.text}</p>{item.products && item.products.length > 0 && <div className="chat-products">{item.products.map((product) => <button className="chat-product" key={product.product_id} onClick={() => openChatProduct(product.product_id)}><img src={productImage(product.image_url.replace("/images/", "/products/"))} alt={product.name} /><span>{product.name}</span><strong>{money(product.price)}</strong></button>)}</div>}</div>)}{busy && <p className="chat-assistant-message">Checking the catalogue…</p>}</div><form onSubmit={submit}><input value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Ask about products or stock" disabled={busy} /><button disabled={busy}>Send</button></form></div> : <button className="chat-launch" onClick={() => setOpen(true)}>◌ Chat with us</button>}</aside>;
}

function AuthPage({ mode, visit, onLogin }: { mode: "login" | "create"; visit: (page: "login" | "create") => void; onLogin: (email: string) => void }) {
  const [firstName, setFirstName] = useState(""); const [lastName, setLastName] = useState(""); const [email, setEmail] = useState(""); const [password, setPassword] = useState(""); const [confirmPassword, setConfirmPassword] = useState(""); const [message, setMessage] = useState<string | null>(null); const [success, setSuccess] = useState(false); const [busy, setBusy] = useState(false);
  const isCreate = mode === "create";
  const submit = async (event: FormEvent) => {
    event.preventDefault(); setMessage(null); setSuccess(false);
    if (isCreate && password !== confirmPassword) { setMessage("Error: Password and confirm password do not match"); return; }
    setBusy(true);
    try {
      const response = isCreate ? await registerUser({ first_name: firstName, last_name: lastName, email, password }) : await loginUser({ email, password });
      setSuccess(true); setMessage(response.message); setFirstName(""); setLastName(""); setEmail(""); setPassword(""); setConfirmPassword(""); if (!isCreate && response.user) onLogin(response.user.email);
    } catch (error) { setMessage(error instanceof Error ? `Error: ${error.message}` : "Error: Request failed"); }
    finally { setBusy(false); }
  };
  return <section className="account"><div><p className="eyebrow">Yale Bulldog Blue</p><h1>{isCreate ? "Create your account" : "Welcome back"}</h1><p>{isCreate ? "Create an account to purchase Yale merchandise and track orders." : "Log in with an account registered in the Campus Customs database."}</p><form onSubmit={submit}>{isCreate && <><label>First name<input value={firstName} onChange={(event) => setFirstName(event.target.value)} required /></label><label>Last name<input value={lastName} onChange={(event) => setLastName(event.target.value)} required /></label></>}<label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label><label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} minLength={8} required /></label>{isCreate && <label>Confirm password<input type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} minLength={8} required /></label>}<button className="button" disabled={busy}>{busy ? "Submitting…" : isCreate ? "Register" : "Log in"}</button></form>{message && <p className={success ? "auth-message success" : "auth-message error"}>{message}</p>}<button className="text-button" onClick={() => visit(isCreate ? "login" : "create")}>{isCreate ? "Already have an account? Log in" : "Need an account? Create one"}</button></div></section>;
}

function CartDrawer({ products, openProduct, removeProduct, close }: { products: CartProduct[]; openProduct: (product: Product) => void; removeProduct: (productId: string, size?: string | null) => void; close: () => void }) {
  return <aside className="cart-drawer" aria-label="Shopping cart"><header><h2>Your cart</h2><button className="cart-close" onClick={close} aria-label="Close cart">×</button></header>{products.length === 0 ? <p className="cart-empty">Your cart is empty.</p> : <div className="cart-items">{products.map((product) => <div className="cart-item" key={`${product.product_id}-${product.selected_size ?? "saved"}`}><button className="cart-item-link" onClick={() => openProduct(product)}><img src={productImage(product.image_url)} alt={product.name} /><span>{product.name}{product.selected_size && <small>Size: {product.selected_size}</small>}</span><strong>{money(product.price)}{product.cart_quantity > 1 && ` × ${product.cart_quantity}`}</strong></button><button className="cart-remove" onClick={() => removeProduct(product.product_id, product.selected_size)}>Remove</button></div>)}</div>}</aside>;
}

export default function App() {
  const [page, setPage] = useState<Page>("home"); const [products, setProducts] = useState<Product[]>([]); const [selected, setSelected] = useState<Product | null>(null); const [loading, setLoading] = useState(true); const [error] = useState<string | null>(null); const [search, setSearch] = useState(""); const [category, setCategory] = useState("All products"); const [userEmail, setUserEmail] = useState<string | null>(() => localStorage.getItem("campus-customs-user-email")); const [loginNotice, setLoginNotice] = useState(false); const [cartProducts, setCartProducts] = useState<CartProduct[]>([]); const [cartOpen, setCartOpen] = useState(false); const [selectedCartSize, setSelectedCartSize] = useState(""); const [cartMessage, setCartMessage] = useState<string | null>(null);
  useEffect(() => { setProducts(catalogue); setLoading(false); }, []);
  useEffect(() => { if (!userEmail) { setCartProducts([]); return; } getCart(userEmail).then((result) => setCartProducts(result.products)).catch(() => setCartProducts([])); }, [userEmail]);
  const categories = useMemo(() => ["All products", "Sweaters", "Sweatshirts", "Half-zips", "Jackets", "T-shirts"], []);
  const visible = useMemo(() => { const term = search.toLowerCase().trim(); return products.filter((p) => (category === "All products" || productCategory(p) === category) && (!term || `${p.name} ${p.garment_type} ${p.description} ${p.colors.join(" ")}`.toLowerCase().includes(term))); }, [products, search, category]);
  const visit = (next: Exclude<Page, "detail">) => { setPage(next); setSelected(null); window.scrollTo({ top: 0, behavior: "smooth" }); };
  const openProduct = (product: Product) => { setSelected(product); setSelectedCartSize(product.inventory[0]?.size ?? ""); setCartMessage(null); setPage("detail"); window.scrollTo({ top: 0, behavior: "smooth" }); };
  const account = page === "login" || page === "create";
  const rememberUser = (email: string) => { localStorage.setItem("campus-customs-user-email", email); setUserEmail(email); setLoginNotice(true); visit("home"); };
  const addProductToCart = async (product: Product) => { if (!userEmail) { visit("login"); return; } if (!selectedCartSize) { setCartMessage("Error: Please select a size."); return; } try { const result = await addToCart(userEmail, product.product_id, selectedCartSize); setCartProducts(result.products); setCartMessage(null); setCartOpen(true); } catch (cartError) { setCartMessage(cartError instanceof Error ? `Error: ${cartError.message}` : "Error: Unable to add this size to your cart."); } };
  const removeProductFromCart = async (productId: string, size?: string | null) => { if (!userEmail) return; const result = await removeFromCart(userEmail, productId, size); setCartProducts(result.products); };
  return <div className="site"><header className="site-header"><button className="brand" onClick={() => visit("home")}><span>Y</span><b>YALE<em>Bulldog Blue</em><small>by Campus Customs</small></b></button><nav>{nav.map(([id, label]) => <button key={id} className={page === id ? "active" : ""} onClick={() => visit(id)}>{label}</button>)}<button className="cart-button" onClick={() => userEmail ? setCartOpen(true) : visit("login")}>Cart ({cartProducts.length})</button></nav></header><main>
    {page === "home" && <><section className="hero"><p className="eyebrow">Official Yale merchandise</p><h1>Yale tradition, <i>made for today.</i></h1><p>Welcome to the Yale Bulldog Blue Store! Welcome to your one-stop shop for official Yale merchandise for all in the Yale community.</p>{loginNotice && <p className="login-notice" role="status">✓ You are logged in successfully.</p>}<button className="button light" onClick={() => visit("products")}>Explore products →</button></section><section className="section intro"><h2>Explore our webpages</h2><div className="link-grid"><button onClick={() => visit("about")}><strong>About Us</strong><span>A summary of our mission and products</span></button><button onClick={() => visit("products")}><strong>Products</strong><span>An overview of our full and available catalogue</span></button><button onClick={() => visit("create")}><strong>Create account</strong><span>Make an account with us to purchase the best Yale merchandise we offer</span></button><button onClick={() => visit("login")}><strong>Log in</strong><span>Log in to existing accounts to make purchases or monitor your existing orders</span></button></div></section></>}
    {page === "products" && <section className="section"><div className="heading"><div><p className="eyebrow">The Yale collection</p><h1>Products</h1><p>Browse the complete, currently available Campus Customs catalogue.</p></div><div className="product-controls"><label className="search">Search<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Clothing, color, or style" /></label><label className="category-filter">Category<select value={category} onChange={(event) => setCategory(event.target.value)}>{categories.map((item) => <option key={item} value={item}>{item}</option>)}</select></label></div></div>{loading && <p className="status">Loading the catalogue…</p>}{error && <p className="status error">{error}</p>}{!loading && !error && <><p className="status">{visible.length} products</p><div className="product-grid">{visible.map((product) => <ProductCard key={product.product_id} product={product} open={openProduct} />)}</div></>}</section>}
    {page === "detail" && selected && <section className="section detail"><button className="back" onClick={() => visit("products")}>← Back to products</button><div className="detail-grid"><div className="detail-image"><img src={productImage(selected.image_url)} alt={selected.name} /></div><div><p className="eyebrow">{selected.garment_type}</p><h1>{selected.name}</h1><p className="price">{money(selected.price)}</p><p className="detail-copy">{selected.description}</p><dl><div><dt>Colors</dt><dd>{selected.colors.length ? selected.colors.join(", ") : "See product image"}</dd></div><div><dt>Availability</dt><dd><strong>{selected.stock_total} items in stock</strong></dd></div></dl><div className="sizes"><b>Inventory by size</b>{selected.inventory.map((item) => <span key={item.size}>{item.size}: {item.quantity}</span>)}</div></div></div></section>}
    {page === "about" && <section className="section about"><p className="eyebrow">Our story</p><h1>About Yale Bulldog Blue</h1><div className="about-grid"><div><p>Yale Bulldog Blue is a Yale community storefront in partnership with Campus Customs. We offer an assortment of high-quality Yale-branded products.</p><h2>Our products include</h2><ul><li>Sweaters</li><li>Sweatshirts</li><li>Half-zips</li><li>Jackets</li><li>T-shirts</li><li>And more!</li></ul><p>Browse our digital catalogue to view our products list or come see us in person at <strong>57 Broadway, New Haven, CT 06511.</strong></p></div></div><section className="hours"><h2>Store hours</h2><table><tbody><tr><th>Saturday</th><td>9:30 AM – 9 PM</td></tr><tr><th>Sunday</th><td>10 AM – 6 PM</td></tr>{["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"].map((day) => <tr key={day}><th>{day}</th><td>9:30 AM – 9 PM</td></tr>)}</tbody></table></section><p className="closing">We are looking forward to serving you!</p></section>}
    {account && <AuthPage mode={page === "login" ? "login" : "create"} visit={visit} onLogin={rememberUser} />}
  {page === "detail" && selected && <div className="detail-cart-action"><div className="cart-add-panel"><div><b>Select your size</b><label className="cart-size-label">Size<select value={selectedCartSize} onChange={(event) => { setSelectedCartSize(event.target.value); setCartMessage(null); }}>{selected.inventory.map((item) => <option key={item.size} value={item.size}>{item.size}{item.quantity > 0 ? ` — ${item.quantity} available` : " — unavailable"}</option>)}</select></label></div><button className="button cart-add" onClick={() => addProductToCart(selected)}>Add to cart</button></div>{cartMessage && <p className="cart-add-error" role="alert">{cartMessage}</p>}</div>}</main><footer className="yale-footer" aria-label="Yale Bulldog Blue"><img className="footer-bulldog-photo" src={page === "home" ? "/bulldog-footer.png" : page === "about" ? "/bulldog-about.png" : "/bulldog-site.png"} alt="Yale bulldog" /></footer>{cartOpen && <CartDrawer products={cartProducts} openProduct={(product) => { setCartOpen(false); openProduct(product); }} removeProduct={removeProductFromCart} close={() => setCartOpen(false)} />}<Chat openProduct={openProduct} userEmail={userEmail} pageContext={page === "detail" ? selected : null} /></div>;
}
