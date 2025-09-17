/**
 * Base API service for HTTP communication with the backend
 */

import axios, { AxiosError, AxiosInstance, AxiosResponse } from 'axios'
import { ApiResponse } from '../types'

class ApiService {
  private api: AxiosInstance

  constructor() {
    this.api = axios.create({
      baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Request interceptor to add auth token
    this.api.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('access_token')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    // Response interceptor for error handling
    this.api.interceptors.response.use(
      (response: AxiosResponse) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Token expired or invalid
          localStorage.removeItem('access_token')
          window.location.href = '/login'
        }
        return Promise.reject(this.handleError(error))
      }
    )
  }

  private handleError(error: AxiosError): Error {
    if (error.response?.data) {
      const errorData = error.response.data as ApiResponse
      return new Error(errorData.message || 'An error occurred')
    }
    
    if (error.message) {
      return new Error(error.message)
    }
    
    return new Error('Network error occurred')
  }

  // Generic HTTP methods
  async get<T = unknown>(url: string, params?: Record<string, unknown>): Promise<T> {
    const response = await this.api.get<ApiResponse<T>>(url, { params })
    return response.data.data || response.data
  }

  async post<T = unknown>(url: string, data?: Record<string, unknown>): Promise<T> {
    const response = await this.api.post<ApiResponse<T>>(url, data)
    return response.data.data || response.data
  }

  async put<T = unknown>(url: string, data?: Record<string, unknown>): Promise<T> {
    const response = await this.api.put<ApiResponse<T>>(url, data)
    return response.data.data || response.data
  }

  async patch<T = unknown>(url: string, data?: Record<string, unknown>): Promise<T> {
    const response = await this.api.patch<ApiResponse<T>>(url, data)
    return response.data.data || response.data
  }

  async delete<T = unknown>(url: string): Promise<T> {
    const response = await this.api.delete<ApiResponse<T>>(url)
    return response.data.data || response.data
  }

  // File upload method
  async upload<T = unknown>(url: string, formData: FormData): Promise<T> {
    const response = await this.api.post<ApiResponse<T>>(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data.data || response.data
  }

  // Health check
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    return this.get('/health')
  }
}

export const apiService = new ApiService()
