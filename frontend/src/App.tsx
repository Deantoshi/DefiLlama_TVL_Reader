import React, { useState, useEffect, useMemo } from 'react';
import cod3xLogo from './assets/cod3x.jpg';
import './App.css';
import axios from 'axios';
import ComposedChartComponent from './ComboChart1.tsx';
import LoadingAnimation from './LoadingAnimation';
import AggregateChartComponent from './AggregateChart.tsx';

const api_url = 'http://localhost:8000';

interface ChartData {
  [key: string]: {
    date: string;
    token_usd_amount: number;
    raw_change_in_usd: number;
    incentives_per_day_usd: number;
    weth_change_in_price_percentage: number;
    percentage_change_in_usd: number;
  }[];
}

function App() {
  const [chartData, setChartData] = useState<ChartData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedProtocol, setSelectedProtocol] = useState<string>('Aave-v3');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await axios.get(`${api_url}/api/pool_tvl_incentives_and_change_in_weth_price`);
        setChartData(response.data);
        setIsLoading(false);
      } catch (err) {
        console.error('Error fetching chart data:', err);
        setError('Failed to fetch chart data. Please try again later.');
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  const protocols = useMemo(() => {
    if (!chartData) return ['Aave-v3'];
    const protocolSet = new Set(['Aave-v3', ...Object.keys(chartData).map(key => key.split(' ')[0])]);
    return Array.from(protocolSet);
  }, [chartData]);

  const filteredChartData = useMemo(() => {
    if (!chartData) return null;
    return Object.fromEntries(
      Object.entries(chartData).filter(([key]) => key.startsWith(selectedProtocol))
    );
  }, [chartData, selectedProtocol]);

  return (
    <div className="App">
      <header className="App-header">
        <h1>Superfest Analytics Dashboard</h1>
      </header>
      <main className="main-content">
        <div className="protocol-selector-container">
          <div className="protocol-selector">
            <label htmlFor="protocol-select">Select an App: </label>
            <select 
              id="protocol-select"
              value={selectedProtocol}
              onChange={(e) => setSelectedProtocol(e.target.value)}
            >
              {protocols.map(protocol => (
                <option key={protocol} value={protocol}>{protocol}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="chart-container">
          {isLoading ? (
            <LoadingAnimation />
          ) : error ? (
            <div className="error-message">{error}</div>
          ) : filteredChartData ? (
            <ComposedChartComponent data={filteredChartData} />
          ) : (
            <div>No data available</div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;