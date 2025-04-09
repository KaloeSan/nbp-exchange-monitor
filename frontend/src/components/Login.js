import React, { useState, useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import '../App.css';

const Login = () => {
    // State management for form fields and loading state
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const { login } = useContext(AuthContext);

    const handleSubmit = async (event) => {
        event.preventDefault();
        setError('');
        setIsLoading(true);

        // Basic validation
        if (!username || !password) {
            setError('Please enter both username and password.');
            setIsLoading(false);
            return;
        }

        try {
            // Attempt to login
            await login(username, password);
        } catch (err) {
            const errorMsg = err?.detail || err?.message || "Login failed. Please check your credentials.";
            setError(errorMsg);
            console.error("Login error:", err);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="login-section">
            <h2>Login</h2>
            {error && <div className="message error-message">{error}</div>}
            
            <form onSubmit={handleSubmit} className="login-form">
                <div className="control-item">
                    <label htmlFor="login-username">Username:</label>
                    <input
                        id="login-username"
                        type="text"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        placeholder="Enter username"
                        required
                        disabled={isLoading}
                    />
                </div>

                <div className="control-item">
                    <label htmlFor="login-password">Password:</label>
                    <input
                        id="login-password"
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="Enter password"
                        required
                        disabled={isLoading}
                    />
                </div>

                <button type="submit" className="submit-button" disabled={isLoading}>
                    {isLoading ? 'Logging in...' : 'Login'}
                </button>
            </form>
            
            <p className="login-hint">
                (Try: testuser / testpassword)
            </p>
        </div>
    );
};

export default Login;