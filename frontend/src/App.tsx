import React, { useState, useEffect } from 'react';
import cod3xLogo from './assets/cod3x.jpg';
import './App.css';
import axios from 'axios';
import ComposedChartComponent from './ComboChart1.tsx';
import LoadingAnimation from './LoadingAnimation';

const api_url = 'https://superfest-api-dot-internal-website-427620.uc.r.appspot.com';

interface ChartData {
  [key: string]: {
    date: string;
    token_usd_amount: number;
    raw_change_in_usd: number;
    incentives_per_day_usd: number;
    weth_change_in_price_percentage: number;
  }[];
}

function App() {
  const [chartData, setChartData] = useState<ChartData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <div className="App">
      <header className="App-header">
        {/* <img src={cod3xLogo} className="App-logo" alt="logo" /> */}
        <h1>Superfest Analytics Dashboard</h1>
      </header>
      <main className="main-content">
        <div className="chart-container">
          {isLoading ? (
            <LoadingAnimation />
          ) : error ? (
            <div className="error-message">{error}</div>
          ) : chartData ? (
            <ComposedChartComponent data={chartData} />
          ) : (
            <div>No data available</div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;