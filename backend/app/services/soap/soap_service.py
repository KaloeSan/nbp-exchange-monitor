from http.server import BaseHTTPRequestHandler
from xml.etree import ElementTree
import requests
from datetime import datetime, timedelta
import logging
from wsgiref.simple_server import make_server
from typing import Callable, Dict, List, Any

logger = logging.getLogger(__name__)

class SOAPHandler:
    def __init__(self):
        self.namespace = {'soap': 'http://schemas.xmlsoap.org/soap/envelope/'}

    def __call__(self, environ: dict, start_response: Callable) -> List[bytes]:
        """WSGI application handler for SOAP requests"""
        method = environ.get('REQUEST_METHOD', '')
        
        # Handle OPTIONS for CORS
        if method == 'OPTIONS':
            headers = [
                ('Access-Control-Allow-Origin', '*'),
                ('Access-Control-Allow-Methods', 'POST, OPTIONS'),
                ('Access-Control-Allow-Headers', 'Content-Type, SOAPAction'),
                ('Access-Control-Max-Age', '86400'),
                ('Content-Type', 'text/plain'),
            ]
            start_response('200 OK', headers)
            return [b'']

        # Handle POST request
        if method == 'POST':
            try:
                content_length = int(environ.get('CONTENT_LENGTH', 0))
                request_body = environ['wsgi.input'].read(content_length)
                logger.info(f"Received SOAP request: {request_body.decode('utf-8')}")

                # Parse SOAP request
                root = ElementTree.fromstring(request_body)
                body = root.find('soap:Body', self.namespace)
                if body is None:
                    raise ValueError("Invalid SOAP request: Missing Body element")

                method_element = list(body)[0]
                method_name = method_element.tag.split('}')[-1]  # Remove namespace

                # Route to appropriate handler
                handlers = {
                    'get_exchange_rates': self.handle_get_exchange_rates,
                    'get_historical_rates': self.handle_get_historical_rates,
                    'convert_currency': self.handle_convert_currency
                }

                handler = handlers.get(method_name)
                if not handler:
                    raise ValueError(f"Unknown method: {method_name}")

                response_data = handler(method_element)
                soap_response = self._create_soap_response(response_data)
                response_bytes = soap_response.encode('utf-8')

                headers = [
                    ('Content-Type', 'text/xml; charset=utf-8'),
                    ('Content-Length', str(len(response_bytes))),
                    ('Access-Control-Allow-Origin', '*'),
                    ('Access-Control-Allow-Methods', 'POST, OPTIONS'),
                    ('Access-Control-Allow-Headers', 'Content-Type, SOAPAction'),
                ]
                start_response('200 OK', headers)
                return [response_bytes]

            except Exception as e:
                logger.error(f"SOAP error: {str(e)}", exc_info=True)
                error_response = self._create_soap_fault(str(e))
                error_bytes = error_response.encode('utf-8')
                headers = [
                    ('Content-Type', 'text/xml; charset=utf-8'),
                    ('Content-Length', str(len(error_bytes))),
                    ('Access-Control-Allow-Origin', '*'),
                ]
                start_response('500 Internal Server Error', headers)
                return [error_bytes]

        # Handle unsupported methods
        start_response('405 Method Not Allowed', [
            ('Content-Type', 'text/xml'),
            ('Access-Control-Allow-Origin', '*'),
        ])
        return [b'Method not allowed']

    def _create_soap_response(self, body_content: str) -> str:
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        {body_content}
    </soap:Body>
</soap:Envelope>"""

    def _create_soap_fault(self, error_message: str) -> str:
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <soap:Fault>
            <faultcode>soap:Server</faultcode>
            <faultstring>{error_message}</faultstring>
        </soap:Fault>
    </soap:Body>
</soap:Envelope>"""

    def handle_get_exchange_rates(self, method_element):
        """Handle get_exchange_rates SOAP method"""
        try:
            currency_code = method_element.find('currency_code').text.upper()
            start_date = method_element.find('start_date').text
            end_date = method_element.find('end_date').text

            # Validate dates
            datetime.strptime(start_date, '%Y-%m-%d')
            datetime.strptime(end_date, '%Y-%m-%d')

            # Call NBP API
            url = f"http://api.nbp.pl/api/exchangerates/rates/a/{currency_code}/{start_date}/{end_date}/"
            response = requests.get(url, headers={"Accept": "application/json"})

            if response.status_code == 404:
                return f"<getExchangeRatesResponse><error>No data found for {currency_code}</error></getExchangeRatesResponse>"

            response.raise_for_status()
            data = response.json()
            rates = data.get('rates', [])

            rates_xml = "".join(
                f'<rate><date>{r["effectiveDate"]}</date><value>{r["mid"]}</value></rate>'
                for r in rates
            )
            return f"<getExchangeRatesResponse>{rates_xml}</getExchangeRatesResponse>"

        except Exception as e:
            logger.error(f"Error in get_exchange_rates: {str(e)}", exc_info=True)
            raise

    def handle_get_historical_rates(self, method_element):
        """Handle get_historical_rates SOAP method"""
        try:
            currency_code = method_element.find('currency_code').text.upper()
            date_str = method_element.find('date').text

            # Validate date
            datetime.strptime(date_str, '%Y-%m-%d')

            # Call NBP API
            url = f"http://api.nbp.pl/api/exchangerates/rates/a/{currency_code}/{date_str}/"
            response = requests.get(url, headers={"Accept": "application/json"})

            if response.status_code == 404:
                return f"<getHistoricalRatesResponse><error>No data found for {currency_code} on {date_str}</error></getHistoricalRatesResponse>"

            response.raise_for_status()
            data = response.json()
            rate = data['rates'][0] if data.get('rates') else None

            if not rate:
                raise ValueError(f"No rate data available for {currency_code} on {date_str}")

            return f"""<getHistoricalRatesResponse>
                <rate>
                    <date>{rate['effectiveDate']}</date>
                    <value>{rate['mid']}</value>
                    <currency>{currency_code}</currency>
                </rate>
            </getHistoricalRatesResponse>"""

        except Exception as e:
            logger.error(f"Error in get_historical_rates: {str(e)}", exc_info=True)
            raise

    def handle_convert_currency(self, method_element):
        """Handle convert_currency SOAP method"""
        try:
            from_currency = method_element.find('from_currency').text.upper()
            to_currency = method_element.find('to_currency').text.upper()
            amount = float(method_element.find('amount').text)

            if amount <= 0:
                raise ValueError("Amount must be positive")

            # Get latest rates for both currencies
            today = datetime.now().strftime('%Y-%m-%d')
            rates = {}

            for currency in [from_currency, to_currency]:
                if currency != 'PLN':
                    url = f"http://api.nbp.pl/api/exchangerates/rates/a/{currency}/today/"
                    response = requests.get(url, headers={"Accept": "application/json"})
                    
                    if response.status_code == 404:
                        # Try yesterday if today's rate is not available
                        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                        url = f"http://api.nbp.pl/api/exchangerates/rates/a/{currency}/{yesterday}/"
                        response = requests.get(url, headers={"Accept": "application/json"})
                        
                        if response.status_code == 404:
                            raise ValueError(f"No rate found for {currency}")
                    
                    response.raise_for_status()
                    rates[currency] = response.json()['rates'][0]['mid']
                else:
                    rates[currency] = 1.0

            # Calculate conversion
            if from_currency == 'PLN':
                result = amount / rates[to_currency]
            elif to_currency == 'PLN':
                result = amount * rates[from_currency]
            else:
                pln_amount = amount * rates[from_currency]
                result = pln_amount / rates[to_currency]

            return f"""<convertCurrencyResponse>
                <result>{result:.4f}</result>
                <from_currency>{from_currency}</from_currency>
                <to_currency>{to_currency}</to_currency>
                <amount>{amount}</amount>
                <date>{today}</date>
            </convertCurrencyResponse>"""

        except Exception as e:
            logger.error(f"Error in convert_currency: {str(e)}", exc_info=True)
            raise

# Create WSGI application
wsgi_app = SOAPHandler()

def run_server(host='0.0.0.0', port=8001):
    """Run the SOAP server using WSGI"""
    with make_server(host, port, wsgi_app) as httpd:
        logger.info(f"SOAP service starting on http://{host}:{port}")
        httpd.serve_forever()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    run_server()