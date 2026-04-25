"""
API报税服务实现
通过HTTP API调用税务系统进行报税
"""
import httpx
import asyncio
from typing import Dict, Any, List
from datetime import datetime

from .base_tax_service import (
    BaseTaxService, 
    TaxSubmissionRequest, 
    TaxSubmissionResult,
    TaxSubmissionStatus,
    TaxSubmissionType
)


class APITaxService(BaseTaxService):
    """API报税服务"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_base_url = config.get("api_base_url")
        self.api_key = config.get("api_key")
        self.api_secret = config.get("api_secret")
        self.timeout = config.get("timeout", 30)
        self.retry_count = config.get("retry_count", 3)
        
        # 支持的报税类型
        self.supported_types = [
            TaxSubmissionType.VAT,
            TaxSubmissionType.INCOME_TAX,
            TaxSubmissionType.PERSONAL_TAX
        ]
    
    async def submit_tax(self, request: TaxSubmissionRequest) -> TaxSubmissionResult:
        """通过API提交报税"""
        submission_id = f"api_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{request.user_id}"
        
        try:
            # 验证数据
            validation_result = await self.validate_tax_data(request.submission_data)
            if not validation_result.get("valid", False):
                return TaxSubmissionResult(
                    submission_id=submission_id,
                    status=TaxSubmissionStatus.FAILED,
                    error_message=f"数据验证失败: {validation_result.get('errors', [])}"
                )
            
            # 准备API请求
            api_request_data = {
                "tax_type": request.tax_type.value,
                "tax_period": request.tax_period,
                "data": request.submission_data,
                "metadata": request.metadata or {}
            }
            
            # 调用税务系统API
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                response = await client.post(
                    f"{self.api_base_url}/tax/submit",
                    json=api_request_data,
                    headers=headers
                )
                
                if response.status_code == 200:
                    result_data = response.json()
                    return TaxSubmissionResult(
                        submission_id=submission_id,
                        status=TaxSubmissionStatus.COMPLETED,
                        result_data=result_data,
                        submission_time=datetime.now().isoformat(),
                        completion_time=datetime.now().isoformat(),
                        external_reference=result_data.get("reference_id")
                    )
                else:
                    return TaxSubmissionResult(
                        submission_id=submission_id,
                        status=TaxSubmissionStatus.FAILED,
                        error_message=f"API调用失败: {response.status_code} - {response.text}"
                    )
                    
        except Exception as e:
            return TaxSubmissionResult(
                submission_id=submission_id,
                status=TaxSubmissionStatus.FAILED,
                error_message=f"API报税异常: {str(e)}"
            )
    
    async def get_submission_status(self, submission_id: str) -> TaxSubmissionResult:
        """获取API报税状态"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                
                response = await client.get(
                    f"{self.api_base_url}/tax/status/{submission_id}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return TaxSubmissionResult(
                        submission_id=submission_id,
                        status=TaxSubmissionStatus(data.get("status", "pending")),
                        result_data=data.get("result"),
                        external_reference=data.get("reference_id")
                    )
                else:
                    return TaxSubmissionResult(
                        submission_id=submission_id,
                        status=TaxSubmissionStatus.FAILED,
                        error_message=f"获取状态失败: {response.status_code}"
                    )
                    
        except Exception as e:
            return TaxSubmissionResult(
                submission_id=submission_id,
                status=TaxSubmissionStatus.FAILED,
                error_message=f"获取状态异常: {str(e)}"
            )
    
    async def cancel_submission(self, submission_id: str) -> bool:
        """取消API报税"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                
                response = await client.post(
                    f"{self.api_base_url}/tax/cancel/{submission_id}",
                    headers=headers
                )
                
                return response.status_code == 200
                
        except Exception as e:
            print(f"取消报税异常: {str(e)}")
            return False
    
    async def validate_tax_data(self, tax_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证税务数据"""
        errors = []
        
        # 基本验证逻辑
        if not tax_data.get("amount"):
            errors.append("缺少金额信息")
        
        if not tax_data.get("tax_period"):
            errors.append("缺少税务期间")
        
        # 可以添加更多验证规则
        # 比如调用税务系统的验证API
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    async def get_supported_tax_types(self) -> List[TaxSubmissionType]:
        """获取支持的报税类型"""
        return self.supported_types
