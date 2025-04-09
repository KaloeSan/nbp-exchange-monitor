import React, { createContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';

// API URL definition - read from environment variable or use default
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api/v1';

// Create context
export const AuthContext = createContext({
    token: null,
    isAuthenticated: false,
    isLoading: true, // Start with loading state true
    login: async () => {},
    logout: () => {},
});

// Create a context provider
export const AuthProvider = ({ children }) => {
    const [token, setToken] = useState(null);
    const [isLoading, setIsLoading] = useState(true); // To check initial token state

    // Check token in localStorage on first load
    useEffect(() => {
        const storedToken = localStorage.getItem('authToken');
        if (storedToken) {
            setToken(storedToken);
            console.log("Token found in localStorage on initial load.");
        } else {
            console.log("No token found in localStorage on initial load.");
        }
        setIsLoading(false); // Finished initial loading check
    }, []);

    const login = useCallback(async (username, password) => {
        try {
            // Backend expects data in form-data for OAuth2PasswordRequestForm
            const formData = new FormData();
            formData.append('username', username);
            formData.append('password', password);

            const response = await axios.post(`${API_BASE_URL}/token`, formData, {
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            });

            if (response.data.access_token) {
                const newToken = response.data.access_token;
                setToken(newToken);
                localStorage.setItem('authToken', newToken); // Save token
                console.log("Login successful, token stored.");
                return true; // Success
            } else {
                 throw new Error("Login failed: No access token received.");
            }
        } catch (error) {
            console.error("Login API call failed:", error.response?.data || error.message);
            // Forward the error so that the Login component can display it
            throw error.response?.data || error;
        }
    }, []);

    const logout = useCallback(() => {
        setToken(null);
        localStorage.removeItem('authToken'); // Remove token
        console.log("Logout successful, token removed.");
    }, []);

    const contextValue = {
        token,
        isAuthenticated: !!token, // Simple check - if there is a token, the user is logged in
        isLoading, // Pass loading state
        login,
        logout,
    };

    return (
        <AuthContext.Provider value={contextValue}>
            {children}
        </AuthContext.Provider>
    );
};