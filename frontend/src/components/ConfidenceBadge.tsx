interface ConfidenceBadgeProps {
  confidenceScore?: number;
  ciWidth?: number;
}

export default function ConfidenceBadge({ confidenceScore, ciWidth }: ConfidenceBadgeProps) {
  // Calculate confidence from CI width if score not provided
  let score = confidenceScore;
  if (score === undefined && ciWidth !== undefined) {
    // Smaller CI = higher confidence
    // Normalize: assume CI width of 20 MW = 0.5 confidence
    score = Math.max(0, Math.min(1, 1 - (ciWidth / 40)));
  }

  if (score === undefined) {
    return null;
  }

  const percentage = (score * 100).toFixed(0);
  let color = 'bg-red-100 text-red-700';
  let label = 'Low';

  if (score >= 0.7) {
    color = 'bg-green-100 text-green-700';
    label = 'High';
  } else if (score >= 0.4) {
    color = 'bg-yellow-100 text-yellow-700';
    label = 'Medium';
  }

  return (
    <div className="bg-white p-3 rounded-xl shadow-md">
      <div className="text-sm text-slate-500 mb-2">Confidence Score</div>
      <div className="flex items-center justify-between">
        <div className="text-2xl font-bold text-slate-800">{percentage}%</div>
        <span className={`px-3 py-1 rounded-full text-xs font-medium ${color}`}>
          {label}
        </span>
      </div>
      <div className="mt-2 w-full bg-slate-200 rounded-full h-2">
        <div
          className="bg-teal-500 h-2 rounded-full transition-all duration-300"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
