"""
报税服务基类
定义统一的报税接口，支持API和浏览器自动化两种方式
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel


class TaxSubmissionStatus(str, Enum):
    """报税状态枚举"""
    PENDING = "pending"          # 待处理
    IN_PROGRESS = "in_progress"  # 处理中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"           # 失败
    CANCELLED = "cancelled"     # 已取消


class TaxSubmissionType(str, Enum):
    """报税类型枚举"""
    VAT = "vat"                 # 增值税
    INCOME_TAX = "income_tax"   # 企业所得税
    PERSONAL_TAX = "personal_tax"  # 个人所得税
    CUSTOMS = "customs"         # 关税
    OTHER = "other"             # 其他


class TaxSubmissionRequest(BaseModel):
    """报税请求模型"""
    user_id: str
    tax_type: TaxSubmissionType
    tax_period: str  # 如 "2024-01", "2024-Q1"
    submission_data: Dict[str, Any]
    submission_method: str = "auto"  # auto, manual, hybrid
    priority: int = 1  # 优先级 1-10
    metadata: Optional[Dict[str, Any]] = None


class TaxSubmissionResult(BaseModel):
    """报税结果模型"""
    submission_id: str
    status: TaxSubmissionStatus
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    submission_time: Optional[str] = None
    completion_time: Optional[str] = None
    external_reference: Optional[str] = None  # 外部系统参考号


class BaseTaxService(ABC):
    """报税服务基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.service_name = self.__class__.__name__
    
    @abstractmethod
    async def submit_tax(self, request: TaxSubmissionRequest) -> TaxSubmissionResult:
        """提交报税"""
        pass
    
    @abstractmethod
    async def get_submission_status(self, submission_id: str) -> TaxSubmissionResult:
        """获取报税状态"""
        pass
    
    @abstractmethod
    async def cancel_submission(self, submission_id: str) -> bool:
        """取消报税"""
        pass
    
    @abstractmethod
    async def validate_tax_data(self, tax_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证税务数据"""
        pass
    
    @abstractmethod
    async def get_supported_tax_types(self) -> List[TaxSubmissionType]:
        """获取支持的报税类型"""
        pass
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "service": self.service_name,
            "status": "healthy",
            "config": self.config
        }
