import { useContext, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { AuthContext } from '../../context/AuthContext';
import { Form, Button, Alert } from 'react-bootstrap';
import './Auth.css';

const Login = () => {
  const navigate = useNavigate();
  const { login: loginUser, loginDemo } = useContext(AuthContext);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const success = await loginUser(username, password);
      if (!success) {
        setError('Invalid username or password. Please try again.');
        return;
      }
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.error || 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleDemoLogin = () => {
    loginDemo();
    navigate('/dashboard');
  };

  return (
    <div className="auth-page">
      <div className="auth-shell">
        <div className="auth-brand-panel">
          <div className="brand-mark">NPD</div>
          <div className="brand-copy">
            <p className="eyebrow">AI surveillance platform</p>
            <h1>NIGHT PLATE DETECTION</h1>
            <p className="subtitle">AI-Powered License Plate Recognition</p>
          </div>

          <div className="feature-grid">
            <div className="feature-item">
              <span className="feature-icon">◎</span>
              <div>
                <strong>Real-time detection</strong>
                <small>Continuous vehicle analysis</small>
              </div>
            </div>
            <div className="feature-item">
              <span className="feature-icon">◌</span>
              <div>
                <strong>Nighttime optimization</strong>
                <small>Low-light enhancement</small>
              </div>
            </div>
            <div className="feature-item">
              <span className="feature-icon">✦</span>
              <div>
                <strong>OCR recognition</strong>
                <small>License plate decoding</small>
              </div>
            </div>
            <div className="feature-item">
              <span className="feature-icon">▣</span>
              <div>
                <strong>Intelligent analytics</strong>
                <small>Patterns and confidence tracking</small>
              </div>
            </div>
          </div>
        </div>

        <div className="auth-form-panel">
          <div className="auth-card">
            <div className="auth-header">
              <p className="eyebrow accent">Secure access</p>
              <h2>Welcome Back</h2>
              <p>Sign in to your account</p>
            </div>

            {error && (
              <Alert variant="danger" dismissible onClose={() => setError('')} className="auth-alert">
                {error}
              </Alert>
            )}

            <Form onSubmit={handleSubmit} className="auth-form">
              <Form.Group className="mb-3">
                <Form.Label htmlFor="username">Email or Username</Form.Label>
                <Form.Control
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Enter your email or username"
                  required
                  autoComplete="username"
                />
              </Form.Group>

              <Form.Group className="mb-3">
                <div className="password-row">
                  <Form.Label htmlFor="password">Password</Form.Label>
                  <button
                    type="button"
                    className="inline-link"
                    onClick={() => setShowPassword((prev) => !prev)}
                  >
                    {showPassword ? 'Hide' : 'Show'}
                  </button>
                </div>
                <Form.Control
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  required
                  autoComplete="current-password"
                />
              </Form.Group>

              <div className="auth-actions-row">
                <button type="button" className="inline-link muted-link">Forgot password?</button>
              </div>

              <Button type="submit" className="auth-submit" disabled={loading}>
                {loading ? 'Signing in...' : 'Sign In'}
              </Button>
            </Form>

            <Button
              type="button"
              variant="outline-info"
              className="auth-submit mt-3"
              onClick={handleDemoLogin}
            >
              Continue with demo dashboard
            </Button>
            <p className="text-center mt-2 mb-0">
              <small>Uses sample data and does not require the Flask backend.</small>
            </p>

            <div className="auth-footer">
              <span>Don’t have an account?</span>
              <Link to="/register">Create account</Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;