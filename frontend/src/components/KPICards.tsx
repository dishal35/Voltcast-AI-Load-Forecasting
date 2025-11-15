interface KPICardsProps {
  mae: number;
  rmse: number;
  mape?: number;
  residual_std: number;
}

export default function KPICards({ mae, rmse, mape, residual_std }: KPICardsProps) {
  const kpis = [
    {
      label: 'MAE',
      value: (mae * 10).toFixed(1),
      unit: 'MW',
      description: 'Mean Absolute Error',
      color: 'bg-blue-100 text-blue-700',
    },
    {
      label: 'RMSE',
      value: (rmse * 10).toFixed(1),
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

  if (mape !== undefined) {
    kpis.push({
      label: 'MAPE',
      value: mape.toFixed(3),
      unit: '%',
      description: 'Mean Absolute Percentage Error',
      color: 'bg-amber-100 text-amber-700',
    });
  }

  return (
    <div className="space-y-3">
      <h3 className="text-lg font-semibold text-slate-800">Model Performance</h3>
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
