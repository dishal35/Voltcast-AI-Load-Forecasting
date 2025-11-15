import { useState } from 'react';
import dayjs from 'dayjs';
import { PredictionPoint } from '../api/forecast';

interface ForecastTableProps {
  predictions: PredictionPoint[];
}

type SortKey = 'time' | 'prediction' | 'baseline' | 'residual' | 'ci_lower' | 'ci_upper';

export default function ForecastTable({ predictions }: ForecastTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('time');
  const [sortAsc, setSortAsc] = useState(true);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(true);
    }
  };

  const sortedPredictions = [...predictions].sort((a, b) => {
    let aVal: number | string;
    let bVal: number | string;

    switch (sortKey) {
      case 'time':
        aVal = a.ts_iso;
        bVal = b.ts_iso;
        break;
      case 'prediction':
        aVal = a.prediction;
        bVal = b.prediction;
        break;
      case 'baseline':
        aVal = a.baseline;
        bVal = b.baseline;
        break;
      case 'residual':
        aVal = a.residual;
        bVal = b.residual;
        break;
      case 'ci_lower':
        aVal = a.ci_lower;
        bVal = b.ci_lower;
        break;
      case 'ci_upper':
        aVal = a.ci_upper;
        bVal = b.ci_upper;
        break;
      default:
        aVal = a.ts_iso;
        bVal = b.ts_iso;
    }

    if (aVal < bVal) return sortAsc ? -1 : 1;
    if (aVal > bVal) return sortAsc ? 1 : -1;
    return 0;
  });

  const downloadCSV = () => {
    const headers = ['Time', 'Prediction (MW)', 'SARIMAX (MW)', 'Residual (MW)', 'CI Lower (MW)', 'CI Upper (MW)', 'Notes'];
    const rows = predictions.map((p) => [
      dayjs(p.ts_iso).format('YYYY-MM-DD HH:mm'),
      (p.prediction ?? 0).toFixed(2),
      (p.baseline ?? 0).toFixed(2),
      (p.residual ?? 0).toFixed(3),
      (p.ci_lower ?? 0).toFixed(2),
      (p.ci_upper ?? 0).toFixed(2),
      p.cache_hit ? 'Cache hit' : '',
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map((row) => row.join(',')),
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `forecast_${dayjs().format('YYYY-MM-DD_HH-mm')}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };

  const SortIcon = ({ active, asc }: { active: boolean; asc: boolean }) => (
    <span className="ml-1 text-xs">
      {active ? (asc ? '↑' : '↓') : '↕'}
    </span>
  );

  return (
    <div className="bg-white p-4 rounded-2xl shadow-md">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-800">Hourly Forecast Data</h3>
        <button
          onClick={downloadCSV}
          className="px-3 py-1.5 bg-teal-500 hover:bg-teal-600 text-white text-sm rounded-lg font-medium transition-colors flex items-center gap-2"
          aria-label="download-csv"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          Export CSV
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th
                className="px-4 py-2 text-left font-medium text-slate-600 cursor-pointer hover:bg-slate-100"
                onClick={() => handleSort('time')}
              >
                Time
                <SortIcon active={sortKey === 'time'} asc={sortAsc} />
              </th>
              <th
                className="px-4 py-2 text-right font-medium text-slate-600 cursor-pointer hover:bg-slate-100"
                onClick={() => handleSort('prediction')}
              >
                Prediction
                <SortIcon active={sortKey === 'prediction'} asc={sortAsc} />
              </th>
              <th
                className="px-4 py-2 text-right font-medium text-slate-600 cursor-pointer hover:bg-slate-100"
                onClick={() => handleSort('baseline')}
              >
                SARIMAX
                <SortIcon active={sortKey === 'baseline'} asc={sortAsc} />
              </th>
              <th
                className="px-4 py-2 text-right font-medium text-slate-600 cursor-pointer hover:bg-slate-100"
                onClick={() => handleSort('residual')}
              >
                Residual
                <SortIcon active={sortKey === 'residual'} asc={sortAsc} />
              </th>
              <th
                className="px-4 py-2 text-right font-medium text-slate-600 cursor-pointer hover:bg-slate-100"
                onClick={() => handleSort('ci_lower')}
              >
                CI Low
                <SortIcon active={sortKey === 'ci_lower'} asc={sortAsc} />
              </th>
              <th
                className="px-4 py-2 text-right font-medium text-slate-600 cursor-pointer hover:bg-slate-100"
                onClick={() => handleSort('ci_upper')}
              >
                CI High
                <SortIcon active={sortKey === 'ci_upper'} asc={sortAsc} />
              </th>
              <th className="px-4 py-2 text-left font-medium text-slate-600">
                Notes
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {sortedPredictions.map((pred, index) => (
              <tr key={index} className="hover:bg-slate-50">
                <td className="px-4 py-2 text-slate-700">
                  {dayjs(pred.ts_iso).format('MMM DD, HH:mm')}
                </td>
                <td className="px-4 py-2 text-right font-medium text-teal-600">
                  {(pred.prediction ?? 0).toFixed(2)}
                </td>
                <td className="px-4 py-2 text-right text-slate-600">
                  {(pred.baseline ?? 0).toFixed(2)}
                </td>
                <td className="px-4 py-2 text-right text-slate-600">
                  {(pred.residual ?? 0).toFixed(3)}
                </td>
                <td className="px-4 py-2 text-right text-slate-500">
                  {(pred.ci_lower ?? 0).toFixed(1)}
                </td>
                <td className="px-4 py-2 text-right text-slate-500">
                  {(pred.ci_upper ?? 0).toFixed(1)}
                </td>
                <td className="px-4 py-2 text-slate-500 text-xs">
                  {pred.cache_hit && (
                    <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full">
                      Cache hit
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
