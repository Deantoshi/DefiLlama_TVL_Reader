import React, { useMemo, useState, useCallback } from 'react';
import { ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface ChartData {
  date: string;
  token_usd_amount: number;
  raw_change_in_usd: number;
  incentives_per_day_usd: number;
  weth_change_in_price_percentage: number;
  percentage_change_in_usd: number;
  tvl_to_incentive_roi_percentage: number;
}

interface ChartProps {
  data: {
    [key: string]: ChartData[];
  };
}

type VisibleLines = {
  [K in VisibleLineKeys]: boolean;
};

type ChartElementType = {
  dataKey: VisibleLineKeys;
  Component: typeof Bar | typeof Line;
  props: React.ComponentProps<typeof Bar> | React.ComponentProps<typeof Line>;
};

type VisibleLineKeys = Exclude<keyof ChartData, 'date'>;

const formatXAxis = (tickItem: string) => {
  const date = new Date(tickItem);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
};

const formatToMillions = (value: number) => {
  const absValue = Math.abs(value);
  let formattedValue: string;
  if (absValue >= 1000000) {
    formattedValue = `${(absValue / 1000000).toFixed(0)}M`;
  } else if (absValue >= 1000) {
    formattedValue = `${(absValue / 1000).toFixed(0)}K`;
  } else {
    formattedValue = absValue.toFixed(1);
  }
  return value < 0 ? `-${formattedValue}` : formattedValue;
};

const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value);
};

const CustomLegend: React.FC<{
  payload: any[];
  onClick: (dataKey: string) => void;
  visibleLines: VisibleLines;
}> = ({ payload, onClick, visibleLines }) => {
  return (
    <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexWrap: 'wrap', justifyContent: 'center' }}>
      {payload.map((entry, index) => (
        <li
          key={`item-${index}`}
          style={{
            marginRight: 20,
            cursor: 'pointer',
            opacity: visibleLines[entry.dataKey as keyof VisibleLines] ? 1 : 0.5,
            textDecoration: visibleLines[entry.dataKey as keyof VisibleLines] ? 'none' : 'line-through',
          }}
          onClick={() => onClick(entry.dataKey)}
        >
          <span style={{ color: entry.color, marginRight: 5 }}>■</span>
          {entry.value}
        </li>
      ))}
    </ul>
  );
};

const SingleChart: React.FC<{ data: ChartData[]; title: string }> = ({ data, title }) => {
  const [visibleLines, setVisibleLines] = useState<VisibleLines>({
    token_usd_amount: true,
    raw_change_in_usd: true,
    incentives_per_day_usd: true,
    weth_change_in_price_percentage: true,
    percentage_change_in_usd: true,
    tvl_to_incentive_roi_percentage: true
  });

  const processedData = useMemo(() => {
    const validData = data.filter(item => !isNaN(new Date(item.date).getTime()));
    return validData.map((item, index) => ({
      ...item,
      weth_change_in_price_percentage: index === 0 ? 0 : item.weth_change_in_price_percentage * 100,
      percentage_change_in_usd: index === 0 ? 0 : item.percentage_change_in_usd * 100
    }));
  }, [data]);

  const calculateYAxisDomain = useCallback((data: ChartData[], key: keyof VisibleLines) => {
    if (!visibleLines[key]) return [0, 1]; // Default domain if series is inactive
    const values = data.map(item => item[key] as number);
    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);
    return [Math.floor(minValue * 0.9), Math.ceil(maxValue * 1.1)];
  }, [visibleLines]);

  const leftYAxisDomain = useMemo(() => {
    const domains = ['token_usd_amount', 'raw_change_in_usd', 'incentives_per_day_usd', 'tvl_to_incentive_roi_percentage']
      .map(key => calculateYAxisDomain(processedData, key as keyof VisibleLines));
    return [
      Math.min(...domains.map(d => d[0])),
      Math.max(...domains.map(d => d[1]))
    ];
  }, [processedData, calculateYAxisDomain]);

  const rightYAxisDomain = useMemo(() => {
    const wethDomain = calculateYAxisDomain(processedData, 'weth_change_in_price_percentage');
    const percentageDomain = calculateYAxisDomain(processedData, 'percentage_change_in_usd');
    return [
      Math.min(wethDomain[0], percentageDomain[0]),
      Math.max(wethDomain[1], percentageDomain[1])
    ];
  }, [processedData, calculateYAxisDomain]);

  const handleLegendClick = useCallback((dataKey: string) => {
    setVisibleLines(prev => ({
      ...prev,
      [dataKey]: !prev[dataKey as keyof VisibleLines]
    }));
  }, []);

  const chartElements: ChartElementType[] = [
    { dataKey: 'token_usd_amount', Component: Bar, props: { yAxisId: "left", stackId: "a", fill: "#e8dab2", name: "Pool TVL" } },
    { dataKey: 'raw_change_in_usd', Component: Bar, props: { yAxisId: "left", stackId: "a", fill: "#82ca9d", name: "Pool Change Since Start" } },
    { dataKey: 'incentives_per_day_usd', Component: Bar, props: { yAxisId: "left", stackId: "a", fill: "#e24343", name: "OP Incentives per Day" } },
    { dataKey: 'tvl_to_incentive_roi_percentage', Component: Bar, props: { yAxisId: "left", stackId: "a", fill: "#4CAF50", name: "TVL Change per USD Incentivized"} },
    { dataKey: 'weth_change_in_price_percentage', Component: Line, props: { yAxisId: "right", type: "monotone", stroke: "#945bd6", name: "WETH Price Change Since Start", dot: false, strokeWidth: 3 } },
    { dataKey: 'percentage_change_in_usd', Component: Line, props: { yAxisId: "right", type: "monotone", stroke: "#F7931A", name: "TVL Change Since Start", dot: false, strokeWidth: 3 } },
  ];

  const visibleData = useMemo(() => {
    return processedData.map(entry => {
      const newEntry: any = { date: entry.date };
      Object.keys(visibleLines).forEach(key => {
        if (visibleLines[key as keyof VisibleLines]) {
          newEntry[key] = entry[key as keyof ChartData];
        }
      });
      return newEntry;
    });
  }, [processedData, visibleLines]);

  return (
    <div className="single-chart">
      <h3>{title}</h3>
      <ResponsiveContainer width="100%" height={600}>
        <ComposedChart data={visibleData}>
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
            domain={leftYAxisDomain}
            label={{ 
              value: 'TVL + Incentives ($)', 
              angle: -90, 
              position: 'outside',
              offset: 5,
              dx: -28,
            }}
          />
          <YAxis 
            yAxisId="right" 
            orientation="right" 
            domain={rightYAxisDomain}
            tickFormatter={(value) => `${value.toFixed(0)}%`}
            label={{ 
              value: 'TVL + WETH Change (%)', 
              angle: -90, 
              position: 'outside',
              offset: 5,
              dx: 28,
            }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#404040',
              padding: '10px',
              border: '1px solid #ccc',
              borderRadius: '4px'
            }}
            formatter={(value, name, props) => {
              switch (name) {
                case "WETH Price Change Since Start":
                case "TVL Change Since Start":
                  return [`${Number(value).toFixed(2)}%`, name];
                case "Pool TVL":
                case "Pool Change Since Start":
                case "OP Incentives per Day":
                case "TVL Change per USD Incentivized":
                  return [formatCurrency(Number(value)), name];
                default:
                  return [value, name];
              }
            }}
            labelFormatter={(label) => `Date: ${new Date(label).toLocaleDateString()}`}
          />
          <Legend content={<CustomLegend 
            payload={chartElements.map(el => ({ 
              dataKey: el.dataKey, 
              value: el.props.name as string, 
              color: 'fill' in el.props ? el.props.fill : (el.props as React.ComponentProps<typeof Line>).stroke 
            }))} 
            onClick={handleLegendClick} 
            visibleLines={visibleLines} 
          />} />
          {chartElements.map(({ dataKey, Component, props }) => (
            React.createElement(
              Component as React.ComponentType<typeof props>,
              {
                key: dataKey,
                dataKey: dataKey,
                ...props,
                hide: !visibleLines[dataKey]
              }
            )
          ))}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};

const ComposedChartComponent: React.FC<ChartProps> = ({ data }) => {
  return (
    <div className="chart-grid">
      {Object.entries(data).map(([key, chartData]) => (
        <SingleChart key={key} data={chartData} title={key} />
      ))}
    </div>
  );
};

export default ComposedChartComponent;