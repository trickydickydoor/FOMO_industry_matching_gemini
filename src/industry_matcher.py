"""
行业匹配核心逻辑模块
"""
import logging
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime
from supabase_client import SupabaseClient
from gemini_client import GeminiClient
from rate_limiter import RateLimiter
from config import BATCH_SIZE, GEMINI_MODEL

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class IndustryMatcher:
    """行业匹配器"""
    
    def __init__(self):
        """初始化行业匹配器"""
        logger.info("Initializing Industry Matcher...")
        
        # 初始化Supabase客户端
        self.supabase = SupabaseClient()
        
        # 初始化速率限制器
        self.rate_limiter = RateLimiter(self.supabase)
        
        # 初始化Gemini客户端
        self.gemini = GeminiClient(self.rate_limiter)
        
        # 统计信息
        self.stats = {
            "total_processed": 0,
            "successfully_classified": 0,
            "failed": 0,
            "skipped": 0,
            "start_time": None,
            "end_time": None
        }
        
        logger.info("Industry Matcher initialized successfully")
    
    def process_batch(self, news_items: List[Dict[str, Any]]) -> int:
        """
        处理一批新闻
        
        Args:
            news_items: 新闻列表
        
        Returns:
            成功处理的数量
        """
        if not news_items:
            return 0
        
        logger.info(f"Processing batch of {len(news_items)} news items")
        
        try:
            # 调用Gemini进行分类
            classifications = self.gemini.classify_news_batch(news_items)
            
            if not classifications:
                logger.warning("No classifications returned from Gemini")
                self.stats["failed"] += len(news_items)
                return 0
            
            # 构建更新列表
            updates = []
            classification_map = {c["id"]: c["industries"] for c in classifications}
            
            for news_item in news_items:
                news_id = news_item["id"]
                
                if news_id in classification_map:
                    industries = classification_map[news_id]
                    
                    if industries:  # 只更新有行业分类的新闻
                        updates.append({
                            "id": news_id,
                            "industries": industries
                        })
                        logger.info(f"News {news_id}: {industries}")
                    else:
                        logger.warning(f"News {news_id}: No industries identified")
                        self.stats["skipped"] += 1
                else:
                    logger.warning(f"News {news_id}: Not in classification results")
                    self.stats["failed"] += 1
            
            # 批量更新数据库
            if updates:
                success_count = self.supabase.batch_update_news_industries(updates)
                self.stats["successfully_classified"] += success_count
                return success_count
            
            return 0
            
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            self.stats["failed"] += len(news_items)
            return 0
    
    def run(self, limit: Optional[int] = None):
        """
        运行行业匹配流程
        
        Args:
            limit: 最大处理数量限制
        """
        logger.info("=" * 50)
        logger.info("Starting Industry Matching Process")
        logger.info(f"Time: {datetime.now()}")
        logger.info(f"Model: {GEMINI_MODEL}")
        logger.info(f"Batch size: {BATCH_SIZE}")
        logger.info("=" * 50)
        
        self.stats["start_time"] = datetime.now()
        
        try:
            # 获取未处理的新闻
            logger.info("Fetching unprocessed news...")
            news_items = self.supabase.get_unprocessed_news(limit=limit)
            
            if not news_items:
                logger.info("No unprocessed news found")
                return
            
            self.stats["total_processed"] = len(news_items)
            logger.info(f"Found {len(news_items)} unprocessed news items")
            
            # 分批处理
            for i in range(0, len(news_items), BATCH_SIZE):
                batch = news_items[i:i + BATCH_SIZE]
                batch_num = (i // BATCH_SIZE) + 1
                total_batches = (len(news_items) + BATCH_SIZE - 1) // BATCH_SIZE
                
                logger.info(f"\nProcessing batch {batch_num}/{total_batches}")
                self.process_batch(batch)
            
        except Exception as e:
            logger.error(f"Error in main process: {e}")
        
        finally:
            self.stats["end_time"] = datetime.now()
            self.print_summary()
    
    def print_summary(self):
        """打印处理摘要"""
        duration = None
        if self.stats["start_time"] and self.stats["end_time"]:
            duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
        
        logger.info("\n" + "=" * 50)
        logger.info("PROCESSING SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Total news items: {self.stats['total_processed']}")
        logger.info(f"Successfully classified: {self.stats['successfully_classified']}")
        logger.info(f"Failed: {self.stats['failed']}")
        logger.info(f"Skipped (no industry): {self.stats['skipped']}")
        
        if self.stats['total_processed'] > 0:
            success_rate = (self.stats['successfully_classified'] / self.stats['total_processed']) * 100
            logger.info(f"Success rate: {success_rate:.1f}%")
        
        if duration:
            logger.info(f"Duration: {duration:.1f} seconds")
            if self.stats['total_processed'] > 0:
                avg_time = duration / self.stats['total_processed']
                logger.info(f"Average time per item: {avg_time:.2f} seconds")
        
        logger.info("=" * 50)


def main():
    """主函数"""
    try:
        matcher = IndustryMatcher()
        matcher.run()
        
    except KeyboardInterrupt:
        logger.info("\nProcess interrupted by user")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()