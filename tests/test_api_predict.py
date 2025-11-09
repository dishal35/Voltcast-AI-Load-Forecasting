"""
Test API prediction endpoints.
Phase 3: Tests for enhanced endpoints with caching and rate limiting.
"""
try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False

import requests
from datetime import datetime
import time


class TestPredictionAPI:
    """Test prediction API endpoints."""
    
    BASE_URL = "http://localhost:8000/api/v1"
    
    def test_predict_endpoint_basic(self):
        """Test basic prediction endpoint."""
        response = requests.post(
            f"{self.BASE_URL}/predict",
            json={
                "timestamp": "2023-01-07T15:00:00",
                "temperature": 25.5,
                "solar_generation": 150.0,
                "humidity": 65.0,
                "cloud_cover": 30.0
            },
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "prediction" in data
        assert "components" in data
        assert "confidence_interval" in data
        assert "metadata" in data
        
        # Check components
        components = data["components"]
        assert "baseline" in components
        assert "residual" in components
        
        # Check confidence interval
        ci = data["confidence_interval"]
        assert "lower" in ci
        assert "upper" in ci
        assert ci["lower"] < ci["upper"]
        
        # Check metadata
        metadata = data["metadata"]
        assert "data_source" in metadata
        assert "cache_hit" in metadata
        
        # Check values are reasonable
        assert 0 < data["prediction"] < 1000  # MW
        assert isinstance(metadata["cache_hit"], bool)
    
    def test_predict_endpoint_auto_weather(self):
        """Test prediction with auto weather fetch."""
        response = requests.post(
            f"{self.BASE_URL}/predict",
            json={"timestamp": "2023-01-07T16:00:00"},
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "prediction" in data
        assert "metadata" in data
        
        # Should have weather source info
        metadata = data["metadata"]
        assert "weather_source" in metadata
    
    def test_predict_horizon_endpoint(self):
        """Test horizon prediction endpoint."""
        response = requests.post(
            f"{self.BASE_URL}/predict/horizon",
            json={
                "timestamp": "2023-01-07T15:00:00",
                "horizon": 12
            },
            timeout=15
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "predictions" in data
        assert "confidence_intervals" in data
        assert "metadata" in data
        
        predictions = data["predictions"]
        assert len(predictions) == 12
        
        # Check each prediction is a float
        for pred in predictions:
            assert isinstance(pred, (int, float))
            assert 0 < pred < 1000
        
        # Check confidence intervals
        cis = data["confidence_intervals"]
        assert len(cis) == 12
        for ci in cis:
            assert "lower" in ci
            assert "upper" in ci
            assert ci["lower"] < ci["upper"]
    
    def test_different_timestamps_different_predictions(self):
        """Test that different timestamps produce different predictions."""
        # First prediction
        response1 = requests.post(
            f"{self.BASE_URL}/predict",
            json={"timestamp": "2023-01-07T10:00:00"},
            timeout=10
        )
        
        # Second prediction (different time)
        response2 = requests.post(
            f"{self.BASE_URL}/predict",
            json={"timestamp": "2023-01-07T18:00:00"},
            timeout=10
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        pred1 = response1.json()["prediction"]
        pred2 = response2.json()["prediction"]
        
        # Predictions should be different
        assert abs(pred1 - pred2) > 1.0  # At least 1 MW difference
    
    def test_rate_limiting_allows_normal_requests(self):
        """Test that rate limiting allows normal request patterns."""
        # Make a few requests (well under limit)
        for i in range(5):
            response = requests.post(
                f"{self.BASE_URL}/predict",
                json={"timestamp": f"2023-01-07T{10+i}:00:00"},
                timeout=10
            )
            
            assert response.status_code == 200
            time.sleep(0.1)  # Small delay
    
    def test_invalid_timestamp_format(self):
        """Test handling of invalid timestamp format."""
        response = requests.post(
            f"{self.BASE_URL}/predict",
            json={
                "timestamp": "invalid-timestamp",
                "temperature": 25.0
            },
            timeout=10
        )
        
        # Should return error (400 or 422)
        assert response.status_code in [400, 422]
    
    def test_missing_required_fields(self):
        """Test handling of missing required fields."""
        response = requests.post(
            f"{self.BASE_URL}/predict",
            json={},  # Empty request
            timeout=10
        )
        
        # Should return validation error
        assert response.status_code in [400, 422]


def test_api_endpoints_standalone():
    """Standalone test function that can be run without pytest."""
    print("\n" + "="*70)
    print("Testing API Prediction Endpoints")
    print("="*70)
    
    base_url = "http://localhost:8000/api/v1"
    
    try:
        # Test 1: Basic prediction
        print("\n1. Testing basic prediction...")
        response = requests.post(
            f"{base_url}/predict",
            json={
                "timestamp": "2023-01-07T15:00:00",
                "temperature": 25.5,
                "solar_generation": 150.0
            },
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        print(f"   ✓ Status: {response.status_code}")
        print(f"   ✓ Prediction: {data['prediction']:.2f} MW")
        print(f"   ✓ Data source: {data['metadata']['data_source']}")
        
        # Test 2: Horizon prediction
        print("\n2. Testing horizon prediction...")
        response = requests.post(
            f"{base_url}/predict/horizon",
            json={
                "timestamp": "2023-01-07T15:00:00",
                "horizon": 6
            },
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        print(f"   ✓ Status: {response.status_code}")
        print(f"   ✓ Predictions: {len(data['predictions'])} hours")
        
        # Test 3: Rate limiting (normal usage)
        print("\n3. Testing rate limiting (normal usage)...")
        for i in range(3):
            response = requests.post(
                f"{base_url}/predict",
                json={"timestamp": f"2023-01-07T{16+i}:00:00"},
                timeout=10
            )
            assert response.status_code == 200
        print("   ✓ Normal requests allowed")
        
        print("\n" + "="*70)
        print("✓ ALL API TESTS PASSED")
        print("="*70)
        return True
        
    except requests.exceptions.ConnectionError:
        print("\n✗ ERROR: Could not connect to API")
        print("   Make sure API is running: python run_api.py")
        return False
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    success = test_api_endpoints_standalone()
    sys.exit(0 if success else 1)
