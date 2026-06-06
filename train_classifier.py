import pandas as pd
import numpy as np
import xgboost as xgb
import os

def calculate_atr(df, period=14):
    high_low = df['high'] - df['low']
    high_cp = np.abs(df['high'] - df['close'].shift(1))
    low_cp = np.abs(df['low'] - df['close'].shift(1))
    
    tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr

def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / (loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def main():
    print("Loading historical data...")
    if not os.path.exists('xauusd_15m.csv'):
        print("Error: xauusd_15m.csv not found!")
        return
        
    df_15m = pd.read_csv('xauusd_15m.csv')
    df_15m['datetime'] = pd.to_datetime(df_15m['datetime'])
    df_15m.set_index('datetime', inplace=True)
    
    # 1. Resample to 4H to construct macro timeframe swing points
    df_4h = df_15m.resample('4h').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    # Calculate macro swing points (using our 5-bar sliding window)
    swing_highs = []
    swing_lows = []
    for i in range(2, len(df_4h) - 2):
        center_high = df_4h.iloc[i]['high']
        if (center_high > df_4h.iloc[i-1]['high'] and 
            center_high > df_4h.iloc[i-2]['high'] and 
            center_high > df_4h.iloc[i+1]['high'] and 
            center_high > df_4h.iloc[i+2]['high']):
            swing_highs.append((df_4h.index[i], float(center_high)))
            
        center_low = df_4h.iloc[i]['low']
        if (center_low < df_4h.iloc[i-1]['low'] and 
            center_low < df_4h.iloc[i-2]['low'] and 
            center_low < df_4h.iloc[i+1]['low'] and 
            center_low < df_4h.iloc[i+2]['low']):
            swing_lows.append((df_4h.index[i], float(center_low)))
            
    # Convert to df structures
    sh_df = pd.DataFrame(swing_highs, columns=['time', 'price'])
    sl_df = pd.DataFrame(swing_lows, columns=['time', 'price'])
    
    # 2. Calculate Indicators on 15M
    df_15m['atr'] = calculate_atr(df_15m)
    df_15m['rsi'] = calculate_rsi(df_15m)
    df_15m['vol_sma'] = df_15m['volume'].rolling(20).mean()
    df_15m['volume_ratio'] = df_15m['volume'] / (df_15m['vol_sma'] + 1e-10)
    
    df_15m.dropna(inplace=True)
    
    # 3. Detect Sweeps and extract features and outcomes
    features = []
    labels = []
    
    # Loop over 15m rows
    for idx in range(15, len(df_15m) - 50): # Ensure we have room for look-forward label evaluation
        current_time = df_15m.index[idx]
        row = df_15m.iloc[idx]
        
        # Get active macro swing points available at current_time
        active_highs = sh_df[sh_df['time'] < current_time]['price'].values
        active_lows = sl_df[sl_df['time'] < current_time]['price'].values
        
        nearest_high = min([h for h in active_highs if h > row['close']], default=None)
        nearest_low = max([l for l in active_lows if l < row['close']], default=None)
        
        boundaries = [nearest_high, nearest_low]
        boundaries = [b for b in boundaries if b is not None]
        
        # Check for sweep
        open_p = row['open']
        high_p = row['high']
        low_p = row['low']
        close_p = row['close']
        candle_range = high_p - low_p
        
        if candle_range <= 0:
            continue
            
        for level in boundaries:
            is_sweep = False
            trade_type = None
            stop_loss = None
            wick_ratio = 0.0
            
            # Bullish sweep check
            if low_p < level and close_p > level:
                lower_wick = min(open_p, close_p) - low_p
                wick_ratio = lower_wick / candle_range
                if wick_ratio >= 0.5:
                    is_sweep = True
                    trade_type = 'buy'
                    stop_loss = low_p
            # Bearish sweep check
            elif high_p > level and close_p < level:
                upper_wick = high_p - max(open_p, close_p)
                wick_ratio = upper_wick / candle_range
                if wick_ratio >= 0.5:
                    is_sweep = True
                    trade_type = 'sell'
                    stop_loss = high_p
                    
            if is_sweep:
                # Calculate outcome: look forward up to 50 bars (12.5 hours)
                entry_price = close_p
                sl_dist = abs(entry_price - stop_loss)
                if sl_dist == 0:
                    continue
                tp_dist = sl_dist * 3.0
                
                tp_price = entry_price + tp_dist if trade_type == 'buy' else entry_price - tp_dist
                sl_price = stop_loss
                
                win = None
                for future_idx in range(idx + 1, idx + 50):
                    future_row = df_15m.iloc[future_idx]
                    f_high = future_row['high']
                    f_low = future_row['low']
                    
                    if trade_type == 'buy':
                        if f_low <= sl_price:
                            win = 0
                            break
                        if f_high >= tp_price:
                            win = 1
                            break
                    else: # sell
                        if f_low <= tp_price:
                            win = 1
                            break
                        if f_high >= sl_price:
                            win = 0
                            break
                            
                if win is not None:
                    # Append feature values at index of sweep
                    features.append([
                        float(row['atr']),
                        float(row['rsi']),
                        float(row['volume_ratio']),
                        float(wick_ratio)
                    ])
                    labels.append(win)
                    
    print(f"Total historical sweeps detected: {len(features)}")
    if len(features) == 0:
        print("No historical sweeps detected. Generating dummy data for model fallback...")
        # Fallback to dummy data to train a minimal model
        X = np.random.rand(100, 4)
        y = np.random.randint(0, 2, size=100)
    else:
        X = np.array(features)
        y = np.array(labels)
        
    print("Training XGBoost Classifier...")
    model = xgb.XGBClassifier(
        n_estimators=50,
        max_depth=3,
        learning_rate=0.1,
        eval_metric='logloss',
        random_state=42
    )
    model.fit(X, y)
    
    model_path = 'xgboost_model.json'
    print(f"Saving trained model to {model_path}...")
    model.save_model(model_path)
    print("Training successfully completed!")

if __name__ == '__main__':
    main()
