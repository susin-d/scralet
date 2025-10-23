import React, { useState } from 'react';
import Card from '../Card';
import { StoreIcon } from '../Icons';
import { authApi } from '../../src/api/auth';
import { LoginResponse } from '../../types';

interface LoginPageProps {
  onLoginSuccess: () => void;
}

const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) {
      setError('Please enter both username and password.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response: LoginResponse = await authApi.login(username, password);
      console.log('Login successful:', response.user);
      onLoginSuccess();
    } catch (err: any) {
      console.error('Login failed:', err);
      setError(err.response?.data?.detail || 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleDemoLogin = () => {
    // Bypass credentials for demo
    onLoginSuccess();
  };

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="flex justify-center items-center mb-8">
           <svg className="w-10 h-10 text-white" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14.08V7.92c0-.41.47-.65.8-.4l4.67 3.08c.33.22.33.64 0 .86l-4.67 3.08c-.33.25-.8.01-.8-.4z"/></svg>
           <span className="ml-3 text-3xl font-bold text-text-primary tracking-wider">PROJECT SCARLET</span>
        </div>
        <Card>
          <h1 className="text-2xl font-bold text-center text-text-primary mb-2">Sign In</h1>
          <p className="text-center text-text-secondary mb-6">Welcome back to your retail command center.</p>
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-text-secondary">Username</label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="admin"
                className="mt-1 block w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-accent focus:border-accent sm:text-sm text-white"
              />
            </div>
            <div>
              <label htmlFor="password-input" className="block text-sm font-medium text-text-secondary">Password</label>
              <input
                id="password-input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="mt-1 block w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-accent focus:border-accent sm:text-sm text-white"
              />
            </div>
            {error && <p className="text-sm text-error">{error}</p>}
            <div>
              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-accent hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-accent transition-transform duration-200 ease-in-out hover:scale-105 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Signing In...' : 'Sign In'}
              </button>
            </div>
          </form>
          <div className="mt-6">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-600" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-gray-700 text-text-secondary">Or continue with</span>
              </div>
            </div>
            <div className="mt-6">
               <button
                onClick={handleDemoLogin}
                type="button"
                className="w-full flex justify-center py-2 px-4 border border-gray-600 rounded-md shadow-sm text-sm font-medium text-text-primary bg-gray-800 hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-accent transition-transform duration-200 ease-in-out hover:scale-105 active:scale-95"
              >
                Demo Login
              </button>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default LoginPage;