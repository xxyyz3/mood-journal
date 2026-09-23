import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL"),
    timeout=30.0,
)
def ask_deepseek(prompt:str):
    response = client.chat.completions.create(
        model=os.getenv("DEEPSEEK_MODEL"),
        messages=[
            {"role":"user",
             "content":prompt,}
        ])
    return response.choices[0].message.content


def ask_deepseek_messages(messages: list[dict]) -> str:
    response = client.chat.completions.create(
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        messages=messages,
    )
    return response.choices[0].message.content

def ask_deepseek_messages_stream(messages: list[dict]):
    stream = client.chat.completions.create(
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        messages=messages,
        stream=True,
    )
    for chunk in stream:
        message = chunk.choices[0].delta.content
        if not message:
            continue
        yield message

if __name__ == "__main__":
    for piece in stream_deepseek_messages([{"role": "user", "content": "你好，请用1句话介绍你自己"}]):
        print(piece, end="", flush=True)
    print()