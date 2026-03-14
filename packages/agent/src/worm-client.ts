import type { TickRequest, TickResponse, ControllerState } from './types.js';

/**
 * HTTP client for the Python worm-bridge controller.
 */
export class WormClient {
  private baseUrl: string;

  constructor(baseUrl: string = 'http://localhost:8642') {
    this.baseUrl = baseUrl.replace(/\/+$/, '');
  }

  /**
   * Send a tick request to the controller and receive a control surface.
   */
  async tick(request: TickRequest): Promise<TickResponse> {
    const res = await fetch(`${this.baseUrl}/tick`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    if (!res.ok) {
      throw new Error(`tick failed: ${res.status} ${await res.text()}`);
    }
    return res.json() as Promise<TickResponse>;
  }

  /**
   * Reset the controller to its initial state.
   */
  async reset(): Promise<void> {
    const res = await fetch(`${this.baseUrl}/reset`, { method: 'POST' });
    if (!res.ok) {
      throw new Error(`reset failed: ${res.status} ${await res.text()}`);
    }
  }

  /**
   * Get the current controller internal state.
   */
  async getState(): Promise<ControllerState> {
    const res = await fetch(`${this.baseUrl}/state`);
    if (!res.ok) {
      throw new Error(`getState failed: ${res.status} ${await res.text()}`);
    }
    return res.json() as Promise<ControllerState>;
  }

  /**
   * Health check endpoint.
   */
  async health(): Promise<{ status: string; controller_type: string }> {
    const res = await fetch(`${this.baseUrl}/health`);
    if (!res.ok) {
      throw new Error(`health failed: ${res.status} ${await res.text()}`);
    }
    return res.json() as Promise<{ status: string; controller_type: string }>;
  }
}
