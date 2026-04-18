from database import SessionLocal, engine, Base
import models

# 确保表已经创建
Base.metadata.create_all(bind=engine)

def seed_foods():
    db = SessionLocal()
    
    # 检查是否已经有数据了，避免重复插入
    if db.query(models.FoodDictionary).first():
        print("数据库中已存在食物数据，跳过初始化。")
        db.close()
        return

    print("开始向数据库写入初始食堂菜品数据...")
    
    foods_data = [
        {
            "name": "菠菜猪肝汤",
            "ingredients": "菠菜, 猪肝, 姜片",
            "calories": 150.0, "protein": 15.0, "fat": 5.0, "carbs": 10.0,
            "iron_score": 10, "calcium_score": 3, "iodine_score": 1, "vit_c_score": 6,
            "price": 12.0, "location": "二食堂一楼营养汤窗口",
            "is_healthy_option": True
        },
        {
            "name": "清炒西兰花",
            "ingredients": "西兰花, 蒜蓉",
            "calories": 80.0, "protein": 4.0, "fat": 3.0, "carbs": 12.0,
            "iron_score": 4, "calcium_score": 6, "iodine_score": 1, "vit_c_score": 9,
            "price": 6.0, "location": "一食堂二楼自选菜",
            "is_healthy_option": True
        },
        {
            "name": "虾皮紫菜豆腐汤",
            "ingredients": "紫菜, 豆腐, 虾皮",
            "calories": 120.0, "protein": 10.0, "fat": 4.0, "carbs": 8.0,
            "iron_score": 3, "calcium_score": 9, "iodine_score": 8, "vit_c_score": 2,
            "price": 8.0, "location": "三食堂风味餐厅",
            "is_healthy_option": True
        },
        {
            "name": "海带排骨汤",
            "ingredients": "海带, 猪排骨",
            "calories": 250.0, "protein": 18.0, "fat": 15.0, "carbs": 5.0,
            "iron_score": 5, "calcium_score": 5, "iodine_score": 10, "vit_c_score": 1,
            "price": 15.0, "location": "二食堂一楼营养汤窗口",
            "is_healthy_option": True
        },
        {
            "name": "牛奶麦片粥",
            "ingredients": "纯牛奶, 燕麦片",
            "calories": 200.0, "protein": 8.0, "fat": 6.0, "carbs": 30.0,
            "iron_score": 2, "calcium_score": 10, "iodine_score": 2, "vit_c_score": 0,
            "price": 5.0, "location": "一食堂一楼早餐区",
            "is_healthy_option": True
        },
        {
            "name": "脆皮炸鸡排",
            "ingredients": "鸡胸肉, 面包糠, 食用油",
            "calories": 600.0, "protein": 25.0, "fat": 40.0, "carbs": 45.0,
            "iron_score": 2, "calcium_score": 1, "iodine_score": 0, "vit_c_score": 0,
            "price": 16.0, "location": "三食堂快餐区",
            "is_healthy_option": False
        }
    ]

    for data in foods_data:
        food = models.FoodDictionary(**data)
        db.add(food)
    
    db.commit()
    db.close()
    print(f"成功插入 {len(foods_data)} 条食堂菜品数据！")

if __name__ == "__main__":
    seed_foods()