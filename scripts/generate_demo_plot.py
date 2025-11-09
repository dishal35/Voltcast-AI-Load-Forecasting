"""
Generate comprehensive evaluation plot for demo.
Shows actual vs predicted with confidence intervals.
"""
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Read test predictions
df = pd.read_csv('test_predictions.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Calculate metrics
mae = np.mean(np.abs(df['hybrid_error']))
rmse = np.sqrt(np.mean(df['hybrid_error']**2))
mape = np.mean(np.abs(df['hybrid_error'] / df['actual'])) * 100

# Residual std for CI (from manifest)
residual_std = 3.883
ci_margin = 1.96 * residual_std  # 95% CI

# Create figure
fig, axes = plt.subplots(2, 1, figsize=(14, 10))

# Plot 1: Time series with confidence intervals
ax1 = axes[0]
ax1.plot(df['timestamp'], df['actual'], 'o-', label='Actual', color='black', linewidth=2, markersize=4)
ax1.plot(df['timestamp'], df['hybrid'], 's-', label='Hybrid Prediction', color='#2E86AB', linewidth=1.5, markersize=3)
ax1.plot(df['timestamp'], df['xgboost'], '^-', label='XGBoost Baseline', color='#A23B72', linewidth=1, markersize=3, alpha=0.7)

# Add confidence interval
ax1.fill_between(df['timestamp'], 
                  df['hybrid'] - ci_margin, 
                  df['hybrid'] + ci_margin,
                  alpha=0.2, color='#2E86AB', label=f'95% CI (±{ci_margin:.2f} MW)')

ax1.set_xlabel('Timestamp', fontsize=11)
ax1.set_ylabel('Demand (MW)', fontsize=11)
ax1.set_title('Voltcast-AI: Actual vs Predicted Electricity Demand', fontsize=14, fontweight='bold')
ax1.legend(loc='best', fontsize=9)
ax1.grid(True, alpha=0.3)
ax1.tick_params(axis='x', rotation=45)

# Add metrics text box
textstr = f'MAE: {mae:.3f} MW\nRMSE: {rmse:.3f} MW\nMAPE: {mape:.3f}%'
props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
ax1.text(0.02, 0.98, textstr, transform=ax1.transAxes, fontsize=10,
         verticalalignment='top', bbox=props)

# Plot 2: Error distribution
ax2 = axes[1]
ax2.hist(df['hybrid_error'], bins=30, color='#2E86AB', alpha=0.7, edgecolor='black')
ax2.axvline(0, color='red', linestyle='--', linewidth=2, label='Zero Error')
ax2.axvline(df['hybrid_error'].mean(), color='orange', linestyle='--', linewidth=2, 
            label=f'Mean Error: {df["hybrid_error"].mean():.3f} MW')
ax2.set_xlabel('Prediction Error (MW)', fontsize=11)
ax2.set_ylabel('Frequency', fontsize=11)
ax2.set_title('Hybrid Model Error Distribution', fontsize=12, fontweight='bold')
ax2.legend(loc='best', fontsize=9)
ax2.grid(True, alpha=0.3, axis='y')

plt.tight_layout()

# Save plot
output_dir = Path('artifacts/plots')
output_dir.mkdir(parents=True, exist_ok=True)
output_path = output_dir / 'comprehensive_evaluation.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight')
print(f"✓ Plot saved to: {output_path}")
print(f"  MAE: {mae:.3f} MW")
print(f"  RMSE: {rmse:.3f} MW")
print(f"  MAPE: {mape:.3f}%")
