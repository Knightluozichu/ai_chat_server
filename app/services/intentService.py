#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from enum import Enum
from typing import Dict, List, Optional, Union
from pydantic import BaseModel
import logging
import json
import re
from pydantic import BaseModel, Field
from app.config import settings
import httpx
from datetime import datetime
from openai import OpenAI

logger = logging.getLogger(__name__)

class IntentResult(BaseModel):
    """意图识别结果"""
    core_intent: str
    aux_intents: List[str]
    confidence_score: float
    risk_level: str

class CoreIntentType(str, Enum):
    GENERATE_BID = "项目招标信息生成"                
    EVALUATE_BID = "投标文件评估"                
    PROCUREMENT_CONSULT = "采购流程咨询"  
    SUPPLIER_REVIEW = "供应商资格审查"          
    PRODUCT_COMPARE = "商品对比与选型"          
    LAW_INTERPRET = "法规条款解读"              
    RISK_ALERT = "风险预警"                    
    COST_CALCULATE = "成本测算"            
    TEMPLATE_GENERATE = "文档模板生成"      
    DATA_VERIFY = "数据验证"                  
    PROCESS_TRACE = "流程追溯"              
    EMERGENCY_HANDLE = "应急处理"        

class AuxIntentType(str, Enum):
    ENHANCED_SEARCH = "信息检索增强"          
    UNCERTAINTY_DECLARE = "不确定性声明"  
    DEEP_REASONING = "深度推理请求"            

class ProcurementConfig(BaseModel):
    domain_dict_path: str = Field(settings.PROCUREMENT_DOMAIN_DICT_PATH)
    chat_intent_enabled: bool = Field(settings.CHAT_INTENT_ENABLED)
    audit_season_weight: float = Field(1.2, description="审计季合规意图权重加成")
    embedding_model: str = Field("text-embedding-3-small", description="OpenAI embedding模型名称")
    intent_confusion_threshold: float = Field(0.15, description="意图混淆检测阈值")
    ocr_endpoint: str = Field("", description="OCR服务地址")  # 默认为空字符串
    policy_monitor_endpoint: str = Field("", description="政策监控服务地址")

class IntentService:
    def __init__(self):
        self.config = ProcurementConfig()
        self.domain_terms = self._load_domain_dict()
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.oai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # 动态生成系统提示词
        core_intent_desc = "\n".join([f"{it.value} ({it.name})" for it in CoreIntentType])
        aux_intent_desc = "\n".join([f"{it.value} ({it.name})" for it in AuxIntentType])
        
        self.system_prompt = f"""
您是一个采购招投标领域专业意图识别引擎。请严格按以下规则处理：

一、核心意图分类（单选）
{core_intent_desc}

二、辅助意图检测（多选）
{aux_intent_desc}

三、处理规则：
1. 法律条款引用检测：当文本包含§、第...条等法律符号时，优先匹配LAW_INTERPRET
2. 风险关键词加权：每匹配一个风险关键词，RISK_ALERT置信度+0.15（上限+0.45）
3. 审计季权重调整：当前为{"审计季" if self._is_audit_season() else "非审计季"}，合规类意图权重×{self.config.audit_season_weight}

四、输出要求：
```json
{{
    "core_intent": "意图类型标识",
    "aux_intents": ["辅助类型1", "辅助类型2"],
    "confidence_score": 0.0-1.0,
    "risk_level": "low/medium/high"
}}
```
请确保JSON格式正确，数值精度保留两位小数。
"""

    def _load_domain_dict(self) -> Dict[str, List[str]]:
        """加载采购领域专业词典"""
        try:
            with open(self.config.domain_dict_path, 'r', encoding='utf-8') as f:
                domain_data = json.load(f)
                logger.info(f"成功加载领域词典，包含{len(domain_data)}个类别，总计{sum(len(v) for v in domain_data.values())}个术语")
                return domain_data
        except Exception as e:
            logger.error(f"领域词典加载失败: {str(e)}")
            return {"risk_keywords": ["围标", "串标", "恶意低价", "资质造假"]}  # 默认风险关键词

    async def _check_policy_updates(self) -> bool:
        """检查政策更新状态"""
        if not self.config.policy_monitor_endpoint:
            return False
            
        try:
            if not settings.POLICY_MONITOR_API_KEY:
                logger.debug("未配置政策监控服务API密钥，跳过政策更新检查")
                return False
                
            response = await self.http_client.get(
                f"{self.config.policy_monitor_endpoint}/updates",
                params={"last_check": datetime.now().isoformat()},
                headers={"X-API-KEY": settings.POLICY_MONITOR_API_KEY}
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("has_update"):
                    logger.warning(f"检测到政策更新：{data.get('update_summary')}")
                return data.get("has_update", False)
            return False
        except httpx.ConnectError:
            logger.error("政策监测服务连接失败，请检查网络或服务状态")
            return False
        except Exception as e:
            logger.error(f"政策检查异常: {str(e)}")
            return False

    async def _process_attachments(self, files: Optional[List[Dict]] = None) -> str:
        """处理附件文件（支持PDF/图片）"""
        if not files:
            return ""
            
        ocr_text = ""
        for file in files:
            try:
                if not settings.OCR_SERVICE_ENDPOINT or not settings.OCR_API_KEY:
                    logger.debug("未配置OCR服务，跳过OCR处理")
                    continue
                    
                response = await self.http_client.post(
                    settings.OCR_SERVICE_ENDPOINT,
                    files={"file": open(file["path"], "rb")},
                    headers={"Authorization": f"Bearer {settings.OCR_API_KEY}"}
                )
                if response.status_code == 200:
                    ocr_text += response.json().get("text", "") + "\n"
            except Exception as e:
                logger.error(f"OCR处理失败：{str(e)}")
        return ocr_text.strip()

    def _get_embeddings(self, text: str) -> List[float]:
        """获取OpenAI文本嵌入向量"""
        try:
            response = self.oai_client.embeddings.create(
                input=text,
                model=self.config.embedding_model
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"获取文本向量失败: {str(e)}")
            return [0.0] * 1536  # text-embedding-3-small 默认维度

    async def classify_intent(
        self, 
        text: str, 
        files: Optional[List[Dict]] = None
    ) -> IntentResult:
        """
        层次化意图分类
        
        Args:
            text: 用户输入文本
            files: 可选的附件文件列表 [{"path": "文件路径", "type": "文件类型"}, ...]
            
        Returns:
            IntentResult: 意图识别结果
        """
        try:
            # 1. 多模态处理
            if files:
                ocr_text = await self._process_attachments(files)
                if ocr_text:
                    text += " " + ocr_text
                
            # 2. 特征提取
            embeddings = self._get_embeddings(text)
            
            # 3. 核心意图分类
            core_intent = await self._classify_core_intent(text)
            
            # 4. 辅助意图检测
            aux_intents = await self._detect_aux_intents(text)
            
            # 5. 动态权重调整
            if await self._check_policy_updates():
                logger.info("检测到政策更新，提升合规性相关意图权重")
                core_intent = self._adjust_weights(core_intent, aux_intents)

            # 6. 计算置信度
            base_score = min(0.85 + len(aux_intents)*0.05, 0.95)
            confidence = round(base_score + self._get_risk_bonus(text), 2)
            
            # 7. 风险评估
            risk_level = await self._assess_risk(text)
            
            return IntentResult(
                core_intent=core_intent.value,
                aux_intents=[a.value for a in aux_intents],
                confidence_score=confidence,
                risk_level=risk_level
            )

        except Exception as e:
            logger.error(f"意图识别流程异常: {str(e)}", exc_info=True)
            # 返回默认结果
            return IntentResult(
                core_intent=CoreIntentType.PROCUREMENT_CONSULT.value,
                aux_intents=[AuxIntentType.UNCERTAINTY_DECLARE.value],
                confidence_score=0.5,
                risk_level="high"
            )

    def _extract_domain_features(self, text: str) -> Dict[str, float]:
        """提取领域特征（增强版）"""
        features = {}
        # 1. 专业术语匹配（带权重）
        for category, terms in self.domain_terms.items():
            matches = sum(1 for term in terms if term in text)
            # 核心术语权重更高
            features[f"term_{category}"] = matches * (2.0 if category == "core_terms" else 1.0)
        
        # 2. 法律条款引用检测
        features["law_ref"] = 1 if any(c in text for c in ["§", "第", "条"]) else 0
        
        # 3. 数值型特征提取
        features["numeric_count"] = len([c for c in text if c.isdigit()])
        
        # 标准化特征值
        total_terms = sum(features.values())
        if total_terms:
            return {k: round(v/total_terms, 4) for k, v in features.items()}
        return features

    def _calculate_conflict(self, text: str) -> float:
        """计算信息冲突率（增强版）"""
        conflict_patterns = [
            (r"(虽然|尽管).*?(但是|然而)", 0.3),    # 转折连词
            (r"(\d+%?[^-]{0,20}不同[^-]{0,20}\d+%?)", 0.4),  # 数值矛盾
            (r"(应当|必须).*?(禁止|不得)", 0.5),     # 规范冲突
            (r"((前者|前者).*?(后者|后者))", 0.2)    # 对立表述
        ]
        total_score = 0.0
        for pattern, score in conflict_patterns:
            if re.search(pattern, text):
                total_score += score
        return min(total_score, 1.0)

    def _is_audit_season(self) -> bool:
        return datetime.now().month in [3, 6, 9, 12]

    def _get_risk_bonus(self, text: str) -> float:
        risk_keywords = self.domain_terms.get("risk_keywords", [])
        matches = sum(1 for kw in risk_keywords if kw in text)
        return min(0.15 * matches, 0.45)

    def _adjust_weights(self,
                      core_intent: CoreIntentType,
                      aux_intents: List[AuxIntentType]) -> CoreIntentType:
        """动态调整意图权重（增强版）"""
        # 基础权重调整
        if self._is_audit_season():  # 审计季
            if core_intent in [CoreIntentType.PROCUREMENT_CONSULT, CoreIntentType.LAW_INTERPRET]:
                core_intent = CoreIntentType.LAW_INTERPRET
        
        # 意图混淆补偿
        confusion_score = self._calculate_confusion(core_intent, aux_intents)
        if confusion_score > self.config.intent_confusion_threshold:
            return CoreIntentType.PROCUREMENT_CONSULT  # 退回流程咨询
            
        return core_intent

    def _calculate_confusion(self, 
                           core_intent: CoreIntentType,
                           aux_intents: List[AuxIntentType]) -> float:
        """计算意图混淆分数"""
        # 获取意图关联规则
        conflict_rules = self.domain_terms.get("intent_conflict_rules", {})
        
        # 计算核心意图与辅助意图的冲突值
        if not aux_intents:
            return 0.0
            
        conflict_score = sum(
            conflict_rules.get(f"{core_intent.name}-{aux.name}", 0) 
            for aux in aux_intents
        )
        
        # 标准化到0-1范围
        return min(conflict_score / len(aux_intents), 1.0)

    async def _classify_core_intent(self, text: str) -> CoreIntentType:
        """核心意图分类逻辑"""
        # 1. 领域特征提取
        features = self._extract_domain_features(text)
        
        # 2. 规则匹配优先
        if any(kw in text for kw in self.domain_terms.get("risk_keywords", [])):
            return CoreIntentType.RISK_ALERT
            
        # 3. OpenAI分类
        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"文本内容：{text}\n\n特征信息：{json.dumps(features, ensure_ascii=False)}"}
            ]
            
            response = self.oai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.2,
                max_tokens=50
            )
            
            intent_text = response.choices[0].message.content.strip()
            for intent_type in CoreIntentType:
                if intent_type.value in intent_text:
                    return intent_type
                    
            return CoreIntentType.PROCUREMENT_CONSULT
            
        except Exception as e:
            logger.error(f"OpenAI分类异常: {str(e)}")
            return CoreIntentType.PROCUREMENT_CONSULT

    async def _detect_aux_intents(self, text: str) -> List[AuxIntentType]:
        """辅助意图检测"""
        aux_intents = []
        
        # 信息检索增强条件
        if any(kw in text for kw in ["对比", "推荐", "top"]):
            aux_intents.append(AuxIntentType.ENHANCED_SEARCH)
            
        # 不确定性声明条件
        conflict_ratio = self._calculate_conflict(text)
        if conflict_ratio > 0.3:
            aux_intents.append(AuxIntentType.UNCERTAINTY_DECLARE)
            
        # 深度推理请求检测
        if "详细说明" in text or "推导过程" in text:
            aux_intents.append(AuxIntentType.DEEP_REASONING)
            
        return aux_intents

    async def _assess_risk(self, text: str) -> str:
        """风险等级评估"""
        if settings.PROCUREMENT_RISK_MODE == "LOCAL":
            try:
                with open(settings.LOCAL_RISK_RULES_PATH, 'r', encoding='utf-8') as f:
                    risk_rules = json.load(f)
                    return self._apply_local_risk_rules(text, risk_rules)
            except Exception as e:
                logger.error(f"本地风险评估失败: {str(e)}")
                return "high"
        else:
            try:
                messages = [
                    {"role": "system", "content": "您正在评估采购招投标文本的风险等级。请根据文本内容，判断其风险等级(low/medium/high)。"},
                    {"role": "user", "content": text}
                ]
                
                response = self.oai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    temperature=0.2,
                    max_tokens=10
                )
                
                risk_text = response.choices[0].message.content.strip().lower()
                if "high" in risk_text:
                    return "high"
                elif "medium" in risk_text:
                    return "medium"
                return "low"
                
            except Exception as e:
                logger.error(f"OpenAI风险评估失败: {str(e)}")
                return "high"

    def _apply_local_risk_rules(self, text: str, rules: dict) -> str:
        """应用本地风险规则"""
        risk_score = 0
        
        # 检测异常投标模式（增强版）
        for pattern in rules.get("bid_abnormal_patterns", []):
            # 使用正则表达式进行模式匹配
            if re.search(pattern["match_condition"], text):
                risk_score += rules["risk_weights"].get(pattern["risk_level"], 0)
        
        # 增强型合规检查（使用正则全匹配）
        for rule in rules.get("compliance_rules", []):
            # 要求所有检查点都必须完全匹配
            if all(re.search(rf'\b{keyword}\b', text) for keyword in rule["check_points"]):
                risk_score -= 0.3  # 增强合规项权重
        
        # 风险等级判定（调整阈值）
        if risk_score >= 0.75:    # 提高高风险阈值
            return "high"
        elif risk_score >= 0.45:  # 提高中风险阈值
            return "medium"
        return "low"

# 初始化服务实例
intent_service = IntentService()
