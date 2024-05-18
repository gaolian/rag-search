import os
import asyncio
from dotenv import load_dotenv
from handlers.rag_search import rag_search, RagSearchReq

load_dotenv()

apiKey = os.getenv("AUTH_API_KEY")
authorization = "Bearer %s" % apiKey

if __name__ == "__main__":
    tasks = []
    for i in range(1):
        req = RagSearchReq(
            query='第%d代iPhone发布时间' % (i + 1),  # str
            locale='',  # Optional[str]
            search_n=10, # Optional[int]
            search_provider='google',  # Optional[str]
            is_reranking=True,  # Optional[bool]
            is_detail=True,  # Optional[bool]
            detail_top_k=6,   # Optional[int]
            detail_min_score=0.70,  # Optional[float]
            is_filter=True,  # Optional[bool]
            filter_min_score=0.80,  # Optional[float]
            filter_top_k=6  # Optional[int]
        )
        task = rag_search(req, authorization)
        tasks.append(task)

    #async def gather_tasks(tasks):
    #    return await asyncio.gather(*tasks)

    #results = asyncio.run(gather_tasks(tasks))

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    resps = loop.run_until_complete(asyncio.gather(*tasks))

    print('resps: %s' % resps)
