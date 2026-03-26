import pandas as pd
import numpy as np

def generate_sample_data(filename, days=30):
    periods = 1440 * days
    timestamps = pd.date_range(end=pd.Timestamp.now(), periods=periods, freq='min')
    
    # Realistic Gold random walk
    np.random.seed(42)
    close = 2000.0 + np.cumsum(np.random.randn(periods) * 0.2)
    df = pd.DataFrame({
        'datetime': timestamps,
        'open': close - np.random.randn(periods) * 0.1,
        'high': close + np.random.rand(periods) * 0.5,
        'low': close - np.random.rand(periods) * 0.5,
        'close': close,
        'volume': np.random.randint(100, 1000, size=periods)
    })
    
    # Save 1m
    df.to_csv(filename, index=False)
    print(f"Generated {filename} ({len(df)} rows)")

    # Generate 5m and 15m resampled versions
    df.set_index('datetime', inplace=True)
    for tf in ['5min', '15min']:
        resampled = df.resample(tf).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        # Create corresponding filename (e.g., xauusd_5m.csv)
        tf_name = tf.replace('min', 'm')
        new_filename = filename.replace('1m', tf_name)
        resampled.to_csv(new_filename, index=True)
        print(f"Generated {new_filename} ({len(resampled)} rows)")

if __name__ == "__main__":
    generate_sample_data("xauusd_1m.csv", days=30)
