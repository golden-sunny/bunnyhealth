from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import engine, Base, get_db
import models
from ai_vision_service import analyze_craving_with_ai

# 创建数据库所有表
Base.metadata.create_all(bind=engine)

app = FastAPI(title="BunnyHealth API")

@app.get("/")
def read_root():
    return {"message": "Welcome to BunnyHealth API"}

from pydantic import BaseModel

# 增加请求体验证模型
class MealRequest(BaseModel):
    user_id: int
    food_name: str # 暂时用文字代替图片识别结果，方便测试
    image_base64: str = None # 预留给前端传图片的字段

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

    return diseases

@app.post("/meals/analyze")
def analyze_meal(meal_req: MealRequest, db: Session = Depends(get_db)):
    """Mock AI 饮食分析接口，并执行结算逻辑"""
    pet = db.query(models.Pet).filter(models.Pet.user_id == meal_req.user_id).first()
    if pet is None:
        raise HTTPException(status_code=404, detail="Pet not found")

    food_name = meal_req.food_name.lower()
    
    # === [核心 MOCK 逻辑区] === 
    # 在接入真实 AI 大模型前，我们用这段规则引擎来模拟大模型的输出
    # 模拟 AI 返回的营养分析 JSON
    ai_result = {
        "food": food_name,
        "is_healthy": True,
        "hp_changes": {
            "fat": 0,
            "iron": 0,
            "calcium": 0,
            "iodine": 0,
            "vit_c": 0
        },
        "reasoning": "这是一顿普通的饭菜，保持了当前状态。"
    }

    # 1. 垃圾食品：炸鸡 / 汉堡
    if "炸鸡" in food_name or "汉堡" in food_name:
        ai_result["is_healthy"] = False
        ai_result["hp_changes"] = {"fat": 20, "iron": -10, "calcium": -5, "iodine": 0, "vit_c": -15}
        ai_result["reasoning"] = "炸鸡含有极高的油脂，并且缺乏维生素C和铁元素，这会让宠物变胖且免疫力下降！"
        
    # 2. 健康食品：蔬菜沙拉
    elif "沙拉" in food_name or "青菜" in food_name:
        ai_result["is_healthy"] = True
        ai_result["hp_changes"] = {"fat": -5, "iron": 5, "calcium": 5, "iodine": 0, "vit_c": 20}
        ai_result["reasoning"] = "太棒了！丰富的维生素C和矿物质让宠物恢复了活力！"

    # 3. 极度缺铁模拟：奶茶 / 咖啡
    elif "奶茶" in food_name or "咖啡" in food_name:
        ai_result["is_healthy"] = False
        ai_result["hp_changes"] = {"fat": 15, "iron": -25, "calcium": -10, "iodine": 0, "vit_c": -10}
        ai_result["reasoning"] = "大量的糖分和咖啡因阻碍了铁的吸收，宠物面临严重的贫血风险！"
    
    # === [/核心 MOCK 逻辑区结束] ===
    
    # 结算数值（更新数据库中的宠物状态）
    changes = ai_result["hp_changes"]
    pet.fat_level = max(0, min(100, pet.fat_level + changes["fat"]))
    pet.iron_hp = max(0, min(100, pet.iron_hp + changes["iron"]))
    pet.calcium_hp = max(0, min(100, pet.calcium_hp + changes["calcium"]))
    pet.iodine_hp = max(0, min(100, pet.iodine_hp + changes["iodine"]))
    pet.vit_c_hp = max(0, min(100, pet.vit_c_hp + changes["vit_c"]))
    
    db.commit()
    db.refresh(pet)

    # 记录这次饮食日志 (MealLog)
    import json
    log = models.MealLog(
        user_id=meal_req.user_id,
        food_name=food_name,
        parsed_nutrition_json=json.dumps(ai_result),
        is_healthy=ai_result["is_healthy"]
    )
    db.add(log)
    db.commit()

    # 重新计算宠物的最新状态
    active_diseases = calculate_disease_states(pet)

    return {
        "analysis": ai_result,
        "pet_current_state": {
            "hp": {
                "fat": pet.fat_level,
                "iron": pet.iron_hp,
                "calcium": pet.calcium_hp,
                "iodine": pet.iodine_hp,
                "vit_c": pet.vit_c_hp
            },
            "active_diseases": active_diseases
        }
    }

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
        "vit_c": pet.vit_c_hp
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
    pet = db.query(models.Pet).filter(models.Pet.user_id == user_id).first()
    if pet is None:
        raise HTTPException(status_code=404, detail="Pet not found")
    
    active_diseases = calculate_disease_states(pet)
    
    return {
        "pet": pet,
        "active_diseases": active_diseases
    }

class CravingRequest(BaseModel):
    user_id: int
    craving_food: str

@app.post("/cravings/analyze")
def analyze_craving(req: CravingRequest, db: Session = Depends(get_db)):
    craving = req.craving_food.lower()
    
    # 真正调用 AI 大模型进行营养学反推！
    ai_analysis = analyze_craving_with_ai(craving)
    
    lacking_element = ai_analysis.get("lacking_element", "vit_c")
    analysis_msg = ai_analysis.get("analysis_message", "分析失败。")

    # 根据推断出的缺乏元素，从食堂图鉴中找出最高评分的 2 道菜推荐给用户
    if lacking_element == "iron":
        order_by_field = models.FoodDictionary.iron_score.desc()
    elif lacking_element == "calcium":
        order_by_field = models.FoodDictionary.calcium_score.desc()
    elif lacking_element == "iodine":
        order_by_field = models.FoodDictionary.iodine_score.desc()
    else:
        order_by_field = models.FoodDictionary.vit_c_score.desc()

    recommendations = db.query(models.FoodDictionary)\
        .filter(models.FoodDictionary.is_healthy_option == True)\
        .order_by(order_by_field)\
        .limit(2).all()

    return {
        "lacking_element": lacking_element,
        "analysis_msg": analysis_msg,
        "recommendations": recommendations
    }
