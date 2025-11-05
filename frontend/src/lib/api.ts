const API_URL = process.env.NEXT_PUBLIC_API_URL;

class APIService {
  private getToken(): string | null {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('token');
    }
    return null;
  }

  private async request(endpoint: string, options: RequestInit = {}) {
    const token = this.getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Request failed' }));
      throw new Error(error.error || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Auth
  async login(email: string, password: string) {
    const data = await this.request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    
    if (data.access_token) {
      if (typeof window !== 'undefined') {
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('user', JSON.stringify(data.user));
        // Set cookie for middleware
        document.cookie = `token=${data.access_token}; path=/; max-age=86400; SameSite=Lax`;
      }
    }
    
    return data;
  }

  async register(email: string, password: string, name: string) {
    const data = await this.request('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, name }),
    });
    
    if (data.access_token) {
      if (typeof window !== 'undefined') {
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('user', JSON.stringify(data.user));
      }
    }
    
    return data;
  }

  logout() {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      // Remove cookie
      document.cookie = 'token=; path=/; max-age=0';
      // Redirect to signin
      window.location.href = '/signin';
    }
  }

  async getCurrentUser() {
    return this.request('/api/auth/me');
  }

  getStoredUser() {
    if (typeof window !== 'undefined') {
      const user = localStorage.getItem('user');
      return user ? JSON.parse(user) : null;
    }
    return null;
  }

  isAuthenticated(): boolean {
    return this.getToken() !== null;
  }

  // Analysis
  async startAnalysis(url: string) {
    return this.request('/api/analyze', {
      method: 'POST',
      body: JSON.stringify({ url }),
    });
  }

  async checkStatus(jobId: string) {
    return this.request(`/api/status/${jobId}`);
  }

  async getHistory(page = 1, perPage = 10) {
    return this.request(`/api/history?page=${page}&per_page=${perPage}`);
  }

  async getAnalysis(id: number) {
    return this.request(`/api/history/${id}`);
  }

  async deleteAnalysis(id: number) {
    return this.request(`/api/history/${id}`, {
      method: 'DELETE',
    });
  }

  // Users (admin only)
  async getUsers() {
    return this.request('/api/auth/users');
  }

  async updateUser(id: number, data: { name?: string; email?: string; role?: string }) {
    return this.request(`/api/auth/users/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteUser(id: number) {
    return this.request(`/api/auth/users/${id}`, {
      method: 'DELETE',
    });
  }
}

export const api = new APIService();
