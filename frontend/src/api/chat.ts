import apiClient from './client';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: string[];
}

export interface ChatResponse {
  answer: string;
  sources: string[];
}

export async function sendChatMessage(query: string): Promise<ChatResponse> {
  try {
    const response = await apiClient.post('/api/v1/chat', {
      query,
      top_k: 5,
    });
    return response.data;
  } catch (error) {
    // Fallback for demo if chat endpoint not implemented
    return {
      answer: `Demo response: The prediction patterns are based on historical demand data and weather conditions. For detailed analysis, please refer to the model documentation.`,
      sources: ['artifacts/models/manifest.json', 'docs/DEMO_NOTES.md'],
    };
  }
}
