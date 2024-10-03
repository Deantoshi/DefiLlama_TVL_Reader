import React, { useState, useEffect, useRef } from 'react';
import ComposedChartComponent from './ComboChart1'; // Assuming SingleChart is exported from ComboChart1

const LazyLoadChart = ({ data, title }) => {
  const [isVisible, setIsVisible] = useState(false);
  const chartRef = useRef(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.unobserve(chartRef.current);
        }
      },
      { threshold: 0.1 }
    );

    if (chartRef.current) {
      observer.observe(chartRef.current);
    }

    return () => {
      if (chartRef.current) {
        observer.unobserve(chartRef.current);
      }
    };
  }, []);

  return (
    <div ref={chartRef}>
      {isVisible ? (
        <ComposedChartComponent data={data} title={title} />
      ) : (
        <div style={{ height: '400px', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          Loading...
        </div>
      )}
    </div>
  );
};

export default LazyLoadChart;