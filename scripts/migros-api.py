#!/usr/bin/env python3
"""
Migros API client — replaces Playwright browser automation with direct API calls.

Uses OAuth PKCE (same as Migros mobile app) to get a Bearer token, which works
on both the mobile API and www.migros.ch web API for search and cart operations.

Requires: curl_cffi (pip install curl_cffi)

Usage:
  migros-api.py login          # Login and cache tokens
  migros-api.py search QUERY   # Search products (online context)
  migros-api.py add ID [QTY]   # Add product to online basket by migrosId
  migros-api.py cart            # Show current online basket
  migros-api.py offers          # Show current offers/promotions
  migros-api.py share           # Get shareable shopping list URL
  migros-api.py newlist NAME    # Create a new shopping list
  migros-api.py lists           # Show all shopping lists
"""

import sys, os, json, hashlib, base64, secrets, re, time
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qs

try:
    from curl_cffi import requests as cffi
except ImportError:
    sys.exit("curl_cffi required: pip install curl_cffi")

# --- Config ---

DOTENV = Path(__file__).resolve().parent.parent / ".env"
TOKEN_FILE = Path.home() / ".migros-cli" / "web_session.json"

CLIENT_ID = "MigrosAPP_Android_5Srz_uFJSZWdZCrmNx10Tw"
CLIENT_SECRET = "ybuoJa1aSj96Ld8JYMFQ8zNZV13h5J"
REDIRECT_URI = "https://www.migros.ch/oauth2/redirect"
AUTH_URL = "https://login.migros.ch/oauth2/authorize"
TOKEN_URL = "https://login.migros.ch/oauth2/token"
SCOPES = "openid offline_access"

WEB_BASE = "https://www.migros.ch"


def load_env():
    """Load .env file into os.environ."""
    if DOTENV.exists():
        for line in DOTENV.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def get_creds():
    load_env()
    user = os.environ.get("MIGROS_USERNAME", "")
    pw = os.environ.get("MIGROS_PASSWORD", "")
    if not user or not pw:
        sys.exit("Set MIGROS_USERNAME and MIGROS_PASSWORD in .env")
    return user, pw


def get_region():
    load_env()
    region = os.environ.get("MIGROS_REGION", "")
    if not region:
        sys.exit("Set MIGROS_REGION in .env (e.g. gmzh, gmbs, gmos)")
    return region


def get_zipcode():
    load_env()
    zipcode = os.environ.get("MIGROS_ZIPCODE", "")
    if not zipcode:
        sys.exit("Set MIGROS_ZIPCODE in .env (e.g. 8047)")
    return zipcode


def get_language():
    load_env()
    return os.environ.get("MIGROS_LANGUAGE", "de")


# --- PKCE helpers ---

def pkce_verifier():
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()

def pkce_challenge(verifier):
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


# --- Session management ---

def save_session(data):
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps(data))
    TOKEN_FILE.chmod(0o600)

def load_session():
    if TOKEN_FILE.exists():
        return json.loads(TOKEN_FILE.read_text())
    return None


def _find_csrf(html):
    """Extract CSRF token from login page HTML."""
    for pattern in [
        r'name="_csrf"\s+value="([^"]+)"',
        r'value="([^"]+)"\s+name="_csrf"',
        r'_csrf[^>]*value="([^"]+)"',
    ]:
        m = re.search(pattern, html)
        if m:
            return m.group(1)
    return ""


# --- OAuth login flow ---

def login():
    """Full OAuth PKCE login → Bearer token."""
    user, pw = get_creds()
    verifier = pkce_verifier()
    challenge = pkce_challenge(verifier)
    state = secrets.token_urlsafe(16)

    s = cffi.Session(impersonate="chrome")

    # Step 1: Start authorization → lands on email page
    auth_params = urlencode({
        "client_id": CLIENT_ID,
        "response_type": "code",
        "scope": SCOPES,
        "redirect_uri": REDIRECT_URI,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
        "nonce": secrets.token_urlsafe(16),
        "ui_locales": "de-CH",
        "display": "touch",
    })
    resp = s.get(f"{AUTH_URL}?{auth_params}", allow_redirects=True, timeout=30)
    csrf = _find_csrf(resp.text)

    # Step 2: Submit email → lands on password page
    resp = s.post("https://login.migros.ch/login/email",
        data={"_csrf": csrf, "email": user, "authenticationPayload": ""},
        allow_redirects=True, timeout=30)

    if "/login/password" not in resp.url:
        sys.exit("Email submission failed — did not reach password page")

    csrf = _find_csrf(resp.text)

    # Step 3: Submit password → redirects with auth code
    resp = s.post("https://login.migros.ch/login/password",
        data={"_csrf": csrf, "username": user, "password": pw},
        allow_redirects=False, timeout=30)

    # Step 4: Follow redirects to capture auth code
    auth_code = None
    for _ in range(10):
        location = resp.headers.get("Location", "")
        if not location:
            break
        if location.startswith(REDIRECT_URI):
            params = parse_qs(urlparse(location).query)
            auth_code = params.get("code", [None])[0]
            if params.get("state", [None])[0] != state:
                sys.exit("State mismatch in OAuth callback")
            break
        resp = s.get(location, allow_redirects=False, timeout=30)

    if not auth_code:
        sys.exit("Failed to obtain authorization code")

    # Step 5: Exchange code for Bearer token
    resp = s.post(TOKEN_URL, data={
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "code_verifier": verifier,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }, timeout=30)
    if resp.status_code != 200:
        sys.exit(f"Token exchange failed: {resp.status_code} {resp.text}")
    tokens = resp.json()

    session = {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "id_token": tokens.get("id_token", ""),
        "expires_at": int(time.time()) + tokens.get("expires_in", 3600),
    }
    save_session(session)
    print(json.dumps({"status": "login-ok", "expires_in": tokens.get("expires_in", 3600)}))


def get_valid_session():
    """Return a valid session, refreshing the token if needed."""
    session = load_session()
    if not session:
        sys.exit("Not logged in. Run: migros-api.py login")

    if time.time() >= session.get("expires_at", 0) - 60:
        s = cffi.Session(impersonate="chrome")
        resp = s.post(TOKEN_URL, data={
            "grant_type": "refresh_token",
            "refresh_token": session["refresh_token"],
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        }, timeout=30)
        if resp.status_code != 200:
            sys.exit("Token refresh failed. Run: migros-api.py login")
        tokens = resp.json()
        session["access_token"] = tokens["access_token"]
        if "refresh_token" in tokens:
            session["refresh_token"] = tokens["refresh_token"]
        session["expires_at"] = int(time.time()) + tokens.get("expires_in", 3600)
        save_session(session)

    return session


def _web_session():
    """Create a curl_cffi session pre-warmed with Cloudflare cookies."""
    session = get_valid_session()
    s = cffi.Session(impersonate="chrome")
    # Visit homepage to establish Cloudflare session
    s.get(f"{WEB_BASE}/de", timeout=15)
    return s, session


def _web_headers(session):
    """Standard headers for www.migros.ch API calls."""
    return {
        "Authorization": f"Bearer {session['access_token']}",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "accept-language": "de",
        "migros-language": "de",
    }


# --- Commands ---

def cmd_search(query):
    """Search products via www.migros.ch API."""
    s, session = _web_session()
    headers = _web_headers(session)

    resp = s.post(f"{WEB_BASE}/onesearch-oc-seaapi/public/v5/search",
        headers=headers,
        json={"query": query, "regionId": get_region(), "from": 0, "language": get_language(),
              "productIds": [], "algorithm": "DEFAULT"},
        timeout=15)

    if resp.status_code != 200:
        sys.exit(f"Search failed: {resp.status_code} {resp.text[:200]}")

    data = resp.json()
    product_ids = data.get("productIds", [])[:10]

    # Get product details via product-display
    products = []
    if product_ids:
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d") + "T00:00:00"
        resp2 = s.post(f"{WEB_BASE}/product-display/public/v4/product-cards",
            headers=headers,
            json={
                "productFilter": {"uids": product_ids},
                "offerFilter": {
                    "storeType": "OFFLINE",
                    "region": "national",
                    "ongoingOfferDate": today,
                },
            },
            timeout=15)
        if resp2.status_code == 200:
            cards = resp2.json()
            for card in cards:
                avail = card.get("productAvailability", "")
                if "ONLINE" not in avail:
                    continue
                offer = card.get("offer", {})
                price = offer.get("price", {})
                products.append({
                    "id": str(card.get("uid", "")),
                    "name": card.get("name", ""),
                    "brand": card.get("brand", ""),
                    "description": card.get("description", ""),
                    "price": price.get("advertisedDisplayValue", ""),
                    "quantity": offer.get("quantity", ""),
                    "promotionText": offer.get("promotionType", ""),
                })
        else:
            products = [{"id": str(pid)} for pid in product_ids]

    print(json.dumps({"query": query, "results": products, "total": data.get("numberOfProducts", 0)},
                      indent=2, ensure_ascii=False))


def cmd_add(product_id, quantity=1):
    """Add product to online basket via shopping list v3 API."""
    s, session = _web_session()
    headers = _web_headers(session)

    list_id = _get_list_id_auto(s, headers)

    # Add item
    body = {
        "shoppingListId": list_id,
        "items": [{"id": str(product_id), "quantity": quantity, "type": "PRODUCT"}]
    }
    resp = s.request("PUT", f"{WEB_BASE}/shopping-list/public/v3/items",
        headers=headers, json=body, timeout=15)

    if resp.status_code >= 400:
        print(json.dumps({
            "status": "error",
            "code": resp.status_code,
            "message": resp.text[:200],
        }), file=sys.stderr)
        sys.exit(1)

    # Parse response for totals
    result = resp.json()
    totals = result.get("totals", {}).get("onlineTotal", {})
    print(json.dumps({
        "status": "added",
        "id": product_id,
        "quantity": quantity,
        "listId": list_id,
        "estimatedTotal": totals.get("estimatedTotal", ""),
    }))


def cmd_cart():
    """Show online basket contents."""
    s, session = _web_session()
    headers = _web_headers(session)

    list_id = _get_list_id_auto(s, headers)

    resp = s.get(f"{WEB_BASE}/shopping-list/public/v2/list/details",
        params={"shoppingListId": list_id, "zipCode": get_zipcode()},
        headers=headers, timeout=15)

    if resp.status_code != 200:
        sys.exit(f"Cart fetch failed: {resp.status_code} {resp.text[:200]}")

    data = resp.json()
    totals = data.get("totals", {}).get("onlineTotal", {})

    # Flatten items from categories
    items = []
    for cat in data.get("categories", []):
        for item in cat.get("items", []):
            items.append({
                "id": item.get("migrosId", item.get("id", "")),
                "name": item.get("name", ""),
                "quantity": item.get("quantity", 1),
                "price": item.get("price", ""),
            })

    print(json.dumps({
        "listId": list_id,
        "items": items,
        "estimatedTotal": totals.get("estimatedTotal", ""),
        "freeDelivery": totals.get("freeDelivery", False),
    }, indent=2, ensure_ascii=False))


def cmd_offers():
    """Show current offers/promotions via www.migros.ch."""
    s, session = _web_session()
    headers = _web_headers(session)

    resp = s.post(f"{WEB_BASE}/onesearch-oc-seaapi/public/v5/search",
        headers=headers,
        json={"query": "", "regionId": get_region(), "from": 0, "language": get_language(),
              "facetsCriteria": [{"facetId": "offers", "values": ["true"]}],
              "algorithm": "DEFAULT"},
        timeout=15)

    if resp.status_code != 200:
        sys.exit(f"Offers failed: {resp.status_code}")

    data = resp.json()
    product_ids = data.get("productIds", [])[:20]

    if product_ids:
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d") + "T00:00:00"
        resp2 = s.post(f"{WEB_BASE}/product-display/public/v4/product-cards",
            headers=headers,
            json={
                "productFilter": {"uids": product_ids},
                "offerFilter": {
                    "storeType": "OFFLINE",
                    "region": "national",
                    "ongoingOfferDate": today,
                },
            },
            timeout=15)
        if resp2.status_code == 200:
            cards = resp2.json()
            offers = []
            for card in cards:
                offer = card.get("offer", {})
                price = offer.get("price", {})
                offers.append({
                    "id": str(card.get("uid", "")),
                    "name": card.get("name", ""),
                    "brand": card.get("brand", ""),
                    "price": price.get("advertisedDisplayValue", ""),
                    "quantity": offer.get("quantity", ""),
                    "promotionText": offer.get("promotionType", ""),
                })
            print(json.dumps({"offers": offers, "total": data.get("numberOfProducts", 0)},
                              indent=2, ensure_ascii=False))
            return

    print(json.dumps({"offers": [], "total": 0}))


def cmd_share():
    """Get shareable shopping list URL via invitation API."""
    s, session = _web_session()
    headers = _web_headers(session)

    list_id = _get_list_id_auto(s, headers)

    resp = s.get(f"{WEB_BASE}/shopping-list/public/v1/lists/{list_id}/invitation",
        headers=headers, timeout=15)
    if resp.status_code != 200:
        sys.exit(f"Share failed: {resp.status_code} {resp.text[:200]}")

    data = resp.json()
    print(json.dumps({"shareUrl": data.get("invitationLink", ""), "listId": list_id}))


def _fetch_lists(s, headers):
    """Fetch all shopping lists from the API."""
    resp = s.get(f"{WEB_BASE}/shopping-list/public/v1/lists/overview",
        headers=headers, timeout=15)
    if resp.status_code != 200:
        return []
    return resp.json()


def _get_list_id_auto(s, headers):
    """Auto-discover the most recent shopping list ID (cached in session)."""
    cached = load_session()
    if cached and cached.get("list_id"):
        return int(cached["list_id"])

    lists = _fetch_lists(s, headers)
    if lists:
        latest = max(lists, key=lambda x: x.get("createdAt", ""))
        list_id = latest["shoppingListId"]
        cached = load_session() or {}
        cached["list_id"] = list_id
        save_session(cached)
        return list_id

    sys.exit("No shopping lists found. Create one on migros.ch first.")


def cmd_newlist(name):
    """Create a new shopping list and set it as active."""
    s, session = _web_session()
    headers = _web_headers(session)

    resp = s.post(f"{WEB_BASE}/shopping-list/public/v1/list",
        headers=headers, json={"name": name}, timeout=15)
    if resp.status_code not in (200, 201):
        sys.exit(f"Create list failed: {resp.status_code} {resp.text[:200]}")

    data = resp.json()
    list_id = data.get("shoppingListId", data) if isinstance(data, dict) else data
    cached = load_session() or {}
    cached["list_id"] = int(list_id)
    save_session(cached)
    print(json.dumps({"status": "created", "listId": int(list_id), "name": name}))


def cmd_lists():
    """Show all shopping lists."""
    s, session = _web_session()
    headers = _web_headers(session)
    lists = _fetch_lists(s, headers)
    result = []
    for l in lists:
        result.append({
            "id": l["shoppingListId"],
            "name": l.get("shoppingListName", ""),
            "items": l.get("itemsCount", 0),
            "created": l.get("createdAt", "")[:10],
        })
    print(json.dumps({"lists": result}, indent=2, ensure_ascii=False))


# --- Main ---

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "login":
        login()
    elif cmd == "search":
        if len(sys.argv) < 3:
            sys.exit("Usage: migros-api.py search QUERY")
        cmd_search(" ".join(sys.argv[2:]))
    elif cmd == "add":
        if len(sys.argv) < 3:
            sys.exit("Usage: migros-api.py add PRODUCT_ID [QUANTITY]")
        qty = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        cmd_add(sys.argv[2], qty)
    elif cmd == "cart":
        cmd_cart()
    elif cmd == "offers":
        cmd_offers()
    elif cmd == "share":
        cmd_share()
    elif cmd == "newlist":
        if len(sys.argv) < 3:
            sys.exit("Usage: migros-api.py newlist NAME")
        cmd_newlist(" ".join(sys.argv[2:]))
    elif cmd == "lists":
        cmd_lists()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)