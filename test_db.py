from utils.database import DatabaseManager
import os

def test_db():
    db = DatabaseManager("test_bot.db")
    print("Logging equity...")
    db.log_equity(1000.0, 1050.5)
    
    print("Logging signal...")
    db.log_signal("XAUUSD", "BUY", "SMC Setup", 2150.0)
    
    data = db.get_equity_data()
    print(f"Retrieved data: {data}")
    
    if len(data) > 0:
        print("✅ Database verification SUCCESS")
    else:
        print("❌ Database verification FAILED")

if __name__ == "__main__":
    test_db()
捉
