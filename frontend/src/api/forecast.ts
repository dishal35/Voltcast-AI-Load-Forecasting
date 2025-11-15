import apiClient from './client';

export interface PredictionPoint {
  ts_iso: string;
  prediction: number;
  baseline: number;
  residual: number;
  ci_lower: number;
  ci_upper: number;
  confidence_score?: number;
  cache_hit?: boolean;
}

export interface ForecastMetadata {
  model_version: string;
  cache_hit: boolean;
  data_source: 'db' | 'placeholder';
  mae: number;
  rmse: number;
  mape?: number;
  residual_std: number;
}

export interface ForecastResponse {
  timestamp: string;
  predictions: PredictionPoint[];
  metadata: ForecastMetadata;
}

export interface ModelMetadata {
  model_store_version: string;
  models: {
    hourly: {
      name: string;
      performance_metrics: {
        hybrid: {
          mae: number;
          rmse: number;
          mape: number;
        };
      };
    };
  };
  database: {
    type: string;
  };
}

export async function getForecast(timestamp: string, horizon: number = 24): Promise<ForecastResponse> {
  const response = await apiClient.post('/api/v1/predict/horizon', {
    timestamp,
    horizon,
  });

  // Transform response to match expected format
  const data = response.data;
  console.log('API Response data:', data);
  console.log('Confidence scores from API:', data.confidence_scores);
  
  // Handle the actual API response format
  const predictions: PredictionPoint[] = data.predictions.map((pred: number, index: number) => {
    const ci = data.confidence_intervals[index];
    const residual = data.residuals[index];
    const baseline = data.baselines ? data.baselines[index] : (data.baseline || pred);
    const confidence_score = data.confidence_scores ? data.confidence_scores[index] : undefined;
    console.log(`Mapping prediction ${index}: confidence_score = ${confidence_score}`);
    const startTime = new Date(data.timestamp);
    startTime.setHours(startTime.getHours() + index);
    
    return {
      ts_iso: startTime.toISOString(),
      prediction: pred,
      baseline: baseline,
      residual: residual || 0,
      ci_lower: ci?.lower || pred - 7.6,
      ci_upper: ci?.upper || pred + 7.6,
      confidence_score: confidence_score,
      cache_hit: data.metadata?.cache_hit || false,
    };
  });

  const metadata: ForecastMetadata = {
    model_version: data.metadata?.model_version || '1.0',
    cache_hit: data.metadata?.cache_hit || false,
    data_source: data.metadata?.data_source || 'db',
    mae: 2.016, // From manifest
    rmse: 3.888, // From manifest
    mape: 0.413, // From manifest
    residual_std: 3.883, // From manifest
  };

  return {
    timestamp: data.timestamp,
    predictions,
    metadata,
  };
}

export async function getModelMetadata(): Promise<ModelMetadata> {
  const response = await apiClient.get('/api/v1/status');
  return response.data;
}
