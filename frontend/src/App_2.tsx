import React, { useState, useEffect } from 'react';
import cod3xLogo from './assets/cod3x.jpg';
import './App.css';
import axios from 'axios';
import TokenRevenuePieChart from './TokenRevenuePieChart';
import RevenueCards from './RevenueCards';
import DeploymentRevenueChart from './DeploymentRevenueChart';
import SevenDayMARevenueChart from './SevenDayMARevenueChart';
import ThirtyDayMARevenueChart from './ThirtyDayMARevenueChart';
import NinetyDayMARevenueChart from './NinetyDayMARevenueChart';
import OneEightyDayMARevenueChart from './OneEightyDayMARevenueChart';
import RevenueByTypeChart from './RevenueByTypeChart';
import RewarderDataDisplay from './RewarderDataDisplay';

const api_url = "https://api-dot-internal-website-427620.uc.r.appspot.com";

interface FileData {
  filename: string;
  signedUrl: string;
}

function App() {
  const [files, setFiles] = useState<string[]>([]);
  const [selectedFile, setSelectedFile] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingFiles, setIsLoadingFiles] = useState(true);
  const [activeTab, setActiveTab] = useState('rewarder');

  useEffect(() => {
    setIsLoadingFiles(true);
    axios.get<string[]>(`${api_url}/api/files`)
      .then(response => {
        setFiles(response.data);
      })
      .catch(error => {
        console.error('Error fetching files:', error);
      })
      .finally(() => {
        setIsLoadingFiles(false);
      });
  }, []);

  const handleFileSelect = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedFile(event.target.value);
  };

  const handleDownload = async () => {
    if (selectedFile) {
      setIsLoading(true);
      try {
        const response = await axios.get<FileData>(`${api_url}/api/download/${selectedFile}`);
        const { signedUrl } = response.data;
        
        const link = document.createElement('a');
        link.href = signedUrl;
        link.setAttribute('download', selectedFile);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      } catch (error) {
        console.error('Error fetching signed URL:', error);
        alert('Failed to initiate download. Please try again.');
      } finally {
        setIsLoading(false);
      }
    }
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'rewarder':
        return <RewarderDataDisplay />;
      case 'revenue':
        return <RevenueCards />;
      case 'tokenRevenue':
        return <TokenRevenuePieChart />;
      case 'deploymentRevenue':
        return <DeploymentRevenueChart />;
      case 'sevenDayMA':
        return <SevenDayMARevenueChart />;
      case 'thirtyDayMA':
        return <ThirtyDayMARevenueChart />;
      case 'ninetyDayMA':
        return <NinetyDayMARevenueChart />;
      case 'oneEightyDayMA':
        return <OneEightyDayMARevenueChart />;
      case 'revenueByType':
        return <RevenueByTypeChart />;
      default:
        return null;
    }
  };

  return (
    <div className="app-container">
      <aside className="sidebar">
        <div className="logo-container">
          <a href="https://www.cod3x.org/" target="_blank" rel="noopener noreferrer">
            <img src={cod3xLogo} className="logo cod3x-logo" alt="Cod3x logo" />
          </a>
        </div>
        <nav className="sidebar-navigation">
          <button onClick={() => setActiveTab('rewarder')} className={activeTab === 'rewarder' ? 'active' : ''}>Rewarder Data</button>
          <button onClick={() => setActiveTab('revenue')} className={activeTab === 'revenue' ? 'active' : ''}>Revenue Summary</button>
          <button onClick={() => setActiveTab('tokenRevenue')} className={activeTab === 'tokenRevenue' ? 'active' : ''}>Token Revenue</button>
          <button onClick={() => setActiveTab('deploymentRevenue')} className={activeTab === 'deploymentRevenue' ? 'active' : ''}>Deployment Revenue</button>
          <button onClick={() => setActiveTab('sevenDayMA')} className={activeTab === 'sevenDayMA' ? 'active' : ''}>7 Day MA</button>
          <button onClick={() => setActiveTab('thirtyDayMA')} className={activeTab === 'thirtyDayMA' ? 'active' : ''}>30 Day MA</button>
          <button onClick={() => setActiveTab('ninetyDayMA')} className={activeTab === 'ninetyDayMA' ? 'active' : ''}>90 Day MA</button>
          <button onClick={() => setActiveTab('oneEightyDayMA')} className={activeTab === 'oneEightyDayMA' ? 'active' : ''}>180 Day MA</button>
          <button onClick={() => setActiveTab('revenueByType')} className={activeTab === 'revenueByType' ? 'active' : ''}>Revenue by Type</button>
        </nav>
      </aside>

      <main className="main-content">
        <header>
          <h1>MRP Hub</h1>
        </header>

        <section className="file-downloader">
          <h2>Select a file to download:</h2>
          {isLoadingFiles ? (
            <p>Loading files...</p>
          ) : (
            <>
              <select 
                className="file-dropdown"
                value={selectedFile} 
                onChange={handleFileSelect}
                disabled={isLoading}
              >
                <option value="">Select a file</option>
                {files.map(file => (
                  <option key={file} value={file}>
                    {file}
                  </option>
                ))}
              </select>
              <button 
                className={`download-button ${isLoading ? 'downloading' : ''}`}
                onClick={handleDownload} 
                disabled={!selectedFile || isLoading}
              >
                {isLoading ? 'Initiating Download...' : 'Download'}
              </button>
              {isLoading && <div className="download-animation"></div>}
            </>
          )}
        </section>

        <section className="chart-display">
          <h2>{activeTab.charAt(0).toUpperCase() + activeTab.slice(1)} Chart</h2>
          {renderContent()}
        </section>
      </main>
    </div>
  );
}

export default App;