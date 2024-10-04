import React, { useState, useEffect, useMemo } from 'react';
import cod3xLogo from './assets/cod3x.jpg';
import './App.css';
import axios from 'axios';
import ComposedChartComponent from './ComboChart1';
import LoadingAnimation from './LoadingAnimation';
import AggregateChart from './AggregateChart';

const api_url = 'http://localhost:8000';

interface ComposedChartData {
  [key: string]: {
    date: string;
    token_usd_amount: number;
    raw_change_in_usd: number;
    incentives_per_day_usd: number;
    weth_change_in_price_percentage: number;
    percentage_change_in_usd: number;
  }[];
}

interface ChartData {
  date: string;
  token_usd_amount: number;
  raw_change_in_usd: number;
  cumulative_incentives_usd: number;
  percentage_change_in_usd: number;
  weth_change_in_price_percentage: number;
  tvl_to_incentive_roi_percentage: number;
}

interface AggregateChartData {
  [key: string]: ChartData[];
}

function App() {
  const [composedChartData, setComposedChartData] = useState<ComposedChartData | null>(null);
  const [aggregateChartData, setAggregateChartData] = useState<AggregateChartData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedView, setSelectedView] = useState<string>('Aggregate');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [poolResponse, aggregateResponse] = await Promise.all([
          axios.get<ComposedChartData>(`${api_url}/api/pool_tvl_incentives_and_change_in_weth_price`),
          axios.get<AggregateChartData>(`${api_url}/api/aggregate_data`)
        ]);
        setComposedChartData(poolResponse.data);
        
        // Combine all aggregate data into a single array under a new key
        const combinedAggregateData = Object.values(aggregateResponse.data).flat();
        setAggregateChartData({
          "All Aggregated Data": combinedAggregateData
        });
        
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
    if (!composedChartData) return ['Aggregate'];
    const protocolSet = new Set(['Aggregate', ...Object.keys(composedChartData).map(key => key.split(' ')[0])]);
    return Array.from(protocolSet);
  }, [composedChartData]);

  const filteredComposedChartData = useMemo(() => {
    if (!composedChartData) return null;
    if (selectedView === 'Aggregate') return null;
    return Object.fromEntries(
      Object.entries(composedChartData).filter(([key]) => key.startsWith(selectedView))
    );
  }, [composedChartData, selectedView]);

  return (
    <div className="App">
      <header className="App-header">
        <h1>Superfest Analytics Dashboard</h1>
      </header>
      <main className="main-content">
        <div className="protocol-selector-container">
          <div className="protocol-selector">
            <label htmlFor="protocol-select">Select View: </label>
            <select 
              id="protocol-select"
              value={selectedView}
              onChange={(e) => setSelectedView(e.target.value)}
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
          ) : selectedView === 'Aggregate' && aggregateChartData ? (
            <AggregateChart data={aggregateChartData} />
          ) : filteredComposedChartData ? (
            <ComposedChartComponent data={filteredComposedChartData} />
          ) : (
            <div>No data available</div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;