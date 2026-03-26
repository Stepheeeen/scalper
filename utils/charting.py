import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import os
from .logger import logger

def generate_equity_chart(equity_data: list, output_path: str = "equity_curve.png"):
    """
    Generates a professional equity curve chart from history data.
    
    Args:
        equity_data (list): List of dicts with 'timestamp' and 'equity'.
        output_path (str): File path to save the chart.
    """
    if not equity_data:
        logger.warning("No equity data available to generate chart.")
        return None

    try:
        # Prepare data
        times = [datetime.fromisoformat(d['timestamp']) for d in equity_data]
        equities = [d['equity'] for d in equity_data]

        # Create plot
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(10, 6), dpi=100)
        
        # Plot styling
        ax.plot(times, equities, color='#00d1b2', linewidth=2, label='Account Equity')
        ax.fill_between(times, equities, min(equities), color='#00d1b2', alpha=0.1)
        
        # Grid and Labels
        ax.set_title("XAUUSD Scalp Bot - Equity Curve", fontsize=14, pad=20, color='white')
        ax.set_xlabel("Time", fontsize=10, color='#888888')
        ax.set_ylabel("Equity (USD)", fontsize=10, color='#888888')
        ax.grid(True, linestyle='--', alpha=0.2)
        
        # Date formatting on X-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        fig.autofmt_xdate()

        # Legend
        ax.legend(loc='upper left', frameon=False)

        # Annotations (Starting/Final Equity)
        start_val = equities[0]
        end_val = equities[-1]
        profit = end_val - start_val
        ax.text(0.02, 0.95, f"Start: ${start_val:.2f}\nCurrent: ${end_val:.2f}\nProfit: ${profit:+.2f}", 
                transform=ax.transAxes, verticalalignment='top', fontsize=10, 
                bbox=dict(boxstyle='round', facecolor='black', alpha=0.5))

        plt.savefig(output_path, bbox_inches='tight', transparent=False)
        plt.close()
        
        return output_path
    
    except Exception as e:
        logger.error(f"Failed to generate equity chart: {e}")
        return None
