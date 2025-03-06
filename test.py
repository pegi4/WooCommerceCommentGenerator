from playwright.sync_api import sync_playwright

def submit_review(url, name, email, rating, comment):
    with sync_playwright() as p:
        # Zaženi brskalnik (headless=False za razhroščevanje)
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # Odpri stran
        page.goto(url)
        print(f"Odprl stran: {url}")

        # Klikni na zavihek "Mnenja"
        page.click("#tab-title-reviews", timeout=10000)
        print("Kliknil na zavihek 'Mnenja'")

        # Počakaj, da je obrazec viden
        page.wait_for_selector("#respond", state="visible", timeout=15000)
        print("Obrazec za mnenja (#respond) je viden")

        # Nastavi oceno v <select id="rating">
        page.select_option("#rating", str(rating))
        print(f"Nastavil oceno na: {rating}")

        # Sproži dogodek 'change', da JavaScript zazna spremembo
        page.evaluate('document.querySelector("#rating").dispatchEvent(new Event("change"))')
        print("Sprožil dogodek 'change' na #rating")

        # Preveri trenutno izbrano vrednost (razhroščevanje)
        selected_rating = page.evaluate('document.querySelector("#rating").value')
        print(f"Trenutna vrednost v #rating: {selected_rating}")

        # Izpolni ostale dele obrazca
        page.fill("#author", name)
        print(f"Vnesel ime: {name}")
        page.fill("#email", email)
        print(f"Vnesel e-pošto: {email}")
        page.fill("#comment", comment)
        print(f"Vnesel mnenje: {comment}")
        page.check("#wp-comment-cookies-consent")
        print("Označil soglasje za piškotke")

        # Oddaj obrazec
        page.click("#submit")
        print("Oddal obrazec")

        # Počakaj 5 sekund, da se stran osveži
        page.wait_for_timeout(5000)
        
        # Preveri, ali je komentar viden (če ni moderiranja)
        comments_section = page.query_selector("#comments")
        if comments_section:
            print("Komentarji so vidni:")
            print(comments_section.inner_text())
        else:
            print("Sekcija #comments ni najdena.")

        browser.close()

# Statične vrednosti za testiranje
url = "https://frizerskahisaandrejka.si/izdelek/otroski-sampon-za-preventivo-pred-usmi-subrina-professional-250-ml-kopija"
name = "Testno Ime"
email = "test@example.com"
rating = 5  # Ocena 5 (Odlično)
comment = "To je testno mnenje."

# Zaženi skripto
submit_review(url, name, email, rating, comment)