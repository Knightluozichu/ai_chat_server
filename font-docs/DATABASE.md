# 数据库设计文档

## 表结构

### conversations（对话表）

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | uuid | 对话ID | PRIMARY KEY |
| user_id | uuid | 用户ID | REFERENCES auth.users |
| title | text | 对话标题 | NOT NULL |
| created_at | timestamptz | 创建时间 | DEFAULT now() |

### messages（消息表）

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | uuid | 消息ID | PRIMARY KEY |
| conversation_id | uuid | 对话ID | REFERENCES conversations ON DELETE CASCADE |
| content | text | 消息内容 | NOT NULL |
| is_user | boolean | 是否用户消息 | DEFAULT true |
| created_at | timestamptz | 创建时间 | DEFAULT now() |

## 行级安全策略（RLS）

### conversations 表策略

1. 查看策略
```sql
CREATE POLICY "Users can view own conversations"
  ON conversations
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);
```

2. 插入策略
```sql
CREATE POLICY "Users can insert own conversations"
  ON conversations
  FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);
```

### messages 表策略

1. 查看策略
```sql
CREATE POLICY "Users can view messages in own conversations"
  ON messages
  FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM conversations
      WHERE id = messages.conversation_id
      AND user_id = auth.uid()
    )
  );
```

2. 插入策略
```sql
CREATE POLICY "Users can insert messages in own conversations"
  ON messages
  FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM conversations
      WHERE id = messages.conversation_id
      AND user_id = auth.uid()
    )
  );
```