# Industry Matching with Gemini

基于 Python 和 Google Gemini API 的新闻行业自动分类系统，通过 GitHub Actions 定时执行。

## 功能特点

- 🤖 **智能分类**：使用 Google Gemini API 自动为新闻匹配行业标签
- 💾 **持久化存储**：基于 Supabase 数据库跟踪 API 使用情况，防止超出免费额度
- ⏰ **定时执行**：通过 GitHub Actions 每小时自动运行
- 🚦 **速率限制**：智能管理 API 调用速率（RPM/TPM/RPD）
- 📊 **批量处理**：支持批量处理新闻以提高效率
- 🔄 **自动重试**：失败时自动重试机制
- 📝 **详细日志**：完整的执行日志和统计信息

## 支持的行业分类（38个）

- 5G通信、农业科技、人工智能、AIGC、汽车制造
- 智能驾驶、生物医药、云计算、商业航天、建筑工程
- 内容创作、跨境电商、文化创意、网络安全、电子商务
- 企业服务、金融科技、游戏、大健康、IDC数据中心
- 物联网、本地生活服务、物流快递、医疗器械、新能源汽车
- 新材料、在线教育、石油化工、房地产、新能源
- 零售消费、机器人、SaaS、半导体、短视频直播
- 智能制造、钢铁冶金、纺织服装、旅游酒店

## Gemini 模型免费额度

| 模型 | RPM | TPM | RPD |
|------|-----|-----|-----|
| Gemini 2.0 Flash-Lite | 30 | 1,000,000 | 200 |
| Gemini 2.0 Flash | 15 | 1,000,000 | 200 |
| Gemini 2.5 Flash-Lite | 15 | 250,000 | 1,000 |
| Gemini 2.5 Flash | 10 | 250,000 | 250 |
| Gemini 2.5 Pro | 5 | 250,000 | 100 |

## 系统架构

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│  GitHub Actions │────▶│   Python App  │────▶│   Supabase  │
│   (每小时触发)    │     │  (行业匹配器)  │     │  (数据存储)  │
└─────────────────┘     └──────────────┘     └─────────────┘
                               │
                               ▼
                        ┌──────────────┐
                        │  Gemini API   │
                        │  (智能分类)    │
                        └──────────────┘
```

## 数据库结构

### news_items 表
- `id`: UUID (主键)
- `title`: 新闻标题
- `content`: 新闻内容
- `published_at`: 发布时间
- `industries`: 行业标签数组
- 其他字段...

### api_usage 表（API使用跟踪）
- `id`: UUID (主键)
- `service_name`: 服务名称 (gemini)
- `model_name`: 模型名称
- `date`: 日期
- `requests_per_minute`: 分钟请求数
- `requests_per_day`: 每日请求数
- `tokens_per_minute`: 分钟Token数
- `tokens_per_day`: 每日Token数

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/industry_matching_gemini.git
cd industry_matching_gemini
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：
```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.0-flash-lite
```

### 4. 创建数据库表

在 Supabase 中执行 `create_api_usage_table.sql` 创建 API 使用跟踪表。

### 5. 本地测试

```bash
python src/industry_matcher.py
```

### 6. 配置 GitHub Actions

在 GitHub 仓库的 Settings → Secrets and variables → Actions 中添加：

**Secrets:**
- `SUPABASE_URL`: Supabase 项目 URL
- `SUPABASE_KEY`: Supabase Anon Key
- `GEMINI_API_KEY`: Google Gemini API Key

**Variables (可选):**
- `GEMINI_MODEL`: 使用的模型（默认: gemini-2.0-flash-lite）

## 使用方法

### 自动执行
GitHub Actions 会每小时自动执行一次，处理过去 2 小时内未分类的新闻。

### 手动触发
在 GitHub Actions 页面可以手动触发工作流，可选参数：
- `limit`: 最大处理新闻数量

### 本地运行

```python
from industry_matcher import IndustryMatcher

matcher = IndustryMatcher()
matcher.run(limit=10)  # 处理最多10条新闻
```

## 项目结构

```
industry_matching_gemini/
├── .github/
│   └── workflows/
│       └── industry_matcher.yml    # GitHub Action 配置
├── src/
│   ├── config.py                  # 配置管理
│   ├── supabase_client.py        # Supabase 客户端
│   ├── gemini_client.py          # Gemini API 客户端
│   ├── rate_limiter.py           # 速率限制器
│   └── industry_matcher.py       # 核心匹配逻辑
├── tests/
│   └── test_industry_matcher.py  # 单元测试
├── requirements.txt               # Python 依赖
├── .env.example                  # 环境变量示例
└── README.md                     # 项目文档
```

## 运行测试

```bash
pytest tests/ -v
```

## 监控和日志

- GitHub Actions 运行日志可在 Actions 页面查看
- 每次运行会生成详细的处理统计信息
- 日志文件会作为 Artifacts 保存 7 天

## 注意事项

1. **API 限制**：系统会自动管理 API 调用速率，确保不超过免费额度
2. **数据库持久化**：API 使用计数存储在 Supabase，跨运行保持状态
3. **批处理优化**：默认每批处理 5 条新闻，可在 `config.py` 中调整
4. **时区设置**：默认使用 Asia/Shanghai 时区，可在配置中修改
5. **错误处理**：包含自动重试和优雅降级机制

## 故障排除

### 常见问题

1. **API 限制错误**
   - 检查 api_usage 表中的使用记录
   - 考虑切换到其他模型或等待限制重置

2. **分类不准确**
   - 调整 prompt 提示词
   - 确保新闻内容包含足够的上下文信息

3. **数据库连接失败**
   - 验证 Supabase URL 和 Key
   - 检查网络连接

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License