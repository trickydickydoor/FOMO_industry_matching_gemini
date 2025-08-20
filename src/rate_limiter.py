"""
速率限制器模块 - 基于Supabase持久化存储
"""
import time
import logging
from typing import Dict, Optional
from datetime import datetime, timezone
from config import MODEL_LIMITS

logger = logging.getLogger(__name__)


class RateLimiter:
    """基于数据库的速率限制器"""
    
    def __init__(self, supabase_client):
        """
        初始化速率限制器
        
        Args:
            supabase_client: Supabase客户端实例
        """
        self.supabase = supabase_client
        self.current_model = None
        self.model_limits = MODEL_LIMITS
    
    def set_model(self, model_name: str):
        """
        设置当前使用的模型
        
        Args:
            model_name: 模型名称
        """
        if model_name not in self.model_limits:
            raise ValueError(f"Unknown model: {model_name}")
        self.current_model = model_name
        logger.info(f"Rate limiter set to model: {model_name}")
    
    def can_make_request(self, estimated_tokens: int = 0) -> Dict[str, bool]:
        """
        检查是否可以发送请求
        
        Args:
            estimated_tokens: 预估的token使用量
        
        Returns:
            包含各项限制检查结果的字典
        """
        if not self.current_model:
            raise ValueError("Model not set. Call set_model() first.")
        
        limits = self.model_limits[self.current_model]
        
        # 从数据库检查当前使用情况
        check_result = self.supabase.check_api_limits(self.current_model, limits)
        
        # 额外检查：预估的token是否会超过限制
        if estimated_tokens > 0:
            usage = self.supabase.get_api_usage(self.current_model)
            if usage:
                now = datetime.now(timezone.utc)
                last_request = datetime.fromisoformat(usage["last_request_at"].replace('Z', '+00:00'))
                
                # 如果是同一分钟内
                if last_request.minute == now.minute:
                    # 检查加上预估token后是否会超过TPM限制
                    future_tpm = usage["tokens_per_minute"] + estimated_tokens
                    if future_tpm > limits["tpm"]:
                        check_result["tpm_ok"] = False
                        logger.warning(f"Estimated tokens ({estimated_tokens}) would exceed TPM limit")
        
        return check_result
    
    def wait_if_needed(self, estimated_tokens: int = 0) -> bool:
        """
        如果需要，等待直到可以发送请求
        
        Args:
            estimated_tokens: 预估的token使用量
        
        Returns:
            是否可以继续（True）或已达到每日限制（False）
        """
        max_wait_time = 70  # 最多等待70秒（超过1分钟）
        wait_start = time.time()
        
        while True:
            check_result = self.can_make_request(estimated_tokens)
            
            # 检查每日限制
            if not check_result["rpd_ok"]:
                logger.error(f"Daily request limit reached for {self.current_model}")
                return False
            
            # 检查分钟限制
            if check_result["rpm_ok"] and check_result["tpm_ok"]:
                return True
            
            # 计算等待时间
            elapsed = time.time() - wait_start
            if elapsed > max_wait_time:
                logger.error(f"Waited too long ({elapsed:.1f}s) for rate limit")
                return False
            
            # 等待到下一分钟
            now = datetime.now(timezone.utc)
            seconds_to_next_minute = 60 - now.second
            wait_time = min(seconds_to_next_minute + 1, 10)  # 最多等10秒
            
            if not check_result["rpm_ok"]:
                logger.info(f"RPM limit reached, waiting {wait_time}s...")
            else:
                logger.info(f"TPM limit reached, waiting {wait_time}s...")
            
            time.sleep(wait_time)
    
    def record_usage(self, tokens_used: int):
        """
        记录API使用情况
        
        Args:
            tokens_used: 实际使用的token数量
        """
        if not self.current_model:
            raise ValueError("Model not set. Call set_model() first.")
        
        success = self.supabase.update_api_usage(
            model_name=self.current_model,
            requests=1,
            tokens=tokens_used
        )
        
        if success:
            logger.info(f"Recorded usage: 1 request, {tokens_used} tokens for {self.current_model}")
        else:
            logger.error(f"Failed to record usage for {self.current_model}")
    
    def get_best_available_model(self, preferred_models: Optional[list] = None) -> Optional[str]:
        """
        获取当前最佳可用的模型
        
        Args:
            preferred_models: 优先选择的模型列表
        
        Returns:
            可用的模型名称，如果没有可用模型则返回None
        """
        if preferred_models is None:
            # 默认优先级：从最高免费额度到最低
            preferred_models = [
                "gemini-2.0-flash-lite",  # 30 RPM, 1M TPM, 200 RPD
                "gemini-2.0-flash",        # 15 RPM, 1M TPM, 200 RPD
                "gemini-2.5-flash-lite",   # 15 RPM, 250K TPM, 1000 RPD
                "gemini-2.5-flash",        # 10 RPM, 250K TPM, 250 RPD
                "gemini-2.5-pro",          # 5 RPM, 250K TPM, 100 RPD
            ]
        
        for model in preferred_models:
            if model not in self.model_limits:
                continue
            
            limits = self.model_limits[model]
            check_result = self.supabase.check_api_limits(model, limits)
            
            # 如果每日限制未达到，这个模型可用
            if check_result["rpd_ok"]:
                logger.info(f"Selected model: {model}")
                return model
        
        logger.error("No models available within daily limits")
        return None
    
    def estimate_tokens(self, text: str) -> int:
        """
        估算文本的token数量
        简单估算：中文约1.5个字符/token，英文约4个字符/token
        
        Args:
            text: 输入文本
        
        Returns:
            估算的token数量
        """
        # 简单估算
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        other_chars = len(text) - chinese_chars
        
        estimated = (chinese_chars / 1.5) + (other_chars / 4)
        return int(estimated * 1.2)  # 增加20%的缓冲