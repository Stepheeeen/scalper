from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from config.database import db
import os

app = FastAPI(title="XAUUSD System Dashboard")

# Setup templates directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@app.on_event("startup")
async def startup_db_client():
    await db.connect()

@app.on_event("shutdown")
async def shutdown_db_client():
    await db.disconnect()

@app.get("/")
async def read_root(request: Request):
    """Serve the main dashboard page."""
    # Fetch recent trades
    trades_cursor = db.trades.find().sort("date", -1).limit(10) if db.trades is not None else []
    recent_trades = await trades_cursor.to_list(length=10) if trades_cursor else []
    
    # Fetch recent logs
    logs_cursor = db.system_logs.find().sort("timestamp", -1).limit(20) if db.system_logs is not None else []
    recent_logs = await logs_cursor.to_list(length=20) if logs_cursor else []
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "trades": recent_trades,
        "logs": recent_logs
    })

@app.get("/api/stats")
async def get_stats():
    """Returns analytics stats as JSON."""
    if db.daily_analytics is None:
        return {"error": "DB not connected"}
        
    stats_cursor = db.daily_analytics.find().sort("date", -1).limit(30)
    stats = await stats_cursor.to_list(length=30)
    
    # Simple serialization helper
    for s in stats:
        s['_id'] = str(s['_id'])
        
    return {"stats": stats}
