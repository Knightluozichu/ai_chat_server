# AI Chat Server API 文档

## 基本信息

### 1. 服务概述
- 这是一个基于 FastAPI 的 AI 聊天服务
- 集成了 Supabase 用于数据存储和实时消息同步
- 使用 LangChain 框架调用 OpenAI 模型生成 AI 回复
- 支持异步消息处理和历史记录管理

### 2. 基础 URL
- 开发环境：http://localhost:3000
- 生产环境：[https://aichatserver-hellsingluo.replit.app/]

### 3. 认证与安全
- 目前使用 user_id 参数进行基本身份识别
- 通过 Supabase 服务进行权限验证
- 所有 API 调用需要在请求头中包含 Content-Type: application/json
- [计划] 未来将实现基于 JWT 的完整认证机制

## API 端点

### 1. 发送聊天消息
**发送用户消息并获取 AI 回复**

- 端点：`POST /api/chat/{conversation_id}`
- 描述：向指定对话发送消息，服务器会返回 AI 生成的回复

#### 请求参数
- Path 参数：
  * `conversation_id` (string, 必需) - 对话 ID

- 请求体 (JSON)：
```json
{
  "user_id": "string",    // 用户 ID
  "message": "string"     // 用户发送的消息内容
}
```

#### 响应
- 成功响应 (200 OK)：
```json
{
  "response": "string"    // AI 生成的回复内容
}
```

- 错误响应：
  * 400 Bad Request - 请求参数无效
  * 403 Forbidden - 用户无权访问该对话
  * 404 Not Found - 对话不存在
  * 500 Internal Server Error - 服务器内部错误

#### 示例

请求：
```bash
curl -X POST "http://localhost:3000/api/chat/conv_123" \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": "user_1",
       "message": "你好，请介绍一下你自己"
     }'
```

成功响应：
```json
{
  "response": "你好！我是一个 AI 助手，可以帮助回答问题、参与讨论等。请问有什么我可以帮你的吗？"
}
```

### 2. 获取对话历史
**获取指定对话的历史消息记录**

- 端点：`GET /api/chat/{conversation_id}/history`
- 描述：获取指定对话的所有历史消息，按时间顺序排列

#### 请求参数
- Path 参数：
  * `conversation_id` (string, 必需) - 对话 ID

#### 响应
- 成功响应 (200 OK)：
```json
[
  {
    "content": "string",      // 消息内容
    "is_user": boolean       // true 表示用户消息，false 表示 AI 回复
  }
]
```

- 错误响应：
  * 404 Not Found - 对话不存在
  * 500 Internal Server Error - 服务器内部错误

#### 示例

请求：
```bash
curl "http://localhost:3000/api/chat/conv_123/history"
```

成功响应：
```json
[
  {
    "content": "你好，请介绍一下你自己",
    "is_user": true
  },
  {
    "content": "你好！我是一个 AI 助手，可以帮助回答问题、参与讨论等。请问有什么我可以帮你的吗？",
    "is_user": false
  }
]
```

### 3. 健康检查
**检查服务运行状态**

- 端点：`GET /health`
- 描述：用于监控服务的运行状态

#### 响应
- 成功响应 (200 OK)：
```json
{
  "status": "healthy"     // 服务运行正常
}
```

#### 示例

请求：
```bash
curl "http://localhost:3000/health"
```

成功响应：
```json
{
  "status": "healthy"
}
```

## 错误处理

所有 API 在发生错误时会返回统一格式的错误响应：

```json
{
  "detail": "错误描述信息"
}
```

常见错误码：
- 400 Bad Request：请求参数无效或格式错误
- 403 Forbidden：权限验证失败
- 404 Not Found：请求的资源不存在
- 500 Internal Server Error：服务器内部错误

## 注意事项

1. 请求限制
- API 调用频率限制：[待定]
- 单次消息长度限制：[待定]
- 历史记录保存时长：[待定]

2. 最佳实践
- 建议在发送新消息前先通过历史记录接口检查之前的对话状态
- 对于长时间未活动的对话，建议创建新的对话 ID
- 在处理敏感信息时，确保使用 HTTPS 进行通信

3. 未来计划
- 添加用户认证机制
- 支持消息流式输出
- 添加更多对话管理功能
- 支持自定义 AI 模型参数
