from motor.motor_asyncio import AsyncIOMotorClient
from config.settings import settings

class Database:
    def __init__(self):
        self.client = None
        self.db = None
        self.trades = None
        self.daily_analytics = None
        self.system_logs = None

    async def connect(self):
        """Connects to the MongoDB server."""
        self.client = AsyncIOMotorClient(
            settings.mongodb_uri,
            tlsAllowInvalidCertificates=True
        )
        self.db = self.client[settings.db_name]
        
        self.trades = self.db["trades"]
        self.daily_analytics = self.db["daily_analytics"]
        self.system_logs = self.db["system_logs"]
        
        # Ensure indexes (e.g., fast lookups by day for trade counts)
        await self.trades.create_index([("date", 1)])
        await self.system_logs.create_index([("timestamp", -1)])
        
    async def disconnect(self):
        """Closes the connection to the MongoDB server."""
        if self.client:
            self.client.close()

db = Database()
