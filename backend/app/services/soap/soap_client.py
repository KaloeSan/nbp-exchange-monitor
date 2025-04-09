from zeep import Client, Transport
from zeep.exceptions import Fault, TransportError
import logging
from urllib3.exceptions import MaxRetryError
from ...config import settings

logger = logging.getLogger(__name__)

# Use service name in Docker or localhost for development
WSDL_URL = f"http://{settings.SOAP_SERVICE_HOST}:{settings.SOAP_SERVICE_PORT}/soap/?wsdl"

def fetch_exchange_rates(currency_code: str, start_date: str, end_date: str):
    """
    Fetch exchange rates using the SOAP service with proper error handling.
    
    Args:
        currency_code: 3-letter currency code (e.g. 'USD')
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    
    Returns:
        List of exchange rate data or None if error occurs
    """
    try:
        transport = Transport(timeout=10)
        client = Client(WSDL_URL, transport=transport)
        
        logger.info(f"Fetching rates for {currency_code} from {start_date} to {end_date}")
        response = client.service.get_exchange_rates(
            currency_code=currency_code,
            start_date=start_date,
            end_date=end_date
        )
        return response
    
    except Fault as fault:
        logger.error(f"SOAP Fault: {fault.message}")
    except TransportError as transport_error:
        logger.error(f"Transport Error: {transport_error}")
    except MaxRetryError:
        logger.error("Max retries exceeded - service unavailable")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    
    return None

if __name__ == "__main__":
    # Example usage with error handling
    try:
        result = fetch_exchange_rates("USD", "2023-01-01", "2023-01-10")
        if result:
            for item in result:
                print(item)
        else:
            print("Failed to fetch exchange rates")
    except Exception as e:
        print(f"Error in example usage: {e}")
