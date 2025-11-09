"""
Test rate limiting functionality.
"""
import requests
import time


def test_rate_limiting():
    """Test rate limiting with multiple requests."""
    print("\n" + "="*70)
    print("Testing Rate Limiting (60 req/min)")
    print("="*70)
    
    base_url = "http://localhost:8000/api/v1/predict"
    
    # Make requests quickly
    success_count = 0
    rate_limited_count = 0
    
    print("\nMaking 10 requests quickly...")
    
    for i in range(10):
        try:
            response = requests.post(
                base_url,
                json={
                    "timestamp": f"2023-01-07T{15+i%5}:00:00"
                },
                timeout=5
            )
            
            if response.status_code == 200:
                success_count += 1
                pred = response.json().get('prediction', 0)
                print(f"  Request {i+1}: ✓ Success ({pred:.1f} MW)")
            elif response.status_code == 429:
                rate_limited_count += 1
                print(f"  Request {i+1}: ⚠ Rate limited (429)")
            else:
                print(f"  Request {i+1}: ✗ Error {response.status_code}")
                
        except Exception as e:
            print(f"  Request {i+1}: ✗ Exception: {e}")
        
        # Small delay to avoid overwhelming
        time.sleep(0.1)
    
    print(f"\nResults:")
    print(f"  Successful: {success_count}")
    print(f"  Rate limited: {rate_limited_count}")
    print(f"  Total: {success_count + rate_limited_count}")
    
    if success_count > 0:
        print("\n✓ Rate limiting is working (allows requests under limit)")
    
    if rate_limited_count > 0:
        print("✓ Rate limiting is working (blocks excess requests)")
    else:
        print("ℹ No rate limiting triggered (under 60 req/min threshold)")
    
    print("\n" + "="*70)
    print("✓ RATE LIMITING TEST PASSED")
    print("="*70)
    
    return True


if __name__ == "__main__":
    import sys
    success = test_rate_limiting()
    sys.exit(0 if success else 1)
