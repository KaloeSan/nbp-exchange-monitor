import axios from 'axios';
import { saveAs } from 'file-saver';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api/v1';

// Create axios instance
const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    },
});

// --- Axios Request Interceptor ---
// Adds a JWT token to the Authorization header for each request
apiClient.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('authToken'); // Read token
        if (token) {
            // Add header if token exists
            config.headers['Authorization'] = `Bearer ${token}`;
        }
        return config; // Return modified configuration
    },
    (error) => {
        // Handle request configuration error
        return Promise.reject(error);
    }
);

// --- Axios Response Interceptor ---
apiClient.interceptors.response.use(
    (response) => {
        // Any response with status 2xx will go through here
        return response;
    },
    (error) => {
        // Any response with a status other than 2xx will go through here
        console.error("Axios response error:", error.response?.status, error.response?.data || error.message);
        if (error.response && error.response.status === 401) {
            // If the server returns 401 (e.g. the token has expired or is invalid)
            console.warn("Received 401 Unauthorized response. Logging out.");
            localStorage.removeItem('authToken'); // Clear invalid token
        }
        // Pass the error on so that components can handle it
        return Promise.reject(error.response?.data || error);
    }
);

// --- Existing API Functions (apiClient with interceptor) ---

export const getAvailableCurrencies = async () => {
    try {
        const response = await apiClient.get('/currencies');
        return response.data;
    } catch (error) {
        console.error("Error fetching available currencies:", error);
        throw error;
    }
};

export const getHistoricalData = async (dataType, startDate, endDate, currencies = []) => {
     try {
        const params = { start_date: startDate, end_date: endDate };
        if (dataType === 'currency' && currencies.length > 0) {
            params.currencies = currencies.join(',');
        } else if (dataType === 'currency') { return []; } // Return empty list

        const response = await apiClient.get(`/data/${dataType}`, { params });
        return response.data;
    } catch (error) {
         console.error(`Error fetching ${dataType} data:`, error);
        throw error;
    }
};

export const addNotification = async (notificationData) => {
    try {
        const response = await apiClient.post('/notifications', notificationData);
        return response.data;
    } catch (error) {
        console.error("Error adding notification:", error.response?.data || error);
        throw error.response?.data || error;
    }
};

export const exportData = async (format, dataType, startDate, endDate, currencies = []) => {
    try {
         const params = { data_type: dataType, start_date: startDate, end_date: endDate };
        if (dataType === 'currency' && currencies.length > 0) {
            params.currencies = currencies.join(',');
        }
        // The interceptor will add the token if the export endpoint requires it in the future
        const response = await apiClient.get(`/export/${format}`, {
            params: params,
            responseType: 'blob',
        });

        const contentDisposition = response.headers['content-disposition'];
        let filename = `${dataType}_data.${format}`;
        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
            if (filenameMatch && filenameMatch.length > 1) filename = filenameMatch[1];
        }
        saveAs(new Blob([response.data]), filename);
    } catch (error) {
         console.error(`Error exporting data as ${format}:`, error);
        // Trying to read the JSON error from the Blob if possible
         if (error instanceof Blob && error.type.includes('json')) {
             try {
                 const errorText = await error.text();
                 const errorJson = JSON.parse(errorText);
                 console.error("Export error details:", errorJson);
                 throw errorJson;
             } catch (parseError) {
                  console.error("Could not parse error blob:", parseError);
                  throw error; // Throw original error blob
             }
         } else {
            throw error; // Throw a caught error (e.g. from an interceptor)
         }
    }
};