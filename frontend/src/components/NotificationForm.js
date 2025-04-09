import React, { useState, useEffect, useContext } from 'react';
import { getAvailableCurrencies, addNotification } from '../services/api';
import { AuthContext } from '../context/AuthContext';
import '../App.css';

const NotificationForm = () => {
    const { isAuthenticated } = useContext(AuthContext);
    const [email, setEmail] = useState('');
    const [currency, setCurrency] = useState('');
    const [threshold, setThreshold] = useState('');
    const [direction, setDirection] = useState('above');
    const [availableCurrencies, setAvailableCurrencies] = useState([]);
    const [isLoadingCurrencies, setIsLoadingCurrencies] = useState(true);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    useEffect(() => {
        // Only fetch currencies if user is authenticated
        if (isAuthenticated) {
            const fetchCurrencies = async () => {
                setIsLoadingCurrencies(true);
                try {
                    const currencies = await getAvailableCurrencies();
                    setAvailableCurrencies(currencies);
                    if (currencies.length > 0) {
                        setCurrency(currencies[0].value);
                    }
                } catch (err) {
                    setError('Could not load currencies');
                } finally {
                    setIsLoadingCurrencies(false);
                }
            };
            fetchCurrencies();
        }
    }, [isAuthenticated]);

    const handleSubmit = async (event) => {
        event.preventDefault();
        if (!isAuthenticated) {
            setError('Please log in to set notifications');
            return;
        }

        setError('');
        setSuccess('');
        setIsSubmitting(true);

        try {
            const notificationData = {
                email,
                currency: currency.toUpperCase(),
                threshold: parseFloat(threshold),
                direction
            };

            await addNotification(notificationData);
            setSuccess(`Notification set successfully for ${currency} ${direction} ${threshold} to ${email}`);
            
            // Optional: Clear form
            setEmail('');
            setThreshold('');
        } catch (err) {
            const errorMsg = err?.detail || err?.message || 'Failed to set notification';
            setError(errorMsg);
            console.error("Notification submission error:", err);
        } finally {
            setIsSubmitting(false);
        }
    };

    if (!isAuthenticated) {
        return null; // Hide form completely when not authenticated
    }

    return (
        <div className="notification-section">
            <h2>Set Currency Rate Alert</h2>
            {error && <div className="error-message">{error}</div>}
            {success && <div className="success-message">{success}</div>}
            
            <form onSubmit={handleSubmit} className="notification-form">
                <div className="control-item">
                    <label htmlFor="notif-currency">Currency:</label>
                    <select
                        id="notif-currency"
                        value={currency}
                        onChange={(e) => setCurrency(e.target.value)}
                        required
                        disabled={isLoadingCurrencies || availableCurrencies.length === 0}
                    >
                        {isLoadingCurrencies ? (
                            <option>Loading...</option>
                        ) : availableCurrencies.length === 0 ? (
                            <option>No currencies</option>
                        ) : (
                            availableCurrencies.map(c => (
                                <option key={c.value} value={c.value}>
                                    {c.label}
                                </option>
                            ))
                        )}
                    </select>
                </div>
                <div className="control-item">
                    <label htmlFor="notif-threshold">Threshold (PLN):</label>
                    <input
                        id="notif-threshold"
                        type="number"
                        step="0.0001"
                        min="0.0001"
                        value={threshold}
                        onChange={(e) => setThreshold(e.target.value)}
                        placeholder="e.g., 4.50"
                        required
                        disabled={isLoadingCurrencies || isSubmitting}
                    />
                </div>
                <div className="control-item">
                    <label htmlFor="notif-direction">Alert When Rate Is:</label>
                    <select
                        id="notif-direction"
                        value={direction}
                        onChange={(e) => setDirection(e.target.value)}
                        required
                        disabled={isLoadingCurrencies || isSubmitting}
                    >
                        <option value="above">Above Threshold</option>
                        <option value="below">Below Threshold</option>
                    </select>
                </div>
                <div className="control-item">
                    <label htmlFor="notif-email">Email Address:</label>
                    <input
                        id="notif-email"
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="your.email@example.com"
                        required
                        disabled={isLoadingCurrencies || isSubmitting}
                    />
                </div>
                <button type="submit" className="set-alert-button" disabled={isLoadingCurrencies || isSubmitting}>
                    {isSubmitting ? 'Setting...' : 'Set Alert'}
                </button>
            </form>
        </div>
    );
};

export default NotificationForm;