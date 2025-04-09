import requests
from datetime import date, timedelta
from typing import List, Dict, Any, Literal, Union
from ..config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NBP_API_BASE_URL = settings.NBP_API_BASE_URL
MAX_NBP_RANGE_DAYS = 93 # NBP limit for date ranges in a single request

def fetch_nbp_data(url: str) -> List[Dict[str, Any]] | None:
    """Helper function to fetch data from NBP API with error handling."""
    try:
        response = requests.get(
            url,
            headers={'Accept': 'application/json'},
            timeout=15 # Increased timeout
        )
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.Timeout:
        logger.error(f"Timeout while requesting {url}")
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err} - URL: {url}")
        # NBP often returns 404 for no data or bad date ranges, 400 for bad requests
        if response.status_code == 404:
            logger.warning(f"NBP API returned 404 for {url}. Often means no data for the period or invalid query.")
        elif response.status_code == 400:
             logger.warning(f"NBP API returned 400 Bad Request for {url}. Check parameters.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data from {url}: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred fetching {url}: {e}")
    return None


def get_currency_data_for_range(currency: str, start_date: date, end_date: date) -> List[Dict[str, Any]]:
    """
    Fetches currency data for a single currency, handling NBP date range limits
    by splitting into multiple requests if necessary.
    """
    all_rates = []
    current_start = start_date
    currency = currency.upper()

    while current_start <= end_date:
        # Calculate end date for this chunk, respecting NBP limit and overall end_date
        chunk_end = min(current_start + timedelta(days=MAX_NBP_RANGE_DAYS - 1), end_date)
        start_str = current_start.strftime('%Y-%m-%d')
        end_str = chunk_end.strftime('%Y-%m-%d')

        url = f"{NBP_API_BASE_URL}/exchangerates/rates/a/{currency}/{start_str}/{end_str}/"
        logger.info(f"Fetching NBP currency data: {currency} from {start_str} to {end_str}")
        data = fetch_nbp_data(url)

        if data and isinstance(data, dict) and 'rates' in data:
            # Ensure we have the expected structure before appending
             all_rates.extend(data['rates'])
        elif data:
             logger.warning(f"Unexpected data format received from NBP for {currency}: {data}")
        # If fetch_nbp_data returned None due to error, loop continues but logs error

        # Move to the next chunk
        current_start = chunk_end + timedelta(days=1)

    # Deduplicate rates (NBP might return overlapping dates if chunk boundaries align with weekends/holidays)
    # This assumes 'effectiveDate' is unique per day for a currency
    unique_rates = []
    seen_dates = set()
    for rate in all_rates:
        if rate['effectiveDate'] not in seen_dates:
            unique_rates.append(rate)
            seen_dates.add(rate['effectiveDate'])

    return unique_rates


def get_gold_data_for_range(start_date: date, end_date: date) -> List[Dict[str, Any]]:
    """
    Fetches gold price data, handling NBP date range limits by splitting
    into multiple requests if necessary.
    """
    all_prices = []
    current_start = start_date

    while current_start <= end_date:
        chunk_end = min(current_start + timedelta(days=MAX_NBP_RANGE_DAYS - 1), end_date)
        start_str = current_start.strftime('%Y-%m-%d')
        end_str = chunk_end.strftime('%Y-%m-%d')

        url = f"{NBP_API_BASE_URL}/cenyzlota/{start_str}/{end_str}/"
        logger.info(f"Fetching NBP gold data from {start_str} to {end_str}")
        data = fetch_nbp_data(url)

        if data and isinstance(data, list): # Gold API returns a list directly
            all_prices.extend(data)
        elif data:
             logger.warning(f"Unexpected data format received from NBP for gold: {data}")

        current_start = chunk_end + timedelta(days=1)

    # Deduplicate based on 'data' field
    unique_prices = []
    seen_dates = set()
    for price in all_prices:
        if price['data'] not in seen_dates:
            unique_prices.append(price)
            seen_dates.add(price['data'])

    return unique_prices


def format_currency_data(rates: List[Dict[str, Any]], currency_code: str) -> List[Dict[str, Any]]:
    """Formats raw NBP currency rates into the structure needed by the frontend/export."""
    return [
        {"Date": entry['effectiveDate'], "Rate": entry['mid'], "Currency": currency_code.upper()}
        for entry in rates
    ]

def format_gold_data(prices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Formats raw NBP gold prices into the structure needed by the frontend/export."""
    return [
        {"Date": entry['data'], "Price": entry['cena']} # Match 'Price' key from original code
        for entry in prices
    ]

def get_latest_rate(currency: str) -> float | None:
    """Fetches the most recent available exchange rate for a currency."""
    currency = currency.upper()
    # Fetch last 10 days to increase chance of getting a recent rate, as NBP might not publish on weekends/holidays
    end_date = date.today()
    start_date = end_date - timedelta(days=10)
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')

    url = f"{NBP_API_BASE_URL}/exchangerates/rates/a/{currency}/{start_str}/{end_str}/"
    logger.info(f"Fetching latest rate for {currency}")
    data = fetch_nbp_data(url)

    if data and isinstance(data, dict) and 'rates' in data and data['rates']:
        # Return the rate from the latest entry
        latest_entry = data['rates'][-1]
        logger.info(f"Latest rate for {currency} ({latest_entry['effectiveDate']}): {latest_entry['mid']}")
        return latest_entry['mid']
    else:
        # Fallback: Try fetching just today's rate (might fail if not published yet)
        url_today = f"{NBP_API_BASE_URL}/exchangerates/rates/a/{currency}/today/"
        data_today = fetch_nbp_data(url_today)
        if data_today and isinstance(data_today, list) and data_today: # 'today' endpoint returns a list
             entry = data_today[0]
             logger.info(f"Latest rate for {currency} (fallback 'today' - {entry['effectiveDate']}): {entry['mid']}")
             return entry['mid']
        logger.warning(f"Could not fetch latest rate for {currency}")
        return None