import axios from 'axios';
import { parseSoapFault } from '../../utils/soapUtils';

// Get SOAP URL from environment variables or use default
const SOAP_BASE_URL = process.env.REACT_APP_SOAP_URL || 'http://localhost:8001/soap';

/**
 * Helper function to make SOAP requests
 * @param {string} soapBody - The SOAP request body
 * @returns {Promise<Document>} - The parsed XML response
 */
const makeSoapRequest = async (soapBody) => {
    try {
        const soapEnvelope = `<?xml version="1.0" encoding="UTF-8"?>
            <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ser="http://services.soap.nbp/">
                <soapenv:Header/>
                <soapenv:Body>
                    ${soapBody}
                </soapenv:Body>
            </soapenv:Envelope>`;

        const response = await axios.post(SOAP_BASE_URL, soapEnvelope, {
            headers: {
                'Content-Type': 'text/xml;charset=UTF-8',
                'SOAPAction': ''
            },
            timeout: 30000,
            withCredentials: false
        });

        const parser = new DOMParser();
        const xmlDoc = parser.parseFromString(response.data, 'text/xml');

        const fault = xmlDoc.getElementsByTagName('soap:Fault')[0];
        if (fault) {
            throw new Error(parseSoapFault(fault));
        }

        return xmlDoc;
    } catch (error) {
        if (axios.isAxiosError(error)) {
            if (error.response) {
                throw new Error(`SOAP Error: ${error.response.status} - ${error.response.statusText}`);
            } else if (error.request) {
                throw new Error('SOAP Error: No response from server. Check if SOAP service is running.');
            }
        }
        throw error;
    }
};

/**
 * Fetch exchange rates for a given currency and date range
 * @param {string} currencyCode - Currency code (e.g., 'EUR')
 * @param {string} startDate - Start date in YYYY-MM-DD format
 * @param {string} endDate - End date in YYYY-MM-DD format
 * @returns {Promise<Array>} Array of exchange rates
 */
export const fetchExchangeRates = async (currencyCode, startDate, endDate) => {
    try {
        const soapBody = `
            <ser:get_exchange_rates>
                <currency_code>${currencyCode}</currency_code>
                <start_date>${startDate}</start_date>
                <end_date>${endDate}</end_date>
            </ser:get_exchange_rates>
        `;

        const xmlDoc = await makeSoapRequest(soapBody);
        const ratesNodes = xmlDoc.getElementsByTagName('rate');
        
        return Array.from(ratesNodes).map(node => ({
            date: node.getElementsByTagName('date')[0]?.textContent,
            rate: parseFloat(node.getElementsByTagName('value')[0]?.textContent)
        }));
    } catch (error) {
        console.error('Error in fetchExchangeRates:', error);
        throw error;
    }
};

/**
 * Get historical exchange rate for a specific date
 * @param {string} currencyCode - Currency code (e.g., 'EUR')
 * @param {string} date - Date in YYYY-MM-DD format
 * @returns {Promise<Object>} Historical rate data
 */
export const getHistoricalRates = async (currencyCode, date) => {
    try {
        const soapBody = `
            <ser:get_historical_rates>
                <currency_code>${currencyCode}</currency_code>
                <date>${date}</date>
            </ser:get_historical_rates>
        `;

        const xmlDoc = await makeSoapRequest(soapBody);
        const rateNode = xmlDoc.getElementsByTagName('rate')[0];
        
        if (!rateNode) {
            throw new Error('No rate data found');
        }

        return {
            date: rateNode.getElementsByTagName('date')[0]?.textContent,
            rate: parseFloat(rateNode.getElementsByTagName('value')[0]?.textContent),
            currency: rateNode.getElementsByTagName('currency')[0]?.textContent
        };
    } catch (error) {
        console.error('Error in getHistoricalRates:', error);
        throw error;
    }
};

/**
 * Convert currency amount
 * @param {string} fromCurrency - Source currency code
 * @param {string} toCurrency - Target currency code
 * @param {number} amount - Amount to convert
 * @returns {Promise<Object>} Conversion result
 */
export const convertCurrency = async (fromCurrency, toCurrency, amount) => {
    try {
        const soapBody = `
            <ser:convert_currency>
                <from_currency>${fromCurrency}</from_currency>
                <to_currency>${toCurrency}</to_currency>
                <amount>${amount}</amount>
            </ser:convert_currency>
        `;

        const xmlDoc = await makeSoapRequest(soapBody);
        const resultNode = xmlDoc.getElementsByTagName('convertCurrencyResponse')[0];
        
        if (!resultNode) {
            throw new Error('No conversion result found');
        }

        return {
            result: parseFloat(resultNode.getElementsByTagName('result')[0]?.textContent),
            fromCurrency: resultNode.getElementsByTagName('from_currency')[0]?.textContent,
            toCurrency: resultNode.getElementsByTagName('to_currency')[0]?.textContent,
            amount: parseFloat(resultNode.getElementsByTagName('amount')[0]?.textContent),
            date: resultNode.getElementsByTagName('date')[0]?.textContent
        };
    } catch (error) {
        console.error('Error in convertCurrency:', error);
        throw error;
    }
};