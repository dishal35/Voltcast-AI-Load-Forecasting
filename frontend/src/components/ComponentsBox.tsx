import dayjs from 'dayjs';
import { PredictionPoint } from '../api/forecast';

interface ComponentsBoxProps {
  selectedPoint: PredictionPoint | null;
  dataSource: string;
  cacheHit: boolean;
}

export default function ComponentsBox({ selectedPoint, dataSource, cacheHit }: ComponentsBoxProps) {
  if (!selectedPoint) {
    return (
      <div className="bg-white p-4 rounded-xl shadow-md">
        <h3 className="text-lg font-semibold text-slate-800 mb-3">Hour Details</h3>
        <p className="text-sm text-slate-500 text-center py-8">
          Click on a point in the chart to see details
        </p>
      </div>
    );
  }

  const percentDiff = selectedPoint.baseline !== 0
    ? ((selectedPoint.prediction - selectedPoint.baseline) / selectedPoint.baseline * 100)
    : 0;

  const ciMargin = (selectedPoint.ci_upper - selectedPoint.ci_lower) / 2;
  const isSmallResidual = Math.abs(selectedPoint.residual) < 0.5;

  return (
    <div className="bg-white p-4 rounded-xl shadow-md">
      <h3 className="text-lg font-semibold text-slate-800 mb-3">Hour Details</h3>
      
      <div className="space-y-3">
        {/* Time */}
        <div>
          <div className="text-sm text-slate-500">Time</div>
          <div className="text-lg font-semibold text-slate-800">
            {dayjs(selectedPoint.ts_iso).format('MMM DD, HH:mm')}
          </div>
        </div>

        {/* Hybrid Prediction */}
        <div className="border-t pt-3">
          <div className="text-sm text-slate-500">Hybrid Prediction</div>
          <div className="text-2xl font-bold text-teal-600">
            {selectedPoint.prediction.toFixed(2)} MW
          </div>
        </div>

        {/* Baseline */}
        <div>
          <div className="text-sm text-slate-500">Baseline (XGBoost)</div>
          <div className="text-lg font-semibold text-slate-700">
            {selectedPoint.baseline.toFixed(2)} MW
            <span className="text-sm font-normal text-slate-500 ml-2">
              ({percentDiff >= 0 ? '+' : ''}{percentDiff.toFixed(2)}%)
            </span>
          </div>
        </div>

        {/* Residual */}
        <div>
          <div className="text-sm text-slate-500">Residual (Transformer)</div>
          <div className="text-lg font-semibold text-slate-700">
            {selectedPoint.residual.toFixed(3)} MW
          </div>
          {isSmallResidual && (
            <div className="text-xs text-amber-600 mt-1 bg-amber-50 p-2 rounded">
              ⚠️ Transformer residuals are small vs baseline
            </div>
          )}
        </div>

        {/* Confidence Interval */}
        <div className="border-t pt-3">
          <div className="text-sm text-slate-500">95% Confidence Interval</div>
          <div className="text-sm font-medium text-slate-700">
            [{selectedPoint.ci_lower.toFixed(1)}, {selectedPoint.ci_upper.toFixed(1)}] MW
          </div>
          <div className="text-xs text-slate-500 mt-1">
            Margin: ±{ciMargin.toFixed(1)} MW
          </div>
        </div>

        {/* Data Source */}
        <div className="border-t pt-3 text-xs text-slate-500">
          <div className="flex items-center justify-between">
            <span>Data source: <span className="font-medium text-slate-700">{dataSource}</span></span>
            <span className={`px-2 py-0.5 rounded-full ${cacheHit ? 'bg-blue-100 text-blue-700' : 'bg-green-100 text-green-700'}`}>
              {cacheHit ? 'Cached' : 'Fresh'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
