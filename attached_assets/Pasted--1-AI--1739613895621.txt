# 知识库功能文档

## 1. 功能概述

知识库模块提供了文件管理的基础功能，支持用户上传、查看、搜索和删除文档文件。该模块作为 AI 聊天助手的补充功能，为用户提供文档管理和知识沉淀的能力。

### 1.1 核心功能

- 文件上传：支持 PDF 和 Word 文档上传
- 文件管理：查看、搜索、下载和删除文件
- 权限控制：基于用户身份的访问控制
- 存储限制：单文件大小限制为 10MB

### 1.2 技术栈

- 前端：React + TypeScript + Tailwind CSS
- 状态管理：Zustand
- 存储服务：Supabase Storage
- 数据库：Supabase PostgreSQL

## 2. 数据库设计

### 2.1 files 表

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | uuid | 文件ID | PRIMARY KEY |
| user_id | uuid | 用户ID | REFERENCES auth.users |
| name | text | 文件名 | NOT NULL |
| size | bigint | 文件大小(字节) | NOT NULL |
| type | text | 文件类型 | NOT NULL |
| url | text | 文件访问URL | NOT NULL |
| created_at | timestamptz | 创建时间 | DEFAULT now() |
| updated_at | timestamptz | 更新时间 | DEFAULT now() |

### 2.2 行级安全策略 (RLS)

```sql
-- 查看权限
CREATE POLICY "Users can view own files"
  ON files FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

-- 上传权限
CREATE POLICY "Users can upload own files"
  ON files FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

-- 删除权限
CREATE POLICY "Users can delete own files"
  ON files FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);
```

## 3. 存储配置

### 3.1 存储桶设置

- 桶名称：files
- 访问权限：公开读取
- 上传权限：仅认证用户

### 3.2 文件存储规则

- 文件路径格式：`{user_id}/{random_filename}.{extension}`
- 支持的文件类型：
  - PDF (.pdf)
  - Word (.doc, .docx)
- 文件大小限制：10MB

## 4. 前端实现

### 4.1 组件结构

```
src/components/KnowledgeBase/
├── KnowledgeCapsule.tsx   # 知识库胶囊组件
└── KnowledgePanel.tsx     # 知识库面板组件
```

### 4.2 状态管理

```typescript
interface KnowledgeState {
  files: File[];           // 文件列表
  loading: boolean;        // 加载状态
  searchQuery: string;     // 搜索关键词
  uploadFile: (file: File) => Promise<void>;
  deleteFile: (id: string) => Promise<void>;
  loadFiles: () => Promise<void>;
  setSearchQuery: (query: string) => void;
}
```

## 5. 用户界面

### 5.1 知识库胶囊

- 位置：屏幕右侧中部
- 状态：可展开/收起
- 功能：快速访问知识库面板

### 5.2 知识库面板

- 布局：右侧滑出面板
- 主要区域：
  - 顶部操作栏：上传按钮、搜索框
  - 文件列表：支持搜索过滤
  - 文件操作：下载、删除

## 6. 安全性考虑

### 6.1 访问控制

- 文件访问：仅创建者可查看
- 文件上传：需要用户认证
- 文件删除：仅创建者可删除

### 6.2 数据安全

- 文件存储：使用随机文件名
- 用户隔离：基于用户ID的存储路径
- 权限控制：严格的RLS策略

## 7. 性能优化

### 7.1 前端优化

- 文件列表懒加载
- 搜索防抖处理
- 文件大小限制检查
- 上传状态反馈

### 7.2 存储优化

- 文件类型限制
- 文件大小限制
- 存储空间隔离

## 8. 后续优化方向

1. 文件预览功能
2. 文件分类管理
3. 批量操作支持
4. 文件版本控制
5. 文件分享功能
6. 全文检索能力
7. 文件标签系统
8. 存储空间配额
9. 文件加密存储
10. 文件在线编辑

## 9. 注意事项

1. 文件上传前端限制：
   - 仅支持 PDF 和 Word 文档
   - 单文件大小不超过 10MB
   
2. 存储安全：
   - 使用随机文件名存储
   - 严格的访问控制策略
   
3. 错误处理：
   - 上传失败重试机制
   - 友好的错误提示
   - 完整的错误日志

## 10. 更新日志

### v1.0.0 (2025-02-15)

- 基础文件管理功能
- 文件上传和下载
- 文件列表和搜索
- 基本的权限控制