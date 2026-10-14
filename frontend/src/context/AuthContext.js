import { createContext, useState, useCallback, useEffect } from 'react';
import axios from '../api/axios';

/**
 * AuthContext
 * Manages authentication state and user sessions
 * Persists user data to localStorage
 */
export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [authenticated, setAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  /**
   * Restore user session on app load
   */
  useEffect(() => {
    const restoreSession = () => {
      try {
        const token = localStorage.getItem('authToken');
        const userStr = localStorage.getItem('user');

        const demoMode = localStorage.getItem('demoMode') === 'true';

        if ((token || demoMode) && userStr) {
          const parsedUser = JSON.parse(userStr);
          setUser(parsedUser);
          setAuthenticated(true);
          setError(null);
        } else {
          setAuthenticated(false);
        }
      } catch (err) {
        console.error('Error restoring session:', err);
        // Clear corrupted data
        localStorage.removeItem('authToken');
        localStorage.removeItem('user');
        setAuthenticated(false);
      } finally {
        setLoading(false);
      }
    };

    restoreSession();
  }, []);

  /**
   * Login user
   */
  const login = useCallback(async (username, password) => {
    setLoading(true);
    setError(null);

    try {
      const response = await axios.post('/auth/login', {
        username,
        password
      });

      const { token, user_id, username: userName, email } = response.data;

      // Store token
      localStorage.setItem('authToken', token);
      localStorage.removeItem('demoMode');

      // Build user object from response
      const userData = {
        _id: user_id,
        id: user_id,
        user_id: user_id,
        username: userName,
        email: email
      };

      localStorage.setItem('user', JSON.stringify(userData));
      setUser(userData);

      // Update headers for future requests
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;

      setAuthenticated(true);
      return true;
    } catch (err) {
      const message = err.response?.data?.error || 'Login failed';
      setError(message);
      setAuthenticated(false);
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Start a local demo session without contacting the backend
   */
  const loginDemo = useCallback(() => {
    const demoUser = {
      id: 'demo-user',
      _id: 'demo-user',
      username: 'Demo Operator',
      email: 'demo@nightplate.local',
      isDemo: true,
    };

    localStorage.removeItem('authToken');
    delete axios.defaults.headers.common['Authorization'];
    localStorage.setItem('demoMode', 'true');
    localStorage.setItem('user', JSON.stringify(demoUser));
    setUser(demoUser);
    setAuthenticated(true);
    setError(null);
  }, []);

  /**
   * Register user
   */
  const register = useCallback(async (username, email, password) => {
    setLoading(true);
    setError(null);

    try {
      await axios.post('/auth/register', {
        username,
        email,
        password
      });

      // Auto-login after successful registration
      return await login(username, password);
    } catch (err) {
      const message = err.response?.data?.error || 'Registration failed';
      setError(message);
      return false;
    } finally {
      setLoading(false);
    }
  }, [login]);

  /**
   * Logout user
   */
  const logout = useCallback(() => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('demoMode');
    localStorage.removeItem('user');
    setUser(null);
    setAuthenticated(false);
    delete axios.defaults.headers.common['Authorization'];
  }, []);

  /**
   * Update user profile
   */
  const updateUser = useCallback((updatedUserData) => {
    const newUser = { ...user, ...updatedUserData };
    localStorage.setItem('user', JSON.stringify(newUser));
    setUser(newUser);
  }, [user]);

  /**
   * Check if user is authenticated
   */
  const isAuthenticated = useCallback(() => {
    const token = localStorage.getItem('authToken');
    const demoMode = localStorage.getItem('demoMode') === 'true';
    return (!!token || demoMode) && !!user;
  }, [user]);

  const value = {
    // State
    user,
    authenticated,
    loading,
    error,

    // Methods
    login,
    loginDemo,
    register,
    logout,
    updateUser,
    isAuthenticated,

    // Computed
    isLoggedIn: authenticated && !!user,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;
