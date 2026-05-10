import requests
import json

# --- 1. CONFIGURATION ---
# These details are in your "student pack" [cite: 358, 360]
USERNAME = "hackathon6@hackathon.com"
PASSWORD = "Gono399764"
IAM_URL = "https://iam-vandv.sophiagenetics.com/account/token"
VQS_URL = "https://platform-vandv1.sophiagenetics.com/api/variant/query"

# Important: Find your specific dataset key in the browser network tab [cite: 407, 411]
DATASET_KEY = "PASTE_YOUR_KEY_HERE"

def get_access_token():
    """Fetches a fresh 1-hour IAM bearer token[cite: 527, 529]."""
    payload = {
        "username": USERNAME,
        "password": PASSWORD
    }
    response = requests.post(IAM_URL, json=payload)
    
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        raise Exception(f"Authentication failed: {response.text}")

def query_pathogenic_variants(token):
    """Queries the VQS for Pathogenic and Likely Pathogenic variants[cite: 595]."""
    headers = {
        "Authorization": f"Bearer {token}", # [cite: 522]
        "Content-Type": "application/json" # [cite: 500]
    }
    
    # Query Body [cite: 550, 551]
    query_body = {
        "columns": ["*"], # Request all available data points [cite: 553]
        "filters": {
            # FQL requires escaped quotes for column names with dots 
            "filterString": "fql:(\"userAnnotations.interpretation.acmg.result.classificationFinal\" anyOf ('Pathogenic', 'Likely Pathogenic'))"
        },
        "pagination": {
            "offset": 0,
            "limit": 50 # Default max is often 1000 [cite: 570]
        }
    }
    
    # The 'key' must be passed as a query parameter [cite: 548, 597]
    params = {"parameters.key": DATASET_KEY}
    
    response = requests.post(VQS_URL, params=params, json=query_body, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Query Error: {response.status_code}")
        return None

# --- EXECUTION ---
try:
    print("Authenticating...")
    token = get_access_token()
    
    print("Fetching Pathogenic variants...")
    results = query_pathogenic_variants(token)
    
    if results:
        # Access the structured data inside pageContent [cite: 604, 606]
        columns = results['pageContent']['columns']
        data_rows = results['pageContent']['data']
        
        print(f"Found {len(data_rows)} high-priority variants.")
        # Process the first row as an example
        if data_rows:
            print(f"Sample Data: {dict(zip(columns, data_rows[0]))}")
            
except Exception as e:
    print(f"An error occurred: {e}")