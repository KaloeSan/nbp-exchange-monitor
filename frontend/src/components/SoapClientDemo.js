import React, { useState } from 'react';
import { fetchExchangeRates, getHistoricalRates, convertCurrency } from '../services/soap/soapClient';
import '../App.css';

const SoapClientDemo = () => {
    // Get default dates
    const today = new Date();
    const lastMonth = new Date();
    lastMonth.setMonth(lastMonth.getMonth() - 1);

    // States for exchange rates
    const [currencyCode, setCurrencyCode] = useState('EUR');
    const [startDate, setStartDate] = useState(lastMonth.toISOString().split('T')[0]);
    const [endDate, setEndDate] = useState(today.toISOString().split('T')[0]);
    const [rates, setRates] = useState([]);

    // States for historical rates
    const [historicalCurrency, setHistoricalCurrency] = useState('USD');
    const [historicalDate, setHistoricalDate] = useState('2025-01-15');
    const [historicalRate, setHistoricalRate] = useState(null);

    // States for currency conversion
    const [fromCurrency, setFromCurrency] = useState('EUR');
    const [toCurrency, setToCurrency] = useState('USD');
    const [amount, setAmount] = useState('100');
    const [conversionResult, setConversionResult] = useState(null);

    // State for errors
    const [error, setError] = useState('');

    // Handler for fetching exchange rates
    const handleFetchRates = async () => {
        setError('');
        setRates([]);
        try {
            const result = await fetchExchangeRates(currencyCode, startDate, endDate);
            setRates(result);
        } catch (err) {
            setError('Failed to fetch exchange rates: ' + err.message);
        }
    };

    // Handler for fetching historical rates
    const handleGetHistoricalRate = async () => {
        setError('');
        setHistoricalRate(null);
        try {
            const result = await getHistoricalRates(historicalCurrency, historicalDate);
            setHistoricalRate(result);
        } catch (err) {
            setError('Failed to fetch historical rate: ' + err.message);
        }
    };

    // Handler for currency conversion
    const handleConvertCurrency = async () => {
        setError('');
        setConversionResult(null);
        try {
            const result = await convertCurrency(fromCurrency, toCurrency, parseFloat(amount));
            setConversionResult(result);
        } catch (err) {
            setError('Failed to convert currency: ' + err.message);
        }
    };

    return (
        <div className="soap-client-demo">
            <h2>SOAP Operations</h2>
            {error && <div className="error-message">{error}</div>}

            <div className="soap-section">
                <h3>Exchange Rates</h3>
                <div className="form-group">
                    <input
                        type="text"
                        value={currencyCode}
                        onChange={(e) => setCurrencyCode(e.target.value)}
                        placeholder="Currency (e.g., EUR)"
                    />
                    <input
                        type="date"
                        value={startDate}
                        onChange={(e) => setStartDate(e.target.value)}
                    />
                    <input
                        type="date"
                        value={endDate}
                        onChange={(e) => setEndDate(e.target.value)}
                    />
                    <button onClick={handleFetchRates}>Fetch Rates</button>
                </div>
                {rates.length > 0 && (
                    <div className="results">
                        <h4>Results:</h4>
                        <ul>
                            {rates.map((rate, index) => (
                                <li key={index}>
                                    {rate.date}: {rate.rate}
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
            </div>

            <div className="soap-section">
                <h3>Historical Rate</h3>
                <div className="form-group">
                    <input
                        type="text"
                        value={historicalCurrency}
                        onChange={(e) => setHistoricalCurrency(e.target.value)}
                        placeholder="Currency (e.g., USD)"
                    />
                    <input
                        type="date"
                        value={historicalDate}
                        onChange={(e) => setHistoricalDate(e.target.value)}
                    />
                    <button onClick={handleGetHistoricalRate}>Get Historical Rate</button>
                </div>
                {historicalRate && (
                    <div className="results">
                        <h4>Result:</h4>
                        <p>
                            {historicalRate.currency} on {historicalRate.date}: {historicalRate.rate}
                        </p>
                    </div>
                )}
            </div>

            <div className="soap-section">
                <h3>Currency Conversion</h3>
                <div className="form-group">
                    <input
                        type="text"
                        value={fromCurrency}
                        onChange={(e) => setFromCurrency(e.target.value)}
                        placeholder="From Currency (e.g., EUR)"
                    />
                    <input
                        type="text"
                        value={toCurrency}
                        onChange={(e) => setToCurrency(e.target.value)}
                        placeholder="To Currency (e.g., USD)"
                    />
                    <input
                        type="number"
                        value={amount}
                        onChange={(e) => setAmount(e.target.value)}
                        placeholder="Amount"
                    />
                    <button onClick={handleConvertCurrency}>Convert</button>
                </div>
                {conversionResult && (
                    <div className="results">
                        <h4>Result:</h4>
                        <p>
                            {conversionResult.amount} {conversionResult.fromCurrency} = {' '}
                            {conversionResult.result} {conversionResult.toCurrency}
                            <br />
                            <small>(Rate as of {conversionResult.date})</small>
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default SoapClientDemo;