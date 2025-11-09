import { useState } from 'react';
import dayjs from 'dayjs';

interface ForecastFormProps {
  defaultDate?: string;
  onSubmit: (date: string) => Promise<void>;
}

export default function ForecastForm({ defaultDate, onSubmit }: ForecastFormProps) {
  // Default to today
  const [date, setDate] = useState(defaultDate ?? dayjs().format('YYYY-MM-DD'));
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e?: React.FormEvent) {
    e?.preventDefault();
    setLoading(true);
    try {
      await onSubmit(date);
    } finally {
      setLoading(false);
    }
  }

  const setPreset = (preset: 'today' | 'tomorrow' | 'yesterday') => {
    switch (preset) {
      case 'today':
        setDate(dayjs().format('YYYY-MM-DD'));
        break;
      case 'tomorrow':
        setDate(dayjs().add(1, 'day').format('YYYY-MM-DD'));
        break;
      case 'yesterday':
        setDate(dayjs().subtract(1, 'day').format('YYYY-MM-DD'));
        break;
    }
  };

  return (
    <form className="bg-white p-4 rounded-2xl shadow-md" onSubmit={handleSubmit}>
      <h3 className="text-lg font-semibold text-slate-800 mb-3">Select Date for 24-Hour Forecast</h3>
      <p className="text-sm text-slate-500 mb-3">Get hourly predictions from 00:00 to 23:00 for the selected date</p>
      
      <div className="space-y-3">
        <div>
          <label className="block text-sm text-slate-600 mb-1">Forecast Date</label>
          <input
            aria-label="forecast-date"
            className="w-full p-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent"
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </div>

        <div className="flex items-center gap-3">
          <button
            aria-label="get-forecast"
            className="flex-1 bg-teal-500 hover:bg-teal-600 px-6 py-2 text-white rounded-lg font-medium transition-colors disabled:bg-slate-300 disabled:cursor-not-allowed"
            disabled={loading}
            type="submit"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Loading…
              </span>
            ) : (
              'Get 24-Hour Forecast'
            )}
          </button>
        </div>

        <div className="flex gap-2 pt-2">
          <button
            type="button"
            onClick={() => setPreset('yesterday')}
            className="px-3 py-1 text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors"
          >
            Yesterday
          </button>
          <button
            type="button"
            onClick={() => setPreset('today')}
            className="px-3 py-1 text-xs bg-teal-100 hover:bg-teal-200 text-teal-700 rounded-lg transition-colors font-medium"
          >
            Today
          </button>
          <button
            type="button"
            onClick={() => setPreset('tomorrow')}
            className="px-3 py-1 text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors"
          >
            Tomorrow
          </button>
        </div>
      </div>
    </form>
  );
}
