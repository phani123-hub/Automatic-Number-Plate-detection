import { Spinner } from 'react-bootstrap';
import './Spinner.css';

const LoadingSpinner = ({ size = 'md', message = 'Loading...', fullScreen = false }) => {
  const sizeMap = {
    sm: { spinner: 'spinner-sm', text: 'small' },
    md: { spinner: '', text: '' },
    lg: { spinner: 'spinner-lg', text: 'large' },
  };

  const spinnerClass = sizeMap[size]?.spinner || '';

  if (fullScreen) {
    return (
      <div className="spinner-fullscreen">
        <div className="spinner-content">
          <Spinner animation="border" variant="primary" className={spinnerClass} />
          {message && <p className="mt-3">{message}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="spinner-inline">
      <Spinner animation="border" variant="primary" className={spinnerClass} />
      {message && <span className="ms-2">{message}</span>}
    </div>
  );
};

export default LoadingSpinner;
