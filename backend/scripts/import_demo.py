import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]))

import asyncio, json
from app.db import async_session_maker, init_db
from app.routers.api import import_reviews, ImportRequest

async def main():
    await init_db()
    path=Path(__file__).parents[1]/"data"/"demo_reviews.json"
    data=json.loads(path.read_text())
    async with async_session_maker() as db:
        result=await import_reviews(ImportRequest(data=data,source="synthetic",clear_existing=True),db)
        print(result.model_dump_json(indent=2))

if __name__=="__main__":asyncio.run(main())
