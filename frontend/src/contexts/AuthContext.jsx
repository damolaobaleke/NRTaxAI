import React, { createContext, useContext, useState, useEffect } from 'react';
import { authService } from '../services/authService';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem('accessToken'));

  useEffect(() => {
    const initAuth = async () => {
      try {
        if (token) {
          // Verify token and get user info
          const userData = await authService.getCurrentUser(token);
          setUser(userData);
        }
      } catch (error) {
        console.error('Auth initialization error:', error);
        // Clear invalid token
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        setToken(null);
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, [token]);

  const login = async (email, password) => {
    try {
      const response = await authService.login(email, password);
      const { access_token, refresh_token } = response;
      
      localStorage.setItem('accessToken', access_token);
      localStorage.setItem('refreshToken', refresh_token);
      setToken(access_token);
      
      // Get user data
      const userData = await authService.getCurrentUser(access_token);
      setUser(userData);
      
      return { success: true };
    } catch (error) {
      const errorMessage = error.response?.data?.detail || error.message || 'Login failed';
      return { success: false, error: errorMessage };
    }
  };

  const register = async (email, password, mfaEnabled = false) => {
    try {
      const response = await authService.register(email, password, mfaEnabled);
      const { access_token, refresh_token } = response;
      console.log('Register response:', response);
      
      localStorage.setItem('accessToken', access_token);
      localStorage.setItem('refreshToken', refresh_token);
      setToken(access_token);
      
      // Get user data
      const userData = await authService.getCurrentUser(access_token);
      setUser(userData);
      
      return { success: true };
    } catch (error) {
      const errorMessage = error.response?.data?.detail || error.message || 'Registration failed';
      return { success: false, error: errorMessage };
    }
  };

  const logout = () => {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    setToken(null);
    setUser(null);
  };

  const refreshToken = async () => {
    try {
      const refresh_token = localStorage.getItem('refreshToken');
      if (!refresh_token) {
        throw new Error('No refresh token available');
      }
      
      const response = await authService.refreshToken(refresh_token);
      const { access_token, refresh_token: new_refresh_token } = response;
      
      localStorage.setItem('accessToken', access_token);
      localStorage.setItem('refreshToken', new_refresh_token);
      setToken(access_token);
      
      return access_token;
    } catch (error) {
      logout();
      throw error;
    }
  };

  const value = {
    user,
    token,
    loading,
    login,
    register,
    logout,
    refreshToken,
    isAuthenticated: !!user
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
