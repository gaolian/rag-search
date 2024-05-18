import os
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core import ServiceContext

#from llama_index.embeddings.huggingface import HuggingFaceEmbedding


def decorator(func):
    def wrapper(*args, **kwargs):
        print("params:", args, kwargs)
        return func(*args, **kwargs)
    return wrapper


def get_service_context():
    api_key = os.getenv("OPENAI_API_KEY")
    api_base = os.getenv("OPENAI_BASE_URL")
    llm_model = os.getenv("OPENAI_MODEL")
    embed_model = os.getenv("OPENAI_EMBED_MODEL")

    llm_engine = OpenAI(
        model=llm_model,
        api_key=api_key,
        api_base=api_base,
    )

    embed_engine = OpenAIEmbedding(
        model=embed_model,
        api_key=api_key,
        api_base=api_base,
    )

    # embed_engine =HuggingFaceEmbedding(
    #     model_name="BAAI/bge-small-en-v1.5"
    # )

    service_context = ServiceContext.from_defaults(
        llm=llm_engine,
        embed_model=embed_engine,
    )
    # set_global_service_context(service_context)
    print("init service_context with apibase", api_base)

    return service_context
