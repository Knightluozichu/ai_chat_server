#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import asyncio
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import List, Dict, Any, Optional
from langchain.agents import AgentType, initialize_agent
from langchain_community.utilities import SerpAPIWrapper
from langchain.tools import Tool
from langchain.utilities import DuckDuckGoSearchAPIWrapper

from app.config import settings
from app.services.supabase import supabase_service
from app.services.intentService import intent_service, IntentType

logger = logging.getLogger(__name__)

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

            # # 初始化搜索工具
            # search = SerpAPIWrapper(serpapi_api_key=settings.SERPAPI_API_KEY)
            # self.tool = [
            #     Tool(
            #         name="Search",
            #         func=search.run,
            #         description="当你需要搜索实时信息时使用这个工具"
            #     )
            # ]
            
           # 初始化搜索工具
            general_search = DuckDuckGoSearchAPIWrapper(
                region="cn-zh",
                max_results=3,
                time='m',
                safesearch='moderate'
            )

            # 初始化商品搜索工具
            product_search = DuckDuckGoSearchAPIWrapper(
                region="cn-zh",
                max_results=5,
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
                        你是一名在采购招投标领域具有专业知识和丰富经验的智能助手，需要针对不同需求场景（如项目招标信息生成、投标文件评估、采购流程咨询、供应商资格审查等），提供严谨、准确且可追溯的解决方案或信息。你应始终遵循以下要求：
                        	1.	回答语言
                        	•	请始终使用中文回答问题。
                        	2.	搜索与信息处理
                        	•	当需要检索信息时，应优先查找排名前3的网页或可靠来源，并提取其正文内容。
                        	•	去除重复或相似的部分，进行简要的总结与摘要。
                        	•	务必结合最新的搜索信息。如果搜索结果中包含具体数值，请直接引用，避免自行编造或使用虚假数据。
                        	3.	专业与严谨
                        	•	所有答案应基于采购招投标的行业标准、法律法规（如《政府采购法》《招标投标法》等）以及权威来源。
                        	•	引用法律条款、技术规范或标准时，需保证来源可信、内容准确，并在必要时列出参考依据。
                        	4.	合规与合法
                        	•	对可能存在法律合规风险的问题，要及时提示并给出可行的合规建议。
                        	•	不得提供任何违规、舞弊或不公平竞争的引导或暗示。
                        	5.	准确与可靠
                        	•	回答中出现的专业术语、数据信息或技术指标应有充分依据，逻辑严整并可追溯。
                        	•	如遇难以确定的事项，应明确说明不确定性，或提出进一步调查和确认的建议。
                        	6.	覆盖不同场景
                        	•	项目招标信息生成：应包括项目概述、采购内容及规格要求、投标人资质、招标时间安排、投标文件递交方式及地点、评标标准等关键信息。
                        	•	投标文件评估：从商务（报价、条款等）、技术（方案可行性、指标满足度等）、服务（售后、培训等）多角度评估，并指出优劣势。
                        	•	采购招投标流程咨询：覆盖从项目审批、预算确定到发布招标公告、编制投标文件、开标评标、定标和合同签订的完整流程，并强调各阶段合规要点。
                        	•	供应商资格审查：包括营业执照、行业资质、业绩、财务、信誉等审查标准，明确判断依据与衡量方式。
                            •	商品对比与选型：根据需求特点、性能指标、价格、售后服务等因素，提供合理的商品对比分析和选型建议，输出用表格形式。
                        	7.	客观与中立
                        	•	回答时不应偏向任何投标方或供应商，也不得表现出不当利益倾斜。
                        	•	对方案或供应商的比较分析需中立客观，基于事实与数据。
                        	8.	信息安全与保密
                        	•	不得泄露用户的机密或敏感信息，对商业秘密材料应妥善保护。
                        	•	避免在公共答复中出现可识别具体单位或个人的敏感信息。
                        	9.	可操作性与明确性
                        	•	回答应条理清晰，尽量给出可执行的步骤或方案。
                        	•	必要时使用示例或格式化方式（如清单、表格）帮助用户理解和落地实施。
                        	10.	持续更新与改进

                        	•	保持对最新政策法规、行业实践和市场动态的关注，及时更新知识库。
                        	•	若发现信息错误或不足，应迅速进行核实与修正，持续优化自身答案质量。
                        
                        商品搜索与比较指南：
                            1. 搜索策略
                               • 使用 ProductSearch 工具在电商平台（1688、京东、义乌购）搜索商品信息
                               • 优先关注以下信息：
                                 - 月销量/总销量排名
                                 - 店铺等级与评分
                                 - 价格区间与价格趋势
                                 - 商品规格与参数
                                 - 买家真实评价

                            2. 数据处理要求
                               • 销量数据：标注具体时间段（如月销量/年销量）
                               • 价格信息：注明价格区间，标识是否含税、运费
                               • 规格参数：突出关键技术指标和质量标准
                               • 评价信息：筛选有效评价，提炼共性问题

                            3. 比较分析框架
                               • 必须使用表格形式展示对比信息：
                                 | 商品名称 | 价格区间 | 销量/评分 | 规格参数 | 质量等级 | 售后服务 | 适用场景 |
                               • 每个商品至少包含以上7个维度的信息
                               • 价格区间需标注最低起订量

                            4. 采购建议规范
                               • 基于以下维度提供选购建议：
                                 - 性价比分析
                                      - 质量可靠性
                                 - 供应商资质
                                 - 交货能力
                                 - 售后保障
                               • 说明不同价位产品的适用场景
                               • 提供规模采购的议价建议

                            5. 风险提示
                               • 提示价格异常低的潜在风险
                               • 标注质量认证缺失的隐患
                               • 说明售后服务的保障范围
                               • 注意供应商资质的完整性
                        请在每一次回答时，严格遵循以上准则，确保输出内容专业、严谨、准确、可靠，并能有效解决采购招投标领域内的各类需求。
                            
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

    async def _get_relevant_docs(
        self, query: str, user_id: str
    ) -> List[Dict]:
        """
        获取相关文档片段
        
        Args:
            query: 查询文本
            user_id: 用户ID
            
        Returns:
            相关文档列表
        """
        try:
            # 生成查询文本的向量嵌入
            query_embedding = await self.embeddings.aembed_query(query)
            
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

    async def _process_query(
        self,
        user_input: str,
        message_history: List[Dict[str, Any]],
        intent: IntentType,
        docs: List[Dict] = None
    ) -> str:
        """
        统一处理各类查询请求

        Args:
            user_input: 用户输入
            message_history: 历史消息记录
            intent: 意图类型
            docs: 相关文档列表（可选）

        Returns:
            处理后的响应字符串
        """
        try:
            formatted_history = self.format_message_history(message_history)
            
            # 根据不同意图构造输入
            input_map = {
                IntentType.QUERY: f"请搜索并回答：{user_input}",
                IntentType.DOCUMENT: self._construct_doc_query(user_input, docs),
                IntentType.TASK: f"执行任务：{user_input}",
                IntentType.CHAT: user_input
            }
            
            query_input = input_map.get(intent, user_input)
            
            response = await self.agent.ainvoke({
                "input": query_input,
                "chat_history": formatted_history
            })
            
            return self._extract_response(response)
            
        except Exception as e:
            logger.error(f"处理{intent.value}请求失败: {str(e)}")
            raise Exception(f"处理请求失败: {str(e)}")

    def _construct_doc_query(self, user_input: str, docs: List[Dict]) -> str:
        """构造基于文档的查询"""
        if not docs:
            return user_input
            
        docs_content = "\n\n".join([
            f"文档片段 {i+1}:\n{doc['content']}" 
            for i, doc in enumerate(docs)
        ])
        
        return f"基于以下文档内容回答问题：\n\n{docs_content}\n\n问题：{user_input}"

    def _extract_response(self, response: Any) -> str:
        """从响应中提取有效内容"""
        try:
            if isinstance(response, dict):
                for key in ["action_input", "output", "response", "answer"]:
                    if key in response and response[key]:
                        return str(response[key]).strip()
                return str(response)
                
            if isinstance(response, str):
                try:
                    parsed = json.loads(response)
                    return self._extract_response(parsed)
                except json.JSONDecodeError:
                    return response.strip()
                    
            return str(response)
            
        except Exception as e:
            logger.error(f"提取响应内容失败: {str(e)}")
            return str(response)

    async def generate_response(
        self, 
        user_input: str, 
        message_history: List[Dict[str, Any]], 
        user_id: Optional[str] = None
    ) -> str:
        """
        根据用户输入和历史消息生成 AI 回复

        Args:
            user_input: 用户输入的文本
            message_history: 历史消息记录
            user_id: 用户ID（可选）

        Returns:
            AI 生成的响应文本

        Raises:
            Exception: 当处理失败时抛出异常
        """
        try:
            # 1. 意图识别
            intent = await intent_service.classify_intent(user_input)
            
            # 2. 获取相关文档（仅当有user_id且为文档相关查询时）
            docs = []
            if user_id and intent == IntentType.DOCUMENT:
                docs = await self._get_relevant_docs(user_input, user_id)
            
            # 3. 统一处理请求
            return await self._process_query(user_input, message_history, intent, docs)
            
        except asyncio.TimeoutError:
            logger.error("响应超时")
            raise Exception("生成响应超时，请稍后重试")
        except Exception as e:
            error_msg = f"生成回复失败: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

# 全局服务实例
chat_service = ChatService()
