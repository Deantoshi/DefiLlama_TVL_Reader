import React, { useState, useMemo } from 'react';
import { ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface ChartData {
  date: string;
  token_usd_amount: number;
  raw_change_in_usd: number;
  incentives_per_day_usd: number;
  weth_change_in_price_percentage: number;
}

interface ChartProps {
  data: {
    [key: string]: ChartData[];
  };
}

const calculateYAxisDomain = (data: ChartData[]) => {
  const percentages = data.map(item => item.weth_change_in_price_percentage);
  const minValue = Math.min(...percentages);
  const maxValue = Math.max(...percentages);
  return [Math.floor(minValue * 1.1), Math.ceil(maxValue * 1.1)];
};

const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value);
};

const formatXAxis = (tickItem: string) => {
  const date = new Date(tickItem);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
};

const formatToMillions = (value: number) => {
  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(1)}M`;
  } else if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}K`;
  }
  return value.toFixed(0);
};

const ComposedChartComponent: React.FC<ChartProps> = ({ data }) => {
  const [selectedKey, setSelectedKey] = useState<string>(Object.keys(data)[0]);

  const processedData = useMemo(() => {
    const validData = data[selectedKey].filter(item => !isNaN(new Date(item.date).getTime()));
    return validData.map((item, index) => ({
      ...item,
      weth_change_in_price_percentage: index === 0 ? 0 : item.weth_change_in_price_percentage * 100
    }));
  }, [selectedKey, data]);

  const yAxisDomain = useMemo(() => calculateYAxisDomain(processedData), [processedData]);

  const handleSelectChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedKey(event.target.value);
  };

  return (
    <div className="chart-content">
      <div className="chart-select-container">
        <select 
          className="chart-select"
          onChange={handleSelectChange} 
          value={selectedKey}
        >
          {Object.keys(data).map((key) => (
            <option key={key} value={key}>{key}</option>
          ))}
        </select>
      </div>
      <div className="chart-wrapper">
        <ResponsiveContainer width="100%" height={500}>
          <ComposedChart data={processedData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="date" 
              tickFormatter={formatXAxis}
              angle={-45}
              textAnchor="end"
              height={70}
              interval="preserveStartEnd"
            />
            <YAxis 
              yAxisId="left" 
              tickFormatter={formatToMillions}
              label={{ value: 'USD (Millions)', angle: -90, position: 'insideLeft' }}
            />
            <YAxis 
              yAxisId="right" 
              orientation="right" 
              domain={yAxisDomain} 
              tickFormatter={(value) => `${value.toFixed(2)}%`}
              label={{ value: 'WETH Price Change (%)', angle: -90, position: 'insideRight' }}
            />
            <Tooltip
              formatter={(value, name, props) => {
                switch (name) {
                  case "WETH Price Change %":
                    return [`${Number(value).toFixed(2)}%`, "WETH Price Change"];
                  case "Pool TVL":
                  case "Pool Change in USD":
                  case "Incentives per Day USD":
                    return [formatCurrency(Number(value)), name];
                  default:
                    return [value, name];
                }
              }}
              labelFormatter={(label) => `Date: ${new Date(label).toLocaleDateString()}`}
            />
            <Legend />
            <Bar yAxisId="left" dataKey="token_usd_amount" stackId="a" fill="#8884d8" name="Pool TVL" />
            <Bar yAxisId="left" dataKey="raw_change_in_usd" stackId="a" fill="#82ca9d" name="Pool Change in USD" />
            <Bar yAxisId="left" dataKey="incentives_per_day_usd" stackId="a" fill="#ffc658" name="Incentives per Day USD" />
            <Line 
              yAxisId="right" 
              type="monotone" 
              dataKey="weth_change_in_price_percentage" 
              stroke="#ff7300" 
              name="WETH Price Change %" 
              dot={false}
              strokeWidth={3}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default ComposedChartComponent;