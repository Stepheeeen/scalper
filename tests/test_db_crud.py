import asyncio
import logging
from datetime import datetime, timezone
from config.database import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestDBCrud")

async def test_crud():
    logger.info("Initializing database connection...")
    await db.connect()
    
    try:
        # 1. Insert a test log
        test_msg = f"Integration Test Message - {datetime.now(timezone.utc).isoformat()}"
        logger.info(f"Inserting test log: '{test_msg}'")
        
        insert_result = await db.system_logs.insert_one({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "INFO",
            "message": test_msg,
            "test_flag": True
        })
        
        doc_id = insert_result.inserted_id
        logger.info(f"Insert successful. Document ID: {doc_id}")
        
        # 2. Retrieve the inserted log
        logger.info("Retrieving the inserted log...")
        retrieved_doc = await db.system_logs.find_one({"_id": doc_id})
        
        if retrieved_doc:
            logger.info("Retrieval successful!")
            logger.info(f"Retrieved: {retrieved_doc}")
            assert retrieved_doc["message"] == test_msg, "Message mismatch!"
        else:
            raise Exception("Failed to retrieve the inserted log document.")
            
        # 3. Clean up the test log
        logger.info(f"Deleting test document: {doc_id}")
        delete_result = await db.system_logs.delete_one({"_id": doc_id})
        logger.info(f"Deleted documents: {delete_result.deleted_count}")
        
        print("Database CRUD operations and index tests PASSED successfully.")
        
    except Exception as e:
        logger.error(f"Database CRUD Test FAILED: {e}")
        raise e
    finally:
        logger.info("Disconnecting database client...")
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(test_crud())
