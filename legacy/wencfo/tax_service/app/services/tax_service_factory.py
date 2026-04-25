"""
报税服务工厂
根据配置创建不同的报税服务实例
"""
from typing import Dict, Any, Optional
from .base_tax_service import BaseTaxService
from .api_tax_service import APITaxService
from .browser_tax_service import BrowserTaxService
from ..core.config import settings


class TaxServiceFactory:
    """报税服务工厂"""
    
    @staticmethod
    def create_service(service_type: str, config: Dict[str, Any]) -> BaseTaxService:
        """创建报税服务实例"""
        if service_type == "api":
            return APITaxService(config)
        elif service_type == "browser":
            return BrowserTaxService(config)
        else:
            raise ValueError(f"不支持的报税服务类型: {service_type}")
    
    @staticmethod
    def create_hybrid_service(config: Dict[str, Any]) -> 'HybridTaxService':
        """创建混合报税服务"""
        return HybridTaxService(config)


class HybridTaxService(BaseTaxService):
    """混合报税服务
    根据报税类型和可用性自动选择API或浏览器自动化方式
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # 创建API和浏览器服务实例
        self.api_service = APITaxService(config.get("api_config", {}))
        self.browser_service = BrowserTaxService(config.get("browser_config", {}))
        
        # 服务优先级配置
        self.service_priority = {
            "vat": ["api", "browser"],  # 增值税优先使用API
            "income_tax": ["browser", "api"],  # 企业所得税优先使用浏览器
            "personal_tax": ["api", "browser"],
            "customs": ["browser"],  # 关税只能使用浏览器
            "other": ["browser", "api"]
        }
    
    async def submit_tax(self, request) -> 'TaxSubmissionResult':
        """智能选择报税方式"""
        tax_type = request.tax_type.value
        
        # 获取该税种的优先级顺序
        priority_list = self.service_priority.get(tax_type, ["browser", "api"])
        
        last_error = None
        
        for service_name in priority_list:
            try:
                if service_name == "api" and settings.TAX_API_ENABLED:
                    result = await self.api_service.submit_tax(request)
                    if result.status.value in ["completed", "in_progress"]:
                        return result
                    last_error = result.error_message
                    
                elif service_name == "browser" and settings.TAX_BROWSER_AUTOMATION_ENABLED:
                    result = await self.browser_service.submit_tax(request)
                    if result.status.value in ["completed", "in_progress"]:
                        return result
                    last_error = result.error_message
                    
            except Exception as e:
                last_error = str(e)
                continue
        
        # 所有方式都失败
        return TaxSubmissionResult(
            submission_id=f"hybrid_{request.user_id}_{request.tax_type.value}",
            status="failed",
            error_message=f"所有报税方式都失败，最后错误: {last_error}"
        )
    
    async def get_submission_status(self, submission_id: str):
        """获取报税状态"""
        # 根据submission_id判断使用哪个服务
        if submission_id.startswith("api_"):
            return await self.api_service.get_submission_status(submission_id)
        elif submission_id.startswith("browser_"):
            return await self.browser_service.get_submission_status(submission_id)
        else:
            # 尝试两个服务
            try:
                return await self.api_service.get_submission_status(submission_id)
            except:
                return await self.browser_service.get_submission_status(submission_id)
    
    async def cancel_submission(self, submission_id: str) -> bool:
        """取消报税"""
        if submission_id.startswith("api_"):
            return await self.api_service.cancel_submission(submission_id)
        elif submission_id.startswith("browser_"):
            return await self.browser_service.cancel_submission(submission_id)
        else:
            # 尝试两个服务
            try:
                return await self.api_service.cancel_submission(submission_id)
            except:
                return await self.browser_service.cancel_submission(submission_id)
    
    async def validate_tax_data(self, tax_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证税务数据"""
        # 使用API服务进行验证（通常更准确）
        try:
            return await self.api_service.validate_tax_data(tax_data)
        except:
            return await self.browser_service.validate_tax_data(tax_data)
    
    async def get_supported_tax_types(self):
        """获取支持的报税类型"""
        api_types = await self.api_service.get_supported_tax_types()
        browser_types = await self.browser_service.get_supported_tax_types()
        
        # 合并两个服务的支持类型
        all_types = set(api_types + browser_types)
        return list(all_types)
