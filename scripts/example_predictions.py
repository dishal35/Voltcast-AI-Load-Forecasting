"""
Example: Using Hybrid Predictor for Load Forecasting

This script demonstrates both prediction types:
1. 24-hour day-ahead predictions
2. 7-day daily mean predictions
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from api.services.model_loader import ModelLoader
from api.services.hybrid_predictor import HybridPredictor
import json


def example_24h_prediction():
    """Example: Predict next 24 hours."""
    print("=" * 80)
    print("EXAMPLE 1: 24-Hour Day-Ahead Prediction")
    print("=" * 80)
    
    # Initialize
    model_loader = ModelLoader()
    model_loader.load_all()
    predictor = HybridPredictor(model_loader, use_db=False)
    
    # Predict 24 hours starting from 2024-01-01 23:00:00
    result = predictor.predict_24h_from_csv(
        csv_path='scripts/master_db.csv',
        start_timestamp='2024-01-01 23:00:00',
        return_metrics=True
    )
    
    # Display results
    print(f"\nPrediction Start: {result['start_timestamp']}")
    print(f"Number of Hours: {len(result['predictions'])}")
    
    print(f"\n{'Hour':<6} {'Timestamp':<20} {'Predicted':<12} {'Actual':<12} {'Error':<10}")
    print("-" * 70)
    
    for i in range(min(10, len(result['predictions']))):  # Show first 10 hours
        ts = result['timestamps'][i].split('T')[1][:5]  # Extract HH:MM
        pred = result['predictions'][i]
        actual = result['actuals'][i]
        error = pred - actual
        print(f"{i:<6} {ts:<20} {pred:<12.2f} {actual:<12.2f} {error:<10.2f}")
    
    if len(result['predictions']) > 10:
        print("... (showing first 10 hours)")
    
    # Display metrics
    print(f"\n{'Performance Metrics':-^70}")
    print(f"\nHybrid Model (LGBM + Transformer):")
    print(f"  MAE:  {result['metrics']['hybrid']['mae']:>8.2f} MW")
    print(f"  MAPE: {result['metrics']['hybrid']['mape']:>8.4f} %")
    print(f"  RMSE: {result['metrics']['hybrid']['rmse']:>8.2f} MW")
    
    print(f"\nLGBM Baseline Only:")
    print(f"  MAE:  {result['metrics']['lgbm_baseline']['mae']:>8.2f} MW")
    print(f"  MAPE: {result['metrics']['lgbm_baseline']['mape']:>8.4f} %")
    print(f"  RMSE: {result['metrics']['lgbm_baseline']['rmse']:>8.2f} MW")
    
    improvement = ((result['metrics']['lgbm_baseline']['mape'] - 
                   result['metrics']['hybrid']['mape']) / 
                   result['metrics']['lgbm_baseline']['mape'] * 100)
    print(f"\nImprovement: {improvement:.2f}% reduction in MAPE")
    
    return result


def example_7day_prediction():
    """Example: Predict daily means for next 7 days."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: 7-Day Daily Mean Prediction")
    print("=" * 80)
    
    # Initialize
    model_loader = ModelLoader()
    model_loader.load_all()
    predictor = HybridPredictor(model_loader, use_db=False)
    
    # Predict 7 days starting from 2024-01-01 23:00:00
    result = predictor.predict_7day_daily_means_from_csv(
        csv_path='scripts/master_db.csv',
        start_timestamp='2024-01-01 23:00:00',
        return_metrics=True
    )
    
    # Display results
    print(f"\nPrediction Start: {result['start_timestamp']}")
    print(f"Number of Days: {len(result['daily_mean_predictions'])}")
    
    print(f"\n{'Date':<12} {'Predicted':<12} {'Actual':<12} {'Error':<10} {'Error %':<10}")
    print("-" * 66)
    
    for i in range(len(result['daily_dates'])):
        date = result['daily_dates'][i]
        pred = result['daily_mean_predictions'][i]
        actual = result['daily_mean_actuals'][i]
        error = pred - actual
        error_pct = (error / actual) * 100
        print(f"{date:<12} {pred:<12.2f} {actual:<12.2f} {error:<10.2f} {error_pct:<10.2f}")
    
    # Display metrics
    print(f"\n{'Performance Metrics':-^66}")
    print(f"\nHybrid Model (LGBM + Transformer):")
    print(f"  MAE:  {result['metrics']['hybrid']['mae']:>8.2f} MW")
    print(f"  MAPE: {result['metrics']['hybrid']['mape']:>8.4f} %")
    print(f"  RMSE: {result['metrics']['hybrid']['rmse']:>8.2f} MW")
    
    print(f"\nLGBM Baseline Only:")
    print(f"  MAE:  {result['metrics']['lgbm_baseline']['mae']:>8.2f} MW")
    print(f"  MAPE: {result['metrics']['lgbm_baseline']['mape']:>8.4f} %")
    print(f"  RMSE: {result['metrics']['lgbm_baseline']['rmse']:>8.2f} MW")
    
    improvement = ((result['metrics']['lgbm_baseline']['mape'] - 
                   result['metrics']['hybrid']['mape']) / 
                   result['metrics']['lgbm_baseline']['mape'] * 100)
    print(f"\nImprovement: {improvement:.2f}% reduction in MAPE")
    
    return result


def example_2025_prediction():
    """Example: Predict on 2025 data."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: 2025 Data Prediction")
    print("=" * 80)
    
    # Check if 2025 data exists
    if not os.path.exists('scripts/2025_master_db.csv'):
        print("\n2025 dataset not found at scripts/2025_master_db.csv")
        print("Skipping 2025 example.")
        return
    
    # Initialize
    model_loader = ModelLoader()
    model_loader.load_all()
    predictor = HybridPredictor(model_loader, use_db=False)
    
    # Predict 24 hours
    try:
        result = predictor.predict_24h_from_csv(
            csv_path='scripts/2025_master_db.csv',
            start_timestamp='2025-01-08 00:00:00',
            return_metrics=True
        )
        
        print(f"\n24-Hour Prediction on 2025 Data:")
        print(f"  Start: {result['start_timestamp']}")
        print(f"  Hybrid MAPE: {result['metrics']['hybrid']['mape']:.4f}%")
        print(f"  Hybrid MAE:  {result['metrics']['hybrid']['mae']:.2f} MW")
        print(f"  Hybrid RMSE: {result['metrics']['hybrid']['rmse']:.2f} MW")
        
        # Show first 5 predictions
        print(f"\n{'Hour':<6} {'Predicted':<12} {'Actual':<12}")
        print("-" * 36)
        for i in range(5):
            print(f"{i:<6} {result['predictions'][i]:<12.2f} {result['actuals'][i]:<12.2f}")
        
    except Exception as e:
        print(f"\nError predicting 2025 data: {e}")


def save_predictions_to_json():
    """Example: Save predictions to JSON file."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Save Predictions to JSON")
    print("=" * 80)
    
    # Initialize
    model_loader = ModelLoader()
    model_loader.load_all()
    predictor = HybridPredictor(model_loader, use_db=False)
    
    # Make predictions
    result_24h = predictor.predict_24h_from_csv(
        csv_path='scripts/master_db.csv',
        start_timestamp='2024-01-01 23:00:00',
        return_metrics=True
    )
    
    result_7d = predictor.predict_7day_daily_means_from_csv(
        csv_path='scripts/master_db.csv',
        start_timestamp='2024-01-01 23:00:00',
        return_metrics=True
    )
    
    # Combine results
    output = {
        '24h_prediction': result_24h,
        '7day_prediction': result_7d
    }
    
    # Save to JSON
    output_file = 'predictions_output.json'
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nPredictions saved to: {output_file}")
    print(f"File size: {os.path.getsize(output_file) / 1024:.2f} KB")


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("HYBRID PREDICTOR EXAMPLES")
    print("Demonstrating LGBM + Transformer Residual Model")
    print("=" * 80)
    
    # Run examples
    example_24h_prediction()
    example_7day_prediction()
    example_2025_prediction()
    save_predictions_to_json()
    
    print("\n" + "=" * 80)
    print("EXAMPLES COMPLETE")
    print("=" * 80)
    print("\nFor more information, see HYBRID_PREDICTOR_GUIDE.md")
