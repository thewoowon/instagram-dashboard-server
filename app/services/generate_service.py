import json
import re
from openai import AsyncOpenAI
from app.core.config import settings
from app.prompts.brand_profiles import BRAND_PROFILES

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


def _extract_json(text: str) -> dict:
    """GPT 응답에서 JSON 블록 추출."""
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    # 코드블록 없으면 전체를 JSON으로 시도
    return json.loads(text)


async def generate_draft_content(
    brand_name: str,
    topic: str,
    angle: str,
    format_type: str,
) -> dict:
    """브랜드 프로파일 기반 드래프트 콘텐츠 생성."""
    profile = BRAND_PROFILES.get(brand_name)
    if not profile:
        raise ValueError(f"Unknown brand: {brand_name}")

    task_key = "carousel_task" if format_type == "carousel" else "single_task"
    task_prompt = profile[task_key].format(topic=topic, angle=angle or topic)

    response = await client.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {"role": "system", "content": profile["system"]},
            {"role": "user", "content": task_prompt},
        ],
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    return json.loads(content)


async def generate_ideas(brand_name: str, count: int = 5) -> list[dict]:
    """브랜드 맞춤 아이디어 후보 생성."""
    profile = BRAND_PROFILES.get(brand_name)
    if not profile:
        raise ValueError(f"Unknown brand: {brand_name}")

    prompt = f"""다음 브랜드를 위한 인스타그램 포스트 아이디어 {count}개를 생성하세요.

출력 형식 (JSON):
{{
  "ideas": [
    {{
      "topic": "주제",
      "angle": "접근 각도 (어떤 관점으로 다룰지)",
      "format_type": "carousel 또는 single",
      "priority_score": 0-100
    }}
  ]
}}

각 아이디어는 구체적이고 실행 가능해야 합니다."""

    response = await client.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {"role": "system", "content": profile["system"]},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    data = json.loads(content)
    return data.get("ideas", [])
