import { PredictionPoint } from '../api/forecast';

interface KPICardsProps {
  mae: number;
  rmse: number;
  mape?: number;
  residual_std: number;
  predictions?: PredictionPoint[];
}

export default function KPICards({ mae, rmse, mape, residual_std, predictions }: KPICardsProps) {
  // Calculate actual metrics if we have predictions with actuals
  let actualMetrics: { mae: number; rmse: number; mape: number } | null = null;
  let actualsCount = 0;
  
  if (predictions) {
    const validPairs = predictions.filter(p => p.actual !== null && p.actual !== undefined);
    actualsCount = validPairs.length;
    
    if (validPairs.length > 0) {
      const errors = validPairs.map(p => Math.abs(p.prediction - p.actual!));
      const squaredErrors = validPairs.map(p => Math.pow(p.prediction - p.actual!, 2));
      const percentErrors = validPairs.map(p => Math.abs((p.prediction - p.actual!) / p.actual!) * 100);
      
      actualMetrics = {
        mae: errors.reduce((a, b) => a + b, 0) / errors.length,
        rmse: Math.sqrt(squaredErrors.reduce((a, b) => a + b, 0) / squaredErrors.length),
        mape: percentErrors.reduce((a, b) => a + b, 0) / percentErrors.length
      };
    }
  }
  
  // Use actual metrics if available, otherwise use model defaults
  const displayMAE = actualMetrics ? actualMetrics.mae : (mae * 10);
  const displayRMSE = actualMetrics ? actualMetrics.rmse : (rmse * 10);
  const displayMAPE = actualMetrics ? actualMetrics.mape : mape;
  const dataSource = actualMetrics ? `Calculated from ${actualsCount} actual values` : 'Model baseline (2024 test set)';
  
  const kpis = [
    {
      label: 'MAE',
      value: displayMAE.toFixed(1),
      unit: 'MW',
      description: 'Mean Absolute Error',
      color: 'bg-blue-100 text-blue-700',
    },
    {
      label: 'RMSE',
      value: displayRMSE.toFixed(1),
      unit: 'MW',
      description: 'Root Mean Square Error',
      color: 'bg-purple-100 text-purple-700',
    },
    {
      label: 'Residual Std',
      value: (residual_std * 10).toFixed(1),
      unit: 'MW',
      description: 'Residual Standard Deviation',
      color: 'bg-teal-100 text-teal-700',
    },
  ];

  if (displayMAPE !== undefined) {
    kpis.push({
      label: 'MAPE',
      value: displayMAPE.toFixed(3),
      unit: '%',
      description: 'Mean Absolute Percentage Error',
      color: 'bg-amber-100 text-amber-700',
    });
  }

  return (
    <div className="space-y-3">
      <h3 className="text-lg font-semibold text-slate-800">Model Performance</h3>
      <div className="text-xs text-slate-500 mb-2">
        {dataSource}
      </div>
      <div className="grid grid-cols-1 gap-3">
        {kpis.map((kpi, index) => (
          <div key={index} className="bg-white p-3 rounded-xl shadow-md">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium text-slate-600">{kpi.label}</span>
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${kpi.color}`}>
                {kpi.unit}
              </span>
            </div>
            <div className="text-2xl font-bold text-slate-800">{kpi.value}</div>
            <div className="text-xs text-slate-500 mt-1">{kpi.description}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
