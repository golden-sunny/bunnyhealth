from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    target_calories = Column(Float, default=2000.0) # 每日目标摄入热量
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    pets = relationship("Pet", back_populates="owner")
    meal_logs = relationship("MealLog", back_populates="user")

class Pet(Base):
    __tablename__ = "pets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, default="Bunny")
    stage = Column(String, default="baby") # 阶段：baby, adult
    health_hp = Column(Integer, default=100) # 整体健康生命值
    fat_level = Column(Integer, default=0) # 肥胖值，吃垃圾食品增加
    
    # 细分微量元素健康值 (满分 100，低于 80 为轻度，低于 40 为重度)
    vit_c_hp = Column(Integer, default=100) # 维C
    iron_hp = Column(Integer, default=100)  # 铁 (Fe)
    calcium_hp = Column(Integer, default=100) # 钙 (Ca)
    iodine_hp = Column(Integer, default=100)  # 碘 (I)
    fiber_hp = Column(Integer, default=100)  # 膳食纤维

    exp = Column(Integer, default=0) # 经验值，健康饮食增加

    owner = relationship("User", back_populates="pets")

class FoodDictionary(Base):
    """食堂菜单数据库，供推荐使用"""
    __tablename__ = "food_dictionary"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True) # 如：香煎鸡胸肉
    ingredients = Column(String) # 主要原料
    
    # 宏量营养素
    calories = Column(Float)
    protein = Column(Float)
    fat = Column(Float)
    carbs = Column(Float)
    
    # 微量元素 (用于智能推荐，1-10分制，分数越高代表该元素越丰富)
    iron_score = Column(Integer, default=0)    # 补铁评分
    calcium_score = Column(Integer, default=0) # 补钙评分
    iodine_score = Column(Integer, default=0)  # 补碘评分
    vit_c_score = Column(Integer, default=0)   # 补维C评分
    
    price = Column(Float)
    location = Column(String) # 如：一食堂二楼
    is_healthy_option = Column(Boolean, default=True) # 是否是健康推荐菜

class MealLog(Base):
    """用户餐饮记录（拍照上传的结果）"""
    __tablename__ = "meal_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    image_url = Column(String, nullable=True) # 如果传了照片就存S3/OSS链接
    food_name = Column(String)
    parsed_nutrition_json = Column(String) # AI大模型返回的营养成分 JSON 字符串
    is_healthy = Column(Boolean, default=True) # 本次饮食是否健康
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="meal_logs")

class HealthTaskCompletion(Base):
    """每日健康任务完成记录"""
    __tablename__ = "health_task_completions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    task_id = Column(String, index=True)
    task_date = Column(String, index=True)
    effects_json = Column(String)
    completed_at = Column(DateTime(timezone=True), server_default=func.now())

class PetEventCollection(Base):
    """趣味随机事件收集记录"""
    __tablename__ = "pet_event_collections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    event_id = Column(String, index=True)
    title = Column(String)
    description = Column(String)
    trigger_source = Column(String)
    collected_at = Column(DateTime(timezone=True), server_default=func.now())

class UserActionStats(Base):
    """用户累计行为，用来触发随机事件"""
    __tablename__ = "user_action_stats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True)
    photo_count = Column(Integer, default=0)
    ask_count = Column(Integer, default=0)
    task_count = Column(Integer, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
