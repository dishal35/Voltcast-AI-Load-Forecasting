export default function Footer() {
  return (
    <footer className="mt-8 py-4 text-center text-sm text-slate-500 border-t border-slate-200">
      <p>
        Voltcast-AI Load Forecasting System • Phase 3 Demo •{' '}
        <a
          href="https://github.com/yourusername/voltcast-ai"
          className="text-teal-600 hover:text-teal-700 underline"
          target="_blank"
          rel="noopener noreferrer"
        >
          Documentation
        </a>
      </p>
      <p className="mt-1 text-xs">
        Hybrid Transformer-XGBoost Model • 210k+ Historical Records • Real-time Predictions
      </p>
    </footer>
  );
}
