/**
 * Authentication service for user login, registration, and profile management
 */

import { LoginRequest, LoginResponse, RegisterRequest, User } from '../types';
import { apiService } from './apiService';

class AuthService {
  /**
   * Authenticate user with email and password
   */
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    return apiService.post<LoginResponse>('/auth/login', credentials)
  }

  /**
   * Register a new user account
   */
  async register(userData: RegisterRequest): Promise<{ message: string; user: User }> {
    return apiService.post('/auth/register', userData)
  }

  /**
   * Get current user profile
   */
  async getCurrentUser(): Promise<User> {
    return apiService.get<User>('/auth/me')
  }

  /**
   * Update user profile
   */
  async updateProfile(userData: Partial<User>): Promise<User> {
    return apiService.put<User>('/auth/profile', userData)
  }

  /**
   * Change user password
   */
  async changePassword(oldPassword: string, newPassword: string): Promise<{ message: string }> {
    return apiService.post('/auth/change-password', {
      old_password: oldPassword,
      new_password: newPassword,
    })
  }

  /**
   * Request password reset
   */
  async requestPasswordReset(email: string): Promise<{ message: string }> {
    return apiService.post('/auth/password-reset', { email })
  }

  /**
   * Reset password with token
   */
  async resetPassword(token: string, newPassword: string): Promise<{ message: string }> {
    return apiService.post('/auth/password-reset/confirm', {
      token,
      new_password: newPassword,
    })
  }

  /**
   * Refresh authentication token
   */
  async refreshToken(): Promise<{ access_token: string; expires_in: number }> {
    return apiService.post('/auth/refresh')
  }

  /**
   * Logout user (revoke token)
   */
  async logout(): Promise<{ message: string }> {
    try {
      await apiService.post('/auth/logout')
    } catch (error) {
      // Even if logout fails on server, clear local storage
      console.warn('Logout request failed:', error)
    }
    
    // Always clear local storage
    localStorage.removeItem('access_token')
    
    return { message: 'Logged out successfully' }
  }
}

export const authService = new AuthService()
