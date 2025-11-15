import { useState } from 'react';
import Header from './components/Header';
import ForecastForm from './components/ForecastForm';
import ForecastChart from './components/ForecastChart';
import KPICards from './components/KPICards';
import ComponentsBox from './components/ComponentsBox';
import ConfidenceBadge from './components/ConfidenceBadge';
import ChatBox from './components/ChatBox';
import ForecastTable from './components/ForecastTable';
import WeeklyForecast from './components/WeeklyForecast';
import Footer from './components/Footer';
import { getForecast, ForecastResponse } from './api/forecast';

function App() {
  const [forecastData, setForecastData] = useState<ForecastResponse | null>(null);
  const [selectedHourIndex, setSelectedHourIndex] = useState<number | null>(null);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [historyWarning, setHistoryWarning] = useState<string | null>(null);

  const handleForecastSubmit = async (date: string) => {
    setError(null);
    setHistoryWarning(null);
    setSelectedDate(date);
    
    try {
      // Convert date to timestamp at midnight (00:00)
      const timestamp = `${date}T00:00:00`;
      const data = await getForecast(timestamp, 24);
      
      // Validate data
      if (!data || !data.predictions || data.predictions.length === 0) {
        throw new Error('No forecast data received from API');
      }
      
      setForecastData(data);
      setSelectedHourIndex(0); // Select first hour by default

      // Check for limited history
      if (data.metadata.data_source === 'placeholder') {
        setHistoryWarning('Limited history available. Predictions may be approximate.');
      }
    } catch (err: any) {
      console.error('Forecast error:', err);
      setError(
        err.response?.data?.detail ||
        err.message ||
        'Server error — check logs. Use Run pre-demo checks.'
      );
      setForecastData(null); // Clear any existing data
    }
  };

  const selectedPoint = forecastData && selectedHourIndex !== null
    ? forecastData.predictions[selectedHourIndex]
    : null;

  const avgCIWidth = forecastData
    ? forecastData.predictions.reduce((sum, p) => sum + (p.ci_upper - p.ci_lower), 0) / forecastData.predictions.length
    : undefined;

  const avgConfidenceScore = forecastData
    ? forecastData.predictions.reduce((sum, p) => {
        console.log('Confidence score for prediction:', p.confidence_score);
        return sum + (p.confidence_score || 0);
      }, 0) / forecastData.predictions.length
    : undefined;

  console.log('Average confidence score:', avgConfidenceScore);

  return (
    <div className="min-h-screen bg-slate-50">
      <Header />

      <main className="container mx-auto px-4 py-6">
        {/* Error Banner */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            <div className="flex items-start gap-2">
              <svg className="w-5 h-5 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <div>
                <div className="font-medium">Error</div>
                <div className="text-sm">{error}</div>
              </div>
              <button
                onClick={() => setError(null)}
                className="ml-auto text-red-500 hover:text-red-700"
              >
                ×
              </button>
            </div>
          </div>
        )}

        {/* History Warning */}
        {historyWarning && (
          <div className="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg text-yellow-800">
            <div className="flex items-start gap-2">
              <svg className="w-5 h-5 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              <div className="text-sm">⚠️ {historyWarning}</div>
              <button
                onClick={() => setHistoryWarning(null)}
                className="ml-auto text-yellow-600 hover:text-yellow-800"
              >
                ×
              </button>
            </div>
          </div>
        )}

        {/* Main Grid Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-[2fr,1fr] gap-6">
          {/* Left Column */}
          <div className="space-y-6">
            <ForecastForm
              onSubmit={handleForecastSubmit}
            />

            {forecastData && (
              <>
                <ForecastChart
                  data={forecastData.predictions}
                  selectedHourIndex={selectedHourIndex ?? undefined}
                  onSelectHour={setSelectedHourIndex}
                />

                <ForecastTable predictions={forecastData.predictions} />
              </>
            )}

            {!forecastData && (
              <div className="bg-white p-12 rounded-2xl shadow-md text-center">
                <svg className="w-16 h-16 mx-auto text-slate-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                <h3 className="text-lg font-semibold text-slate-700 mb-2">No Forecast Data</h3>
                <p className="text-sm text-slate-500">
                  Select a timestamp and click "Get Forecast" to generate predictions
                </p>
              </div>
            )}
          </div>

          {/* Right Column */}
          <div className="space-y-6">
            {forecastData && (
              <>
                <KPICards
                  mae={forecastData.metadata.mae}
                  rmse={forecastData.metadata.rmse}
                  mape={forecastData.metadata.mape}
                  residual_std={forecastData.metadata.residual_std}
                />

                <ComponentsBox
                  selectedPoint={selectedPoint}
                  dataSource={forecastData.metadata.data_source}
                  cacheHit={forecastData.metadata.cache_hit}
                />

                <ConfidenceBadge 
                  confidenceScore={avgConfidenceScore} 
                  ciWidth={avgCIWidth} 
                />
              </>
            )}

            {selectedDate && <WeeklyForecast startDate={selectedDate} />}

            <ChatBox />
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}

export default App;
