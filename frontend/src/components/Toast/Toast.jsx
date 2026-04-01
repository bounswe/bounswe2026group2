import React, { useEffect, useState } from 'react';
import './Toast.css';

const Toast = ({ message, type = 'error', duration = 4000, onClose }) => {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setVisible(false);
      setTimeout(onClose, 300);
    }, duration);
    return () => clearTimeout(timer);
  }, [duration, onClose]);

  const icons = {
    error: '!',
    success: '\u2713',
    info: 'i',
  };

  return (
    <div className={`toast toast--${type} ${visible ? 'toast--enter' : 'toast--exit'}`}>
      <span className="toast__icon">{icons[type]}</span>
      <span className="toast__message">{message}</span>
      <button className="toast__close" onClick={() => { setVisible(false); setTimeout(onClose, 300); }}>&times;</button>
    </div>
  );
};

export const ToastContainer = ({ toasts, removeToast }) => (
  <div className="toast-container">
    {toasts.map((t) => (
      <Toast key={t.id} message={t.message} type={t.type} onClose={() => removeToast(t.id)} />
    ))}
  </div>
);

export const useToast = () => {
  const [toasts, setToasts] = useState([]);
  let idCounter = 0;

  const addToast = (message, type = 'error') => {
    const id = Date.now() + (idCounter++);
    setToasts((prev) => [...prev, { id, message, type }]);
  };

  const removeToast = (id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return { toasts, addToast, removeToast };
};

export default Toast;
