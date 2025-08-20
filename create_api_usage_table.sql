-- 创建API使用情况跟踪表
CREATE TABLE IF NOT EXISTS api_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_name TEXT NOT NULL, -- 'gemini'
    model_name TEXT NOT NULL, -- 'gemini-2.0-flash-lite', 'gemini-2.0-flash', etc.
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    hour INT NOT NULL DEFAULT EXTRACT(HOUR FROM NOW()), -- 0-23
    minute_window INT NOT NULL DEFAULT EXTRACT(MINUTE FROM NOW()), -- 0-59
    
    -- 计数器
    requests_per_minute INT DEFAULT 0, -- RPM计数
    requests_per_day INT DEFAULT 0, -- RPD计数
    tokens_per_minute INT DEFAULT 0, -- TPM计数
    tokens_per_day INT DEFAULT 0, -- TPD计数
    
    -- 元数据
    last_request_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 确保每个模型每天只有一条记录
    CONSTRAINT unique_api_usage_per_day UNIQUE (service_name, model_name, date)
);

-- 创建索引以提高查询性能
CREATE INDEX idx_api_usage_date ON api_usage(date);
CREATE INDEX idx_api_usage_service_model ON api_usage(service_name, model_name);
CREATE INDEX idx_api_usage_last_request ON api_usage(last_request_at);

-- 创建更新触发器
CREATE OR REPLACE FUNCTION update_api_usage_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER api_usage_updated_at
    BEFORE UPDATE ON api_usage
    FOR EACH ROW
    EXECUTE FUNCTION update_api_usage_updated_at();

-- 添加注释
COMMENT ON TABLE api_usage IS 'API使用情况跟踪表，用于管理免费额度限制';
COMMENT ON COLUMN api_usage.service_name IS 'API服务名称，如gemini';
COMMENT ON COLUMN api_usage.model_name IS '模型名称，如gemini-2.0-flash-lite';
COMMENT ON COLUMN api_usage.requests_per_minute IS '当前分钟内的请求次数';
COMMENT ON COLUMN api_usage.requests_per_day IS '当天的总请求次数';
COMMENT ON COLUMN api_usage.tokens_per_minute IS '当前分钟内的token使用量';
COMMENT ON COLUMN api_usage.tokens_per_day IS '当天的总token使用量';