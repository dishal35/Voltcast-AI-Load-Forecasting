"""
Test API Predictions
Verify that API returns varying predictions.
"""
import requests
import json
from datetime import datetime

API_BASE = "http://localhost:8000/api/v1"


def test_horizon_predictions():
    """Test 24-hour horizon predictions."""
    print("=" * 80)
    print("TEST: 24-Hour Horizon Predictions via API")
    print("=" * 80)
    
    url = f"{API_BASE}/predict/horizon"
    payload = {
        "timestamp": "2024-01-01T23:00:00",
        "horizon": 24
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        
        predictions = data['predictions']
        
        print(f"\nReceived {len(predictions)} predictions")
        print(f"\nFirst 5 predictions:")
        for i in range(min(5, len(predictions))):
            print(f"  Hour {i}: {predictions[i]:.2f} MW")
        
        print(f"\nLast 5 predictions:")
        for i in range(max(0, len(predictions) - 5), len(predictions)):
            print(f"  Hour {i}: {predictions[i]:.2f} MW")
        
        # Check variation
        unique_preds = len(set([round(p, 2) for p in predictions]))
        print(f"\nUnique predictions: {unique_preds}/{len(predictions)}")
        
        if unique_preds == len(predictions):
            print("✅ All predictions are different")
        elif unique_preds > len(predictions) * 0.8:
            print("✅ Most predictions are different")
        else:
            print("⚠️  Many predictions are the same")
        
        # Statistics
        import numpy as np
        preds_arr = np.array(predictions)
        print(f"\nStatistics:")
        print(f"  Min:  {preds_arr.min():.2f} MW")
        print(f"  Max:  {preds_arr.max():.2f} MW")
        print(f"  Mean: {preds_arr.mean():.2f} MW")
        print(f"  Std:  {preds_arr.std():.2f} MW")
        print(f"  Range: {preds_arr.max() - preds_arr.min():.2f} MW")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ API not running. Start with: python run_api.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")


def test_weekly_predictions():
    """Test 7-day weekly predictions."""
    print("\n" + "=" * 80)
    print("TEST: 7-Day Weekly Predictions via API")
    print("=" * 80)
    
    url = f"{API_BASE}/predict/weekly"
    payload = {
        "start_date": "2024-01-01T00:00:00"
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        
        daily_forecasts = data['daily_forecasts']
        
        print(f"\nReceived {len(daily_forecasts)} daily forecasts")
        print(f"\n{'Date':<12} {'Avg Demand':<12} {'Peak Demand':<12} {'Peak Hour':<10}")
        print("-" * 56)
        
        for day in daily_forecasts:
            print(f"{day['date']:<12} {day['avg_demand_mw']:<12.2f} "
                  f"{day['peak_demand_mw']:<12.2f} {day.get('peak_hour', 'N/A'):<10}")
        
        # Check variation
        avg_demands = [d['avg_demand_mw'] for d in daily_forecasts]
        unique_avgs = len(set([round(a, 2) for a in avg_demands]))
        print(f"\nUnique daily averages: {unique_avgs}/{len(daily_forecasts)}")
        
        if unique_avgs == len(daily_forecasts):
            print("✅ All daily predictions are different")
        else:
            print("⚠️  Some daily predictions are the same")
        
        # Statistics
        import numpy as np
        avgs_arr = np.array(avg_demands)
        print(f"\nStatistics:")
        print(f"  Min:  {avgs_arr.min():.2f} MW")
        print(f"  Max:  {avgs_arr.max():.2f} MW")
        print(f"  Mean: {avgs_arr.mean():.2f} MW")
        print(f"  Std:  {avgs_arr.std():.2f} MW")
        print(f"  Range: {avgs_arr.max() - avgs_arr.min():.2f} MW")
        
        # Weekly summary
        summary = data['weekly_summary']
        print(f"\nWeekly Summary:")
        print(f"  Average: {summary['avg_demand_mw']:.2f} MW")
        print(f"  Peak Day: {summary['peak_day']}")
        print(f"  Peak Demand: {summary['peak_demand_mw']:.2f} MW")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ API not running. Start with: python run_api.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("API PREDICTION VARIATION TEST")
    print("=" * 80)
    print("\nMake sure API is running: python run_api.py")
    print("Then run this script to verify predictions vary correctly")
    
    test_horizon_predictions()
    test_weekly_predictions()
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
