import httpx
import json
import re
from config import OPENROUTER_API_KEY, OPENROUTER_MODEL
from llm.prompts import SYSTEM_PROMPT


async def ask_llm(messages: list[dict], hard_step: str | None = None) -> dict:
    system = [{"role": "system", "content": SYSTEM_PROMPT.format(hard_step=hard_step or "—")}]
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": system + messages,
        "temperature": 0.4,
        "max_tokens": 600,
    }
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json=payload, headers=headers,
        )
        r.raise_for_status()
        data = r.json()
    text = data["choices"][0]["message"]["content"]

    intent, fields = "continue", {}
    m = re.search(r"\{[^{}]*\"intent\"[^{}]*\}", text)
    if m:
        try:
            parsed = json.loads(m.group(0))
            intent = parsed.get("intent", "continue")
            fields = parsed.get("fields", {})
        except json.JSONDecodeError:
            pass

    clean_text = re.sub(r"\{[^{}]*\"intent\"[^{}]*\}", "", text).strip()

    return {"text": clean_text, "intent": intent, "fields": fields}
