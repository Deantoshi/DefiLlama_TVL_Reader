import loadingGif from './assets/pepe_4d.gif'; // Adjust the path as needed

const LoadingAnimation = () => {
    return (
      <div className="loading-animation-overlay">
        <div className="loading-animation">
          <img src={loadingGif} alt="Loading..." />
        </div>
      </div>
    );
  };
  
  export default LoadingAnimation;