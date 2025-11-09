# Voltcast-AI Frontend — Professional Demo UI

Single-page React application for the Voltcast-AI Load Forecasting system. Built with Vite, TypeScript, and Tailwind CSS.

## Features

### Core Functionality
- **24-Hour Forecast Visualization** - Interactive line chart with hybrid prediction, baseline, and 95% confidence intervals
- **Real-time KPI Dashboard** - Model performance metrics (MAE, RMSE, MAPE, Residual Std)
- **Hour-by-Hour Details** - Click any point to see baseline, residual, and CI breakdown
- **Forecast Table** - Sortable table with all hourly data and CSV export
- **RAG Chat Assistant** - Ask questions about forecasts and model behavior
- **Confidence Scoring** - Visual confidence indicator based on CI width

### Design
- **Mobile-First Responsive** - Works on all screen sizes
- **Tailwind CSS** - Clean, professional styling
- **Accessible** - ARIA labels, keyboard navigation, high contrast
- **Fast** - Vite HMR for instant development updates

## Tech Stack

- **React 18** with TypeScript
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **Recharts** - Chart visualization
- **Axios** - API client
- **Day.js** - Date handling

## Quick Start

### Prerequisites
- Node.js 18+
- Voltcast-AI API running on `http://localhost:8000`

### Installation

```bash
npm install
```

### Development

```bash
npm run dev
```

App runs at **http://localhost:3000**

### Production Build

```bash
npm run build
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── api/
│   │   ├── client.ts       # Axios client configuration
│   │   ├── forecast.ts     # Forecast API calls
│   │   └── chat.ts         # Chat API calls
│   ├── components/
│   │   ├── Header.tsx      # App header with model info
│   │   ├── ForecastForm.tsx    # Timestamp picker and submit
│   │   ├── ForecastChart.tsx   # 24-hour line chart
│   │   ├── KPICards.tsx        # Model metrics cards
│   │   ├── ComponentsBox.tsx   # Selected hour details
│   │   ├── ConfidenceBadge.tsx # Confidence score indicator
│   │   ├── ChatBox.tsx         # RAG chat interface
│   │   ├── ForecastTable.tsx   # Sortable data table
│   │   └── Footer.tsx          # App footer
│   ├── App.tsx             # Main app component
│   ├── main.tsx            # Entry point
│   ├── types.ts            # TypeScript types
│   └── index.css           # Tailwind directives
├── public/                 # Static assets
├── .env                    # Environment variables
├── vite.config.ts          # Vite configuration
├── tailwind.config.js      # Tailwind configuration
├── postcss.config.js       # PostCSS configuration
├── tsconfig.json           # TypeScript configuration
└── package.json            # Dependencies
```

## API Integration

### Endpoints Used

#### 1. Get Model Metadata
```
GET /api/v1/status
Response: {
  models: {
    hourly: {
      name: string,
      performance_metrics: {
        hybrid: { mae, rmse, mape }
      }
    }
  },
  database: { type: string }
}
```

#### 2. Get Forecast
```
POST /api/v1/predict/horizon
Body: { timestamp: string, horizon: number }
Response: {
  timestamp: string,
  predictions: [
    {
      timestamp: string,
      prediction: number,
      confidence_interval: { lower, upper },
      components: { baseline, residual }
    }
  ],
  metadata: {
    mae, rmse, mape, residual_std,
    data_source, cache_hit, model_version
  }
}
```

#### 3. Chat (Optional)
```
POST /api/v1/chat
Body: { query: string, top_k: number }
Response: {
  answer: string,
  sources: string[]
}
```

## Configuration

### Environment Variables

Create a `.env` file:

```bash
VITE_API_URL=http://localhost:8000
```

### Vite Proxy

The Vite config includes a proxy for `/api` requests to avoid CORS issues during development.

## Usage Flow

1. **Page Load** - Header fetches model metadata from `/api/v1/status`
2. **Select Timestamp** - Use datetime picker or preset buttons (Now, Today Midnight, Tomorrow Noon)
3. **Get Forecast** - Click button to fetch 24-hour predictions
4. **View Chart** - Interactive chart with hybrid prediction, baseline, and CI
5. **Click Hour** - Select any point to see detailed breakdown in Components Box
6. **Export Data** - Download CSV with all hourly data
7. **Ask Questions** - Use chat box to query the RAG assistant

## Components

### Header
- Shows app title and subtitle
- Displays model name and health status badges
- Auto-fetches metadata on load

### ForecastForm
- Datetime-local input for timestamp selection
- Horizon input (1-168 hours, default 24)
- Quick preset buttons
- Loading state with spinner
- Converts local time to ISO UTC for API

### ForecastChart
- Recharts ComposedChart with Line and Area
- Hybrid prediction (teal, thick line)
- Baseline (gray, dashed line)
- 95% CI (shaded area)
- Custom tooltip with all values
- Click handler for hour selection

### KPICards
- 3-4 cards showing MAE, RMSE, Residual Std, MAPE
- Color-coded badges
- Responsive grid layout

### ComponentsBox
- Shows selected hour details
- Hybrid prediction (large, teal)
- Baseline with % difference
- Residual with warning if < 0.5 MW
- 95% CI with margin
- Data source and cache status

### ConfidenceBadge
- Calculates confidence from CI width
- Progress bar visualization
- Color-coded label (High/Medium/Low)

### ChatBox
- Message history with user/assistant bubbles
- Input field with send button
- Loading indicator
- Shows sources for answers
- Fallback response if endpoint not available

### ForecastTable
- Sortable columns (click header to sort)
- All hourly data in rows
- CSV export button
- Cache hit indicators

### Footer
- App info and links
- Small, unobtrusive

## Styling

### Color Palette
- **Background:** `bg-slate-50`
- **Cards:** `bg-white` with `shadow-md`
- **Primary (Teal):** `#0ea5a4` (buttons, accents)
- **Text:** `text-slate-800` (primary), `text-slate-500` (muted)
- **Borders:** `border-slate-200`

### Tailwind Classes
- **Card:** `bg-white p-4 rounded-2xl shadow-md`
- **Button:** `bg-teal-500 hover:bg-teal-600 px-4 py-2 rounded-lg text-white font-medium`
- **Input:** `p-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500`

### Responsive Breakpoints
- **Mobile:** `< 768px` - Single column
- **Tablet:** `768px - 1024px` - Stacked layout
- **Desktop:** `> 1024px` - Two-column grid (`lg:grid-cols-[2fr,1fr]`)

## Accessibility

- All buttons have `aria-label` attributes
- Contrast ratio > 4.5:1 for text
- Keyboard navigation supported
- Focus indicators on interactive elements
- Semantic HTML structure

## Performance

### Load Times
- **Initial Load:** 1-2 seconds
- **Metadata Fetch:** 100-200ms
- **Forecast Fetch:** 500ms-1s (24 predictions)
- **Chart Render:** 100-200ms

### Bundle Size
- **Development:** ~5-10 MB (unoptimized)
- **Production:** ~300-500 KB (minified + gzipped)

### Optimizations
- Vite code splitting
- Lazy loading (future enhancement)
- Axios request caching
- Recharts performance mode

## Testing

### Manual Testing Checklist
- [ ] Header loads with model name and status
- [ ] Timestamp picker works
- [ ] Preset buttons set correct times
- [ ] Get Forecast button triggers API call
- [ ] Chart displays with 24 points
- [ ] Clicking chart point updates Components Box
- [ ] KPI cards show correct metrics
- [ ] Confidence badge displays
- [ ] Chat box sends and receives messages
- [ ] Table sorts by columns
- [ ] CSV export downloads file
- [ ] Responsive on mobile/tablet/desktop
- [ ] Error handling shows alerts
- [ ] Loading states display

### Unit Tests (Future)
```bash
npm test
```

## Troubleshooting

### API Connection Issues
**Problem:** "Server error — check logs"

**Solutions:**
1. Ensure API is running: `python run_api.py`
2. Check API URL in `.env` file
3. Verify CORS is enabled in FastAPI
4. Check browser console for errors

### Chart Not Rendering
**Problem:** Chart area is blank

**Solutions:**
1. Check browser console for Recharts errors
2. Verify data format matches expected structure
3. Ensure predictions array has data
4. Check for TypeScript errors

### Tailwind Styles Not Applied
**Problem:** Components look unstyled

**Solutions:**
1. Ensure Tailwind is installed: `npm install -D tailwindcss`
2. Check `tailwind.config.js` content paths
3. Verify `@tailwind` directives in `index.css`
4. Restart dev server

### TypeScript Errors
**Problem:** Type errors in IDE

**Solutions:**
1. Run `npm install` to ensure all types are installed
2. Check `tsconfig.json` configuration
3. Restart TypeScript server in IDE
4. Run `npm run build` to see all errors

## Demo Script (3 Minutes)

### 1. Show Header (15 seconds)
- Point out model name and health status
- Explain hybrid architecture

### 2. Generate Forecast (30 seconds)
- Select timestamp (use preset "Now")
- Click "Get Forecast"
- Show loading state
- Chart appears

### 3. Explain Chart (60 seconds)
- **Teal line:** Hybrid prediction
- **Gray dashed:** Baseline
- **Shaded area:** 95% confidence interval
- Click a point to show details

### 4. Show Components (30 seconds)
- Components Box updates
- Explain baseline vs residual
- Show CI margin

### 5. Show KPIs (15 seconds)
- MAE: 2.016 MW
- RMSE: 3.888 MW
- Residual Std: 3.883 MW

### 6. Export Data (15 seconds)
- Click "Export CSV"
- Show downloaded file

### 7. Chat Demo (15 seconds)
- Ask: "Why is prediction at 14:00 high?"
- Show answer and sources

## Production Deployment

### Build
```bash
npm run build
```

Output: `dist/` directory

### Deploy Options

#### Static Hosting (Vercel, Netlify)
```bash
# Vercel
vercel deploy

# Netlify
netlify deploy --prod
```

#### S3 + CloudFront
```bash
aws s3 sync dist/ s3://your-bucket/
aws cloudfront create-invalidation --distribution-id YOUR_ID --paths "/*"
```

#### Docker
```dockerfile
FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Environment Variables for Production
```bash
VITE_API_URL=https://api.voltcast.example.com
```

Build with production API URL:
```bash
VITE_API_URL=https://api.voltcast.example.com npm run build
```

## Future Enhancements

- [ ] Unit tests with Vitest
- [ ] E2E tests with Playwright
- [ ] Dark mode toggle
- [ ] Multiple forecast comparison
- [ ] Historical forecast archive
- [ ] Real-time updates (WebSocket)
- [ ] User authentication
- [ ] Custom date ranges
- [ ] Export to PDF/PNG
- [ ] Internationalization (i18n)

## License

Same as parent project

## Support

See main project README for contact information.

---

**Status:** Production Ready ✅  
**Version:** 1.0.0  
**Last Updated:** November 9, 2025
