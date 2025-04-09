import React, { useState, useCallback, useEffect, useContext } from 'react';
import Controls from './components/Controls';
import ChartDisplay from './components/ChartDisplay';
import NotificationForm from './components/NotificationForm';
import Login from './components/Login';
import { AuthContext } from './context/AuthContext';
import { getHistoricalData, exportData } from './services/api';
import './App.css';
import SoapClientDemo from './components/SoapClientDemo';

function App() {
    const [chartData, setChartData] = useState(null);
    const [currentDataType, setCurrentDataType] = useState('currency');
    const [isLoading, setIsLoading] = useState(false);
    const [isExporting, setIsExporting] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState(''); 
    const [lastFetchParams, setLastFetchParams] = useState(null);
    const [file, setFile] = useState(null); // State for the imported file
    const [importedData, setImportedData] = useState(null); // State for imported data
    const [importedDataLabel, setImportedDataLabel] = useState('Imported Data');
    const [compareWithNBP, setCompareWithNBP] = useState(false);
    const [fileType, setFileType] = useState('xml'); // State for file type (default to XML)
    const { isAuthenticated, isLoading: isAuthLoading, logout } = useContext(AuthContext);

    useEffect(() => {
        if (isLoading || isAuthLoading) {
            setError('');
        }
    }, [isLoading, isAuthLoading]);

    const handleFetchData = useCallback(async (dataType, startDate, endDate, currencies) => {
        setIsLoading(true);
        setChartData(null);
        setCurrentDataType(dataType);
        setLastFetchParams({ dataType, startDate, endDate, currencies });
        try {
            const data = await getHistoricalData(dataType, startDate, endDate, currencies);
            setChartData(data);
        } catch (err) {
            const errorMsg = err?.detail || err?.message || 'An error occurred while fetching data.';
            if (err?.detail !== "Could not validate credentials" && err?.detail !== "Inactive user") {
                setError(errorMsg);
            }
            console.error("Fetch data error:", err);
            setChartData([]);
        } finally {
            setIsLoading(false);
        }
    }, []);

    const handleExport = async (format) => {
        if (!lastFetchParams || !chartData || chartData.length === 0) {
            setError("Please generate a chart with data first before exporting.");
            return;
        }
        setError('');
        setIsExporting(true);
        const { dataType, startDate, endDate, currencies } = lastFetchParams;
        try {
            await exportData(format, dataType, startDate, endDate, currencies);
        } catch (err) {
            const errorMessage = err?.detail || err?.message || `Failed to export data as ${format}.`;
            if (err?.detail !== "Could not validate credentials" && err?.detail !== "Inactive user") {
                setError(errorMessage);
            }
            console.error("Export error:", err);
        } finally {
            setIsExporting(false);
        }
    };

    const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api/v1';

    const handleImport = async (event) => {
        event.preventDefault();
        if (!file) {
            setError("Please select a file to import.");
            return;
        }

        // Get the currently selected currency
        const selectedCurrency = lastFetchParams?.currencies?.[0]?.toUpperCase();

        setError('');
        setSuccess(''); // Clear previous success message
        setImportedData(null); // Clear previous imported data
        setIsLoading(true); // Set loading state

        try {
            const formData = new FormData();
            formData.append('file', file);
    
            const response = await fetch(`${API_BASE_URL}/import/${fileType}`, {
                method: 'POST',
                body: formData,
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('authToken')}`,
                },
                credentials: 'include',
            });
    
            const result = await response.json();
            if (!result.data || !Array.isArray(result.data)) {
                throw new Error('Invalid data format received from server');
            }

            // Check if imported currency is different from selected
            const importedCurrency = result.data[0]?.Currency?.toUpperCase();
            if (selectedCurrency && importedCurrency === selectedCurrency) {
                setError('Please import data for a different currency than the one selected in the main controls');
                return;
            }
    
            // Ensure currency information is preserved from the imported data
            setImportedData(result.data.map(item => ({
                ...item,
                Currency: item.Currency || 'Unknown' // Fallback if currency is not specified
            })));
            
            // Set the import label to include the currency for clarity
            setImportedDataLabel(`Imported ${result.data[0]?.Currency || 'Data'}`);
            setSuccess('File imported successfully');
            setFile(null);
        } catch (err) {
            console.error("Import error:", err);
            setError(err.message || 'Failed to import file');
        } finally {
            setIsLoading(false);
        }
    };

    // Visualize imported data
    const handleVisualizeImported = async () => {
        if (!importedData || importedData.length === 0) {
            setError('No imported data to visualize');
            return;
        }
    
        try {
            // Transform imported data for chart visualization with custom label
            const importedSeries = importedData.map(item => ({
                Date: item.Date,
                Rate: parseFloat(item.Value || item.Rate),
                Currency: importedDataLabel // Use custom label for imported data
            }));
    
            let combinedData = [...importedSeries];
    
            if (compareWithNBP) {
                // Get date range from imported data
                const dates = importedData.map(item => new Date(item.Date));
                const startDate = new Date(Math.min(...dates)).toISOString().split('T')[0];
                const endDate = new Date(Math.max(...dates)).toISOString().split('T')[0];
                
                // Get selected currency from the main controls
                const selectedCurrency = lastFetchParams?.currencies?.[0];
                
                if (!selectedCurrency) {
                    setError('Please select a currency from the main controls first');
                    return;
                }
    
                try {
                    // Fetch NBP data for the selected currency
                    const nbpData = await getHistoricalData('currency', startDate, endDate, [selectedCurrency]);
                    
                    if (nbpData && nbpData.length > 0) {
                        // Transform NBP data and add it to the combined dataset
                        combinedData = [
                            ...importedSeries,  // Imported data
                            ...nbpData          // NBP data
                        ];
                    }
                } catch (nbpError) {
                    console.error('Failed to fetch NBP data:', nbpError);
                    setError('Could not fetch NBP data for comparison.');
                    return;
                }
            }
    
            // Update chart state
            setCurrentDataType('currency');
            setChartData(combinedData);
            setSuccess('Data visualized successfully');
    
        } catch (error) {
            setError('Failed to visualize data: ' + error.message);
            console.error('Visualization error:', error);
        }
    };

    <div className="import-section">
    <h2>Import Data</h2>
    <form onSubmit={handleImport} className="import-form">
        <div className="file-input-group">
            <select 
                value={fileType} 
                onChange={(e) => setFileType(e.target.value)}
                className="file-type-select"
            >
                <option value="xml">XML</option>
                <option value="json">JSON</option>
                <option value="yaml">YAML</option>
            </select>
            <input 
                type="file" 
                accept={`.${fileType}`}
                onChange={(e) => setFile(e.target.files[0])} 
            />
        </div>
        <button type="submit" disabled={!file || isLoading}>
            {isLoading ? 'Importing...' : `Import ${fileType.toUpperCase()}`}
        </button>
    </form>

        {importedData && (
            <div className="imported-data-controls">
                <h3>Configure Visualization</h3>
                <div className="imported-data-preview">
                    <p>Successfully imported {importedData.length} records.</p>
                    <p>Date range: {importedData[0]?.Date} - {importedData[importedData.length-1]?.Date}</p>
                </div>
                
                <div className="control-item">
                    <label htmlFor="data-label">Series Label:</label>
                    <input
                        id="data-label"
                        type="text"
                        value={importedDataLabel}
                        onChange={(e) => setImportedDataLabel(e.target.value)}
                        placeholder="Custom label for imported data"
                    />
                </div>
                
                <div className="control-item checkbox-item">
                    <label>
                        <input
                            type="checkbox"
                            checked={compareWithNBP}
                            onChange={(e) => setCompareWithNBP(e.target.checked)}
                        />
                        Compare with NBP Data
                    </label>
                    {compareWithNBP && (
                        <small className="helper-text">
                            This will overlay NBP official rates for comparison
                        </small>
                    )}
                </div>

                <button 
                    onClick={handleVisualizeImported}
                    className="visualize-button"
                >
                    Visualize Data
                </button>
            </div>
        )}
    </div>

    const disableExport = !chartData || chartData.length === 0 || isLoading || isExporting;
    
    if (isAuthLoading) {
        return <div className="App"><p className="loading-message">Checking authentication...</p></div>;
    }

    return (
        <div className="App">
            <header className="App-header">
                <h1>NBP Currency & Gold Analysis Platform</h1>
                {isAuthenticated && (
                    <button onClick={logout} className="logout-button">
                        Logout
                    </button>
                )}
            </header>
    
            {error && <div className="message error-message">{error}</div>}
            {success && <div className="message success-message">{success}</div>}
    
            {!isAuthenticated ? (
                <Login />
            ) : (
                <>
                    <Controls onFetchData={handleFetchData} isFetching={isLoading} />

                    <div className="import-section">
                        <h2>Import Data</h2>
                        <form onSubmit={handleImport} className="import-form">
                            <div className="file-input-group">
                                <select 
                                    value={fileType} 
                                    onChange={(e) => setFileType(e.target.value)}
                                    className="file-type-select"
                                >
                                    <option value="xml">XML</option>
                                    <option value="json">JSON</option>
                                    <option value="yaml">YAML</option>
                                </select>
                                <input 
                                    type="file" 
                                    accept={`.${fileType}`}
                                    onChange={(e) => setFile(e.target.files[0])} 
                                />
                            </div>
                            <button type="submit" disabled={!file || isLoading}>
                                {isLoading ? 'Importing...' : `Import ${fileType.toUpperCase()}`}
                            </button>
                        </form>

                        {importedData && (
                            <div className="imported-data-controls">
                                <h3>Configure Visualization</h3>
                                <div className="imported-data-preview">
                                    <p>Successfully imported {importedData.length} records.</p>
                                    <p>Date range: {importedData[0]?.Date} - {importedData[importedData.length-1]?.Date}</p>
                                </div>
                                
                                <div className="control-item">
                                    <label htmlFor="data-label">Series Label:</label>
                                    <input
                                        id="data-label"
                                        type="text"
                                        value={importedDataLabel}
                                        onChange={(e) => setImportedDataLabel(e.target.value)}
                                        placeholder="Custom label for imported data"
                                    />
                                </div>
                                
                                <div className="control-item checkbox-item">
                                    <label>
                                        <input
                                            type="checkbox"
                                            checked={compareWithNBP}
                                            onChange={(e) => setCompareWithNBP(e.target.checked)}
                                        />
                                        Compare with NBP Data
                                    </label>
                                    {compareWithNBP && (
                                        <small className="helper-text">
                                            This will overlay NBP official rates for comparison
                                        </small>
                                    )}
                                </div>

                                <button 
                                    onClick={handleVisualizeImported}
                                    className="visualize-button"
                                >
                                    Visualize Data
                                </button>
                            </div>
                        )}
                    </div>

                    <ChartDisplay
                        chartData={chartData}
                        dataType={currentDataType}
                        isLoading={isLoading}
                    />

                    <div className="export-buttons">
                        <button onClick={() => handleExport('json')} disabled={disableExport}>
                            {isExporting ? 'Exporting...' : 'Export to JSON'}
                        </button>
                        <button onClick={() => handleExport('xml')} disabled={disableExport}>
                            {isExporting ? 'Exporting...' : 'Export to XML'}
                        </button>
                        <button onClick={() => handleExport('yaml')} disabled={disableExport}>
                            {isExporting ? 'Exporting...' : 'Export to YAML'}
                        </button>
                    </div>

                    <SoapClientDemo />
                        
                    <NotificationForm />
                </>
            )}
        </div>
    );
}

export default App;