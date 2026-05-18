"""
JH City Research — Marts, Bike Showrooms, Banks
Uses Google Maps Places API → Saves to Google Sheet + Local CSV
"""

import json
import csv
import time
import urllib.request
import urllib.parse
from pathlib import Path

# ── Config ──
API_KEY = "AIzaSyChnRGxZ30DZRu2qc68oN6YyJZy5zXpA2A"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# 33 JH Cities
CITIES = [
    "Dhanbad", "Bokaro Steel City", "Deoghar", "Giridih", "Ramgarh",
    "Daltonganj", "Chaibasa", "Dumka", "Chatra", "Koderma",
    "Gumla", "Sahibganj", "Jamtara", "Chakradharpur", "Saraikela",
    "Chirkunda", "Barhi", "Madhupur", "Garhwa", "Khunti",
    "Patratu", "Godda", "Bundu", "Lohardagga", "Silli",
    "Barkagaon", "Kujju", "Chouparan", "Ghatsila", "Bero",
    "Bhurkunda", "Pithoria", "Hunterganj",
]

# Search queries per category
SEARCHES = {
    "marts": [
        "Vishal Mega Mart", "D-Mart", "DMart", "Reliance Smart",
        "Big Bazaar", "More Supermarket", "Spencer's", "Star Bazaar",
        "Grocery Mart", "Supermarket", "Departmental Store",
    ],
    "bike_showrooms": [
        "Honda showroom", "Hero showroom", "TVS showroom",
        "Bajaj showroom", "Suzuki showroom", "Royal Enfield showroom",
        "Yamaha showroom", "KTM showroom",
    ],
    "banks": [
        "HDFC Bank", "ICICI Bank", "SBI Bank", "Axis Bank",
        "PNB Bank", "Bank of Baroda", "Canara Bank", "Union Bank",
        "Kotak Mahindra Bank", "IndusInd Bank", "Bank of India",
        "Central Bank of India", "UCO Bank",
    ],
}


def search_places(query: str, city: str) -> list:
    """Search Google Maps Places API for a query in a city."""
    full_query = f"{query} in {city}, Jharkhand, India"
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = urllib.parse.urlencode({
        "query": full_query,
        "key": API_KEY,
    })

    req = urllib.request.Request(f"{url}?{params}")
    try:
        resp = json.loads(urllib.request.urlopen(req, timeout=15).read())
        results = []
        for place in resp.get("results", []):
            address = place.get("formatted_address", "")
            # Extract area from address (first part before city name)
            area = address.split(",")[0] if "," in address else ""
            lat = place.get("geometry", {}).get("location", {}).get("lat", "")
            lng = place.get("geometry", {}).get("location", {}).get("lng", "")
            maps_link = f"https://www.google.com/maps/place/?q=place_id:{place.get('place_id', '')}"

            results.append({
                "city": city,
                "area": area.strip(),
                "name": place.get("name", ""),
                "address": address,
                "rating": place.get("rating", ""),
                "total_ratings": place.get("user_ratings_total", ""),
                "maps_link": maps_link,
            })
        return results
    except Exception as e:
        print(f"  [Error] {query} in {city}: {e}")
        return []


def search_category(category: str, queries: list) -> list:
    """Search all cities for a category."""
    all_results = []
    seen = set()  # Deduplicate by place name + city

    for city in CITIES:
        city_count = 0
        for query in queries:
            results = search_places(query, city)
            for r in results:
                key = f"{r['name']}|{r['city']}"
                if key not in seen:
                    seen.add(key)
                    r["category"] = category
                    r["search_query"] = query
                    all_results.append(r)
                    city_count += 1
            time.sleep(0.3)  # Rate limit

        print(f"  {city}: {city_count} {category}")

    return all_results


def save_csv(data: list, filename: str):
    """Save results to CSV."""
    if not data:
        return
    path = OUTPUT_DIR / filename
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    print(f"[Saved] {path} ({len(data)} rows)")


def build_summary(marts: list, showrooms: list, banks: list) -> list:
    """Build city-wise summary with counts."""
    summary = []
    for city in CITIES:
        city_marts = [r for r in marts if r["city"] == city]
        city_showrooms = [r for r in showrooms if r["city"] == city]
        city_banks = [r for r in banks if r["city"] == city]

        # Count by brand
        mart_names = set(r["name"] for r in city_marts)
        showroom_brands = {}
        for r in city_showrooms:
            for brand in ["Honda", "Hero", "TVS", "Bajaj", "Suzuki", "Royal Enfield", "Yamaha", "KTM"]:
                if brand.lower() in r["name"].lower():
                    showroom_brands[brand] = showroom_brands.get(brand, 0) + 1
        bank_names = {}
        for r in city_banks:
            for bank in ["HDFC", "ICICI", "SBI", "Axis", "PNB", "Bank of Baroda", "Canara", "Union", "Kotak", "IndusInd"]:
                if bank.lower() in r["name"].lower():
                    bank_names[bank] = bank_names.get(bank, 0) + 1

        summary.append({
            "City": city,
            "Total Marts": len(city_marts),
            "Mart Names": ", ".join(mart_names)[:200] if mart_names else "None",
            "Total Showrooms": len(city_showrooms),
            "Honda": showroom_brands.get("Honda", 0),
            "Hero": showroom_brands.get("Hero", 0),
            "TVS": showroom_brands.get("TVS", 0),
            "Bajaj": showroom_brands.get("Bajaj", 0),
            "Royal Enfield": showroom_brands.get("Royal Enfield", 0),
            "Total Banks": len(city_banks),
            "HDFC": bank_names.get("HDFC", 0),
            "ICICI": bank_names.get("ICICI", 0),
            "SBI": bank_names.get("SBI", 0),
            "Axis": bank_names.get("Axis", 0),
            "Grand Total": len(city_marts) + len(city_showrooms) + len(city_banks),
        })
    return summary


def upload_to_sheet(summary, marts, showrooms, banks):
    """Upload all data to a new Google Sheet."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        creds_path = Path(__file__).parent.parent.parent / "credentials" / "google-service-account.json"
        creds = Credentials.from_service_account_file(
            str(creds_path),
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        gc = gspread.authorize(creds)

        # Create new sheet
        sh = gc.create("JH City Research — Marts, Showrooms, Banks")
        print(f"\n[Sheet Created] {sh.url}")

        # Share with Satyam
        sh.share("satyam.gupta@apnamart.in", perm_type="user", role="writer")
        sh.share("satyamgupta1312@gmail.com", perm_type="user", role="writer")

        # Tab 1: Summary
        ws_summary = sh.sheet1
        ws_summary.update_title("Summary")
        if summary:
            headers = list(summary[0].keys())
            ws_summary.append_row(headers)
            for row in summary:
                ws_summary.append_row(list(row.values()))
            time.sleep(1)

        # Tab 2: Marts
        ws_marts = sh.add_worksheet("Marts", rows=max(len(marts)+1, 10), cols=10)
        if marts:
            headers = ["City", "Area", "Name", "Address", "Rating", "Total Ratings", "Google Maps"]
            ws_marts.append_row(headers)
            for r in marts:
                ws_marts.append_row([r["city"], r["area"], r["name"], r["address"], r["rating"], r["total_ratings"], r["maps_link"]])
            time.sleep(1)

        # Tab 3: Bike Showrooms
        ws_show = sh.add_worksheet("Bike Showrooms", rows=max(len(showrooms)+1, 10), cols=10)
        if showrooms:
            headers = ["City", "Area", "Name", "Brand", "Address", "Rating", "Total Ratings", "Google Maps"]
            ws_show.append_row(headers)
            for r in showrooms:
                brand = ""
                for b in ["Honda", "Hero", "TVS", "Bajaj", "Suzuki", "Royal Enfield", "Yamaha", "KTM"]:
                    if b.lower() in r["name"].lower():
                        brand = b
                        break
                ws_show.append_row([r["city"], r["area"], r["name"], brand, r["address"], r["rating"], r["total_ratings"], r["maps_link"]])
            time.sleep(1)

        # Tab 4: Banks
        ws_banks = sh.add_worksheet("Banks", rows=max(len(banks)+1, 10), cols=10)
        if banks:
            headers = ["City", "Area", "Name", "Bank Type", "Address", "Rating", "Total Ratings", "Google Maps"]
            ws_banks.append_row(headers)
            for r in banks:
                bank_type = ""
                for b in ["HDFC", "ICICI", "SBI", "Axis", "PNB", "Bank of Baroda", "Canara", "Union", "Kotak", "IndusInd", "Bank of India", "Central Bank", "UCO"]:
                    if b.lower() in r["name"].lower():
                        bank_type = b
                        break
                ws_banks.append_row([r["city"], r["area"], r["name"], bank_type, r["address"], r["rating"], r["total_ratings"], r["maps_link"]])

        print(f"[Sheet URL] {sh.url}")
        return sh.url

    except Exception as e:
        print(f"[Sheet Error] {e}")
        return None


def main():
    print(f"\n{'='*60}")
    print(f"  JH CITY RESEARCH — 33 Cities")
    print(f"  Marts + Bike Showrooms + Banks")
    print(f"  Google Maps Places API")
    print(f"{'='*60}\n")

    # Search Marts
    print("[1/3] Searching Marts...")
    marts = search_category("marts", SEARCHES["marts"])
    save_csv(marts, "marts.csv")

    # Search Bike Showrooms
    print("\n[2/3] Searching Bike Showrooms...")
    showrooms = search_category("bike_showrooms", SEARCHES["bike_showrooms"])
    save_csv(showrooms, "bike_showrooms.csv")

    # Search Banks
    print("\n[3/3] Searching Banks...")
    banks = search_category("banks", SEARCHES["banks"])
    save_csv(banks, "banks.csv")

    # Build Summary
    print("\n[Summary] Building city-wise counts...")
    summary = build_summary(marts, showrooms, banks)
    save_csv(summary, "summary.csv")

    # Upload to Google Sheet
    print("\n[Upload] Creating Google Sheet...")
    sheet_url = upload_to_sheet(summary, marts, showrooms, banks)

    # Final stats
    print(f"\n{'='*60}")
    print(f"  DONE!")
    print(f"  Marts: {len(marts)}")
    print(f"  Showrooms: {len(showrooms)}")
    print(f"  Banks: {len(banks)}")
    print(f"  Cities: {len(CITIES)}")
    if sheet_url:
        print(f"  Sheet: {sheet_url}")
    print(f"  Local: {OUTPUT_DIR}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
