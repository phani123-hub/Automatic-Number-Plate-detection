import { Toast, ToastContainer } from 'react-bootstrap';
import { useEffect, useState } from 'react';
import './Notification.css';

const Notification = ({
  show,
  type = 'info',
  message,
  title,
  autoClose = true,
  delay = 3000,
  onClose,
}) => {
  const [isVisible, setIsVisible] = useState(show);

  useEffect(() => {
    setIsVisible(show);

    if (show && autoClose) {
      const timer = setTimeout(() => {
        setIsVisible(false);
        onClose?.();
      }, delay);

      return () => clearTimeout(timer);
    }
  }, [show, autoClose, delay, onClose]);

  const bgColor = {
    success: 'bg-success',
    error: 'bg-danger',
    warning: 'bg-warning',
    info: 'bg-info',
  }[type] || 'bg-info';

  const iconMap = {
    success: '✓',
    error: '✕',
    warning: '⚠',
    info: 'ℹ',
  };

  return (
    <ToastContainer position="top-end" className="p-3 notification-container">
      <Toast show={isVisible} onClose={() => setIsVisible(false)}>
        <Toast.Header closeButton className={bgColor}>
          <span className="notification-icon me-2">{iconMap[type]}</span>
          <strong className="me-auto text-white">{title || type.toUpperCase()}</strong>
        </Toast.Header>
        <Toast.Body>{message}</Toast.Body>
      </Toast>
    </ToastContainer>
  );
};

export default Notification;
