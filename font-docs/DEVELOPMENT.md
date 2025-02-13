# 开发指南

## 项目结构

```
src/
├── components/          # React 组件
│   ├── Auth.tsx        # 认证组件
│   └── ChatSidebar.tsx # 聊天侧边栏组件
├── store/              # Zustand 状态管理
│   ├── authStore.ts    # 认证状态
│   └── chatStore.ts    # 聊天状态
├── lib/                # 工具库
│   └── supabase.ts     # Supabase 客户端
├── App.tsx             # 主应用组件
└── main.tsx           # 应用入口

docs/                   # 文档
├── API.md             # API 文档
├── DATABASE.md        # 数据库设计
└── DEVELOPMENT.md     # 开发指南
```

## 状态管理

项目使用 Zustand 进行状态管理，分为两个主要的 store：

### authStore
- 管理用户认证状态
- 处理登录、注册、登出
- 维护用户信息

### chatStore
- 管理对话列表和当前对话
- 处理消息发送和接收
- 管理对话标题更新

## 开发规范

### TypeScript
- 使用类型注解
- 避免使用 any
- 为所有函数添加返回类型

### 组件开发
- 使用函数组件
- 使用 React Hooks
- 遵循单一职责原则

### 样式规范
- 使用 Tailwind CSS
- 遵循移动优先原则
- 保持样式类名的语义化

### 错误处理
- 使用 try-catch 捕获异常
- 使用 toast 显示错误信息
- 提供用户友好的错误提示

## 环境变量

项目需要以下环境变量：

```env
VITE_SUPABASE_URL=你的Supabase项目URL
VITE_SUPABASE_ANON_KEY=你的Supabase匿名密钥
```

## 本地开发

1. 安装依赖：
```bash
npm install
```

2. 启动开发服务器：
```bash
npm run dev
```

3. 运行测试：
```bash
npm run test
```

4. 构建生产版本：
```bash
npm run build
```