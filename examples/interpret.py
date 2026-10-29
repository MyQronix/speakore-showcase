"""Interpret one sentence with NVIDIA Nemotron Super on Nebius Token Factory (EU), thinking off, temperature 0."""
import os
import time

from openai import OpenAI

client = OpenAI(base_url="https://api.tokenfactory.nebius.com/v1/", api_key=os.environ["NEBIUS_API_KEY"])

start = time.monotonic()
response = client.chat.completions.create(
    model="nvidia/nemotron-3-super-120b-a12b",
    temperature=0,
    messages=[
        {
            "role": "system",
            "content": "You are a professional interpreter. Translate the user's sentence from Spanish to Dutch, "
            "completely and faithfully, in natural everyday Dutch. Reply with the translation only.",
        },
        {"role": "user", "content": "No quiero el postre. Gracias."},
    ],
    extra_body={"chat_template_kwargs": {"enable_thinking": False}},
)
print(response.choices[0].message.content)
print(f"{time.monotonic() - start:.2f} s")
