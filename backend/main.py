import json
import random
from datetime import date

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from database import engine, Base, get_db
from ai_vision_service import analyze_food_image_with_ai, normalize_ai_result
from food_advice_service import get_food_advice_from_ai
from typing import Optional
import models

# 创建数据库所有表
Base.metadata.create_all(bind=engine)

def ensure_runtime_schema():
    """Add lightweight SQLite columns for local dev databases created before model changes."""
    with engine.begin() as conn:
        pet_columns = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(pets)")).fetchall()
        }
        if "fiber_hp" not in pet_columns:
            conn.execute(text("ALTER TABLE pets ADD COLUMN fiber_hp INTEGER DEFAULT 100"))

ensure_runtime_schema()

app = FastAPI(title="BunnyHealth API")

@app.get("/")
def read_root():
    return {"message": "Welcome to BunnyHealth API"}

from pydantic import BaseModel

# 增加请求体验证模型
class MealRequest(BaseModel):
    user_id: int
    food_name: str # 暂时用文字代替图片识别结果，方便测试
    image_base64: Optional[str] = None # 预留给前端传图片的字段

class CravingAdviceRequest(BaseModel):
    user_id: int
    craving: str
    location: Optional[str] = "附近"

class HealthTaskCompleteRequest(BaseModel):
    user_id: int
    task_id: str

class PetNameRequest(BaseModel):
    name: str

# 用户测试接口
class FoodRequest(BaseModel):
    name: str
    ingredients: str
    calories: float
    protein: float
    fat: float
    carbs: float
    iron_score: int = 0
    calcium_score: int = 0
    iodine_score: int = 0
    vit_c_score: int = 0
    price: float
    location: str
    is_healthy_option: bool = True

NUTRIENT_LABELS = {
    "health": "活力",
    "fat": "脂肪负担",
    "iron": "铁",
    "calcium": "钙",
    "iodine": "碘",
    "vit_c": "维C",
    "fiber": "膳食纤维",
}

def clamp_hp(value: int):
    return max(0, min(100, int(value)))

HEALTH_TASK_POOL = [
    {
        "id": "drink_water",
        "title": "喝一杯水",
        "description": "给身体一点补水时间，慢慢喝完就算完成。",
        "tag": "补水",
        "effects": {"health": 4, "vit_c": 1},
        "pet_message": "小兔子的精神值亮了一点，home 里的空气也更清爽了。",
    },
    {
        "id": "pushup_5",
        "title": "俯卧撑 5 个",
        "description": "不用追求标准满分，认真动起来就很好。",
        "tag": "力量",
        "effects": {"health": 5, "fat": -3},
        "pet_message": "小兔子获得了运动能量，脂肪负担悄悄下降。",
    },
    {
        "id": "walk_10",
        "title": "走路 10 分钟",
        "description": "去楼下、走廊或操场绕一小圈。",
        "tag": "活动",
        "effects": {"health": 5, "fat": -2, "fiber": 1},
        "pet_message": "小兔子跟着伸了伸腿，home 变得更有活力。",
    },
    {
        "id": "stretch_neck",
        "title": "拉伸肩颈 2 分钟",
        "description": "放下手机，慢慢转动肩颈。",
        "tag": "放松",
        "effects": {"health": 3, "calcium": 2},
        "pet_message": "小兔子的姿态更轻松了，骨骼状态也稳了一点。",
    },
    {
        "id": "fruit_piece",
        "title": "吃一份水果",
        "description": "苹果、橙子、猕猴桃都可以，选手边方便的。",
        "tag": "维C",
        "effects": {"vit_c": 8, "fiber": 4, "health": 2},
        "pet_message": "小兔子收到了维C补给，毛毛看起来更精神。",
    },
    {
        "id": "veggie_bite",
        "title": "补一份蔬菜",
        "description": "下一餐加一点青菜、菌菇或玉米。",
        "tag": "纤维",
        "effects": {"fiber": 8, "vit_c": 4, "health": 2},
        "pet_message": "小兔子的膳食纤维条涨了一截，home 的灯更暖了。",
    },
    {
        "id": "no_sugary_drink",
        "title": "今天少喝一杯含糖饮料",
        "description": "把奶茶换成水、茶或无糖饮料。",
        "tag": "控糖",
        "effects": {"health": 4, "fat": -2},
        "pet_message": "小兔子的负担变轻了，脚步都轻快了一点。",
    },
    {
        "id": "early_sleep_plan",
        "title": "定一个早睡提醒",
        "description": "给今晚设一个提醒，提前 20 分钟收尾。",
        "tag": "作息",
        "effects": {"health": 6},
        "pet_message": "小兔子窝进了柔软的小床，恢复力提升了。",
    },
]

EVENT_DEFINITIONS = [
    {
        "id": "photo_3",
        "title": "三餐侦探",
        "description": "你已经记录了 3 次饮食，小兔子开始认识你的餐桌节奏。",
        "trigger_type": "photo_count",
        "threshold": 3,
        "locked_hint": "累计拍照 3 次后出现。",
    },
    {
        "id": "ask_3",
        "title": "想吃雷达",
        "description": "你认真问过 3 次想吃什么，小兔子学会了温柔拦截嘴馋。",
        "trigger_type": "ask_count",
        "threshold": 3,
        "locked_hint": "累计询问 3 次想吃什么后出现。",
    },
    {
        "id": "task_1",
        "title": "第一枚胡萝卜徽章",
        "description": "完成第一个健康小任务，小兔子把徽章挂在了墙上。",
        "trigger_type": "task_count",
        "threshold": 1,
        "locked_hint": "完成 1 个健康任务后出现。",
    },
    {
        "id": "task_5",
        "title": "习惯发芽",
        "description": "5 个小任务让 home 角落长出了一株小绿芽。",
        "trigger_type": "task_count",
        "threshold": 5,
        "locked_hint": "累计完成 5 个健康任务后出现。",
    },
    {
        "id": "home_bright",
        "title": "晨光房间",
        "description": "综合状态达到 90，小兔子把窗帘全部拉开了。",
        "trigger_type": "overall_score",
        "threshold": 90,
        "locked_hint": "宠物综合状态达到 90 后出现。",
    },
    {
        "id": "fiber_low",
        "title": "纤维警报",
        "description": "膳食纤维太低时，小兔子举起了蔬菜求救牌。",
        "trigger_type": "fiber_below",
        "threshold": 50,
        "locked_hint": "膳食纤维低于 50 时出现。",
    },
    {
        "id": "fried_4",
        "title": "炸鸡乌云",
        "description": "油炸快餐累积太多，home 上空飘来一朵小乌云。",
        "trigger_type": "fried_count",
        "threshold": 4,
        "locked_hint": "最近油炸快餐达到 4 次时出现。",
    },
    {
        "id": "healthy_streak_3",
        "title": "连续清爽三餐",
        "description": "最近连续 3 餐比较健康，小兔子在房间里跳了一圈。",
        "trigger_type": "healthy_streak",
        "threshold": 3,
        "locked_hint": "最近连续 3 餐健康后出现。",
    },
]

def get_today_key():
    return date.today().isoformat()

def get_daily_tasks_for_user(user_id: int, task_date: str = None):
    task_date = task_date or get_today_key()
    seeded_random = random.Random(f"{user_id}-{task_date}")
    return seeded_random.sample(HEALTH_TASK_POOL, 2)

def apply_pet_effects(pet: models.Pet, effects: dict):
    effects = effects or {}
    pet.health_hp = clamp_hp(pet.health_hp + effects.get("health", 0))
    pet.fat_level = clamp_hp(pet.fat_level + effects.get("fat", 0))
    pet.iron_hp = clamp_hp(pet.iron_hp + effects.get("iron", 0))
    pet.calcium_hp = clamp_hp(pet.calcium_hp + effects.get("calcium", 0))
    pet.iodine_hp = clamp_hp(pet.iodine_hp + effects.get("iodine", 0))
    pet.vit_c_hp = clamp_hp(pet.vit_c_hp + effects.get("vit_c", 0))
    pet.fiber_hp = clamp_hp((getattr(pet, "fiber_hp", 100) or 100) + effects.get("fiber", 0))

def get_or_create_stats(db: Session, user_id: int):
    stats = db.query(models.UserActionStats).filter(models.UserActionStats.user_id == user_id).first()
    if stats is None:
        stats = models.UserActionStats(user_id=user_id)
        db.add(stats)
        db.commit()
        db.refresh(stats)
    return stats

def serialize_task(task: dict, completed_ids):
    return {
        **task,
        "completed": task["id"] in completed_ids,
        "effect_items": [
            {
                "key": key,
                "label": NUTRIENT_LABELS.get(key, key),
                "value": value,
                "direction": "down" if key == "fat" and value < 0 else "up",
            }
            for key, value in task["effects"].items()
        ],
    }

def get_attribute_value(pet_status: dict, key: str, default: int = 100):
    for attribute in pet_status.get("attributes", []):
        if attribute.get("key") == key:
            return attribute.get("value", default)
    return default

def event_is_triggered(event: dict, pet_status: dict, stats: models.UserActionStats):
    trigger_type = event["trigger_type"]
    threshold = event["threshold"]

    if trigger_type == "photo_count":
        return (stats.photo_count or 0) >= threshold
    if trigger_type == "ask_count":
        return (stats.ask_count or 0) >= threshold
    if trigger_type == "task_count":
        return (stats.task_count or 0) >= threshold
    if trigger_type == "overall_score":
        return (pet_status.get("pet", {}).get("overall_score") or 0) >= threshold
    if trigger_type == "fiber_below":
        return get_attribute_value(pet_status, "fiber") < threshold
    if trigger_type == "fried_count":
        return (pet_status.get("history_summary", {}).get("fried_count") or 0) >= threshold
    if trigger_type == "healthy_streak":
        return (pet_status.get("history_summary", {}).get("recent_healthy_streak") or 0) >= threshold

    return False

def collect_available_events(db: Session, user_id: int, pet_status: dict, trigger_source: str):
    stats = get_or_create_stats(db, user_id)
    existing_ids = {
        row.event_id
        for row in db.query(models.PetEventCollection)
            .filter(models.PetEventCollection.user_id == user_id)
            .all()
    }
    new_events = []

    for event in EVENT_DEFINITIONS:
        if event["id"] in existing_ids:
            continue
        if not event_is_triggered(event, pet_status, stats):
            continue

        row = models.PetEventCollection(
            user_id=user_id,
            event_id=event["id"],
            title=event["title"],
            description=event["description"],
            trigger_source=trigger_source,
        )
        db.add(row)
        new_events.append({
            **event,
            "collected": True,
            "is_new": True,
            "trigger_source": trigger_source,
        })

    if new_events:
        db.commit()

    return new_events

def build_event_collection(db: Session, user_id: int):
    rows = db.query(models.PetEventCollection)\
        .filter(models.PetEventCollection.user_id == user_id)\
        .all()
    collected_by_id = {row.event_id: row for row in rows}

    return [
        {
            "id": event["id"],
            "title": event["title"] if event["id"] in collected_by_id else "未收集事件",
            "description": collected_by_id[event["id"]].description if event["id"] in collected_by_id else event["locked_hint"],
            "trigger_hint": event["locked_hint"],
            "collected": event["id"] in collected_by_id,
            "silhouette": event["id"] not in collected_by_id,
            "collected_at": collected_by_id[event["id"]].collected_at.isoformat() if event["id"] in collected_by_id and collected_by_id[event["id"]].collected_at else None,
        }
        for event in EVENT_DEFINITIONS
    ]

@app.post("/foods/")
def create_food(food: FoodRequest, db: Session = Depends(get_db)):
    """录入新的食堂菜品到图鉴中"""
    db_food = models.FoodDictionary(**food.model_dump())
    db.add(db_food)
    db.commit()
    db.refresh(db_food)
    return {"message": "菜品录入成功", "food_id": db_food.id}

@app.post("/users/")
def create_user(username: str, target_calories: float, db: Session = Depends(get_db)):
    db_user = models.User(username=username, target_calories=target_calories)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # 初始化宠物
    db_pet = models.Pet(user_id=db_user.id, name="My Bunny")
    db.add(db_pet)
    db.commit()
    
    return {"message": "User and Pet created", "user_id": db_user.id}

def get_or_create_pet(db: Session, user_id: int):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        user = models.User(
            id=user_id,
            username=f"Demo User {user_id}",
            target_calories=2000,
        )
        db.add(user)
        db.commit()

    pet = db.query(models.Pet).filter(models.Pet.user_id == user_id).first()
    if pet is None:
        pet = models.Pet(user_id=user_id, name="Bunny")
        db.add(pet)
        db.commit()
        db.refresh(pet)

    return pet

def calculate_disease_states(pet: models.Pet):
    """根据各项HP计算当前疾病状态，供前端加载插图图层"""
    diseases = []
    
    # 死亡判定
    if pet.health_hp <= 0:
        return [{"element": "general", "severity": "dead", "symptom": "已死亡", "layer_name": "dead_ghost"}]

    # 1. 肥胖 (fat)
    if pet.fat_level >= 80:
        diseases.append({"element": "fat", "severity": "severe", "symptom": "重度肥胖", "layer_name": "fat_severe"})
    elif pet.fat_level >= 50:
        diseases.append({"element": "fat", "severity": "mild", "symptom": "轻度肥胖", "layer_name": "fat_mild"})

    # 2. 铁 Fe (iron)
    if pet.iron_hp < 40:
        diseases.append({"element": "iron", "severity": "severe", "symptom": "缺铁性贫血、极度疲劳、免疫力下降", "layer_name": "iron_severe"})
    elif pet.iron_hp < 80:
        diseases.append({"element": "iron", "severity": "mild", "symptom": "面色苍白、畏寒", "layer_name": "iron_mild"})

    # 3. 钙 Ca (calcium)
    if pet.calcium_hp < 40:
        diseases.append({"element": "calcium", "severity": "severe", "symptom": "骨质疏松/佝偻病、骨质软化", "layer_name": "calcium_severe"})
    elif pet.calcium_hp < 80:
        diseases.append({"element": "calcium", "severity": "mild", "symptom": "肌肉痉挛(抽筋)", "layer_name": "calcium_mild"})

    # 4. 碘 I (iodine)
    if pet.iodine_hp < 40:
        diseases.append({"element": "iodine", "severity": "severe", "symptom": "呆小症(智力低下、发育迟缓)", "layer_name": "iodine_severe"})
    elif pet.iodine_hp < 80:
        diseases.append({"element": "iodine", "severity": "mild", "symptom": "地方性甲状腺肿(大脖子病)", "layer_name": "iodine_mild"})

    # 5. 维C (vit_c)
    if pet.vit_c_hp < 40:
        diseases.append({"element": "vit_c", "severity": "severe", "symptom": "重度坏血病(牙龈出血)", "layer_name": "vit_c_severe"})
    elif pet.vit_c_hp < 80:
        diseases.append({"element": "vit_c", "severity": "mild", "symptom": "毛发脱落、轻度坏血", "layer_name": "vit_c_mild"})

    # 6. 膳食纤维 (fiber)
    fiber_hp = getattr(pet, "fiber_hp", 100) or 100
    if fiber_hp < 40:
        diseases.append({"element": "fiber", "severity": "severe", "symptom": "严重缺膳食纤维，肠胃状态很差", "layer_name": "fiber_severe"})
    elif fiber_hp < 80:
        diseases.append({"element": "fiber", "severity": "mild", "symptom": "缺膳食纤维，需要多吃蔬菜和粗粮", "layer_name": "fiber_mild"})

    return diseases

def analyze_food_by_name(food_name: str):
    food_name = (food_name or "未知食物").lower()
    ai_result = {
        "food": food_name,
        "is_healthy": True,
        "hp_changes": {
            "fat": 0,
            "iron": 0,
            "calcium": 0,
            "iodine": 0,
            "vit_c": 0,
            "fiber": 0,
        },
        "reasoning": "这是一顿普通的饭菜，保持了当前状态。"
    }

    if "炸鸡" in food_name or "汉堡" in food_name:
        ai_result["is_healthy"] = False
        ai_result["hp_changes"] = {"fat": 20, "iron": -10, "calcium": -5, "iodine": 0, "vit_c": -15, "fiber": -22}
        ai_result["reasoning"] = "炸鸡和汉堡油脂较高，蔬菜和粗粮通常不足，会明显拉低膳食纤维状态。"
    elif "番茄牛腩饭" in food_name:
        ai_result["is_healthy"] = True
        ai_result["hp_changes"] = {"fat": 8, "iron": 12, "calcium": 2, "iodine": 0, "vit_c": 8, "fiber": 3}
        ai_result["reasoning"] = "番茄牛腩饭属于米饭类盖浇饭，牛腩提供铁和蛋白质，番茄能补充一些维生素C。"
    elif "沙拉" in food_name or "青菜" in food_name:
        ai_result["is_healthy"] = True
        ai_result["hp_changes"] = {"fat": -5, "iron": 5, "calcium": 5, "iodine": 0, "vit_c": 20, "fiber": 18}
        ai_result["reasoning"] = "蔬菜类食物维生素C、矿物质和膳食纤维更丰富，整体比较清爽健康。"
    elif "奶茶" in food_name or "咖啡" in food_name:
        ai_result["is_healthy"] = False
        ai_result["hp_changes"] = {"fat": 15, "iron": -25, "calcium": -10, "iodine": 0, "vit_c": -10, "fiber": -8}
        ai_result["reasoning"] = "大量糖分和咖啡因会影响健康状态，也不适合作为正餐。"

    return normalize_ai_result(ai_result, food_name)

def load_recent_meals(db: Session, user_id: int, limit: int = 12):
    logs = db.query(models.MealLog)\
        .filter(models.MealLog.user_id == user_id)\
        .order_by(models.MealLog.created_at.desc(), models.MealLog.id.desc())\
        .limit(limit).all()

    meals = []
    for log in logs:
        try:
            parsed = json.loads(log.parsed_nutrition_json or "{}")
        except json.JSONDecodeError:
            parsed = {}

        food_name = parsed.get("food") or log.food_name or "未知食物"
        hp_changes = parsed.get("hp_changes") or {}
        meals.append({
            "id": log.id,
            "food": food_name,
            "is_healthy": bool(log.is_healthy),
            "dish_category": parsed.get("dish_category") or "其他",
            "food_type": parsed.get("food_type") or "普通餐食",
            "hp_changes": hp_changes,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })

    return meals

def summarize_meal_history(meals):
    unhealthy_count = sum(1 for meal in meals if not meal["is_healthy"])
    healthy_count = sum(1 for meal in meals if meal["is_healthy"])
    fried_count = sum(
        1
        for meal in meals
        if any(keyword in meal["food"] for keyword in ["炸鸡", "汉堡", "薯条", "油炸"])
    )
    fiber_support_count = sum(
        1
        for meal in meals
        if any(keyword in meal["food"] for keyword in ["沙拉", "青菜", "蔬菜", "西兰花", "杂粮", "玉米"])
        or int((meal["hp_changes"] or {}).get("fiber", 0) or 0) > 0
    )
    recent_healthy_streak = 0
    for meal in meals:
        if meal["is_healthy"]:
            recent_healthy_streak += 1
        else:
            break

    return {
        "total_recent_meals": len(meals),
        "healthy_count": healthy_count,
        "unhealthy_count": unhealthy_count,
        "fried_count": fried_count,
        "fiber_support_count": fiber_support_count,
        "recent_healthy_streak": recent_healthy_streak,
    }

def calculate_overall_score(pet: models.Pet):
    nutrients = [
        pet.health_hp,
        pet.iron_hp,
        pet.calcium_hp,
        pet.iodine_hp,
        pet.vit_c_hp,
        getattr(pet, "fiber_hp", 100) or 100,
        100 - pet.fat_level,
    ]
    return clamp_hp(sum(nutrients) / len(nutrients))

def calculate_home_state(pet: models.Pet, history_summary):
    overall_score = calculate_overall_score(pet)
    diseases = calculate_disease_states(pet)
    severe_count = sum(1 for disease in diseases if disease["severity"] == "severe")
    fried_count = history_summary["fried_count"]
    recent_healthy_streak = history_summary["recent_healthy_streak"]

    if pet.health_hp <= 0:
        return {
            "state": "dead",
            "image_key": "nighthome",
            "message": "房间几乎没有光，小兔子需要立刻恢复健康饮食。",
        }
    if severe_count > 0 or fried_count >= 4 or overall_score < 45:
        return {
            "state": "dark",
            "image_key": "nighthome",
            "message": "最近负担太重，home 变暗了。少吃油炸，多补蔬菜和粗粮。",
        }
    if fried_count >= 2 or history_summary["unhealthy_count"] >= 3 or overall_score < 70:
        return {
            "state": "sick",
            "image_key": "sickhome",
            "message": "home 有点暗，小兔子的状态在提醒你调整饮食。",
        }
    if recent_healthy_streak >= 3 and overall_score >= 85:
        return {
            "state": "bright",
            "image_key": "betterhome",
            "message": "最近吃得很稳，home 变得明亮，小兔子也更有精神。",
        }
    if overall_score >= 80:
        return {
            "state": "healthy",
            "image_key": "healthhome",
            "message": "home 状态不错，继续保持均衡饮食。",
        }
    return {
        "state": "normal",
        "image_key": "normal",
        "message": "home 保持普通状态，下一餐可以补一点蔬菜或粗粮。",
    }

def calculate_pet_status_text(overall_score: int, home: dict, active_diseases: list, history_summary: dict):
    """Keep the short status label consistent with the room state and recent diet."""
    home_state = home.get("state")
    severe_count = sum(1 for disease in active_diseases if disease.get("severity") == "severe")
    mild_count = sum(1 for disease in active_diseases if disease.get("severity") == "mild")

    if home_state == "dead":
        return "急需恢复"
    if home_state == "dark" or severe_count > 0:
        return "负担偏重"
    if home_state == "sick" or mild_count > 0 or history_summary.get("unhealthy_count", 0) >= 3:
        return "需要调整"
    if home_state == "bright":
        return "状态很好"
    if home_state == "healthy" and overall_score >= 80:
        return "状态不错"
    if overall_score < 70:
        return "需要照顾"
    return "状态稳定"

def build_pet_status(db: Session, pet: models.Pet, user_id: int):
    recent_meals = load_recent_meals(db, user_id)
    history_summary = summarize_meal_history(recent_meals)
    active_diseases = calculate_disease_states(pet)
    home = calculate_home_state(pet, history_summary)
    overall_score = calculate_overall_score(pet)

    attributes = {
        "health": pet.health_hp,
        "fat": pet.fat_level,
        "iron": pet.iron_hp,
        "calcium": pet.calcium_hp,
        "iodine": pet.iodine_hp,
        "vit_c": pet.vit_c_hp,
        "fiber": getattr(pet, "fiber_hp", 100) or 100,
    }
    attribute_items = [
        {
            "key": key,
            "label": NUTRIENT_LABELS[key],
            "value": value,
            "is_inverse": key == "fat",
        }
        for key, value in attributes.items()
    ]

    return {
        "pet": {
            "name": pet.name,
            "stage": pet.stage,
            "overall_score": overall_score,
            "status_text": calculate_pet_status_text(overall_score, home, active_diseases, history_summary),
        },
        "home": home,
        "attributes": attribute_items,
        "active_diseases": active_diseases,
        "history_summary": history_summary,
        "recent_meals": recent_meals,
    }

@app.post("/meals/analyze")
def analyze_meal(meal_req: MealRequest, db: Session = Depends(get_db)):
    """Mock AI 饮食分析接口，并执行结算逻辑"""
    pet = get_or_create_pet(db, meal_req.user_id)
    stats = get_or_create_stats(db, meal_req.user_id)

    if meal_req.image_base64:
        ai_result = analyze_food_image_with_ai(
            meal_req.image_base64,
            text_hint=meal_req.food_name,
        )
    else:
        ai_result = analyze_food_by_name(meal_req.food_name)
    
    # 结算数值（更新数据库中的宠物状态）
    changes = ai_result["hp_changes"]
    apply_pet_effects(pet, changes)
    pet.health_hp = clamp_hp(pet.health_hp + (3 if ai_result["is_healthy"] else -6))
    pet.exp = pet.exp + (5 if ai_result["is_healthy"] else 1)
    stats.photo_count = (stats.photo_count or 0) + 1
    
    db.commit()
    db.refresh(pet)

    # 记录这次饮食日志 (MealLog)
    import json
    log = models.MealLog(
        user_id=meal_req.user_id,
        food_name=ai_result["food"],
        parsed_nutrition_json=json.dumps(ai_result, ensure_ascii=False),
        is_healthy=ai_result["is_healthy"]
    )
    db.add(log)
    db.commit()

    # 重新计算宠物的最新状态
    pet_status = build_pet_status(db, pet, meal_req.user_id)
    newly_collected_events = collect_available_events(db, meal_req.user_id, pet_status, "meal_photo")

    return {
        "analysis": ai_result,
        "pet_current_state": {
            "hp": {
                "health": pet.health_hp,
                "fat": pet.fat_level,
                "iron": pet.iron_hp,
                "calcium": pet.calcium_hp,
                "iodine": pet.iodine_hp,
                "vit_c": pet.vit_c_hp,
                "fiber": pet.fiber_hp,
            },
            "active_diseases": pet_status["active_diseases"],
            "home": pet_status["home"],
        },
        "newly_collected_events": newly_collected_events,
    }

@app.post("/cravings/advice")
def get_craving_advice(request: CravingAdviceRequest, db: Session = Depends(get_db)):
    pet = get_or_create_pet(db, request.user_id)
    stats = get_or_create_stats(db, request.user_id)
    pet_context = {
        "fat": pet.fat_level,
        "iron": pet.iron_hp,
        "calcium": pet.calcium_hp,
        "iodine": pet.iodine_hp,
        "vit_c": pet.vit_c_hp,
        "fiber": getattr(pet, "fiber_hp", 100) or 100,
        "active_diseases": calculate_disease_states(pet),
    }

    advice = get_food_advice_from_ai(
        craving=request.craving,
        location=request.location or "附近",
        pet_context=pet_context,
    )
    stats.ask_count = (stats.ask_count or 0) + 1
    db.commit()
    pet_status = build_pet_status(db, pet, request.user_id)
    newly_collected_events = collect_available_events(db, request.user_id, pet_status, "craving_advice")

    return {
        "advice": advice,
        "pet_current_state": {
            "hp": {
                "fat": pet.fat_level,
                "iron": pet.iron_hp,
                "calcium": pet.calcium_hp,
                "iodine": pet.iodine_hp,
                "vit_c": pet.vit_c_hp,
                "fiber": getattr(pet, "fiber_hp", 100) or 100,
            },
            "active_diseases": pet_context["active_diseases"],
        },
        "newly_collected_events": newly_collected_events,
    }

@app.get("/health-tasks/{user_id}/today")
def get_today_health_tasks(user_id: int, db: Session = Depends(get_db)):
    pet = get_or_create_pet(db, user_id)
    get_or_create_stats(db, user_id)
    task_date = get_today_key()
    completed_rows = db.query(models.HealthTaskCompletion)\
        .filter(
            models.HealthTaskCompletion.user_id == user_id,
            models.HealthTaskCompletion.task_date == task_date,
        )\
        .all()
    completed_ids = {row.task_id for row in completed_rows}
    tasks = [
        serialize_task(task, completed_ids)
        for task in get_daily_tasks_for_user(user_id, task_date)
    ]
    pet_status = build_pet_status(db, pet, user_id)
    newly_collected_events = collect_available_events(db, user_id, pet_status, "health_task_panel")

    return {
        "date": task_date,
        "tasks": tasks,
        "completed_count": len(completed_ids),
        "pet_status": pet_status,
        "newly_collected_events": newly_collected_events,
        "event_collection": build_event_collection(db, user_id),
    }

@app.post("/health-tasks/complete")
def complete_health_task(request: HealthTaskCompleteRequest, db: Session = Depends(get_db)):
    pet = get_or_create_pet(db, request.user_id)
    stats = get_or_create_stats(db, request.user_id)
    task_date = get_today_key()
    daily_tasks = get_daily_tasks_for_user(request.user_id, task_date)
    selected_task = next((task for task in daily_tasks if task["id"] == request.task_id), None)

    if selected_task is None:
        raise HTTPException(status_code=400, detail="这个任务不是今天的健康任务")

    existing = db.query(models.HealthTaskCompletion)\
        .filter(
            models.HealthTaskCompletion.user_id == request.user_id,
            models.HealthTaskCompletion.task_id == request.task_id,
            models.HealthTaskCompletion.task_date == task_date,
        )\
        .first()

    if existing:
        completed_rows = db.query(models.HealthTaskCompletion)\
            .filter(
                models.HealthTaskCompletion.user_id == request.user_id,
                models.HealthTaskCompletion.task_date == task_date,
            )\
            .all()
        completed_ids = {row.task_id for row in completed_rows}
        pet_status = build_pet_status(db, pet, request.user_id)
        return {
            "message": "这个任务今天已经完成过了。",
            "already_completed": True,
            "task": serialize_task(selected_task, completed_ids),
            "pet_status": pet_status,
            "newly_collected_events": [],
            "event_collection": build_event_collection(db, request.user_id),
        }

    apply_pet_effects(pet, selected_task["effects"])
    pet.exp = pet.exp + 3
    stats.task_count = (stats.task_count or 0) + 1

    completion = models.HealthTaskCompletion(
        user_id=request.user_id,
        task_id=request.task_id,
        task_date=task_date,
        effects_json=json.dumps(selected_task["effects"], ensure_ascii=False),
    )
    db.add(completion)
    db.commit()
    db.refresh(pet)

    completed_rows = db.query(models.HealthTaskCompletion)\
        .filter(
            models.HealthTaskCompletion.user_id == request.user_id,
            models.HealthTaskCompletion.task_date == task_date,
        )\
        .all()
    completed_ids = {row.task_id for row in completed_rows}
    pet_status = build_pet_status(db, pet, request.user_id)
    newly_collected_events = collect_available_events(db, request.user_id, pet_status, "health_task")

    return {
        "message": selected_task["pet_message"],
        "already_completed": False,
        "task": serialize_task(selected_task, completed_ids),
        "tasks": [serialize_task(task, completed_ids) for task in daily_tasks],
        "pet_status": pet_status,
        "newly_collected_events": newly_collected_events,
        "event_collection": build_event_collection(db, request.user_id),
    }

@app.get("/events/{user_id}")
def read_event_collection(user_id: int, db: Session = Depends(get_db)):
    pet = get_or_create_pet(db, user_id)
    pet_status = build_pet_status(db, pet, user_id)
    newly_collected_events = collect_available_events(db, user_id, pet_status, "event_collection")
    return {
        "newly_collected_events": newly_collected_events,
        "event_collection": build_event_collection(db, user_id),
    }

@app.get("/pets/{user_id}/status")
def read_pet_status(user_id: int, db: Session = Depends(get_db)):
    pet = get_or_create_pet(db, user_id)
    return build_pet_status(db, pet, user_id)

@app.patch("/pets/{user_id}/name")
def update_pet_name(user_id: int, request: PetNameRequest, db: Session = Depends(get_db)):
    pet = get_or_create_pet(db, user_id)
    pet_name = request.name.strip()

    if not pet_name:
        raise HTTPException(status_code=400, detail="宠物名字不能为空")
    if len(pet_name) > 16:
        raise HTTPException(status_code=400, detail="宠物名字最多 16 个字符")

    pet.name = pet_name
    db.commit()
    db.refresh(pet)

    return build_pet_status(db, pet, user_id)

@app.get("/pets/{user_id}/recommendations")
def get_food_recommendations(user_id: int, db: Session = Depends(get_db)):
    """根据宠物当前最缺乏的营养，从食堂图鉴中推荐食物"""
    pet = db.query(models.Pet).filter(models.Pet.user_id == user_id).first()
    if pet is None:
        raise HTTPException(status_code=404, detail="Pet not found")

    # 1. 找出宠物最缺的营养素 (HP最低的那个)
    hp_dict = {
        "iron": pet.iron_hp,
        "calcium": pet.calcium_hp,
        "iodine": pet.iodine_hp,
        "vit_c": pet.vit_c_hp,
        "fiber": getattr(pet, "fiber_hp", 100) or 100,
    }
    
    # 找到 HP 最低的一项
    most_lacking_element = min(hp_dict, key=hp_dict.get)
    lowest_hp = hp_dict[most_lacking_element]

    # 如果所有 HP 都在 80 以上，说明很健康，随便推荐点低脂健康的
    if lowest_hp >= 80:
        recommendations = db.query(models.FoodDictionary)\
            .filter(models.FoodDictionary.is_healthy_option == True)\
            .order_by(models.FoodDictionary.calories.asc())\
            .limit(2).all()
        reason = "宠物目前非常健康！推荐一些低卡路里的轻食保持状态。"
    
    # 否则，针对性推荐（比如最缺铁，就按 iron_score 降序排）
    else:
        if most_lacking_element == "iron":
            order_by_field = models.FoodDictionary.iron_score.desc()
            reason = "宠物现在面色苍白，非常缺铁！建议去食堂吃这些补铁的食物："
        elif most_lacking_element == "calcium":
            order_by_field = models.FoodDictionary.calcium_score.desc()
            reason = "宠物骨骼有些脆弱（缺钙）！建议去食堂吃这些高钙食物："
        elif most_lacking_element == "iodine":
            order_by_field = models.FoodDictionary.iodine_score.desc()
            reason = "宠物缺乏碘元素！建议去食堂吃这些海产品："
        elif most_lacking_element == "fiber":
            order_by_field = models.FoodDictionary.vit_c_score.desc()
            reason = "宠物缺乏膳食纤维！建议吃蔬菜、杂粮和菌菇类餐品："
        else: # vit_c
            order_by_field = models.FoodDictionary.vit_c_score.desc()
            reason = "宠物缺乏维生素C！建议去食堂吃这些富含维C的食物："

        recommendations = db.query(models.FoodDictionary)\
            .filter(models.FoodDictionary.is_healthy_option == True)\
            .order_by(order_by_field)\
            .limit(2).all()

    return {
        "most_lacking_element": most_lacking_element,
        "current_hp": lowest_hp,
        "reasoning": reason,
        "recommendations": recommendations
    }

@app.get("/pets/{user_id}")
def read_pet(user_id: int, db: Session = Depends(get_db)):
    pet = get_or_create_pet(db, user_id)
    
    active_diseases = calculate_disease_states(pet)
    
    return {
        "pet": pet,
        "active_diseases": active_diseases
    }
