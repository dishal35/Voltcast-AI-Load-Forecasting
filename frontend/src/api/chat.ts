import apiClient from './client';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  sources?: string[];
}

export interface ChatRequest {
  message: string;
  conversation_history?: Array<{
    user: string;
    assistant: string;
    timestamp: string;
  }>;
}

export interface ChatResponse {
  response: string;
  context: {
    current_demand_mw?: number;
    avg_demand_24h_mw?: number;
    current_temperature?: number;
    current_weather?: string;
    humidity?: number;
    wind_speed?: number;
    cloud_cover?: number;
    demand_trend?: string;
    timestamp?: string;
  };
  timestamp: string;
  model: string;
  success: boolean;
  error?: string;
}

export interface SuggestedQuestionsResponse {
  questions: string[];
}

export async function sendChatMessage(
  message: string,
  conversationHistory?: ChatMessage[]
): Promise<ChatResponse> {
  // Convert ChatMessage format to API format
  const history = conversationHistory
    ?.filter(msg => msg.role === 'user' || msg.role === 'assistant')
    ?.reduce((acc, msg, index, arr) => {
      if (msg.role === 'user' && index + 1 < arr.length && arr[index + 1].role === 'assistant') {
        acc.push({
          user: msg.content,
          assistant: arr[index + 1].content,
          timestamp: msg.timestamp || new Date().toISOString()
        });
      }
      return acc;
    }, [] as Array<{ user: string; assistant: string; timestamp: string }>);

  const request: ChatRequest = {
    message,
    conversation_history: history
  };

  const response = await apiClient.post('/api/v1/chat', request);
  return response.data;
}

export async function getSuggestedQuestions(): Promise<string[]> {
  const response = await apiClient.get('/api/v1/chat/suggestions');
  return response.data.questions;
}

export async function getChatbotStatus() {
  const response = await apiClient.get('/api/v1/chat/status');
  return response.data;
}