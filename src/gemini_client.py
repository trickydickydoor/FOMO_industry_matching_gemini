"""
Gemini API客户端模块
"""
import json
import logging
from typing import List, Dict, Optional, Any
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential
from config import GEMINI_API_KEY, INDUSTRIES_CN, INDUSTRIES_EN, INDUSTRIES_EN_MAPPING, MAX_RETRIES
from rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class GeminiClient:
    """Gemini API客户端"""
    
    def __init__(self, rate_limiter: RateLimiter):
        """
        初始化Gemini客户端
        
        Args:
            rate_limiter: 速率限制器实例
        """
        if not GEMINI_API_KEY:
            raise ValueError("Missing Gemini API key")
        
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.rate_limiter = rate_limiter
        logger.info("Gemini client initialized")
    
    def _detect_language(self, text: str) -> str:
        """
        检测文本语言（简单实现，检测是否主要是英文）
        
        Args:
            text: 要检测的文本
            
        Returns:
            'en' 或 'zh'
        """
        # 统计英文字符和中文字符的比例
        english_chars = sum(1 for c in text if ord(c) < 256 and c.isalpha())
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        
        # 如果英文字符明显多于中文字符，判定为英文
        if english_chars > chinese_chars * 2:
            return 'en'
        return 'zh'
    
    def _get_system_instruction(self, language: str = 'zh') -> str:
        """
        获取系统指令
        
        Args:
            language: 语言类型 'zh' 或 'en'
        
        Returns:
            系统指令字符串
        """
        if language == 'en':
            industries_list = "\n".join([f"- {industry}" for industry in INDUSTRIES_EN])
            
            return f"""You are a professional news industry classification expert. Your task is to match the most relevant industry labels for news articles.

Available industry labels:
{industries_list}

Classification rules:
1. Each news article can match 1-3 most relevant industries
2. Only use industry names from the above list, do not create new industries
3. Classify based on the main content of news title and content
4. If the news involves multiple industries, select the top 2-3 most relevant ones
5. If unable to determine the industry, return an empty array

Output format requirements:
- Must return standard JSON format
- Structure: {{"classifications": [{{"id": "news_id", "industries": ["Industry1", "Industry2"]}}]}}
- Ensure JSON format is correct and can be parsed by Python json.loads()"""
        else:
            industries_list = "\n".join([f"- {industry}" for industry in INDUSTRIES_CN])
            
            return f"""你是一个专业的新闻行业分类专家。你的任务是为新闻匹配最相关的行业标签。

可选的行业标签：
{industries_list}

分类规则：
1. 每条新闻可以匹配1-3个最相关的行业
2. 只能使用上述列表中的行业名称，不能创造新的行业
3. 基于新闻标题和内容的主要内容进行分类
4. 如果新闻内容涉及多个行业，可以选择最主要的2-3个
5. 如果完全无法确定行业，返回空数组

输出格式要求：
- 必须返回标准JSON格式
- 结构：{{"classifications": [{{"id": "新闻ID", "industries": ["行业1", "行业2"]}}]}}
- 确保JSON格式正确，可以被Python json.loads()解析"""
    
    def _get_classification_prompt(self, news_items: List[Dict[str, Any]]) -> str:
        """
        生成分类提示词
        
        Args:
            news_items: 新闻列表
        
        Returns:
            提示词字符串
        """
        news_text = ""
        for i, item in enumerate(news_items, 1):
            title = item.get("title", "")
            content = item.get("content", "") if item.get("content") else ""  # 使用完整内容
            news_text += f"\n新闻{i}:\nID: {item['id']}\n标题: {title}\n内容: {content}\n"
        
        prompt = f"""请为以下新闻进行行业分类：
{news_text}

请返回JSON格式的分类结果。"""
        
        return prompt
    
    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def classify_news_batch(self, news_items: List[Dict[str, Any]], model_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        批量分类新闻
        
        Args:
            news_items: 新闻列表
            model_name: 指定使用的模型
        
        Returns:
            分类结果列表
        """
        try:
            # 选择模型
            if model_name:
                self.rate_limiter.set_model(model_name)
            else:
                # 自动选择最佳可用模型
                best_model = self.rate_limiter.get_best_available_model()
                if not best_model:
                    logger.error("No available models within limits")
                    return []
                self.rate_limiter.set_model(best_model)
                model_name = best_model
            
            # 根据语言分组新闻
            zh_news = []
            en_news = []
            
            for item in news_items:
                text = item.get("title", "") + " " + (item.get("content", "")[:500] if item.get("content") else "")
                lang = self._detect_language(text)
                
                if lang == 'en':
                    en_news.append(item)
                    logger.debug(f"News {item.get('id')}: English")
                else:
                    zh_news.append(item)
                    logger.debug(f"News {item.get('id')}: Chinese")
            
            logger.info(f"Language distribution: {len(zh_news)} Chinese, {len(en_news)} English")
            
            all_results = []
            
            # 处理中文新闻
            if zh_news:
                prompt_zh = self._get_classification_prompt(zh_news)
                estimated_tokens = self.rate_limiter.estimate_tokens(prompt_zh)
                
                if not self.rate_limiter.wait_if_needed(estimated_tokens):
                    logger.error("Cannot proceed due to rate limits")
                    return []
                
                logger.info(f"Processing {len(zh_news)} Chinese news items")
                response_zh = self.client.models.generate_content(
                    model=model_name,
                    config=types.GenerateContentConfig(
                        system_instruction=self._get_system_instruction('zh')
                    ),
                    contents=prompt_zh
                )
                
                # 解析中文结果
                try:
                    response_text = response_zh.text
                    start_idx = response_text.find('{')
                    end_idx = response_text.rfind('}') + 1
                    if start_idx != -1 and end_idx > start_idx:
                        json_str = response_text[start_idx:end_idx]
                        result = json.loads(json_str)
                        all_results.extend(result.get("classifications", []))
                except Exception as e:
                    logger.error(f"Error parsing Chinese response: {e}")
                
                # 记录token使用
                actual_tokens = self.rate_limiter.estimate_tokens(prompt_zh + response_zh.text)
                self.rate_limiter.record_usage(actual_tokens)
            
            # 处理英文新闻
            if en_news:
                prompt_en = self._get_classification_prompt(en_news)
                estimated_tokens = self.rate_limiter.estimate_tokens(prompt_en)
                
                if not self.rate_limiter.wait_if_needed(estimated_tokens):
                    logger.error("Cannot proceed due to rate limits")
                    return []
                
                logger.info(f"Processing {len(en_news)} English news items")
                response_en = self.client.models.generate_content(
                    model=model_name,
                    config=types.GenerateContentConfig(
                        system_instruction=self._get_system_instruction('en')
                    ),
                    contents=prompt_en
                )
                
                # 解析英文结果
                try:
                    response_text = response_en.text
                    start_idx = response_text.find('{')
                    end_idx = response_text.rfind('}') + 1
                    if start_idx != -1 and end_idx > start_idx:
                        json_str = response_text[start_idx:end_idx]
                        result = json.loads(json_str)
                        all_results.extend(result.get("classifications", []))
                except Exception as e:
                    logger.error(f"Error parsing English response: {e}")
                
                # 记录token使用
                actual_tokens = self.rate_limiter.estimate_tokens(prompt_en + response_en.text)
                self.rate_limiter.record_usage(actual_tokens)
            
            # 验证和清理所有结果
            cleaned_results = []
            
            for item in all_results:
                industries = item.get("industries", [])
                valid_industries = []
                
                for ind in industries:
                    # 如果已经是中文，直接验证
                    if ind in INDUSTRIES_CN:
                        valid_industries.append(ind)
                    # 如果是英文，转换为中文
                    elif ind in INDUSTRIES_EN_MAPPING:
                        valid_industries.append(INDUSTRIES_EN_MAPPING[ind])
                    # 尝试忽略大小写匹配
                    else:
                        matched = False
                        for en_key, cn_value in INDUSTRIES_EN_MAPPING.items():
                            if en_key.lower() == ind.lower():
                                valid_industries.append(cn_value)
                                matched = True
                                break
                        if not matched:
                            logger.warning(f"Unknown industry label: {ind}")
                
                cleaned_results.append({
                    "id": item.get("id"),
                    "industries": valid_industries
                })
            
            logger.info(f"Successfully classified {len(cleaned_results)} news items")
            return cleaned_results
            
        except Exception as e:
            logger.error(f"Error in classify_news_batch: {e}")
            raise
    
    def classify_single_news(self, news_item: Dict[str, Any]) -> List[str]:
        """
        分类单条新闻
        
        Args:
            news_item: 新闻数据
        
        Returns:
            行业列表
        """
        results = self.classify_news_batch([news_item])
        
        if results and len(results) > 0:
            return results[0].get("industries", [])
        
        return []