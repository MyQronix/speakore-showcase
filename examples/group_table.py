"""Table mode: one sentence into every language at the table, in a single Nemotron Super call (JSON out)."""
import json
import os
import time

from openai import OpenAI

client = OpenAI(base_url="https://api.tokenfactory.nebius.com/v1/", api_key=os.environ["NEBIUS_API_KEY"])

sentence = "We meet tomorrow at half past eight at the station."
targets = ["es", "nl", "de", "ja"]

start = time.monotonic()
response = client.chat.completions.create(
    model="nvidia/nemotron-3-super-120b-a12b",
    temperature=0,
    messages=[
        {
            "role": "system",
            "content": "You are a professional interpreter. Translate the user's sentence from English into each of "
            f"these languages: {', '.join(targets)}. Keep times and names exact. "
            'Reply with JSON only, one key per language code, for example {"es": "..."}.',
        },
        {"role": "user", "content": sentence},
    ],
    extra_body={"chat_template_kwargs": {"enable_thinking": False}},
)
text = response.choices[0].message.content
translations = json.loads(text[text.find("{"): text.rfind("}") + 1])
for code in targets:
    print(f"{code}: {translations.get(code)}")
print(f"{len(targets)} languages in one call, {time.monotonic() - start:.2f} s")
