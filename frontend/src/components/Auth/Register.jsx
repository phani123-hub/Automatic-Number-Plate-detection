import { useContext, useMemo, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { AuthContext } from '../../context/AuthContext';
import { Form, Button, Alert } from 'react-bootstrap';
import './Auth.css';

const Register = () => {
  const navigate = useNavigate();
  const { register } = useContext(AuthContext);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const passwordChecks = useMemo(() => {
    const password = formData.password;
    return [
      { label: 'Minimum 8 characters', valid: password.length >= 8 },
      { label: 'Uppercase letter', valid: /[A-Z]/.test(password) },
      { label: 'Lowercase letter', valid: /[a-z]/.test(password) },
      { label: 'Number', valid: /[0-9]/.test(password) },
      { label: 'Special character', valid: /[^A-Za-z0-9]/.test(password) },
    ];
  }, [formData.password]);

  const passwordStrength = useMemo(() => {
    const validCount = passwordChecks.filter((item) => item.valid).length;
    if (validCount <= 2) return { label: 'Weak', value: 25 };
    if (validCount <= 4) return { label: 'Good', value: 65 };
    return { label: 'Strong', value: 100 };
  }, [passwordChecks]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }

    if (!/[A-Z]/.test(formData.password)) {
      setError('Password must contain at least one uppercase letter.');
      return;
    }

    if (!/[a-z]/.test(formData.password)) {
      setError('Password must contain at least one lowercase letter.');
      return;
    }

    if (!/[0-9]/.test(formData.password)) {
      setError('Password must contain at least one number.');
      return;
    }

    if (!/[^A-Za-z0-9]/.test(formData.password)) {
      setError('Password must contain at least one special character.');
      return;
    }

    setLoading(true);

    try {
      await register(formData.username, formData.email, formData.password);
      navigate('/login');
    } catch (err) {
      setError(err.response?.data?.error || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-shell register-shell">
        <div className="auth-brand-panel">
          <div className="brand-mark">NPD</div>
          <div className="brand-copy">
            <p className="eyebrow">Secure onboarding</p>
            <h1>Create your access</h1>
            <p className="subtitle">Build a secure monitoring workspace for intelligent plate recognition.</p>
          </div>

          <div className="feature-grid compact-grid">
            {passwordChecks.map((item) => (
              <div key={item.label} className={`check-item ${item.valid ? 'ok' : ''}`}>
                <span>{item.valid ? '✓' : '•'}</span>
                <small>{item.label}</small>
              </div>
            ))}
          </div>
        </div>

        <div className="auth-form-panel">
          <div className="auth-card">
            <div className="auth-header">
              <p className="eyebrow accent">Account setup</p>
              <h2>Create Account</h2>
              <p>Join Night Plate Detection</p>
            </div>

            {error && (
              <Alert variant="danger" dismissible onClose={() => setError('')} className="auth-alert">
                {error}
              </Alert>
            )}

            <Form onSubmit={handleSubmit} className="auth-form">
              <Form.Group className="mb-3">
                <Form.Label htmlFor="username">Name</Form.Label>
                <Form.Control
                  id="username"
                  type="text"
                  name="username"
                  placeholder="Your full name"
                  value={formData.username}
                  onChange={handleChange}
                  required
                  autoComplete="name"
                />
              </Form.Group>

              <Form.Group className="mb-3">
                <Form.Label htmlFor="email">Email</Form.Label>
                <Form.Control
                  id="email"
                  type="email"
                  name="email"
                  placeholder="Enter your email"
                  value={formData.email}
                  onChange={handleChange}
                  required
                  autoComplete="email"
                />
              </Form.Group>

              <Form.Group className="mb-3">
                <div className="password-row">
                  <Form.Label htmlFor="password">Password</Form.Label>
                  <button type="button" className="inline-link" onClick={() => setShowPassword((prev) => !prev)}>
                    {showPassword ? 'Hide' : 'Show'}
                  </button>
                </div>
                <Form.Control
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  name="password"
                  placeholder="Create a strong password"
                  value={formData.password}
                  onChange={handleChange}
                  required
                  autoComplete="new-password"
                />
              </Form.Group>

              <Form.Group className="mb-3">
                <Form.Label htmlFor="confirmPassword">Confirm Password</Form.Label>
                <Form.Control
                  id="confirmPassword"
                  type={showPassword ? 'text' : 'password'}
                  name="confirmPassword"
                  placeholder="Confirm your password"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  required
                  autoComplete="new-password"
                />
              </Form.Group>

              <div className="strength-panel">
                <div className="strength-header">
                  <span>Password strength</span>
                  <strong>{passwordStrength.label}</strong>
                </div>
                <div className="strength-bar">
                  <span style={{ width: `${passwordStrength.value}%` }} />
                </div>
              </div>

              <Button type="submit" className="auth-submit" disabled={loading}>
                {loading ? 'Creating account...' : 'Create Account'}
              </Button>
            </Form>

            <div className="auth-footer">
              <span>Already have an account?</span>
              <Link to="/login">Sign in</Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Register;