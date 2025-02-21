#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple, Union

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from app.config import settings
from app.services.intentService import intent_service,IntentService, IntentResult, CoreIntentType, AuxIntentType
from app.services.supabase import SupabaseService,supabase_service
from app.services.document_service import DocumentService
from langchain_community.tools import Tool
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain_community.vectorstores import SupabaseVectorStore


logger = logging.getLogger(__name__)

@dataclass
class ReasoningStep:
    """推理步骤记录"""
    step_number: int
    step_name: str
    description: str
    reasoning: str
    conclusion: Optional[str] = None

class ChatService:
    def _validate_api_keys(self):
        """验证API密钥是否正确配置"""
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not configured")
        if not settings.DeepSeek_API_KEY:
            raise ValueError("DEEPSEEK_API_KEY not configured")

    def __init__(self):
        """
        初始化 Chat 服务，创建模型实例。
        根据settings中的配置决定使用哪个模型和功能。
        """
        try:
            self._validate_api_keys()
            # 初始化向量嵌入模型
            self.embeddings = OpenAIEmbeddings(
                api_key=settings.OPENAI_API_KEY
            )

            # 初始化工具列表
            self.tools = []
            
            # 根据settings决定是否启用网络搜索
            if settings.USE_WEB_SEARCH:
                # 初始化搜索工具
                general_search = DuckDuckGoSearchAPIWrapper(
                    region="cn-zh",
                    max_results=20,
                    time='m',
                    safesearch='moderate'
                )

                # 初始化商品搜索工具
                product_search = DuckDuckGoSearchAPIWrapper(
                    region="cn-zh",
                    max_results=20,
                    time='m',
                    safesearch='moderate'
                )

                self.tools.extend([
                    Tool(
                        name="GeneralSearch",
                        func=general_search.run,
                        description="用于搜索一般信息的工具"
                    ),
                    Tool(
                        name="ProductSearch",
                        func=lambda q: product_search.run(f"site:https://www.1688.com/ OR site:jd.com OR site:https://www.yiwugo.com/ {q} 销量排行"),
                        description="用于搜索商品信息的工具，会在主流电商平台搜索商品销量排行"
                    )
                ])

            logger.info("ChatService 初始化成功")
        except Exception as e:
            logger.error(f"ChatService 初始化失败: {str(e)}")
            raise

    def _get_model(self) -> ChatOpenAI:
        """
        根据当前设置获取对应的模型实例
        """
        try:
            if settings.MODEL_PROVIDER == "openai":
                return ChatOpenAI(
                    model=settings.MODEL_NAME,
                    temperature=0.7,
                    streaming=True,
                    api_key=settings.OPENAI_API_KEY
                )
            else:  # deepseek
                return ChatOpenAI(
                    model='deepseek-chat',
                    api_key=settings.DeepSeek_API_KEY,
                    base_url='https://api.deepseek.com/v1',
                    temperature=0.7,
                    streaming=True  # 添加streaming参数保持一致
                )
        except Exception as e:
            logger.error(f"模型初始化失败: {str(e)}")
            raise

    def _get_prompt_template(self) -> ChatPromptTemplate:
        """
        根据当前设置获取 prompt 模板
        """
        system_prompt = settings.SYSTEM_PROMPT if settings.SYSTEM_PROMPT else """
            角色设定
            你是一名在采购招投标领域具备深厚专业知识与丰富实践经验的智能助手，能够进行复杂推理与精准决策。
            针对不同需求场景（如项目招标信息生成、投标文件评估、采购流程咨询、供应商资格审查等），需提供严谨、准确且可追溯的解决方案或信息。

            思考过程展示
            1. 解析问题：请先用简洁的语言说明你对问题的理解
            2. 确定方向：解释为什么选择特定的解决方案
            3. 执行计划：展示完整的解决步骤
            4. 结果优化：说明如何让结论更容易理解和应用

            表达方式要求
            1. 使用恰当的过渡语连接各个部分
            2. 避免过于机械的格式化输出
            3. 适时使用类比和举例增强理解
            4. 根据问题的严肃程度调整语气

            两阶段强化学习策略
            第一阶段：优化思考步骤
            提示词：生成解决问题的详细步骤，确保每一步都清晰、高效且逻辑严谨。
            目标：通过强化学习，训练模型生成更有效的思考步骤，提升推理效率与准确性。

            第二阶段：提升输出可读性
            提示词：依据人类偏好，调整上述步骤的表述，使其易于理解且连贯。
            目标：结合人类反馈，优化模型输出的可读性和流畅性。

            专业与严谨
            依据标准：所有答案应严格基于采购招投标的行业标准、法律法规（如《政府采购法》《招标投标法》等）以及权威来源。
            引用规范：引用法律条款、技术规范或标准时，必须保证来源可信、内容准确，并在必要时列出参考依据。

            信息处理原则
            1. 数据有效性验证
               - 优先使用最新数据
               - 标注数据时间戳
               - 说明数据来源可靠性

            2. 结论可追溯性
               - 清晰展示推理过程
               - 指出关键依据
               - 说明不确定因素

            3. 实用性要求
               - 确保建议可操作
               - 提供具体实施步骤
               - 预估可能风险
        """
        
        messages = [
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")
        ]
        
        return ChatPromptTemplate.from_messages(messages)

    def format_message_history(
        self, messages: List[Dict[str, Any]]
    ) -> List[BaseMessage]:
        """
        将消息历史记录格式化为模型所需的格式
        """
        formatted_messages = []
        try:
            for msg in messages:
                content = msg.get("content", "").strip()
                if not content:
                    continue
                    
                if msg.get("is_user"):
                    formatted_messages.append(HumanMessage(content=content))
                else:
                    formatted_messages.append(AIMessage(content=content))
                    
            return formatted_messages
        except Exception as e:
            logger.error(f"格式化消息历史失败: {str(e)}")
            return []

    def _build_reasoning_steps(self, text: str, intent_result: IntentResult) -> List[ReasoningStep]:
        """构建推理步骤"""
        steps = []
        
        # 步骤1：问题解析
        steps.append(ReasoningStep(
            step_number=1,
            step_name="问题解析",
            description="分析用户问题和意图",
            reasoning=f"识别到核心意图：{intent_result.core_intent}，辅助意图：{', '.join(intent_result.aux_intents)}",
            conclusion="需要结合具体意图类型进行定向处理"
        ))
        
        # 步骤2：解决方案设计
        solution_step = ReasoningStep(
            step_number=2,
            step_name="解决方案设计",
            description="根据意图确定处理策略",
            reasoning="考虑意图特点和处理要求",
            conclusion=None
        )
        
        if "项目招标信息生成" in intent_result.core_intent:
            solution_step.conclusion = "需要生成完整的招标文件框架"
        elif "投标文件评估" in intent_result.core_intent:
            solution_step.conclusion = "按照多维度评分标准进行评估"
        elif "商品对比与选型" in intent_result.core_intent:
            solution_step.conclusion = "采用多因素对比分析方法"
        else:
            solution_step.conclusion = "使用通用咨询处理方案"
        
        steps.append(solution_step)
        
        # 步骤3：执行计划制定
        execution_step = ReasoningStep(
            step_number=3,
            step_name="执行计划",
            description="确定具体执行步骤",
            reasoning="根据解决方案设计具体流程",
            conclusion="按计划逐步执行并记录结果"
        )
        steps.append(execution_step)
        
        return steps

    def _explain_reasoning_steps(self, steps: List[ReasoningStep]) -> str:
        """将推理步骤转化为易读的说明"""
        result = ["思考过程："]
        
        for step in steps:
            # 添加过渡语
            if step.step_number == 1:
                result.append("首先，让我们来理解问题：")
            elif step.step_number == 2:
                result.append("接下来，我们需要设计解决方案：")
            else:
                result.append("然后，")
                
            result.append(f"{step.step_number}. {step.step_name}")
            result.append(f"   - 分析：{step.reasoning}")
            if step.conclusion:
                result.append(f"   - 结论：{step.conclusion}")
            result.append("")
            
        return "\n".join(result)

    def _process_core_intent(self, text: str, intent_result: IntentResult) -> Tuple[str, str]:
        """处理核心意图，为不同类型的意图构造专门的查询，并记录推理过程"""
        # 构建推理步骤
        steps = self._build_reasoning_steps(text, intent_result)
        reasoning_explanation = self._explain_reasoning_steps(steps)
        
        # 根据意图类型构造查询
        intent_processors = {
            # 项目招标信息生成
            CoreIntentType.GENERATE_BID.value: lambda t: "\n".join((
                "请生成一份标准的项目招标信息：",
                "1. 项目基本信息",
                "2. 技术要求说明",
                "3. 资质要求说明", 
                "4. 评标方法说明",
                f"项目信息：{t}"
            )),
            # 投标文件评估
            CoreIntentType.EVALUATE_BID.value: lambda t: "\n".join((
                "请评估以下投标文件：",
                "1. 形式合规性",
                "2. 技术响应度",
                "3. 商务合理性",
                "4. 风险提示",
                f"文件内容：{t}"
            )),
            # 采购流程咨询
            CoreIntentType.PROCUREMENT_CONSULT.value: lambda t: "\n".join((
                "请解答以下采购流程问题：",
                "1. 流程说明",
                "2. 注意事项",
                "3. 相关规定",
                "4. 最佳实践",
                f"问题描述：{t}"
            )),
            # 供应商资格审查
            CoreIntentType.SUPPLIER_REVIEW.value: lambda t: "\n".join((
                "请对供应商资格进行审查：",
                "1. 基本资质",
                "2. 业务能力",
                "3. 履约记录",
                "4. 风险评估",
                f"供应商信息：{t}"
            )),
            # 商品对比与选型
            CoreIntentType.PRODUCT_COMPARE.value: lambda t: "\n".join((
                "请对以下商品进行对比分析：",
                "1. 功能对比(40%)",
                "2. 价格分析(30%)",
                "3. 质量评估(20%)",
                "4. 其他因素(10%)",
                f"商品信息：{t}"
            )),
            # 法规条款解读
            CoreIntentType.LAW_INTERPRET.value: lambda t: "\n".join((
                "请对以下法规条款进行专业解读：",
                "1. 条款原文解释",
                "2. 适用场景分析", 
                "3. 实践案例参考",
                "4. 关联法规说明",
                f"法规内容：{t}"
            )),
            # 风险预警
            CoreIntentType.RISK_ALERT.value: lambda t: "\n".join((
                "请对以下情况进行风险评估：",
                "1. 识别风险点",
                "2. 评估风险等级",
                "3. 提供防范建议",
                "4. 应急预案建议",
                f"情况描述：{t}"
            ))
        }
        
        processor = intent_processors.get(intent_result.core_intent, lambda t: t)
        query = processor(text)
        
        return query, reasoning_explanation

    def _enhance_with_aux_intents(self, query_tuple: Union[str, Tuple[str, str]], intent_result: IntentResult) -> str:
        """
        根据辅助意图增强查询内容，增加可读性
        """
        # 解包query_tuple
        if isinstance(query_tuple, tuple):
            query, reasoning = query_tuple
        else:
            query = query_tuple
            reasoning = ""

        # 辅助意图增强
        enhancements = []
        transitions = ["此外，请注意：", "同时：", "另外："]
        
        if AuxIntentType.ENHANCED_SEARCH.value in intent_result.aux_intents:
            enhancements.append("需要进行更深入的信息检索")
            
        if AuxIntentType.UNCERTAINTY_DECLARE.value in intent_result.aux_intents:
            enhancements.append("如有不确定的信息请明确说明")
            
        if AuxIntentType.DEEP_REASONING.value in intent_result.aux_intents:
            enhancements.append("需要详细的推理过程")
        
        if enhancements:
            enhancement_text = ""
            for i, (transition, enhancement_group) in enumerate(zip(transitions, [enhancements[i:i+3] for i in range(0, len(enhancements), 3)])):
                enhancement_text += f"\n{transition}\n"
                enhancement_text += "\n".join(f"- {e}" for e in enhancement_group)
            
            query += f"\n处理要求：{enhancement_text}"
        
        return query

    async def _get_relevant_docs(
        self, query: str, user_id: str
    ) -> List[Dict]:
        """
        获取相关文档片段
        """
        try:
            # 使用 self.embeddings 来生成嵌入
            query_embedding = await asyncio.to_thread(
                self.embeddings.embed_query,
                query
            )
            
            # 将同步的 Supabase RPC 调用包装在 asyncio.to_thread 中执行
            result = await asyncio.to_thread(
                lambda: supabase_service.client.rpc(
                    'match_documents',
                    {
                        'query_embedding': query_embedding,
                        'user_id_input': user_id,
                        'match_threshold': 0.8,
                        'match_count': 3
                    }
                ).execute()
            )
            
            if result.data:
                return result.data
            return []
        except Exception as e:
            logger.error(f"获取相关文档失败: {str(e)}")
            return []

    def _construct_doc_query(self, user_input: str, docs: List[Dict]) -> str:
        """构造基于文档的查询"""
        if not docs:
            return user_input
            
        docs_content = "\n".join([
            f"文档片段 {i+1}:\n{doc['content']}" 
            for i, doc in enumerate(docs)
        ])
        
        return (
            f"基于以下参考资料：\n"
            f"{docs_content}\n"
            f"请回答问题：\n{user_input}\n"
            f"注意：\n"
            f"1. 请优先使用文档中的信息\n"
            f"2. 如有信息冲突，请说明原因\n"
            f"3. 需要补充时，可以使用搜索工具"
        )

    def _extract_response(self, response: Any) -> str:
        """从响应中提取有效内容并优化可读性"""
        try:
            raw_content = ""
            if isinstance(response, dict):
                for key in ["action_input", "output", "response", "answer"]:
                    if key in response and response[key]:
                        raw_content = str(response[key]).strip()
                        break
                if not raw_content:
                    raw_content = str(response)
            elif isinstance(response, str):
                raw_content = response.strip()
            else:
                raw_content = str(response)

            # 优化输出格式
            lines = raw_content.split("\n")
            formatted_lines = []
            current_section = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    formatted_lines.append("")
                    continue
                    
                # 检测段落标题
                if line.endswith("：") or line.endswith(":"):
                    current_section = line
                    formatted_lines.append(f"\n{line}")
                # 处理列表项
                elif line.startswith("-") or line.startswith("*"):
                    formatted_lines.append(line)
                # 处理普通段落
                else:
                    if current_section:
                        formatted_lines.append(f"  {line}")
                    else:
                        formatted_lines.append(line)
            
            return "\n".join(formatted_lines).strip()
            
        except Exception as e:
            logger.error(f"提取响应内容失败: {str(e)}")
            return str(response)

    def _clean_response_text(self, text: str) -> str:
        """
        清理响应文本，去除多余的空行
        """
        # 将连续的多个空行替换为单个空行
        cleaned = re.sub(r'\n\s*\n', '\n\n', text.strip())
        return cleaned

    async def generate_response(
        self, 
        user_input: str, 
        message_history: List[Dict[str, Any]], 
        user_id: Optional[str] = None
    ) -> str:
        """根据用户输入和历史消息生成 AI 回复"""
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # 获取当前设置对应的模型实例
                model = self._get_model()
                
                # 1. 意图识别
                intent_result = None
                if settings.USE_INTENT_DETECTION:
                    intent_result = await intent_service.classify_intent(user_input)
                
                # 2. 处理查询
                query_input = user_input
                if intent_result and intent_result.core_intent:  # 修复 && 为 and
                    query_input = self._process_core_intent(user_input, intent_result)
                    if intent_result.aux_intents:
                        query_input = self._enhance_with_aux_intents(query_input, intent_result)
            
                # 3. 格式化历史消息
                formatted_history = self.format_message_history(message_history)
                
                # 4. 相关文档检索
                if settings.USE_WEB_SEARCH and user_id:  # 修复 && 为 and
                    try:
                        docs = await self._get_relevant_docs(query_input, user_id)
                        if docs:
                            query_input = self._construct_doc_query(query_input, docs)
                    except Exception as e:
                        logger.warning(f"文档检索失败，继续处理: {str(e)}")
                        # 文档检索失败不影响主流程
            
                # 5. 创建 prompt 并生成回复
                prompt = self._get_prompt_template()
                chain = prompt | model
                
                # 记录调试信息
                logger.debug(f"尝试 {attempt + 1}: 发送请求到 {settings.MODEL_PROVIDER}")
                logger.debug(f"Query input: {query_input}")
                
                # 发送请求并等待响应
                response = await chain.ainvoke({
                    "input": query_input,
                    "history": formatted_history
                })
                
                # 验证响应
                if not response:
                    raise ValueError("空响应")
                
                # 提取内容
                content = ""
                if isinstance(response, dict):
                    content = response.get("content", "")
                    if not content:
                        for key in ["text", "output", "response", "answer"]:
                            if key in response:
                                content = response[key]
                                break
                elif hasattr(response, "content"):
                    content = response.content
                else:
                    content = str(response)
                
                if not content.strip():
                    raise ValueError("无有效内容")
                
                # 清理响应文本
                cleaned_response = self._clean_response_text(content)
                logger.info(f"成功从{settings.MODEL_PROVIDER}获得响应")
                return cleaned_response
                
            except (json.JSONDecodeError, ValueError) as e:
                last_error = e
                logger.warning(f"{settings.MODEL_PROVIDER} 响应解析错误 (尝试 {attempt + 1}): {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))
                continue
                
            except Exception as e:
                last_error = e
                logger.warning(f"{settings.MODEL_PROVIDER} 请求失败 (尝试 {attempt + 1}): {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))
                continue

        # 所有重试都失败后
        error_msg = f"在 {max_retries} 次尝试后仍然失败: {str(last_error)}"
        logger.error(error_msg)
        raise Exception(error_msg)

# 全局服务实例
chat_service = ChatService()
