"""
配置管理模块
"""
import os
from typing import Dict, List
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# Supabase配置
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# Gemini API配置
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")

# 模型限制配置 (RPM, TPM, RPD)
MODEL_LIMITS = {
    "gemini-2.0-flash-lite": {
        "rpm": 30,  # Requests per minute
        "tpm": 1000000,  # Tokens per minute
        "rpd": 200,  # Requests per day
    },
    "gemini-2.0-flash": {
        "rpm": 15,
        "tpm": 1000000,
        "rpd": 200,
    },
    "gemini-2.5-flash-lite": {
        "rpm": 15,
        "tpm": 250000,
        "rpd": 1000,
    },
    "gemini-2.5-flash": {
        "rpm": 10,
        "tpm": 250000,
        "rpd": 250,
    },
    "gemini-2.5-pro": {
        "rpm": 5,
        "tpm": 250000,
        "rpd": 100,
    }
}

# 行业映射
INDUSTRY_MAPPING = {
    "5g_communication": "5G通信",
    "agricultural_technology": "农业科技",
    "ai": "人工智能",
    "aigc": "AIGC",
    "automotive_manufacturing": "汽车制造",
    "autonomous_driving": "智能驾驶",
    "biotechnology": "生物医药",
    "cloud_computing": "云计算",
    "commercial_space": "商业航天",
    "construction_engineering": "建筑工程",
    "content_creation": "内容创作",
    "cross_border_ecommerce": "跨境电商",
    "cultural_creative": "文化创意",
    "cybersecurity": "网络安全",
    "ecommerce": "电子商务",
    "enterprise_services": "企业服务",
    "fintech": "金融科技",
    "gaming": "游戏",
    "healthcare": "大健康",
    "idc_data_center": "IDC数据中心",
    "iot": "物联网",
    "local_life_services": "本地生活服务",
    "logistics_express": "物流快递",
    "medical_devices": "医疗器械",
    "new_energy_vehicles": "新能源汽车",
    "new_materials": "新材料",
    "online_education": "在线教育",
    "petrochemicals": "石油化工",
    "real_estate": "房地产",
    "renewable_energy": "新能源",
    "retail_consumer": "零售消费",
    "robotics": "机器人",
    "saas": "SaaS",
    "semiconductor": "半导体",
    "short_video_live_streaming": "短视频直播",
    "smart_manufacturing": "智能制造",
    "steel_metallurgy": "钢铁冶金",
    "textile_apparel": "纺织服装",
    "tourism_hotels": "旅游酒店"
}

# 获取所有行业的中文名称列表
INDUSTRIES_CN = list(INDUSTRY_MAPPING.values())

# 英文行业标签映射（标准化的英文名称 -> 中文）
INDUSTRIES_EN_MAPPING = {
    "5G Communication": "5G通信",
    "Agricultural Technology": "农业科技",
    "Artificial Intelligence": "人工智能",
    "AI Generated Content": "AIGC",
    "Automotive Manufacturing": "汽车制造",
    "Autonomous Driving": "智能驾驶",
    "Biotechnology": "生物医药",
    "Cloud Computing": "云计算",
    "Commercial Space": "商业航天",
    "Construction Engineering": "建筑工程",
    "Content Creation": "内容创作",
    "Cross-border E-commerce": "跨境电商",
    "Cultural Creative": "文化创意",
    "Cybersecurity": "网络安全",
    "E-commerce": "电子商务",
    "Enterprise Services": "企业服务",
    "Fintech": "金融科技",
    "Gaming": "游戏",
    "Healthcare": "大健康",
    "Data Center": "IDC数据中心",
    "Internet of Things": "物联网",
    "Local Services": "本地生活服务",
    "Logistics": "物流快递",
    "Medical Devices": "医疗器械",
    "Electric Vehicles": "新能源汽车",
    "New Materials": "新材料",
    "Online Education": "在线教育",
    "Petrochemicals": "石油化工",
    "Real Estate": "房地产",
    "Renewable Energy": "新能源",
    "Retail": "零售消费",
    "Robotics": "机器人",
    "SaaS": "SaaS",
    "Semiconductor": "半导体",
    "Live Streaming": "短视频直播",
    "Smart Manufacturing": "智能制造",
    "Steel": "钢铁冶金",
    "Textile": "纺织服装",
    "Tourism": "旅游酒店"
}

# 获取所有英文行业标签
INDUSTRIES_EN = list(INDUSTRIES_EN_MAPPING.keys())

# 批处理配置
BATCH_SIZE = 5  # 每批处理的新闻数量
MAX_RETRIES = 3  # 最大重试次数
RETRY_DELAY = 5  # 重试延迟（秒）

# 时间配置
HOURS_LOOKBACK = 2  # 查询过去多少小时的新闻
TIMEZONE = "Asia/Shanghai"  # 时区设置