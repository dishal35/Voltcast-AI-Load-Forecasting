import { useEffect, useState } from 'react';
import { getModelMetadata, ModelMetadata } from '../api/forecast';

export default function Header() {
  const [metadata, setMetadata] = useState<ModelMetadata | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchMetadata = async () => {
      try {
        const data = await getModelMetadata();
        setMetadata(data);
      } catch (error) {
        console.error('Failed to fetch metadata:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchMetadata();
  }, []);

  return (
    <header className="flex items-center justify-between p-4 bg-white shadow-sm">
      <div>
        <h1 className="text-xl font-semibold text-slate-800">
          ⚡ Voltcast-AI — 24hr Load Forecast (Demo)
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Hybrid prediction = XGBoost baseline + Transformer residual
        </p>
      </div>
      <div className="flex gap-2">
        {loading ? (
          <div className="animate-pulse bg-slate-200 h-6 w-32 rounded"></div>
        ) : (
          <>
            <span className="px-3 py-1 bg-teal-100 text-teal-700 text-xs rounded-full font-medium">
              Model: {metadata?.models?.hourly?.name || 'hybrid_transformer_xgboost'}
            </span>
            <span className="px-3 py-1 bg-green-100 text-green-700 text-xs rounded-full font-medium">
              Status: Healthy
            </span>
          </>
        )}
      </div>
    </header>
  );
}
