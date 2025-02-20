#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import asyncio
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentType, initialize_agent
from langchain_community.utilities import SerpAPIWrapper
from langchain.tools import Tool
from langchain.utilities import DuckDuckGoSearchAPIWrapper

from app.config import settings
from app.services.supabase import supabase_service
from app.services.intentService import (
    intent_service, IntentResult,
    CoreIntentType, AuxIntentType
)

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
    def __init__(self):
        """
        初始化 Chat 服务，创建 ChatOpenAI 模型实例和 Prompt 模板。
        Prompt 中要求回答时结合最新的搜索信息，确保回复包含最新的数据和时间节点。
        """
        try:
            # 初始化 OpenAI 模型实例
            self.model = ChatOpenAI(
                model=settings.MODEL_NAME,
                temperature=0.7,
                streaming=True,
                api_key=settings.OPENAI_API_KEY
            )
            
            # 初始化向量嵌入模型
            self.embeddings = OpenAIEmbeddings(
                api_key=settings.OPENAI_API_KEY
            )

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

            self.tool = [
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
            ]

            # 构造 Prompt 模板
            self.prompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    """                    
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
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}")
            ])

            # 初始化 Agent
            self.agent = initialize_agent(
                tools=self.tool,
                llm=self.model,
                agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
                verbose=True,
                agent_kwargs={"prompt": self.prompt}
            )
            
            logger.info("ChatService 初始化成功")
        except Exception as e:
            logger.error(f"ChatService 初始化失败: {str(e)}")
            raise

    def format_message_history(
        self, messages: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """
        将数据库中的消息记录转换为 LangChain 格式。

        Args:
            messages: 列表，每个消息包含 "content" 和 "is_user" 字段。

        Returns:
            格式化后的消息列表，每个消息包含 "role" 和 "content" 字段。
        """
        try:
            formatted = []
            for msg in messages:
                role = "human" if msg.get("is_user") else "assistant"
                content = msg.get("content", "").strip()
                if content:  # 确保内容不为空
                    formatted.append({"role": role, "content": content})
            return formatted
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
        intent_handlers = {
            # 项目招标信息生成
            CoreIntentType.GENERATE_BID.value: lambda t: (
                f"让我们按照以下步骤来生成招标信息：\n\n"
                f"第一步，我们需要确定项目基本信息：\n"
                f"- 项目背景和采购需求\n"
                f"- 投标人资质要求\n\n"
                f"第二步，让我们细化技术规范：\n"
                f"- 技术规格指标\n"
                f"- 评标标准设计\n\n"
                f"最后，我们来规划时间节点：\n"
                f"- 具体时间安排\n\n"
                f"项目信息：{t}"
            ),
            # 其他意图处理器保持不变...
        }
        
        handler = intent_handlers.get(intent_result.core_intent, lambda t: t)
        query = handler(text)
        
        return query, reasoning_explanation

    def _enhance_with_aux_intents(self, query: str, intent_result: IntentResult) -> str:
        """根据辅助意图增强查询内容，增加可读性"""
        enhancements = []
        transitions = []
        
        if AuxIntentType.ENHANCED_SEARCH.value in intent_result.aux_intents:
            transitions.append("为了确保信息的准确性和时效性：")
            enhancements.extend([
                "我们需要先搜索最新的市场数据",
                "重点关注产品的实际表现和用户反馈",
                "所有数据都会标注采集时间，确保参考价值"
            ])
        
        if AuxIntentType.UNCERTAINTY_DECLARE.value in intent_result.aux_intents:
            transitions.append("考虑到信息的不确定性：")
            enhancements.extend([
                "我们会特别标注存在争议的信息",
                "对于最近更新的政策，会提供额外说明",
                "同时给出进一步核实的具体建议"
            ])
        
        if AuxIntentType.DEEP_REASONING.value in intent_result.aux_intents:
            transitions.append("为了让推理过程更透明：")
            enhancements.extend([
                "我们会详细展示每个决策的依据",
                "对重要结论提供充分的论证",
                "必要时引用相关法规或标准作为支持"
            ])
        
        if intent_result.risk_level == "high":
            transitions.append("由于存在较高风险：")
            enhancements.extend([
                "我们需要特别关注合规性问题",
                "建议进行多维度的交叉验证",
                "同时提供详细的风险防范建议"
            ])
        
        if enhancements:
            enhancement_text = ""
            for i, (transition, enhancement_group) in enumerate(zip(transitions, [enhancements[i:i+3] for i in range(0, len(enhancements), 3)])):
                enhancement_text += f"\n{transition}\n"
                enhancement_text += "\n".join(f"- {e}" for e in enhancement_group)
            
            query += f"\n\n处理要求：{enhancement_text}"
        
        return query

    async def _process_query(
        self,
        user_input: str,
        message_history: List[Dict[str, Any]],
        intent_result: IntentResult,
        docs: List[Dict] = None
    ) -> str:
        """统一处理各类查询请求"""
        try:
            formatted_history = self.format_message_history(message_history)
            
            # 1. 处理核心意图，获取查询和推理过程
            query_input, reasoning = self._process_core_intent(user_input, intent_result)
            
            # 2. 基于文档构造查询
            if docs:
                query_input = self._construct_doc_query(query_input, docs)
                
            # 3. 增强查询
            query_input = self._enhance_with_aux_intents(query_input, intent_result)
            
            # 4. 添加推理过程
            query_input = f"{reasoning}\n\n{query_input}"
            
            # 5. 执行查询
            response = await self.agent.ainvoke({
                "input": query_input,
                "chat_history": formatted_history
            })
            
            return self._extract_response(response)
            
        except Exception as e:
            logger.error(f"处理请求失败: {str(e)}")
            raise Exception(f"处理请求失败: {str(e)}")

    def _construct_doc_query(self, user_input: str, docs: List[Dict]) -> str:
        """构造基于文档的查询"""
        if not docs:
            return user_input
            
        docs_content = "\n\n".join([
            f"文档片段 {i+1}:\n{doc['content']}" 
            for i, doc in enumerate(docs)
        ])
        
        return (
            f"基于以下参考资料：\n\n"
            f"{docs_content}\n\n"
            f"请回答问题：\n{user_input}\n\n"
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
                try:
                    parsed = json.loads(response)
                    return self._extract_response(parsed)
                except json.JSONDecodeError:
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

    async def generate_response(
        self, 
        user_input: str, 
        message_history: List[Dict[str, Any]], 
        user_id: Optional[str] = None
    ) -> str:
        """根据用户输入和历史消息生成 AI 回复"""
        try:
            # 1. 意图识别
            intent_result = await intent_service.classify_intent(user_input)
            
            # 2. 获取相关文档（仅当有user_id且存在文档时）
            docs = []
            if user_id:
                docs = await self._get_relevant_docs(user_input, user_id)
            
            # 3. 统一处理请求
            return await self._process_query(user_input, message_history, intent_result, docs)
            
        except asyncio.TimeoutError:
            logger.error("响应超时")
            raise Exception("生成响应超时，请稍后重试")
        except Exception as e:
            error_msg = f"生成回复失败: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

# 全局服务实例
chat_service = ChatService()
