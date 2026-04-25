"""
报税服务API路由
提供统一的报税接口，支持API和浏览器自动化两种方式
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List, Dict, Any
from datetime import datetime

from ...services.tax_service_factory import TaxServiceFactory
from ...services.base_tax_service import (
    TaxSubmissionRequest, 
    TaxSubmissionResult,
    TaxSubmissionType,
    TaxSubmissionStatus
)
from ...core.config import settings

router = APIRouter()

# 创建报税服务实例
tax_service = TaxServiceFactory.create_hybrid_service({
    "api_config": {
        "api_base_url": "https://api.tax.gov.cn",
        "api_key": "your_api_key",
        "api_secret": "your_api_secret",
        "timeout": settings.TAX_API_TIMEOUT,
        "retry_count": settings.TAX_API_RETRY_COUNT
    },
    "browser_config": {
        "headless": settings.BROWSER_HEADLESS,
        "timeout": settings.BROWSER_TIMEOUT,
        "wait_timeout": settings.BROWSER_WAIT_TIMEOUT
    }
})


@router.post("/tax/submit", response_model=TaxSubmissionResult)
async def submit_tax(
    request: TaxSubmissionRequest,
    background_tasks: BackgroundTasks
):
    """
    提交报税
    
    支持两种方式：
    1. API自动报税：通过HTTP API调用税务系统
    2. 浏览器自动化：使用Computer Use技术操作浏览器
    
    系统会根据报税类型和可用性自动选择最佳方式
    """
    try:
        # 验证请求
        if not request.user_id:
            raise HTTPException(status_code=400, detail="用户ID不能为空")
        
        if not request.tax_type:
            raise HTTPException(status_code=400, detail="报税类型不能为空")
        
        # 提交报税
        result = await tax_service.submit_tax(request)
        
        # 如果是异步处理，可以在这里添加后台任务
        if result.status == TaxSubmissionStatus.IN_PROGRESS:
            background_tasks.add_task(process_tax_submission_async, result.submission_id)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"报税提交失败: {str(e)}")


@router.get("/tax/status/{submission_id}", response_model=TaxSubmissionResult)
async def get_submission_status(submission_id: str):
    """获取报税状态"""
    try:
        result = await tax_service.get_submission_status(submission_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.post("/tax/cancel/{submission_id}")
async def cancel_submission(submission_id: str):
    """取消报税"""
    try:
        success = await tax_service.cancel_submission(submission_id)
        return {"success": success, "message": "取消成功" if success else "取消失败"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取消报税失败: {str(e)}")


@router.post("/tax/validate")
async def validate_tax_data(tax_data: Dict[str, Any]):
    """验证税务数据"""
    try:
        result = await tax_service.validate_tax_data(tax_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据验证失败: {str(e)}")


@router.get("/tax/supported-types")
async def get_supported_tax_types():
    """获取支持的报税类型"""
    try:
        types = await tax_service.get_supported_tax_types()
        return {
            "supported_types": [t.value for t in types],
            "descriptions": {
                "vat": "增值税",
                "income_tax": "企业所得税", 
                "personal_tax": "个人所得税",
                "customs": "关税",
                "other": "其他税种"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取支持类型失败: {str(e)}")


@router.get("/tax/methods")
async def get_available_methods():
    """获取可用的报税方式"""
    return {
        "api_automation": {
            "enabled": settings.TAX_API_ENABLED,
            "description": "API自动报税",
            "advantages": ["快速", "稳定", "可批量处理"],
            "requirements": ["税务系统API", "API密钥"]
        },
        "browser_automation": {
            "enabled": settings.TAX_BROWSER_AUTOMATION_ENABLED,
            "description": "浏览器自动化报税",
            "advantages": ["通用性强", "无需API", "支持任何网站"],
            "requirements": ["网站访问权限", "登录凭据"]
        },
        "hybrid_mode": {
            "enabled": True,
            "description": "智能混合模式",
            "advantages": ["自动选择最佳方式", "高可用性", "智能降级"],
            "strategy": "根据税种和可用性自动选择API或浏览器方式"
        }
    }


@router.get("/tax/health")
async def health_check():
    """报税服务健康检查"""
    try:
        api_health = await tax_service.api_service.health_check()
        browser_health = await tax_service.browser_service.health_check()
        
        return {
            "overall_status": "healthy",
            "services": {
                "api_service": api_health,
                "browser_service": browser_health
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "overall_status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


async def process_tax_submission_async(submission_id: str):
    """异步处理报税提交"""
    # 这里可以实现异步处理逻辑
    # 比如定期检查状态、发送通知等
    pass
