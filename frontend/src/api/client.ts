// API client for Concept MRI backend
import type {
  ProbeRequest,
  ProbeResponse,
  ExecutionResponse,
  SessionStatus,
  SessionListItem,
  SessionDetailResponse
} from '../types/api';

const API_BASE_URL = 'http://localhost:8000/api';

/**
 * Error class for API-related errors
 */
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public response?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * API client for Concept MRI backend
 */
class ConceptMriApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);

      if (!response.ok) {
        let errorMessage = `HTTP error! status: ${response.status}`;
        let errorResponse;
        
        try {
          errorResponse = await response.json();
          errorMessage = errorResponse.detail || errorMessage;
        } catch {
          // If response isn't JSON, use status text
          errorMessage = response.statusText || errorMessage;
        }

        throw new ApiError(errorMessage, response.status, errorResponse);
      }

      return response.json();
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      // Network or other errors
      throw new ApiError(`Network error: ${error instanceof Error ? error.message : 'Unknown error'}`, 0);
    }
  }

  // Create new probe session
  async createProbeSession(request: ProbeRequest): Promise<ProbeResponse> {
    return this.request<ProbeResponse>('/probes', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // Execute probe session
  async executeProbeSession(sessionId: string): Promise<ExecutionResponse> {
    return this.request<ExecutionResponse>(`/probes/${sessionId}/execute`, {
      method: 'POST',
    });
  }

  // Get session status
  async getSessionStatus(sessionId: string): Promise<SessionStatus> {
    return this.request<SessionStatus>(`/probes/${sessionId}/status`);
  }

  // List all sessions
  async listSessions(): Promise<SessionListItem[]> {
    return this.request<SessionListItem[]>('/probes');
  }

  // Get session details
  async getSessionDetails(sessionId: string): Promise<SessionDetailResponse> {
    return this.request<SessionDetailResponse>(`/probes/${sessionId}`);
  }

  /**
   * Utility method to poll session status until completion
   * @param sessionId - The session to poll
   * @param onProgress - Callback for progress updates
   * @param pollInterval - Polling interval in milliseconds
   * @param maxAttempts - Maximum polling attempts to prevent infinite loops
   */
  async pollSessionUntilComplete(
    sessionId: string,
    onProgress?: (status: SessionStatus) => void,
    pollInterval: number = 2000,
    maxAttempts: number = 300  // 10 minutes at 2s intervals
  ): Promise<SessionStatus> {
    return new Promise((resolve, reject) => {
      let attempts = 0;

      const poll = async () => {
        try {
          attempts++;
          
          if (attempts > maxAttempts) {
            reject(new Error(`Polling timeout after ${maxAttempts} attempts`));
            return;
          }

          const status = await this.getSessionStatus(sessionId);
          onProgress?.(status);

          if (status.state === 'completed') {
            resolve(status);
          } else if (status.state === 'failed') {
            reject(new Error('Session execution failed'));
          } else {
            // Continue polling for 'pending' or 'running' states
            setTimeout(poll, pollInterval);
          }
        } catch (error) {
          reject(error);
        }
      };

      poll();
    });
  }

  /**
   * Create and execute a probe session in one operation
   */
  async createAndExecuteSession(
    request: ProbeRequest,
    onProgress?: (status: SessionStatus) => void
  ): Promise<SessionStatus> {
    const createResponse = await this.createProbeSession(request);
    await this.executeProbeSession(createResponse.session_id);
    return this.pollSessionUntilComplete(createResponse.session_id, onProgress);
  }
}

// Export singleton instance
export const apiClient = new ConceptMriApiClient();
export default apiClient;