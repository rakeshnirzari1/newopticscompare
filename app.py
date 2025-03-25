import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
from flask import Flask, render_template_string, request

# Define the path to the CSV file
csv_path = "sku.csv"  # Adjust path since we're in the api/ directory

# Function to fetch product link from Binocentral search results
def get_binocentral_product_link(sku):
    try:
        search_url = f"https://binocentral.com.au/catalogsearch/result/?q={sku}"
        response = requests.get(search_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        product_link_element = soup.find('a', {'class': 'product-item-link'})
        if product_link_element:
            return product_link_element['href']
        else:
            print(f"No product link found for SKU {sku} on Binocentral")
            return None
    except Exception as e:
        print(f"Error fetching product link for SKU {sku} on Binocentral: {e}")
        return None

# Function to scrape stock and pricing information from Binocentral product page
def scrape_binocentral_product_page(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        stock_element = soup.find('div', {'class': 'stock other'})
        stock_info = stock_element.find('span').text.strip() if stock_element else "N/A"
        price_element = soup.find('span', {'class': 'price-container price-final_price tax weee'})
        price = price_element.find('span', {'class': 'price'}).text.strip() if price_element and price_element.find('span', {'class': 'price'}) else "N/A"
        price_amount = price_element.find('span', {'class': 'price-wrapper'})['data-price-amount'] if price_element and price_element.find('span', {'class': 'price-wrapper'}) else "N/A"
        return {
            "Binocentral Stock Info": stock_info,
            "Binocentral Price": price,
            "Binocentral Price Amount": price_amount,
            "Binocentral Search URL": url
        }
    except Exception as e:
        print(f"Error scraping Binocentral product page {url}: {e}")
        return {
            "Binocentral Stock Info": "N/A",
            "Binocentral Price": "N/A",
            "Binocentral Price Amount": "N/A",
            "Binocentral Search URL": url
        }

# Function to fetch data from Bintel
def fetch_bintel_data(sku):
    try:
        url = f"https://bintel.com.au/search?q={sku}"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        price_container = soup.find('div', {'class': 'price productitem__price'})
        current_price_max = price_container.find('span', {'data-price-max': True}).text.strip() if price_container and price_container.find('span', {'data-price-max': True}) else "N/A"
        stock_container = soup.find('div', {'class': 'product-stock-level-wrapper'})
        stock_status = [span.text.strip() for span in stock_container.find_all('span') if span.text.strip()] if stock_container else ["N/A"]
        button = soup.find('button', {'class': 'productitem--action-atc'})
        button_text = button.find('span', {'class': 'atc-button--text'}).text.strip() if button and button.find('span', {'class': 'atc-button--text'}) else "N/A"
        return {
            "Bintel Current Price Max": current_price_max,
            "Bintel Stock Status": ", ".join(stock_status),
            "Bintel Button Text": button_text,
            "Bintel Search URL": url
        }
    except Exception as e:
        print(f"Error fetching data for SKU {sku} from Bintel: {e}")
        return {
            "Bintel Current Price Max": "N/A",
            "Bintel Stock Status": "N/A",
            "Bintel Button Text": "N/A",
            "Bintel Search URL": url
        }

# Function to fetch data from Sirius Optics
def fetch_sirius_optics_data(sku):
    try:
        url = f"https://www.sirius-optics.com.au/catalogsearch/result/?cat=0&q={sku}"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        price_element = soup.find('span', {'class': 'price'})
        price = price_element.text.strip() if price_element else "N/A"
        stock_element = soup.find('span', {'class': 'amstockstatus'})
        stock_status = stock_element.text.strip() if stock_element else "N/A"
        return {
            "Sirius Optics Price": price,
            "Sirius Optics Stock Status": stock_status,
            "Sirius Optics Search URL": url
        }
    except Exception as e:
        print(f"Error fetching data for SKU {sku} from Sirius Optics: {e}")
        return {
            "Sirius Optics Price": "N/A",
            "Sirius Optics Stock Status": "N/A",
            "Sirius Optics Search URL": url
        }

# Read the CSV file and scrape data (run once at startup)
print("Starting to process SKUs...")
df = pd.read_csv(csv_path)

# Initialize a list to store data for all SKUs
sku_data_list = []

# Counter to limit the number of SKUs processed
max_skus_to_process = 20
processed_skus = 0

# Iterate over each SKU and fetch data, stop after 20 SKUs
for index, row in df.iterrows():
    if processed_skus >= max_skus_to_process:
        print(f"Stopping after processing {max_skus_to_process} SKUs.")
        break

    sku = row['SKU']
    print(f"Processing SKU: {sku}")

    # Fetch data from Binocentral
    binocentral_link = get_binocentral_product_link(sku)
    binocentral_data = scrape_binocentral_product_page(binocentral_link) if binocentral_link else {
        "Binocentral Stock Info": "N/A",
        "Binocentral Price": "N/A",
        "Binocentral Price Amount": "N/A",
        "Binocentral Search URL": f"https://binocentral.com.au/catalogsearch/result/?q={sku}"
    }

    # Fetch data from Bintel
    bintel_data = fetch_bintel_data(sku)

    # Fetch data from Sirius Optics
    sirius_optics_data = fetch_sirius_optics_data(sku)

    # Combine all data for this SKU
    sku_data = {
        "SKU": sku,
        **binocentral_data,
        **bintel_data,
        **sirius_optics_data
    }
    sku_data_list.append(sku_data)

    processed_skus += 1

print("Finished processing SKUs. Starting Flask server...")

# Initialize Flask app
app = Flask(__name__)

# HTML template for the home page with search form and comparison table
home_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SKU Comparison Tool</title>
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            background-color: #f8f9fa;
        }
        .container {
            max-width: 800px;
            margin-top: 50px;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .search-form {
            display: flex;
            justify-content: center;
            margin-bottom: 30px;
        }
        .search-form input[type="text"] {
            width: 300px;
            margin-right: 10px;
        }
        .table-container {
            margin-top: 20px;
        }
        .error-message {
            text-align: center;
            color: #dc3545;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="display-4">SKU Comparison Tool</h1>
            <p class="lead">Search for an SKU to compare prices and stock across suppliers.</p>
        </div>

        <!-- Search Form -->
        <form method="GET" action="/" class="search-form">
            <input type="text" name="sku" class="form-control" placeholder="Enter SKU (e.g., 22450)" value="{{ sku if sku else '' }}" required>
            <button type="submit" class="btn btn-primary">Search</button>
        </form>

        <!-- Comparison Table -->
        {% if data %}
        <div class="table-container">
            <h3>Comparison for SKU: {{ data['SKU'] }}</h3>
            <table class="table table-striped table-bordered">
                <thead class="table-dark">
                    <tr>
                        <th>Supplier</th>
                        <th>Price</th>
                        <th>Stock Status</th>
                        <th>Buy Link</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Binocentral</td>
                        <td>{{ data['Binocentral Price'] }}</td>
                        <td>{{ data['Binocentral Stock Info'] }}</td>
                        <td><a href="{{ data['Binocentral Search URL'] }}" target="_blank" class="btn btn-sm btn-success">Buy from Binocentral</a></td>
                    </tr>
                    <tr>
                        <td>Bintel</td>
                        <td>{{ data['Bintel Current Price Max'] }}</td>
                        <td>{{ data['Bintel Stock Status'] }}</td>
                        <td><a href="{{ data['Bintel Search URL'] }}" target="_blank" class="btn btn-sm btn-success">Buy from Bintel</a></td>
                    </tr>
                    <tr>
                        <td>Sirius Optics</td>
                        <td>{{ data['Sirius Optics Price'] }}</td>
                        <td>{{ data['Sirius Optics Stock Status'] }}</td>
                        <td><a href="{{ data['Sirius Optics Search URL'] }}" target="_blank" class="btn btn-sm btn-success">Buy from Sirius Optics</a></td>
                    </tr>
                </tbody>
            </table>
        </div>
        {% elif sku and not data %}
        <div class="error-message">
            <p>SKU "{{ sku }}" not found. Please try another SKU.</p>
        </div>
        {% endif %}
    </div>

    <!-- Bootstrap JS (for responsiveness) -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# Route for the home page
@app.route('/', methods=['GET'])
def home():
    sku = request.args.get('sku', None)
    data = None
    if sku:
        data = next((item for item in sku_data_list if item['SKU'] == sku), None)
    return render_template_string(home_template, sku=sku, data=data)

# Run the Flask app (Vercel will handle this part)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Use PORT env variable for Vercel
    app.run(host="0.0.0.0", port=port, debug=False)