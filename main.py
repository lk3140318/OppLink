import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, HttpUrl
import logging
import re # Import regular expressions

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="PaheBypass API")

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates directory
templates = Jinja2Templates(directory="templates")

# Pydantic model for request body validation
class BypassRequest(BaseModel):
    pahe_url: str # Use str initially, validate manually

# --- Helper Function to Extract Link ---

def extract_final_link(pahe_url: str) -> str:
    """
    Fetches the Pahe.ink URL and attempts to extract the final download link.
    This logic might need frequent updates if Pahe.ink changes its structure.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://google.com/' # A generic referer can sometimes help
    }
    session = requests.Session() # Use a session to handle cookies if needed

    try:
        logger.info(f"Attempting to fetch URL: {pahe_url}")
        # Initial request to the pahe.ink link
        response = session.get(pahe_url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status() # Raise exception for bad status codes (4xx or 5xx)
        logger.info(f"Initial fetch successful. Status code: {response.status_code}")
        
        # Look for intermediate forms or redirect scripts
        soup = BeautifulSoup(response.text, 'html.parser')

        # --- COMMON PATTERN 1: Form Submission ---
        # Look for a form that might contain the link or trigger the next step
        form = soup.find('form', {'id': 'landing'}) # Often an ID like 'landing' or similar
        if form and form.get('action'):
            action_url = form.get('action')
            logger.info(f"Found form with action: {action_url}")
            
            # Sometimes the form needs to be submitted to get the final link
            # Prepare form data (find hidden inputs)
            form_data = {}
            inputs = form.find_all('input')
            for input_tag in inputs:
                name = input_tag.get('name')
                value = input_tag.get('value', '') # Default to empty string if no value
                if name:
                    form_data[name] = value
            
            logger.info(f"Submitting form data: {form_data}")
            # Make the POST request
            post_response = session.post(action_url, headers=headers, data=form_data, timeout=15, allow_redirects=True)
            post_response.raise_for_status()
            
            # Check if the final URL is in the response URL after redirects
            final_url = post_response.url
            logger.info(f"Form POST successful. Final URL after redirects: {final_url}")

            # Very important: Check if the final URL is *still* a pahe.ink or similar intermediate link
            if "pahe.ink" in final_url or "pahe.li" in final_url or "intercelestial.com" in final_url: 
                 # Sometimes there's another layer, parse the response *again*
                 logger.info("Detected another intermediate layer. Parsing POST response.")
                 post_soup = BeautifulSoup(post_response.text, 'html.parser')
                 # Attempt to find the link in the new page content (common pattern: link with specific class/id)
                 # Example: Look for a link with class 'button' or 'download-button'
                 final_link_tag = post_soup.find('a', class_=re.compile(r'(button|btn|download)', re.IGNORECASE)) 
                 if final_link_tag and final_link_tag.get('href'):
                     final_url = final_link_tag.get('href')
                     logger.info(f"Found final link tag in POST response: {final_url}")
                 else:
                     logger.warning("Could not find a direct link tag in the second layer.")
                     # Fallback or raise error if needed
                     # Maybe the link is in a script? This gets complex.
                     # For now, return the last URL we got, even if intermediate.
                     # Or raise specific error: raise ValueError("Could not extract link after second layer")
            
            # Check if the result is a valid downloadable link (heuristic)
            # (e.g., contains common file hosting domains) - Optional but good
            common_hosts = ["mega.nz", "drive.google.com", "1fichier.com", "uptobox.com", "zippyshare.com", "racaty", "mediafire.com"]
            if any(host in final_url for host in common_hosts):
                 return final_url
            else:
                logger.warning(f"Final URL {final_url} doesn't seem like a typical download link. Returning it anyway.")
                # It might still be correct, or another intermediate step we didn't handle
                return final_url


        # --- COMMON PATTERN 2: Direct Link in Script or Specific Tag ---
        # (Add alternative finding logic here if the form method doesn't work)
        # Example: Look for a specific button or link directly
        # link_tag = soup.find('a', class_='download') # Or by ID, etc.
        # if link_tag and link_tag.get('href'):
        #    logger.info("Found direct link tag on initial page.")
        #    return link_tag.get('href')

        # --- Fallback / Error ---
        logger.error("Could not find the download link using known patterns.")
        raise ValueError("Could not find the final download link structure on the page.")

    except requests.exceptions.Timeout:
        logger.error(f"Timeout while fetching {pahe_url}")
        raise HTTPException(status_code=408, detail="Timeout when contacting Pahe.ink server.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error fetching {pahe_url}: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch the Pahe.ink URL: {e}")
    except ValueError as e: # Catch our custom extraction error
        logger.error(f"Extraction error: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"An unexpected error occurred during bypass: {e}") # Log full traceback
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {e}")

# --- API Endpoints ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main HTML page."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/bypass", response_class=JSONResponse)
async def handle_bypass(request: BypassRequest):
    """API endpoint to handle the bypass request."""
    pahe_url = request.pahe_url.strip()

    # Basic validation
    if not pahe_url:
        raise HTTPException(status_code=400, detail="URL cannot be empty.")
    
    # More specific validation (ensure it looks like a pahe link)
    # Adjust domains as needed (pahe.ink, pahe.li, etc.)
    if not re.match(r"https?://(.*\.)?(pahe\.ink|pahe\.li|intercelestial\.com)/.*", pahe_url):
         raise HTTPException(status_code=400, detail="Invalid URL format. Please provide a valid Pahe.ink/Pahe.li link.")

    try:
        direct_link = extract_final_link(pahe_url)
        logger.info(f"Successfully extracted link: {direct_link}")
        return {"direct_link": direct_link}
    except HTTPException as e:
        # Re-raise known HTTP exceptions
        raise e
    except Exception as e:
        # Catch any other unexpected errors from extract_final_link
        logger.exception(f"Unexpected error in /bypass endpoint for URL {pahe_url}: {e}")
        raise HTTPException(status_code=500, detail=f"An internal error occurred during link extraction: {e}")

# Optional: Add endpoint for health check (useful for deployment platforms)
@app.get("/health")
async def health_check():
    return {"status": "ok"}

# --- To run locally (for development) ---
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)
