import time
import cloudscraper
from bs4 import BeautifulSoup


def extract_odb_data(code):
    """Generates scrapping for an specefic ODB code managing the Cloudflare protection."""
    url = f"https://www.odb.com/{code.lower()}"

    # Create a CloudScraper instance
    scraper = cloudscraper.create_scraper(
        browser={
            "browser" : "chrome",
            "platform" : "windows",
            "desktop" : True,
        }
    )

    # Getting Data
    try:
        print(f"Getting info for Code: {code.upper()}...")
        response = scraper.get(url)
        
        if response.status_code == 404:
            print(f"Code {code.upper()} not found on the server.")
            return None
        elif response.status_code != 200:
            print(f"Failed to retrieve data for Code: {code.upper()}. Status code: {response.status_code}")
            return None
        
        # Parsing HTML with beautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")

        # Extracting main title
        main_title = soup.find("h1")
        title_text = main_title.text.strip() if main_title else "Not Found"

        # Extracting description (tcode class)
        tcode_desc = soup.find("p", class_="tcode")
        desc_short = tcode_desc.text.strip() if tcode_desc else "Not available"

        # Extracticng Sympthoms and Root Causes dinamically looking for h2 headers
        symptoms = []
        causes = []

        for h2 in soup.find_all("h2"):
            header_text = h2.text.lower()

            # Look up fot ul that follows h2 inmediatly
            if "symptoms" in header_text:
                next_ul = h2.find_next_sibling("ul")
                if  next_ul:
                    symptoms = [
                        li.next.strip() for li in next_ul.find_all("li")
                    ]
            elif "causes" in header_text or "potential causes" in header_text:
                next_ul = h2.find_next_sibling("ul")
                if next_ul:
                    causes = [
                        li.text.strip() for li in next_ul.find_all("li")
                    ]

        # Estructuring info for knowlege base
        extracted_info = {
            "code": code.upper(),
            "title": title_text,
            "technical_description": desc_short,
            "symptoms": symptoms,
            "potential_causes": causes,
        }

        return extracted_info
    except Exception as e:
        print(f"Error while processing {code}: {e}")
        return None
    
#Running Example
if __name__ == "__main__":
    test_code = "P0001"
    data =  extract_odb_data(test_code)

    if data:
        print("\n----Info successfully extracted----")
        print(f"Code: {data['code']}")
        print(f"Title: {data['title']}")
        print(f"Description: {data['technical_description']}")
        print(f"Symptoms: {data['symptoms']}")
        print(f"Potential causes: {data['potential_causes']}")