"""Two pipelines, one sentence. Translate never gets tools, so a spoken command is translated, not executed.
Control (Kore) gets tools and acts. This separation is a core design rule of SpeaKore."""
import os

from openai import OpenAI

client = OpenAI(base_url="https://api.tokenfactory.nebius.com/v1/", api_key=os.environ["NEBIUS_API_KEY"])
MODEL = "nvidia/nemotron-3-super-120b-a12b"
THINKING_OFF = {"chat_template_kwargs": {"enable_thinking": False}}
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "set_theme",
            "description": "Switch the app between light and dark mode.",
            "parameters": {"type": "object", "properties": {"theme": {"type": "string", "enum": ["light", "dark"]}}, "required": ["theme"]},
        },
    }
]

said = "Switch the app to dark mode."


def translate(text: str) -> str:
    # No tools are passed at all. Even if a model tried to call one, the translate pipeline would refuse it.
    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": "You are a professional interpreter. Translate the user's sentence from English to Spanish. Reply with the translation only."},
            {"role": "user", "content": text},
        ],
        extra_body=THINKING_OFF,
    )
    message = response.choices[0].message
    if message.tool_calls:
        raise RuntimeError("translate pipeline must never act")
    return message.content


def control(text: str) -> list[str]:
    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": "You control a mobile app. Use a tool when the user asks for an app action."},
            {"role": "user", "content": text},
        ],
        tools=TOOLS,
        extra_body=THINKING_OFF,
    )
    return [f"{c.function.name}({c.function.arguments})" for c in response.choices[0].message.tool_calls or []]


print("translate:", translate(said))
print("control:  ", control(said))
