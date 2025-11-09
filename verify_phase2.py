"""Quick Phase 2 verification script."""

from api.services.storage import get_storage_service

print("\n" + "="*60)
print("Phase 2 Verification")
print("="*60)

# Check database
storage = get_storage_service()
count = storage.get_row_count()
latest = storage.get_latest_timestamp()

print(f"\n✓ Database Status:")
print(f"  Total rows: {count:,}")
print(f"  Latest timestamp: {latest}")

if count > 0:
    history = storage.get_last_n_hours(168)
    print(f"  Retrieved: {len(history)} hours")
    print(f"  Demand range: {history['demand'].min():.2f} - {history['demand'].max():.2f} MW")
    print(f"\n✓ Phase 2 is READY!")
    print(f"\nNext steps:")
    print(f"  1. Start API: python run_api.py")
    print(f"  2. Test predictions with real DB features")
    print(f"  3. Check metadata in responses")
else:
    print(f"\n✗ Database is empty!")
    print(f"  Run: python scripts/seed_hourly_actuals.py hourly_data(2000-2023).csv")

print("="*60 + "\n")
