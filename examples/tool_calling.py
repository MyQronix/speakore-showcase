"""Voice command to app action: Nemotron Super picks a tool (the control pipeline). The translate pipeline gets no tools."""
import json
import os

from openai import OpenAI

client = OpenAI(base_url="https://api.tokenfactory.nebius.com/v1/", api_key=os.environ["NEBIUS_API_KEY"])

tools = [
    {
        "type": "function",
        "function": {
            "name": "set_theme",
            "description": "Switch the app between light and dark mode.",
            "parameters": {
                "type": "object",
                "properties": {"theme": {"type": "string", "enum": ["light", "dark"]}},
                "required": ["theme"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "navigate",
            "description": "Open a screen in the app.",
            "parameters": {
                "type": "object",
                "properties": {"screen": {"type": "string", "enum": ["translate", "connectors", "profile"]}},
                "required": ["screen"],
            },
        },
    },
]

response = client.chat.completions.create(
    model="nvidia/nemotron-3-super-120b-a12b",
    temperature=0,
    messages=[
        {"role": "system", "content": "You control a mobile app. Use a tool when the user asks for an app action."},
        {"role": "user", "content": "Zet het donkere thema aan."},
    ],
    tools=tools,
    extra_body={"chat_template_kwargs": {"enable_thinking": False}},
)
for call in response.choices[0].message.tool_calls or []:
    print(call.function.name, json.loads(call.function.arguments))
