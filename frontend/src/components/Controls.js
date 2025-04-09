import React, { useState, useEffect } from 'react';
import { getAvailableCurrencies } from '../services/api';
import Select from 'react-select';
import './Controls.css';

function Controls({ onFetchData, isFetching }) {
    // Get default dates
    const today = new Date();
    const lastMonth = new Date();
    lastMonth.setMonth(lastMonth.getMonth() - 1);

    const [currencies, setCurrencies] = useState([]);
    const [selectedCurrencies, setSelectedCurrencies] = useState([]);
    const [startDate, setStartDate] = useState(lastMonth.toISOString().split('T')[0]);
    const [endDate, setEndDate] = useState(today.toISOString().split('T')[0]);
    const [dataType, setDataType] = useState('currency');
    const [error, setError] = useState('');

    // Fetch available currencies on component mount
    useEffect(() => {
        const fetchCurrencies = async () => {
            try {
                const availableCurrencies = await getAvailableCurrencies();
                const formattedCurrencies = availableCurrencies.map(curr => ({
                    value: curr.value,
                    label: `${curr.label} (${curr.value.toUpperCase()})`
                }));
                setCurrencies(formattedCurrencies);
                
                // Set EUR as default selected currency
                const eurCurrency = formattedCurrencies.find(c => c.value === 'eur');
                if (eurCurrency) {
                    setSelectedCurrencies([eurCurrency]);
                }
            } catch (err) {
                setError('Failed to load available currencies');
                console.error('Error fetching currencies:', err);
            }
        };
        fetchCurrencies();
    }, []);

    const handleSubmit = (e) => {
        e.preventDefault();
        setError('');

        if (!startDate || !endDate) {
            setError('Please select both start and end dates');
            return;
        }

        if (dataType === 'currency' && selectedCurrencies.length === 0) {
            setError('Please select at least one currency');
            return;
        }

        const selectedCurrencyValues = selectedCurrencies.map(curr => curr.value.toUpperCase());
        onFetchData(dataType, startDate, endDate, selectedCurrencyValues);
    };

    return (
        <div className="controls-container">
            {error && <div className="error-message">{error}</div>}
            <form onSubmit={handleSubmit} className="controls-form">
                <div className="form-row">
                    <div className="control-item">
                        <label>Data Type:</label>
                        <select 
                            value={dataType} 
                            onChange={(e) => {
                                setDataType(e.target.value);
                                if (e.target.value === 'gold') {
                                    setSelectedCurrencies([]);
                                }
                            }}
                            className="data-type-select"
                        >
                            <option value="currency">Currency</option>
                            <option value="gold">Gold</option>
                        </select>
                    </div>

                    {dataType === 'currency' && (
                        <div className="control-item currency-select-container">
                            <label>Select Currencies:</label>
                            <Select
                                isMulti
                                value={selectedCurrencies}
                                onChange={setSelectedCurrencies}
                                options={currencies}
                                className="currency-select"
                                classNamePrefix="select"
                                placeholder="Select currencies..."
                                isDisabled={isFetching}
                            />
                        </div>
                    )}

                    <div className="control-item">
                        <label>Start Date:</label>
                        <input
                            type="date"
                            value={startDate}
                            onChange={(e) => setStartDate(e.target.value)}
                            disabled={isFetching}
                        />
                    </div>

                    <div className="control-item">
                        <label>End Date:</label>
                        <input
                            type="date"
                            value={endDate}
                            onChange={(e) => setEndDate(e.target.value)}
                            disabled={isFetching}
                        />
                    </div>

                    <div className="control-item">
                        <button type="submit" className="submit-button" disabled={isFetching}>
                            {isFetching ? 'Loading...' : 'Fetch Data'}
                        </button>
                    </div>
                </div>
            </form>
        </div>
    );
}

export default Controls;