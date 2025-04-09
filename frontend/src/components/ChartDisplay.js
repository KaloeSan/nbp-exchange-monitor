import React from 'react';
import { Line } from 'react-chartjs-2';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    TimeScale // Import TimeScale for date axes
} from 'chart.js';
import 'chartjs-adapter-date-fns'; // Adapter for date handling
import '../App.css'; // Use shared styles

// Register necessary Chart.js components
ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    TimeScale // Register TimeScale
);

// Predefined color palette for lines
const lineColors = [
    '#3498db', '#e74c3c', '#2ecc71', '#f1c40f', '#9b59b6', '#1abc9c', '#e67e22', '#34495e'
];

const ChartDisplay = ({ chartData, dataType, isLoading, error }) => {

    // Use the dedicated container with styles from App.css
    const renderContent = () => {
        if (isLoading) {
            return <p className="loading-message chart-placeholder">Loading chart data...</p>;
        }

        if (error) {
            // Use error-message style but keep placeholder text style if desired
            return <p className="error-message chart-placeholder">Error loading data: {error}</p>;
        }

        // Ensure chartData is an array before checking length
        if (!chartData || !Array.isArray(chartData) || chartData.length === 0) {
            return <p className="chart-placeholder">No data available for the selected criteria. Adjust dates or currencies.</p>;
        }

        // --- Prepare data for Chart.js (Logic remains the same) ---
        let datasets = [];
        let chartTitle = '';
        let yAxisLabel = '';

        if (dataType === 'currency') {
            chartTitle = 'Currency Exchange Rates vs PLN';
            yAxisLabel = 'Exchange Rate (PLN)';
            const dataByCurrency = chartData.reduce((acc, item) => {
                const currency = item.Currency;
                if (!acc[currency]) {
                    acc[currency] = [];
                }
                // Ensure Date is valid before creating Date object
                const dateObj = new Date(item.Date);
                if (!isNaN(dateObj)) {
                    acc[currency].push({
                        x: dateObj,
                        y: parseFloat(item.Rate)
                    });
                }
                return acc;
            }, {});
    
            // Sort data for each currency
            Object.values(dataByCurrency).forEach(currencyData => 
                currencyData.sort((a, b) => a.x - b.x)
            );
    
            // Create datasets with different colors for each currency
            datasets = Object.keys(dataByCurrency).map((currency, index) => ({
                label: currency,
                data: dataByCurrency[currency],
                borderColor: lineColors[index % lineColors.length],
                backgroundColor: lineColors[index % lineColors.length] + '33',
                fill: false,
                tension: 0.1,
                pointRadius: 2,
                pointHoverRadius: 5,
            }));
        } else if (dataType === 'gold') {
            chartTitle = 'Gold Price History (PLN per gram)';
            yAxisLabel = 'Price (PLN/g)';
            const sortedGoldData = [...chartData].sort((a, b) => new Date(a.Date) - new Date(b.Date));

            datasets = [{
                label: 'Gold Price (PLN/g)',
                 data: sortedGoldData.map(item => {
                      const dateObj = item.Date ? new Date(item.Date) : null;
                      return (dateObj && !isNaN(dateObj)) ? { x: dateObj, y: item.Price } : null;
                 }).filter(item => item !== null), // Filter out invalid dates
                borderColor: '#f1c40f',
                backgroundColor: '#f1c40f33',
                fill: false,
                tension: 0.1,
                pointRadius: 2,
                pointHoverRadius: 5,
            }];
        }

        // --- Chart.js Options (Logic remains the same) ---
        const options = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    display: dataType === 'currency' && datasets.length > 1,
                },
                title: { display: true, text: chartTitle, font: { size: 18 } },
                tooltip: {
                    mode: 'index', intersect: false,
                    callbacks: {
                        title: (tooltipItems) => new Date(tooltipItems[0].parsed.x).toLocaleDateString('en-CA'),
                        label: (context) => `${context.dataset.label || ''}: ${context.parsed.y !== null ? context.parsed.y.toFixed(4) : 'N/A'}`,
                    }
                },
            },
            scales: {
                x: {
                    type: 'time',
                    time: { unit: 'day', tooltipFormat: 'yyyy-MM-dd', displayFormats: { day: 'yyyy-MM-dd' } },
                    title: { display: true, text: 'Date' },
                    grid: { display: false }
                },
                y: {
                    title: { display: true, text: yAxisLabel },
                    ticks: { callback: (value) => value.toFixed(2) }
                }
            },
            interaction: { mode: 'nearest', axis: 'x', intersect: false }
        };

        const chartJsData = { datasets };

        // Render the Line chart if data is valid
        return <Line options={options} data={chartJsData} />;
    };

    return (
        // Container now mainly styled by App.css
        <div className="chart-container">
            {renderContent()}
        </div>
    );
};

export default ChartDisplay;