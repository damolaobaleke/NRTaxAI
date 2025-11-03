import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

// Create axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('accessToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        const refreshToken = localStorage.getItem('refreshToken');
        if (refreshToken) {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken
          });
          
          const { access_token, refresh_token: new_refresh_token } = response.data;
          localStorage.setItem('accessToken', access_token);
          localStorage.setItem('refreshToken', new_refresh_token);
          
          // Retry original request with new token
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return apiClient(originalRequest);
        }
      } catch (refreshError) {
        // Refresh failed, redirect to login
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        window.location.href = '/login';
      }
    }
    
    return Promise.reject(error);
  }
);

export const authService = {
  // Authentication
  async login(email, password) {
    try {
      const response = await axios.post(`${API_BASE_URL}/auth/login`, {
        email,
        password
      });
      return response.data;
    } catch (error) {
      console.error('Login error:', error.response?.data || error.message);
      throw error;
    }
  },

  async register(email, password, mfaEnabled = false) {
    try {
      const response = await axios.post(`${API_BASE_URL}/auth/register`, {
        email,
        password,
        mfa_enabled: mfaEnabled
      });
      // console.log('Register response:', response.data);
      return response.data;
    } catch (error) {
      // Its an exception that is thrown by the backend, so info will be in error object
      console.error('Register error:', error.response?.data || error.message);
      throw error;
    }
  },

  async refreshToken(refreshToken) {
    const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
      refresh_token: refreshToken
    });
    return response.data;
  },

  async getCurrentUser(token) {
    const response = await apiClient.get('/users/me');
    return response.data;
  },

  async logout() {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
  }
};

export const userService = {
  async getProfile() {
    const response = await apiClient.get('/users/me/profile');
    return response.data;
  },

  async updateProfile(profileData) {
    const response = await apiClient.put('/users/me/profile', profileData);
    return response.data;
  },

  async createProfile(profileData) {
    const response = await apiClient.post('/users/me/profile', profileData);
    return response.data;
  }
};

export const chatService = {
  async createSession(taxReturnId = null) {
    const response = await apiClient.post('/chat/session', {
      tax_return_id: taxReturnId,
      status: 'active'
    });
    return response.data;
  },

  async sendMessage(sessionId, message) {
    const response = await apiClient.post('/chat/message', {
      session_id: sessionId,
      message
    });
    return response.data;
  },

  async getChatHistory(sessionId) {
    const response = await apiClient.get(`/chat/history?session_id=${sessionId}`);
    return response.data;
  },

  async getUserSessions() {
    const response = await apiClient.get('/chat/sessions');
    return response.data;
  }
};

export const taxReturnService = {
  async createTaxReturn(taxYear) {
    const response = await apiClient.post('/tax/', {
      tax_year: taxYear,
      status: 'draft'
    });
    return response.data;
  },

  async getTaxReturns() {
    const response = await apiClient.get('/tax/');
    return response.data;
  },

  async getTaxReturn(returnId) {
    const response = await apiClient.get(`/tax/${returnId}`);
    return response.data;
  },

  async getTaxReturnSummary(returnId) {
    const response = await apiClient.get(`/tax/${returnId}/summary`);
    return response.data;
  },

  async computeTax(returnId) {
    const response = await apiClient.post(`/tax/${returnId}/compute`);
    return response.data;
  }
};

export const documentService = {
  async requestUploadUrl(docType, returnId = null) {
    // FastAPI expects query parameters for simple POST params
    const params = new URLSearchParams();
    params.append('doc_type', docType);
    if (returnId) {
      params.append('return_id', returnId);
    }
    const response = await apiClient.post(`/documents/upload?${params.toString()}`);
    return response.data;
  },

  async uploadFile(documentId, file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await apiClient.post(`/documents/${documentId}/upload-file`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },

  async confirmUpload(documentId) {
    const response = await apiClient.post(`/documents/${documentId}/confirm`);
    return response.data;
  },

  async getDocuments(returnId = null, docStatus = null) {
    const params = new URLSearchParams();
    if (returnId) params.append('return_id', returnId);
    if (docStatus) params.append('doc_status', docStatus);
    
    const response = await apiClient.get(`/documents/?${params.toString()}`);
    return response.data;
  },

  async getDocument(documentId) {
    const response = await apiClient.get(`/documents/${documentId}`);
    return response.data;
  },

  async deleteDocument(documentId) {
    const response = await apiClient.delete(`/documents/${documentId}`);
    return response.data;
  },

  async getDownloadUrl(documentId, expiresIn = 3600) {
    const response = await apiClient.get(`/documents/${documentId}/download?expires_in=${expiresIn}`);
    return response.data;
  },

  async startExtraction(documentId) {
    const response = await apiClient.post(`/documents/${documentId}/start`);
    return response.data;
  },

  async getExtractionResult(documentId) {
    const response = await apiClient.get(`/documents/${documentId}/result`);
    return response.data;
  }
};

export default apiClient;
