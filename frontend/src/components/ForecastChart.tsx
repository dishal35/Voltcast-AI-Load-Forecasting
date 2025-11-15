import {
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  ComposedChart,
} from 'recharts';
import dayjs from 'dayjs';
import { PredictionPoint } from '../api/forecast';

interface ForecastChartProps {
  data: PredictionPoint[];
  selectedHourIndex?: number;
  onSelectHour?: (index: number) => void;
}

interface ChartDataPoint {
  hour: string;
  fullTime: string;
  prediction: number;
  baseline: number;
  ci_lower: number;
  ci_upper: number;
  residual: number;
  confidence_score?: number;
  index: number;
}

const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload as ChartDataPoint;
    return (
      <div className="bg-white p-3 rounded-lg shadow-lg border border-slate-200">
        <p className="text-sm font-semibold text-slate-800 mb-2">{data.fullTime}</p>
        <div className="space-y-1 text-xs">
          <p className="text-teal-600">
            <span className="font-medium">Hybrid:</span> {data.prediction.toFixed(1)} MW
          </p>
          <p className="text-slate-600">
            <span className="font-medium">SARIMAX:</span> {data.baseline.toFixed(1)} MW
          </p>
          <p className="text-slate-500">
            <span className="font-medium">Residual:</span> {data.residual.toFixed(2)} MW
          </p>
          <p className="text-slate-400">
            <span className="font-medium">CI:</span> [{data.ci_lower.toFixed(1)}, {data.ci_upper.toFixed(1)}] MW
          </p>
          {data.confidence_score && (
            <p className="text-green-600">
              <span className="font-medium">Confidence:</span> {data.confidence_score.toFixed(1)}%
            </p>
          )}
        </div>
      </div>
    );
  }
  return null;
};

export default function ForecastChart({ data, selectedHourIndex, onSelectHour }: ForecastChartProps) {
  const chartData: ChartDataPoint[] = data.map((pred, index) => ({
    hour: dayjs(pred.ts_iso).format('HH:mm'),
    fullTime: dayjs(pred.ts_iso).format('MMM DD, HH:mm'),
    prediction: pred.prediction,
    baseline: pred.baseline,
    ci_lower: pred.ci_lower,
    ci_upper: pred.ci_upper,
    residual: pred.residual,
    confidence_score: pred.confidence_score,
    index,
  }));

  const handleClick = (data: any) => {
    if (data && data.activePayload && onSelectHour) {
      const index = data.activePayload[0].payload.index;
      onSelectHour(index);
    }
  };

  return (
    <div className="bg-white p-4 rounded-2xl shadow-md">
      <h3 className="text-lg font-semibold text-slate-800 mb-4">24-Hour Forecast</h3>
      
      <div className="w-full" style={{ height: '400px' }}>
        <ResponsiveContainer width="100%" height={400}>
          <ComposedChart
            data={chartData}
            onClick={handleClick}
            margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
          >
            <defs>
              <linearGradient id="colorCI" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#0ea5a4" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#0ea5a4" stopOpacity={0.05} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="hour"
              tick={{ fontSize: 12, fill: '#64748b' }}
              stroke="#cbd5e1"
            />
            <YAxis
              tick={{ fontSize: 12, fill: '#64748b' }}
              stroke="#cbd5e1"
              label={{ value: 'Demand (MW)', angle: -90, position: 'insideLeft', style: { fill: '#64748b' } }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ paddingTop: 20 }}
              iconType="line"
            />
            <Area
              type="monotone"
              dataKey="ci_upper"
              stroke="none"
              fill="url(#colorCI)"
              fillOpacity={1}
              name="95% CI Upper"
            />
            <Area
              type="monotone"
              dataKey="ci_lower"
              stroke="none"
              fill="#fff"
              fillOpacity={1}
              name="95% CI Lower"
            />
            <Line
              type="monotone"
              dataKey="baseline"
              stroke="#94a3b8"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
              name="SARIMAX"
            />
            <Line
              type="monotone"
              dataKey="prediction"
              stroke="#0ea5a4"
              strokeWidth={3}
              dot={{ r: 4, fill: '#0ea5a4', strokeWidth: 2, stroke: '#fff' }}
              activeDot={{ r: 6 }}
              name="Hybrid Prediction"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
