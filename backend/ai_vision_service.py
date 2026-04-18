import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).with_name(".env"))


def get_openai_client():
    return OpenAI()

DEFAULT_HP_CHANGES = {
    "fat": 0,
    "iron": 0,
    "calcium": 0,
    "iodine": 0,
    "vit_c": 0,
    "vit_a": 0,
    "fiber": 0,
}


def infer_food_type(food_name: str) -> tuple[str, str]:
    """Return (dish_category, food_type) from a recognized Chinese food name."""
    name = (food_name or "").strip().lower()

    if not name or name in {"图片识别餐食", "未知食物"}:
        return "未识别", "未知"

    if any(word in name for word in ["盖饭", "盖浇饭", "牛腩饭", "鸡排饭", "卤肉饭", "烩饭"]):
        return "米饭类", "盖浇饭"
    if any(word in name for word in ["炒饭", "拌饭", "焖饭", "煲仔饭"]):
        return "米饭类", "拌炒饭"
    if "饭" in name:
        return "米饭类", "饭类套餐"
    if any(word in name for word in ["面", "拉面", "拌面", "炒面"]):
        return "面食类", "面条"
    if any(word in name for word in ["粉", "米线", "河粉"]):
        return "粉面类", "米粉"
    if any(word in name for word in ["粥", "汤"]):
        return "汤粥类", "汤粥"
    if any(word in name for word in ["沙拉", "轻食"]):
        return "轻食类", "沙拉轻食"
    if any(word in name for word in ["奶茶", "咖啡", "果茶", "饮料"]):
        return "饮品类", "饮品"
    if any(word in name for word in ["蛋糕", "甜品", "布丁"]):
        return "甜品类", "甜品"

    return "其他", "普通餐食"


def normalize_ai_result(result: dict, fallback_name: str = "未知食物") -> dict:
    food_name = str(result.get("food") or fallback_name or "未知食物").strip()
    dish_category, food_type = infer_food_type(food_name)

    hp_changes = result.get("hp_changes") or {}
    safe_hp_changes = {}
    for key, default_value in DEFAULT_HP_CHANGES.items():
        try:
            value = int(hp_changes.get(key, default_value))
        except (TypeError, ValueError):
            value = default_value
        safe_hp_changes[key] = max(-30, min(30, value))

    return {
        "food": food_name,
        "dish_category": result.get("dish_category") or dish_category,
        "food_type": result.get("food_type") or food_type,
        "confidence": float(result.get("confidence") or 0),
        "is_healthy": bool(result.get("is_healthy", True)),
        "hp_changes": safe_hp_changes,
        "reasoning": result.get("reasoning") or "这是根据餐食识别结果给出的营养估算。",
    }


def analyze_food_image_with_ai(image_base64: str, text_hint: str = "") -> dict:
    """
    Analyze a food image and return normalized structured data.
    If the model call fails, use the text hint as a graceful fallback.
    """
    if not image_base64:
        return normalize_ai_result({}, text_hint or "未知食物")

    system_prompt = """
你是一位中文食物识别和公共营养分析助手。请识别用户上传的餐食照片。

你必须只返回一个合法 JSON 对象，不要 markdown，不要解释性废话。

字段要求：
{
  "food": "具体菜名，例如：番茄牛腩饭",
  "dish_category": "大类，例如：米饭类、面食类、粉面类、汤粥类、轻食类、饮品类、甜品类、其他",
  "food_type": "更具体的类型，例如：盖浇饭、饭类套餐、炒饭、面条、沙拉轻食",
  "confidence": 0.0 到 1.0 的识别置信度,
  "is_healthy": true 或 false,
    "hp_changes": {
    "fat": 整数，-30 到 30,
    "iron": 整数，-30 到 30,
    "calcium": 整数，-30 到 30,
    "iodine": 整数，-30 到 30,
    "vit_c": 整数，-30 到 30,
    "fiber": 整数，-30 到 30
  },
  "reasoning": "用一两句话说明识别依据和营养判断"
}

如果识别到类似“番茄牛腩饭”，food 填“番茄牛腩饭”，dish_category 填“米饭类”，food_type 填“盖浇饭”。
如果识别到炸鸡、汉堡、薯条等油炸快餐，fiber 通常给负数；如果识别到蔬菜、杂粮、沙拉，fiber 通常给正数。
"""

    try:
        model_name = os.getenv("LLM_MODEL_NAME", "gpt-4o")
        response = get_openai_client().chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"请识别这张餐食照片。可参考的文字线索：{text_hint or '无'}",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}",
                            },
                        },
                    ],
                },
            ],
            max_tokens=500,
            temperature=0.1,
        )

        raw_content = response.choices[0].message.content or "{}"
        clean_content = raw_content.strip()
        if clean_content.startswith("```"):
            clean_content = clean_content.strip("`").removeprefix("json").strip()

        return normalize_ai_result(json.loads(clean_content), text_hint or "未知食物")
    except Exception as exc:
        print(f"AI 食物识别失败: {exc}")
        fallback = {
            "food": text_hint if text_hint and text_hint != "图片识别餐食" else "未知食物",
            "confidence": 0,
            "is_healthy": True,
            "hp_changes": DEFAULT_HP_CHANGES,
            "reasoning": "AI 识别失败，暂时使用兜底结果。",
        }
        return normalize_ai_result(fallback)


def analyze_food_text_with_ai(food_name: str) -> dict:
    """Compatibility wrapper for text-only food analysis."""
    return normalize_ai_result({"food": food_name or "未知食物"}, food_name or "未知食物")


def analyze_craving_with_ai(craving_food: str) -> dict:
    """Compatibility wrapper for the older craving-analysis endpoint."""
    craving = (craving_food or "").strip()
    unhealthy_words = ["炸", "汉堡", "薯条", "奶茶", "甜品", "可乐"]
    lacking_element = "vit_c" if any(word in craving for word in unhealthy_words) else "fiber"
    return {
        "lacking_element": lacking_element,
        "analysis_message": "可以保留想吃的感觉，同时搭配蔬菜、水果或更完整的一餐来平衡。",
    }
