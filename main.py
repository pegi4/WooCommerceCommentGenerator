import os
import csv
import random
from playwright.sync_api import sync_playwright
import google.generativeai as genai
from dotenv import load_dotenv
import logging
import time

# Utišaj loge, ki niso napake
logging.getLogger('absl').setLevel(logging.ERROR)
logging.getLogger('grpc').setLevel(logging.ERROR)

# Naloži okoljske spremenljivke iz .env datoteke
load_dotenv()
GEMINI_API = os.getenv('GEMINI_API')

# Nastavi Gemini API
genai.configure(api_key=GEMINI_API)

# Funkcija za pridobivanje opisa izdelka iz URL-ja
def get_product_description(url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)

        short_desc_elem = page.query_selector(".product-short-description")
        short_desc = short_desc_elem.inner_text().strip() if short_desc_elem else ""
        long_desc_elem = page.query_selector("#tab-description")
        long_desc = long_desc_elem.inner_text().strip() if long_desc_elem else ""

        if short_desc and long_desc:
            description = f"{short_desc}\n\n{long_desc}"
        elif short_desc:
            description = short_desc
        elif long_desc:
            description = long_desc
        else:
            description = "Opis ni na voljo."

        browser.close()
        return description
    
# Funkcija za branje prompta iz datoteke
def load_prompt(file_path="comment_prompt.txt"):
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read().strip()

# Funkcija za generiranje komentarja z Gemini (če je potreben)
def generate_comment(product_description, rating, existing_comments):
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt_template = load_prompt()
    existing_comments_str = "; ".join(existing_comments) if existing_comments else ""
    prompt = prompt_template.format(product_description=product_description, rating=rating, existing_comments=existing_comments_str)
    response = model.generate_content(prompt)
    return response.text.strip()

# Funkcija za oddajo komentarja prek obrazca
def submit_comment(url, name, email, rating, comment):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)

        print(f"Odpiram stran: {url}")

        # Klikni na zavihek "Mnenja"
        page.click("#tab-title-reviews", timeout=10000)
        print("Kliknil na zavihek 'Mnenja'")

        # Počakaj, da je obrazec viden (div#respond)
        page.wait_for_selector("#respond", state="visible", timeout=15000)
        print("Obrazec za komentarje (#respond) je viden")

        # Izpiši HTML obrazca za razhroščevanje
        respond_html = page.query_selector("#respond").inner_html()
        print("HTML vsebina obrazca (#respond):")
        print(respond_html[:500])  # Prvih 500 znakov za preglednost

        # Preveri, ali obstaja sistem z zvezdicami
        if page.query_selector(".stars"):
            print("Uporabljam sistem z zvezdicami")
            try:
                page.wait_for_selector(".stars", state="visible", timeout=15000)
                print("Element zvezdic (.stars) je viden")
            except Exception as e:
                print(f"Napaka pri čakanju na .stars: {e}")
                print("Poskušam alternativni selektor...")
                page.wait_for_selector("a[class*='star-']", state="visible", timeout=15000)
                print("Alternativni selektor za zvezdice (a[class*='star-']) je viden")

            # Izberi ustrezno zvezdico (star-1 do star-5) in sproži JavaScript dogodke
            star_selector = f".star-{rating}"  # Npr. ".star-5" za oceno 5
            page.evaluate(f'document.querySelector("{star_selector}").click()')  # Simuliraj klik z JS
            print(f"Kliknil na zvezdico z JavaScript: {star_selector} (ocena {rating})")

            # Sproži dogodek 'change' na <select id="rating">
            page.evaluate('document.querySelector("#rating").dispatchEvent(new Event("change"))')
            print("Sprožil dogodek 'change' na <select id='rating'>")
        else:
            print("Sistem z zvezdicami ni prisoten, uporabljam <select>")
            # Počakaj, da je <select id="rating"> viden
            page.wait_for_selector("#rating", state="visible", timeout=15000)
            print("Element <select id='rating'> je viden")
            # Nastavi oceno neposredno prek <select>
            page.select_option("#rating", str(rating))
            print(f"Izbral oceno prek <select>: {rating}")

        # Preveri, ali se je vrednost v <select> posodobila (za razhroščevanje)
        selected_rating = page.evaluate('document.querySelector("#rating").value')
        print(f"Izbrana vrednost v <select id='rating'>: {selected_rating}")

        # Če vrednost ni pravilna, jo ročno nastavi
        if selected_rating != str(rating):
            print(f"Vrednost v <select> ni pravilna, ročno nastavljam na {rating}")
            page.evaluate(f'document.querySelector("#rating").value = "{rating}"')
            page.evaluate('document.querySelector("#rating").dispatchEvent(new Event("change"))')
            print("Ročno nastavil vrednost in sprožil dogodek 'change'")

        # Izpolni ostale dele obrazca
        page.fill("#author", name)
        print(f"Vnesel ime: {name}")
        page.fill("#email", email)
        print(f"Vnesel email: {email}")
        # Če je komentar prazen, ga ne vnašaj
        if comment:
            page.fill("#comment", comment)
            print(f"Vnesel komentar: {comment}")
        else:
            print("Komentar je prazen, izpustil vnos v #comment")
        page.check("#wp-comment-cookies-consent")
        print("Označil soglasje za piškotke")
        
        # Klikni na submit in počakaj na spremembo
        page.click("#submit")
        print("Kliknil na 'Pošlji'")
        
        # Počakaj na morebitno preusmeritev ali potrditev (npr. 5 sekund)
        page.wait_for_timeout(5000)
        
        # Preveri vsebino strani po oddaji
        content = page.content()
        print("Vsebina strani po oddaji:")
        print(content[:500])  # Izpiši prvih 500 znakov za preglednost
        
        # Preveri, ali je komentar viden (če ni moderiranja)
        comments_section = page.query_selector("#comments")
        if comments_section:
            comments_text = comments_section.inner_text()
            print("Trenutna vsebina sekcije komentarjev:")
            print(comments_text)
        else:
            print("Sekcija komentarjev (#comments) ni najdena.")

        browser.close()

# Glavna logika
def main():
    # Preberi povezave iz CSV
    products = []
    with open("products.csv", "r", encoding="utf-8") as file:
        reader = csv.reader(file)
        next(reader)
        products = [row[0] for row in reader]  # Predpostavka: URL v prvem stolpcu

    # Preberi osebe iz CSV
    osebe = []
    with open("osebe.csv", "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        osebe = [(row["Ime"], row["Email"]) for row in reader]

    for product_url in products:
        description = get_product_description(product_url)
        
        # Uporabi samo ocene 4 ali 5 zvezdic
        num_reviews = random.randint(6, 12)  # Skupno število mnenj
        half_reviews = num_reviews // 2  # Polovica z generiranimi komentarji
        remaining_reviews = num_reviews - half_reviews  # Polovica brez komentarjev
        
        print(f"Number of reviews for: {product_url} -> {num_reviews} (with comment: {half_reviews}, without comment: {remaining_reviews})")
        
        comments = []
        existing_comments = []
        
        # Prva polovica z generiranimi komentarji
        for _ in range(half_reviews):
            person = random.choice(osebe)
            name, email = person[0], person[1]
            rating = random.choice([4, 5])
            comment = generate_comment(description, rating, existing_comments)
            comments.append((rating, name, email, comment))
            existing_comments.append(comment)
        
        # Druga polovica brez komentarjev
        for _ in range(remaining_reviews):
            person = random.choice(osebe)
            name, email = person[0], person[1]
            rating = random.choice([4, 5])
            comments.append((rating, name, email, ""))  # Prazen komentar
        
        random.shuffle(comments)
        
        for rating, name, email, comment in comments:
            print(f"Poskušam oddati mnenje: {rating} zvezdic, {name}: {comment or 'brez komentarja'}")
            submit_comment(product_url, name, email, rating, comment)
            print(f"Končal z oddajo mnenja za {product_url}: {rating} zvezdic, {name}: {comment or 'brez komentarja'}")
            print("-" * 50)

if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    main()
    time.sleep(1)