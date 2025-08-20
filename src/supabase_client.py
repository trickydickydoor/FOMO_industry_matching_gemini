"""
Supabase数据库客户端模块
"""
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any
from supabase import create_client, Client
import logging
from config import SUPABASE_URL, SUPABASE_KEY, HOURS_LOOKBACK

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Supabase数据库客户端"""
    
    def __init__(self):
        """初始化Supabase客户端"""
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("Missing Supabase credentials")
        
        self.client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase client initialized")
    
    def get_unprocessed_news(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取过去指定小时内未处理的新闻
        
        Args:
            limit: 返回的最大新闻数量
        
        Returns:
            未处理的新闻列表
        """
        try:
            # 计算时间范围
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=HOURS_LOOKBACK)
            
            # 添加调试日志
            logger.info(f"Querying news from {start_time.isoformat()} to {end_time.isoformat()}")
            logger.info(f"Looking back {HOURS_LOOKBACK} hours")
            
            # 构建查询
            query = self.client.table("news_items").select("*")
            
            # 时间过滤
            query = query.gte("published_at", start_time.isoformat())
            query = query.lte("published_at", end_time.isoformat())
            
            # 过滤未分类的新闻
            query = query.eq("industry_classified", False)
            
            # 按发布时间降序排序
            query = query.order("published_at", desc=True)
            
            # 限制数量
            if limit:
                query = query.limit(limit)
            
            # 执行查询
            response = query.execute()
            
            news_items = response.data
            logger.info(f"Found {len(news_items)} unprocessed news items")
            
            # 如果没有找到数据，尝试查看所有数据
            if len(news_items) == 0:
                logger.info("No items found, checking total count in database...")
                total_query = self.client.table("news_items").select("count", count="exact")
                total_response = total_query.execute()
                logger.info(f"Total items in database: {total_response.count}")
                
                # 查看最近的几条数据
                recent_query = self.client.table("news_items").select("published_at,industries").order("published_at", desc=True).limit(5)
                recent_response = recent_query.execute()
                logger.info(f"Recent items: {recent_response.data}")
            
            return news_items
            
        except Exception as e:
            logger.error(f"Error fetching unprocessed news: {e}")
            raise
    
    def update_news_industries(self, news_id: str, industries: List[str]) -> bool:
        """
        更新新闻的行业分类
        
        Args:
            news_id: 新闻ID
            industries: 行业列表
        
        Returns:
            是否更新成功
        """
        try:
            # 更新industries字段和分类状态
            response = self.client.table("news_items").update({
                "industries": industries,
                "industry_classified": True
            }).eq("id", news_id).execute()
            
            if response.data:
                logger.info(f"Updated news {news_id} with industries: {industries}")
                return True
            else:
                logger.warning(f"Failed to update news {news_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating news {news_id}: {e}")
            return False
    
    def batch_update_news_industries(self, updates: List[Dict[str, Any]]) -> int:
        """
        批量更新新闻的行业分类
        
        Args:
            updates: 更新列表，每个元素包含 {"id": news_id, "industries": [行业列表]}
        
        Returns:
            成功更新的数量
        """
        success_count = 0
        
        for update in updates:
            if self.update_news_industries(update["id"], update["industries"]):
                success_count += 1
        
        logger.info(f"Successfully updated {success_count}/{len(updates)} news items")
        return success_count
    
    # API使用跟踪相关方法
    def get_api_usage(self, model_name: str, date: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """
        获取API使用情况
        
        Args:
            model_name: 模型名称
            date: 日期（默认为今天）
        
        Returns:
            API使用记录
        """
        try:
            if date is None:
                date = datetime.now(timezone.utc).date()
            
            response = self.client.table("api_usage").select("*").eq(
                "service_name", "gemini"
            ).eq(
                "model_name", model_name
            ).eq(
                "date", date.isoformat()
            ).execute()
            
            if response.data:
                return response.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Error fetching API usage: {e}")
            return None
    
    def update_api_usage(self, model_name: str, requests: int = 1, tokens: int = 0) -> bool:
        """
        更新API使用情况
        
        Args:
            model_name: 模型名称
            requests: 请求次数增量
            tokens: Token使用量增量
        
        Returns:
            是否更新成功
        """
        try:
            now = datetime.now(timezone.utc)
            today = now.date()
            current_minute = now.minute
            
            # 获取或创建今天的记录
            usage = self.get_api_usage(model_name, today)
            
            if usage:
                # 检查是否是新的一分钟
                last_request = datetime.fromisoformat(usage["last_request_at"].replace('Z', '+00:00'))
                if last_request.minute != current_minute:
                    # 新的一分钟，重置分钟计数器
                    new_rpm = requests
                    new_tpm = tokens
                else:
                    # 同一分钟内，累加
                    new_rpm = usage["requests_per_minute"] + requests
                    new_tpm = usage["tokens_per_minute"] + tokens
                
                # 更新记录
                response = self.client.table("api_usage").update({
                    "requests_per_minute": new_rpm,
                    "requests_per_day": usage["requests_per_day"] + requests,
                    "tokens_per_minute": new_tpm,
                    "tokens_per_day": usage["tokens_per_day"] + tokens,
                    "minute_window": current_minute,
                    "last_request_at": now.isoformat()
                }).eq("id", usage["id"]).execute()
                
            else:
                # 创建新记录
                response = self.client.table("api_usage").insert({
                    "service_name": "gemini",
                    "model_name": model_name,
                    "date": today.isoformat(),
                    "hour": now.hour,
                    "minute_window": current_minute,
                    "requests_per_minute": requests,
                    "requests_per_day": requests,
                    "tokens_per_minute": tokens,
                    "tokens_per_day": tokens,
                    "last_request_at": now.isoformat()
                }).execute()
            
            return bool(response.data)
            
        except Exception as e:
            logger.error(f"Error updating API usage: {e}")
            return False
    
    def check_api_limits(self, model_name: str, limits: Dict[str, int]) -> Dict[str, bool]:
        """
        检查API限制
        
        Args:
            model_name: 模型名称
            limits: 限制配置
        
        Returns:
            各项限制的检查结果
        """
        try:
            usage = self.get_api_usage(model_name)
            
            if not usage:
                # 没有使用记录，所有限制都通过
                return {
                    "rpm_ok": True,
                    "tpm_ok": True,
                    "rpd_ok": True
                }
            
            now = datetime.now(timezone.utc)
            last_request = datetime.fromisoformat(usage["last_request_at"].replace('Z', '+00:00'))
            
            # 检查是否是新的一分钟
            if last_request.minute != now.minute:
                # 新的一分钟，RPM和TPM限制通过
                rpm_ok = True
                tpm_ok = True
            else:
                # 同一分钟内，检查限制
                rpm_ok = usage["requests_per_minute"] < limits["rpm"]
                tpm_ok = usage["tokens_per_minute"] < limits["tpm"]
            
            # 检查每日限制
            rpd_ok = usage["requests_per_day"] < limits["rpd"]
            
            return {
                "rpm_ok": rpm_ok,
                "tpm_ok": tpm_ok,
                "rpd_ok": rpd_ok
            }
            
        except Exception as e:
            logger.error(f"Error checking API limits: {e}")
            # 出错时保守处理，返回限制未通过
            return {
                "rpm_ok": False,
                "tpm_ok": False,
                "rpd_ok": False
            }