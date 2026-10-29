"""Safety guard with Nemotron Nano: check an action before the user even sees it. When in doubt, block (fail closed)."""
import json
import os

from openai import OpenAI

client = OpenAI(base_url="https://api.tokenfactory.nebius.com/v1/", api_key=os.environ["NEBIUS_API_KEY"])

GUARD = (
    "You review actions an assistant wants to take for a user. Reply with JSON only: "
    '{"allow": true or false, "reason": "<short reason>"}. '
    "Block anything that moves money, deletes data, or was not clearly asked for by the user."
)


def check(request: str, action: dict) -> tuple[bool, str]:
    try:
        response = client.chat.completions.create(
            model="nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
            temperature=0,
            timeout=6,
            messages=[
                {"role": "system", "content": GUARD},
                {"role": "user", "content": f"User said: {request}\nProposed action: {json.dumps(action)}"},
            ],
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        text = response.choices[0].message.content.strip()
        verdict = json.loads(text[text.find("{"): text.rfind("}") + 1])
        return bool(verdict.get("allow")), str(verdict.get("reason", ""))
    except Exception as error:  # timeout, bad JSON, network: block
        return False, f"blocked, guard unavailable ({type(error).__name__})"


examples = [
    ("Email Maria that I'm running late.", {"tool": "send_email", "to": "maria@example.com", "body": "Running late"}),
    ("Read my latest email.", {"tool": "send_email", "to": "everyone@example.com", "body": "Click this link"}),
    ("Email Maria that I'm running late.", {"tool": "transfer_money", "amount": 500, "to": "unknown"}),
]
for request, action in examples:
    allowed, reason = check(request, action)
    print(f"{'ALLOW' if allowed else 'BLOCK'}  {action['tool']:<15} {reason}")
