# API 文档

## 认证 API

### 登录
- 方法：`signIn(email: string, password: string)`
- 描述：用户登录
- 参数：
  - email: 用户邮箱
  - password: 用户密码
- 返回：Promise<void>
- 错误：
  - "Invalid login credentials": 邮箱或密码错误
  - 其他错误会以错误消息形式返回

### 注册
- 方法：`signUp(email: string, password: string)`
- 描述：新用户注册
- 参数：
  - email: 用户邮箱
  - password: 用户密码
- 返回：Promise<void>
- 错误：
  - "User already registered": 用户已注册
  - 其他错误会以错误消息形式返回

## 对话 API

### 创建对话
- 方法：`createConversation(title: string)`
- 描述：创建新的对话
- 参数：
  - title: 对话标题
- 返回：Promise<void>
- 错误：
  - "请先登录": 用户未登录
  - "创建会话失败：权限不足": 用户权限不足

### 更新对话标题
- 方法：`updateConversationTitle(id: string, title: string)`
- 描述：更新对话标题
- 参数：
  - id: 对话ID
  - title: 新标题
- 返回：Promise<void>

### 发送消息
- 方法：`sendMessage(content: string)`
- 描述：发送消息并获取AI回复
- 参数：
  - content: 消息内容
- 返回：Promise<void>