import apiClient from './client';

export interface DailyForecast {
  date: string;
  avg_demand_mw: number;
  peak_demand_mw: number;
  peak_hour: number;
  total_energy_mwh: number;
}

export interface WeeklyForecastResponse {
  forecast_type: string;
  start_date: string;
  model: string;
  daily_forecasts: DailyForecast[];
  weekly_summary: {
    avg_demand_mw: number;
    peak_demand_mw: number;
    peak_day: string;
    total_energy_mwh: number;
  };
}

export async function getWeeklyForecast(startDate: string): Promise<WeeklyForecastResponse> {
  const response = await apiClient.post('/api/v1/predict/weekly', {
    start_date: startDate,
  });
  
  return response.data;
}
