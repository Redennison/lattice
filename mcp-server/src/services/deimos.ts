/**
 * Deimos Router Service - TypeScript Implementation
 * Provides TypeScript interface for Deimos Router integration
 */

import { readFile } from 'fs/promises';
import { join } from 'path';
import { homedir } from 'os';

export enum TaskType {
  ANALYSIS = 'analysis',
  SUMMARIZATION = 'summarization',
  CODE_GENERATION = 'code_generation',
  CLASSIFICATION = 'classification',
  EXTRACTION = 'extraction'
}

export interface RoutingRequest {
  taskType: TaskType;
  prompt: string;
  context?: string;
  maxTokens?: number;
  temperature?: number;
  costPriority?: number; // 0.0 = cheapest, 1.0 = best quality
}

export interface RoutingResponse {
  selectedModel: string;
  estimatedCost: number;
  confidence: number;
  reasoning: string;
  response: string;
}

export interface DeimosCredentials {
  api_url: string;
  api_key: string;
}

export class DeimosRouter {
  private apiUrl?: string;
  private apiKey?: string;

  constructor() {
    this.loadCredentials();
  }

  private async loadCredentials(): Promise<void> {
    try {
      // 1. Check for secrets.json in project root
      const projectSecretsPath = join(process.cwd(), 'secrets.json');
      try {
        const secretsContent = await readFile(projectSecretsPath, 'utf-8');
        const secrets: DeimosCredentials = JSON.parse(secretsContent);
        this.apiUrl = secrets.api_url;
        this.apiKey = secrets.api_key;
        return;
      } catch {
        // File doesn't exist or can't be read, continue to next option
      }

      // 2. Check environment variables
      this.apiUrl = process.env.DEIMOS_API_URL;
      this.apiKey = process.env.DEIMOS_API_KEY;

      if (this.apiUrl && this.apiKey) {
        return;
      }

      // 3. Check home directory
      const homeSecretsPath = join(homedir(), 'secrets.json');
      try {
        const secretsContent = await readFile(homeSecretsPath, 'utf-8');
        const secrets: DeimosCredentials = JSON.parse(secretsContent);
        this.apiUrl = secrets.api_url;
        this.apiKey = secrets.api_key;
        return;
      } catch {
        // File doesn't exist or can't be read
      }

      throw new Error(
        'Deimos API credentials not found. Please set up credentials via:\n' +
        '1. secrets.json file in project root\n' +
        '2. DEIMOS_API_URL and DEIMOS_API_KEY environment variables\n' +
        '3. secrets.json file in home directory'
      );
    } catch (error) {
      console.error('Failed to load Deimos credentials:', error);
      throw error;
    }
  }

  async routeRequest(request: RoutingRequest): Promise<RoutingResponse> {
    if (!this.apiUrl || !this.apiKey) {
      await this.loadCredentials();
    }

    const payload = {
      task_type: request.taskType,
      prompt: request.prompt,
      context: request.context,
      preferences: {
        cost_priority: request.costPriority ?? 0.7,
        max_tokens: request.maxTokens,
        temperature: request.temperature
      }
    };

    const headers = {
      'Authorization': `Bearer ${this.apiKey}`,
      'Content-Type': 'application/json'
    };

    try {
      const response = await fetch(`${this.apiUrl}/route`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Deimos API error ${response.status}: ${errorText}`);
      }

      const result = await response.json();

      // Execute the actual LLM call with selected model
      const llmResponse = await this.executeLLMCall(
        result.selected_model,
        request.prompt,
        request.context,
        request.maxTokens,
        request.temperature
      );

      return {
        selectedModel: result.selected_model,
        estimatedCost: result.estimated_cost ?? 0.0,
        confidence: result.confidence ?? 1.0,
        reasoning: result.reasoning ?? 'Model selected by Deimos Router',
        response: llmResponse
      };

    } catch (error) {
      // Fallback to default model if routing fails
      const fallbackResponse = await this.fallbackRequest(request);
      return {
        selectedModel: 'gpt-3.5-turbo',
        estimatedCost: 0.001,
        confidence: 0.5,
        reasoning: `Fallback due to routing error: ${error}`,
        response: fallbackResponse
      };
    }
  }

  private async executeLLMCall(
    model: string,
    prompt: string,
    context?: string,
    maxTokens?: number,
    temperature?: number
  ): Promise<string> {
    // Build the full prompt
    let fullPrompt = prompt;
    if (context) {
      fullPrompt = `Context: ${context}\n\nTask: ${prompt}`;
    }

    // Prepare LLM request
    const llmPayload: any = {
      model,
      messages: [
        { role: 'user', content: fullPrompt }
      ]
    };

    if (maxTokens) {
      llmPayload.max_tokens = maxTokens;
    }
    if (temperature !== undefined) {
      llmPayload.temperature = temperature;
    }

    const headers = {
      'Authorization': `Bearer ${this.apiKey}`,
      'Content-Type': 'application/json'
    };

    const response = await fetch(`${this.apiUrl}/chat/completions`, {
      method: 'POST',
      headers,
      body: JSON.stringify(llmPayload)
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`LLM API error ${response.status}: ${errorText}`);
    }

    const result = await response.json();
    return result.choices[0].message.content;
  }

  private async fallbackRequest(request: RoutingRequest): Promise<string> {
    try {
      return await this.executeLLMCall(
        'gpt-3.5-turbo',
        request.prompt,
        request.context,
        request.maxTokens,
        request.temperature
      );
    } catch {
      return `Error processing request: ${request.prompt.substring(0, 100)}...`;
    }
  }
}

// Convenience functions for common routing tasks
export async function routeAnalysisRequest(
  prompt: string,
  context?: string,
  costPriority: number = 0.7
): Promise<RoutingResponse> {
  const router = new DeimosRouter();
  const request: RoutingRequest = {
    taskType: TaskType.ANALYSIS,
    prompt,
    context,
    costPriority,
    maxTokens: 2000,
    temperature: 0.3
  };
  return await router.routeRequest(request);
}

export async function routeSummarizationRequest(
  prompt: string,
  context?: string,
  costPriority: number = 0.8
): Promise<RoutingResponse> {
  const router = new DeimosRouter();
  const request: RoutingRequest = {
    taskType: TaskType.SUMMARIZATION,
    prompt,
    context,
    costPriority,
    maxTokens: 1000,
    temperature: 0.2
  };
  return await router.routeRequest(request);
}

export async function routeClassificationRequest(
  prompt: string,
  context?: string,
  costPriority: number = 0.9
): Promise<RoutingResponse> {
  const router = new DeimosRouter();
  const request: RoutingRequest = {
    taskType: TaskType.CLASSIFICATION,
    prompt,
    context,
    costPriority,
    maxTokens: 500,
    temperature: 0.1
  };
  return await router.routeRequest(request);
}
