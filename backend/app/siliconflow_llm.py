import os

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


client = OpenAI(
    api_key=os.getenv("SILICONFLOW_API_KEY"),
    base_url=os.getenv("SILICONFLOW_BASE_URL"),
    timeout=30.0,
)


def get_embedding(text: str) -> list[float]:
    response = client.embeddings.create(
        model="BAAI/bge-m3",
        input=text
    )
    return response.data[0].embedding


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    # 把 list 转成 numpy array
    a = np.array(vec1)
    b = np.array(vec2)
    # 计算点积
    dot_product = np.dot(a, b)
    # 计算模长
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    # 算余弦值
    return dot_product / (norm_a * norm_b)

if __name__ == "__main__":
    question = "她住在哪里"
    chunk_address = "## 住址 现住址：星咲学园附近学生公寓「メゾン・ド・猫尾」302 号室"
    chunk_chat = "## 说话示例 大哥哥说今天好累"

    print("正在获取向量...")
    v_q = get_embedding(question)
    v_address = get_embedding(chunk_address)
    v_chat = get_embedding(chunk_chat)

    print(f"问题 和 住址块 的相似度: {cosine_similarity(v_q, v_address):.4f}")
    print(f"问题 和 说话示例块 的相似度: {cosine_similarity(v_q, v_chat):.4f}")