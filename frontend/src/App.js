import { useContext, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useParams } from 'react-router-dom';
import { AuthContext, AuthProvider } from './context/AuthContext';
import { ConfigProvider } from './context/ConfigContext';
import Login from './components/Auth/Login';
import Register from './components/Auth/Register';
import Dashboard from './components/Dashboard/Dashboard';
import 'bootstrap/dist/css/bootstrap.min.css';
import './App.css';
import './components/Auth/Auth.css';
import './components/Dashboard/Dashboard.css';

const DashboardShell = () => {
  const { panel } = useParams();
  return <Dashboard initialView={panel || 'overview'} />;
};

const ProtectedRoute = ({ children }) => {
  const { authenticated, loading } = useContext(AuthContext);

  if (loading) return null;
  return authenticated ? children : <Navigate to="/login" replace />;
};

function App() {
  useEffect(() => {
    const token = localStorage.getItem('authToken');

    if (token) {
      try {
        const parts = token.split('.');
        if (parts.length !== 3) {
          localStorage.removeItem('authToken');
        }
      } catch (err) {
        console.error('Token validation error:', err);
        localStorage.removeItem('authToken');
      }
    }
  }, []);

  return (
    <AuthProvider>
      <ConfigProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route
              path="/dashboard/:panel"
              element={
                <ProtectedRoute>
                  <DashboardShell />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <DashboardShell />
                </ProtectedRoute>
              }
            />
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </BrowserRouter>
      </ConfigProvider>
    </AuthProvider>
  );
}

export default App;
