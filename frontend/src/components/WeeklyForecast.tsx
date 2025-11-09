import { useEffect, useState } from 'react';
import { getWeeklyForecast, WeeklyForecastResponse } from '../api/weekly';
import dayjs from 'dayjs';

interface WeeklyForecastProps {
  startDate: string;
}

export default function WeeklyForecast({ startDate }: WeeklyForecastProps) {
  const [data, setData] = useState<WeeklyForecastResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchWeekly = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const result = await getWeeklyForecast(startDate);
        setData(result);
      } catch (err: any) {
        console.error('Weekly forecast error:', err);
        setError(err.response?.data?.detail || err.message || 'Failed to fetch weekly forecast');
      } finally {
        setLoading(false);
      }
    };

    fetchWeekly();
  }, [startDate]);

  if (loading) {
    return (
      <div className="bg-white p-4 rounded-xl shadow-md">
        <h3 className="text-lg font-semibold text-slate-800 mb-3">7-Day Forecast (SARIMAX)</h3>
        <div className="animate-pulse space-y-3">
          {[...Array(7)].map((_, i) => (
            <div key={i} className="h-12 bg-slate-200 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white p-4 rounded-xl shadow-md">
        <h3 className="text-lg font-semibold text-slate-800 mb-3">7-Day Forecast (SARIMAX)</h3>
        <div className="text-sm text-red-600 bg-red-50 p-3 rounded">
          {error}
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="bg-white p-4 rounded-xl shadow-md">
      <h3 className="text-lg font-semibold text-slate-800 mb-1">7-Day Forecast (SARIMAX)</h3>
      <p className="text-xs text-slate-500 mb-3">Daily average demand predictions</p>
      
      <div className="space-y-2">
        {data.daily_forecasts.map((day, index) => (
          <div
            key={index}
            className="flex items-center justify-between p-3 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <div className="flex-1">
              <div className="font-medium text-slate-800">
                {dayjs(day.date).format('ddd, MMM D')}
              </div>
              <div className="text-xs text-slate-500">
                Peak: {day.peak_demand_mw.toFixed(1)} MW at {day.peak_hour}:00
              </div>
            </div>
            <div className="text-right">
              <div className="text-lg font-bold text-teal-600">
                {day.avg_demand_mw.toFixed(1)}
              </div>
              <div className="text-xs text-slate-500">MW avg</div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 pt-4 border-t border-slate-200">
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <div className="text-slate-500">Weekly Average</div>
            <div className="font-semibold text-slate-800">
              {data.weekly_summary.avg_demand_mw.toFixed(1)} MW
            </div>
          </div>
          <div>
            <div className="text-slate-500">Peak Day</div>
            <div className="font-semibold text-slate-800">
              {dayjs(data.weekly_summary.peak_day).format('MMM D')}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
