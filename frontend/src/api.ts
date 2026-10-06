export interface InventoryEntry { size: string; quantity: number; }

export interface Product {
  product_id: string; name: string; garment_type: string; description: string;
  colors: string[]; image_url: string; price: number;
  inventory: InventoryEntry[]; stock_total: number;
}

export function productImage(imageUrl: string): string { return imageUrl; }

export interface AuthResponse { ok: boolean; message: string; user?: { id: number; first_name: string; last_name: string; email: string }; }

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000"}${path}`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail ?? "Request failed");
  return data as T;
}

export function registerUser(body: { first_name: string; last_name: string; email: string; password: string }): Promise<AuthResponse> {
  return postJSON<AuthResponse>("/api/auth/register", body);
}

export function loginUser(body: { email: string; password: string }): Promise<AuthResponse> {
  return postJSON<AuthResponse>("/api/auth/login", body);
}

export interface ChatProduct { product_id: string; name: string; garment_type: string; description: string; price: number; colors: string[]; stock_total: number; image_url: string; }
export interface ChatVoice { persona: string; description: string; greeting: string; }
export interface ChatResponse { reply: string; intent: string; products: ChatProduct[]; selection?: { products: ChatProduct[]; summary: string } | null; tools_used: string[]; voice?: ChatVoice | null; }
export interface ChatHistoryEntry { timestamp: string; request: string; reply?: string | null; }
export interface ChatHistory { email: string; entries: ChatHistoryEntry[]; }
export interface CartProduct extends Product { selected_size?: string | null; cart_quantity: number; }
export interface CartResult { email: string; products: CartProduct[]; }

export function sendChat(message: string, userEmail?: string | null, pageContext?: { product_id?: string; product_name?: string } | null, previousVoice?: string | null, conversationContext?: Array<{ role: "user" | "assistant"; text: string }>): Promise<ChatResponse> {
  return postJSON<ChatResponse>("/api/chat", { message, user_email: userEmail || undefined, page_context: pageContext || undefined, previous_voice: previousVoice || undefined, conversation_context: conversationContext || [] });
}

export async function getChatWelcome(previousVoice?: string | null): Promise<ChatVoice> {
  const query = previousVoice ? `?previous_voice=${encodeURIComponent(previousVoice)}` : "";
  const response = await fetch(`${import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000"}/api/chat/welcome${query}`);
  if (!response.ok) throw new Error("Welcome request failed");
  return response.json() as Promise<ChatVoice>;
}

export async function getChatHistory(email: string): Promise<ChatHistory> {
  const response = await fetch(`${import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000"}/api/chat/history?email=${encodeURIComponent(email)}`);
  if (!response.ok) throw new Error("Chat history request failed");
  return response.json() as Promise<ChatHistory>;
}

export function getCart(email: string): Promise<CartResult> {
  return fetch(`${import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000"}/api/cart?email=${encodeURIComponent(email)}`).then(async (response) => {
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail ?? "Cart request failed");
    return data as CartResult;
  });
}

export function addToCart(email: string, productId: string, size: string): Promise<CartResult> {
  return postJSON<CartResult>("/api/cart", { email, product_id: productId, size });
}

export function removeFromCart(email: string, productId: string, size?: string | null): Promise<CartResult> {
  const sizeQuery = size ? `&size=${encodeURIComponent(size)}` : "";
  return fetch(`${import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000"}/api/cart/${encodeURIComponent(productId)}?email=${encodeURIComponent(email)}${sizeQuery}`, { method: "DELETE" }).then(async (response) => {
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail ?? "Cart request failed");
    return data as CartResult;
  });
}
