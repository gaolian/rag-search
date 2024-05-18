import os
import time
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Header
from services.search.serper import get_search_results
from services.document.store import store_results
from services.document.query import query_results
from services.web import batch_fetch_urls
from utils.resp import resp_err, resp_data


rag_router = APIRouter()


class RagSearchReq(BaseModel):
    query: str
    locale: Optional[str] = ''
    search_n: Optional[int] = 10
    search_provider: Optional[str] = 'google'
    is_reranking: Optional[bool] = False
    is_detail: Optional[bool] = False
    detail_top_k: Optional[int] = 6
    detail_min_score: Optional[float] = 0.70
    is_filter: Optional[bool] = False
    filter_min_score: Optional[float] = 0.80
    filter_top_k: Optional[int] = 6


@rag_router.post("/rag-search")
async def rag_search(req: RagSearchReq, authorization: str = Header(None)):
    authApiKey = os.getenv("AUTH_API_KEY")
    apiKey = ""
    if authorization:
        apiKey = authorization.replace("Bearer ", "")
    if apiKey != authApiKey:
        return resp_err("Access Denied")

    if req.query == "":
        return resp_err("invalid params")

    try:
        time_records = []
        time_records.append(('time_start', time.perf_counter()))

        search_results = []
        # 1. get search results
        try:
            search_results = search(req.query, req.search_n, req.locale)
        except Exception as e:
            return resp_err(f"get search results failed: {e}")
        time_records.append(('time_search', time.perf_counter()))

        # 2. reranking
        if req.is_reranking:
            try:
                search_results = reranking(search_results, req.query)
            except Exception as e:
                print(f"reranking search results failed: {e}")
        time_records.append(('time_rerank', time.perf_counter()))

        # 3. fetch details
        if req.is_detail:
            try:
                search_results = await fetch_details(search_results, req.detail_min_score, req.detail_top_k)
            except Exception as e:
                print(f"fetch search details failed: {e}")
        time_records.append(('time_fetch_detail', time.perf_counter()))

        # 4. filter content
        if req.is_filter:
            try:
                search_results = filter_content(search_results, req.query, req.filter_min_score, req.filter_top_k)
            except Exception as e:
                print(f"filter content failed: {e}")
        time_records.append(('time_filter', time.perf_counter()))

        for i in range(1, len(time_records)):
            cur_record = time_records[i]
            last_record = time_records[i-1]
            print("time cost %s: %.6f" % (cur_record[0], cur_record[1]-last_record[1]))

        return resp_data({
            "search_results": search_results,
        })

    except Exception as e:
        return resp_err(f"rag search failed: {e}")


def search(query, num, locale=''):
    params = {
        "q": query,
        "num": num
    }

    if locale:
        params["hl"] = locale

    try:
        search_results = get_search_results(params=params)

        return search_results
    except Exception as e:
        print(f"search failed: {e}")
        raise e


def reranking(search_results, query):
    time_records = []
    time_records.append(('time_start', time.perf_counter()))
    try:
        index = store_results(results=search_results)
        time_records.append(('time_store_result', time.perf_counter()))

        match_results = query_results(index, query, 0.00, len(search_results))
        time_records.append(('time_query_result', time.perf_counter()))
    except Exception as e:
        print(f"reranking search results failed: {e}")
        raise e

    score_maps = {}
    for result in match_results:
        score_maps[result["uuid"]] = result["score"]

    for result in search_results:
        if result["uuid"] in score_maps:
            result["score"] = score_maps[result["uuid"]]

    sorted_search_results = sorted(search_results,
                                   key=lambda x: (x['score']),
                                   reverse=True)
    time_records.append(('time_sort_result', time.perf_counter()))

    for i in range(1, len(time_records)):
        cur_record = time_records[i]
        last_record = time_records[i-1]
        print("- time cost %s: %.6f" % (cur_record[0], cur_record[1]-last_record[1]))

    return sorted_search_results


async def fetch_details(search_results, min_score=0.00, top_k=6):
    urls = []
    for res in search_results:
        if len(urls) > top_k:
            break
        if res["score"] >= min_score:
            urls.append(res["link"])

    try:
        details = await batch_fetch_urls(urls)
    except Exception as e:
        print(f"fetch details failed: {e}")
        raise e

    content_maps = {}
    for url, content in details:
        content_maps[url] = content

    for result in search_results:
        if result["link"] in content_maps:
            result["content"] = content_maps[result["link"]]

    return search_results


def filter_content(search_results, query, filter_min_score=0.8, filter_top_k=10):
    try:
        results_with_content = []
        for result in search_results:
            if "content" in result and len(result["content"]) > len(result["snippet"]):
                results_with_content.append(result)

        index = store_results(results=results_with_content)
        match_results = query_results(index, query, filter_min_score, filter_top_k)

    except Exception as e:
        print(f"filter content failed: {e}")
        raise e

    content_maps = {}
    for result in match_results:
        if result["uuid"] not in content_maps:
            content_maps[result["uuid"]] = ""
        else:
            content_maps[result["uuid"]] += result["content"]

    for result in search_results:
        if result["uuid"] in content_maps:
            result["content"] = content_maps[result["uuid"]]

    return search_results
