// API client for Concept MRI backend
import type {
  ExecutionResponse,
  SessionStatus,
  SessionListItem,
  SessionDetailResponse,
  AnalyzeRoutesRequest,
  AnalyzeClusterRoutesRequest,
  RouteAnalysisResponse,
  RouteDetailsResponse,
  ExpertDetailsResponse,
  LLMInsightsRequest,
  LLMInsightsResponse,
  ReductionRequest,
  ReductionResponse,
  SentenceExperimentRequest,
  SentenceExperimentResponse,
} from '../types/api';
import type {
  TemporalRunMetadata,
  TemporalLagData,
} from '../types/temporal';

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

  private async request<T>(endpoint: string, options: RequestInit = {}, timeoutMs = 300000): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
      signal: controller.signal,
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
      if (error instanceof DOMException && error.name === 'AbortError') {
        throw new ApiError('Request timed out — server may be busy with a capture', 0);
      }
      // Network or other errors
      throw new ApiError(`Network error: ${error instanceof Error ? error.message : 'Unknown error'}`, 0);
    } finally {
      clearTimeout(timeoutId);
    }
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

  // Expert Route Analysis Methods

  /**
   * Analyze expert routes for a session within specified window layers
   * @param request - Route analysis request with session_id, window_layers, filters, etc.
   * @returns Route analysis response with Sankey data and statistics
   * @throws ApiError with status 404 if session not found, 500 for server errors
   */
  async analyzeRoutes(request: AnalyzeRoutesRequest): Promise<RouteAnalysisResponse> {
    return this.request<RouteAnalysisResponse>('/experiments/analyze-routes', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  /**
   * Analyze cluster routes for a session within specified window layers using reduced features
   * @param request - Cluster route analysis request with session_id, window_layers, clustering_config, etc.
   * @returns Route analysis response with Sankey data and statistics (same format as expert routes)
   * @throws ApiError with status 404 if session not found, 500 for server errors
   */
  async analyzeClusterRoutes(request: AnalyzeClusterRoutesRequest): Promise<RouteAnalysisResponse> {
    return this.request<RouteAnalysisResponse>('/experiments/analyze-cluster-routes', {
      method: 'POST',
      body: JSON.stringify(request),
    }, 300000);
  }

  /**
   * Get detailed information about a specific expert route
   * @param sessionId - Session identifier
   * @param signature - Route signature (e.g., "L0E18→L1E11→L2E14")
   * @param windowLayers - Array of layer numbers (e.g., [0, 1, 2])
   * @returns Detailed route information with tokens and category breakdown
   * @throws ApiError with status 400 for invalid layers, 404 if route not found
   */
  async getRouteDetails(
    sessionId: string, 
    signature: string, 
    windowLayers: number[]
  ): Promise<RouteDetailsResponse> {
    const params = new URLSearchParams({
      session_id: sessionId,
      signature: signature,
      window_layers: windowLayers.join(',')
    });
    return this.request<RouteDetailsResponse>(`/experiments/route-details?${params.toString()}`);
  }

  /**
   * Get expert specialization details
   * @param sessionId - Session identifier
   * @param layer - Layer number (e.g., 0, 1, 2)
   * @param expertId - Expert identifier (e.g., 18, 11, 14)
   * @returns Expert specialization information with usage statistics
   * @throws ApiError with status 404 if expert not found
   */
  async getExpertDetails(
    sessionId: string,
    layer: number, 
    expertId: number
  ): Promise<ExpertDetailsResponse> {
    const params = new URLSearchParams({
      session_id: sessionId,
      layer: layer.toString(),
      expert_id: expertId.toString()
    });
    return this.request<ExpertDetailsResponse>(`/experiments/expert-details?${params.toString()}`);
  }

  /**
   * Generate LLM insights from expert routing data
   * @param request - LLM insights request with nodes, links, user prompt, and API key
   * @returns LLM-generated insights and statistics
   * @throws ApiError with status 500 for LLM API errors
   */
  async generateLLMInsights(request: LLMInsightsRequest): Promise<LLMInsightsResponse> {
    return this.request<LLMInsightsResponse>('/experiments/llm-insights', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  /**
   * On-demand dimensionality reduction (PCA/UMAP) for trajectory visualization
   * @param request - Reduction request with session_ids, layers, source, method
   * @returns Flat array of reduced points grouped by probe_id and layer
   */
  async reduce(request: ReductionRequest): Promise<ReductionResponse> {
    return this.request<ReductionResponse>('/experiments/reduce', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  /**
   * Run a sentence experiment from a predefined sentence set
   * @param request - Sentence experiment request with sentence_set_name
   * @returns Session info with labels and counts
   */
  async runSentenceExperiment(request: SentenceExperimentRequest): Promise<SentenceExperimentResponse> {
    return this.request<SentenceExperimentResponse>('/probes/sentence-experiment', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }
  // --- Temporal Analysis ---

  async getTemporalRuns(sessionId: string): Promise<TemporalRunMetadata[]> {
    return this.request<TemporalRunMetadata[]>(`/experiments/temporal-runs/${sessionId}`);
  }

  async getTemporalLagData(request: {
    source_session_id: string
    temporal_session_id: string
    clustering_schema: string
    basin_a_cluster_id: number
    basin_b_cluster_id: number
    basin_layer: number
  }): Promise<TemporalLagData> {
    return this.request<TemporalLagData>('/experiments/temporal-lag-data', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  /**
   * List available clustering schemas for a session
   */
  async listClusterings(sessionId: string): Promise<{clusterings: Array<{name: string, created_at: string, params: any}>}> {
    return this.request(`/probes/sessions/${sessionId}/clusterings`);
  }

  /**
   * Get clustering schema details including reports
   */
  async getClusteringDetails(sessionId: string, schemaName: string): Promise<{
    meta: any;
    probe_assignments?: Record<string, Record<string, number>>;
    reports?: Record<string, string>;
    element_descriptions?: Record<string, string>;
  }> {
    return this.request(`/probes/sessions/${sessionId}/clusterings/${schemaName}`);
  }
}

// Export singleton instance
export const apiClient = new ConceptMriApiClient();
export default apiClient;