import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).with_name(".env"))


def get_openai_client():
    return OpenAI()

DEFAULT_ADVICE = {
    "craving": "想吃的食物",
    "is_healthy_choice": True,
    "health_summary": "这份选择整体可以接受，注意搭配蔬菜和蛋白质会更稳。",
    "possible_missing_nutrients": [],
    "emotional_support": "想吃东西本身不是问题，照顾好自己才是重点。我们可以选一个更舒服的吃法。",
    "better_choice_tip": "可以少油少糖，搭配一份蔬菜或无糖饮品。",
    "restaurant_menus": [
        {
            "restaurant_name": "附近轻食简餐",
            "distance_hint": "附近",
            "menu_items": [
                {
                    "name": "番茄牛腩饭",
                    "reason": "有主食和蛋白质，搭配番茄更均衡。",
                    "nutrient_focus": ["铁", "蛋白质", "维生素C"],
                }
            ],
        }
    ],
}


def _clean_json_response(raw_content: str) -> str:
    content = (raw_content or "{}").strip()
    if content.startswith("```"):
        content = content.strip("`").removeprefix("json").strip()
    return content


def _normalize_nutrient_list(value):
    if not isinstance(value, list):
        return []

    normalized = []
    for item in value[:5]:
        if isinstance(item, dict):
            normalized.append({
                "name": str(item.get("name") or "营养元素"),
                "reason": str(item.get("reason") or "当前饮食可能摄入不足。"),
                "food_sources": [
                    str(source)
                    for source in (item.get("food_sources") or [])
                    if source
                ][:4],
            })
    return normalized


def _normalize_restaurant_menus(value):
    if not isinstance(value, list):
        return DEFAULT_ADVICE["restaurant_menus"]

    restaurants = []
    for restaurant in value[:4]:
        if not isinstance(restaurant, dict):
            continue

        menu_items = []
        for item in (restaurant.get("menu_items") or [])[:4]:
            if isinstance(item, dict):
                menu_items.append({
                    "name": str(item.get("name") or "推荐餐品"),
                    "reason": str(item.get("reason") or "比原本想吃的选择更均衡。"),
                    "nutrient_focus": [
                        str(nutrient)
                        for nutrient in (item.get("nutrient_focus") or [])
                        if nutrient
                    ][:4],
                })

        if menu_items:
            restaurants.append({
                "restaurant_name": str(restaurant.get("restaurant_name") or "附近餐馆"),
                "distance_hint": str(restaurant.get("distance_hint") or "附近"),
                "menu_items": menu_items,
            })

    return restaurants or DEFAULT_ADVICE["restaurant_menus"]


def normalize_food_advice(result: dict, craving: str) -> dict:
    data = {**DEFAULT_ADVICE, **(result or {})}
    data["craving"] = str(data.get("craving") or craving or "想吃的食物")
    data["is_healthy_choice"] = bool(data.get("is_healthy_choice", True))
    data["health_summary"] = str(data.get("health_summary") or DEFAULT_ADVICE["health_summary"])
    data["emotional_support"] = str(data.get("emotional_support") or DEFAULT_ADVICE["emotional_support"])
    data["better_choice_tip"] = str(data.get("better_choice_tip") or DEFAULT_ADVICE["better_choice_tip"])
    data["possible_missing_nutrients"] = _normalize_nutrient_list(data.get("possible_missing_nutrients"))
    data["restaurant_menus"] = _normalize_restaurant_menus(data.get("restaurant_menus"))
    return data


def fallback_food_advice(craving: str, location: str = "附近") -> dict:
    name = (craving or "").strip()
    unhealthy_keywords = ["炸", "汉堡", "薯条", "奶茶", "烧烤", "蛋糕", "甜品", "可乐", "披萨"]
    is_unhealthy = any(keyword in name for keyword in unhealthy_keywords)

    if is_unhealthy:
        result = {
            "craving": name,
            "is_healthy_choice": False,
            "health_summary": f"{name} 可以偶尔吃，但油脂、糖分或盐分可能偏高。",
            "possible_missing_nutrients": [
                {
                    "name": "维生素C",
                    "reason": "高油高糖餐通常蔬果不足。",
                    "food_sources": ["番茄", "西兰花", "橙子", "猕猴桃"],
                },
                {
                    "name": "膳食纤维",
                    "reason": "精制主食和油炸食品容易缺少纤维。",
                    "food_sources": ["杂粮饭", "玉米", "青菜", "菌菇"],
                },
                {
                    "name": "钙",
                    "reason": "快餐饮品替代正餐时，钙摄入可能不足。",
                    "food_sources": ["牛奶", "豆腐", "酸奶", "虾皮"],
                },
            ],
            "emotional_support": "想吃重口味很正常，可能只是今天有点累。我们不需要责备自己，换一个更温和的版本也算照顾自己。",
            "better_choice_tip": "可以点小份，去掉含糖饮料，再加一份蔬菜或汤。",
            "restaurant_menus": [
                {
                    "restaurant_name": f"{location or '附近'}健康简餐",
                    "distance_hint": "约500米内",
                    "menu_items": [
                        {
                            "name": "番茄牛腩饭",
                            "reason": "保留米饭满足感，同时补充铁和蛋白质。",
                            "nutrient_focus": ["铁", "蛋白质", "维生素C"],
                        },
                        {
                            "name": "鸡胸肉蔬菜饭",
                            "reason": "比油炸类更清爽，蛋白质更稳定。",
                            "nutrient_focus": ["蛋白质", "膳食纤维"],
                        },
                    ],
                },
                {
                    "restaurant_name": f"{location or '附近'}轻食沙拉",
                    "distance_hint": "附近可选",
                    "menu_items": [
                        {
                            "name": "牛肉藜麦沙拉",
                            "reason": "补铁，也能增加膳食纤维。",
                            "nutrient_focus": ["铁", "膳食纤维"],
                        }
                    ],
                },
            ],
        }
    else:
        result = {
            "craving": name,
            "is_healthy_choice": True,
            "health_summary": f"{name} 看起来是可以纳入正餐的选择，注意份量和搭配就好。",
            "possible_missing_nutrients": [],
            "emotional_support": "这个选择挺稳的，认真吃饭也是一种给自己充电。",
            "better_choice_tip": "搭配一份蔬菜和无糖饮品，会更均衡。",
            "restaurant_menus": [
                {
                    "restaurant_name": f"{location or '附近'}家常菜馆",
                    "distance_hint": "附近",
                    "menu_items": [
                        {
                            "name": name or "番茄牛腩饭",
                            "reason": "满足想吃的口味，同时作为一顿正餐比较完整。",
                            "nutrient_focus": ["蛋白质", "碳水"],
                        }
                    ],
                }
            ],
        }

    return normalize_food_advice(result, name)


def get_food_advice_from_ai(craving: str, location: str, pet_context: dict) -> dict:
    if not craving.strip():
        return fallback_food_advice("想吃的食物", location)

    system_prompt = """
你是一个温柔但务实的中文饮食建议助手。用户会告诉你 TA 想吃什么，你要判断这个选择是否偏不健康。

你必须只返回合法 JSON，不要 markdown。

输出格式：
{
  "craving": "用户想吃的食物",
  "is_healthy_choice": true 或 false,
  "health_summary": "简短健康判断",
  "possible_missing_nutrients": [
    {
      "name": "可能缺的营养元素，例如：维生素C、膳食纤维、铁、钙、碘",
      "reason": "为什么可能缺",
      "food_sources": ["可补充的食物1", "可补充的食物2"]
    }
  ],
  "emotional_support": "一句自然的情绪安抚，不要说教",
  "better_choice_tip": "保留欲望但更健康的吃法",
  "restaurant_menus": [
    {
      "restaurant_name": "附近餐馆类型或名称",
      "distance_hint": "例如：约500米内、步行10分钟、附近",
      "menu_items": [
        {
          "name": "推荐菜单名",
          "reason": "为什么推荐",
          "nutrient_focus": ["补充重点1", "补充重点2"]
        }
      ]
    }
  ]
}

如果用户想吃的是炸鸡、汉堡、奶茶、烧烤、甜品等，is_healthy_choice 应为 false，并返回可能缺的营养元素和安抚语。
餐馆菜单推荐要像真实附近可点的菜单，但不要声称你查到了实时店铺；如果地点不明确，就写“附近简餐/轻食/家常菜馆”。
"""

    user_prompt = {
        "craving": craving,
        "location": location or "附近",
        "pet_health_context": pet_context,
    }

    try:
        model_name = os.getenv("LLM_MODEL_NAME", "gpt-4o")
        response = get_openai_client().chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(user_prompt, ensure_ascii=False),
                },
            ],
            max_tokens=900,
            temperature=0.4,
        )
        raw_content = response.choices[0].message.content
        result = json.loads(_clean_json_response(raw_content))
        return normalize_food_advice(result, craving)
    except Exception as exc:
        print(f"AI 想吃建议失败: {exc}")
        return fallback_food_advice(craving, location)
