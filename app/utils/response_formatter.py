"""
Response Formatter Module

将分析结果格式化为结构化的 JSON 响应。

主要功能：
- 格式化功能分析结果
- 添加测试结果到响应
- 格式化错误响应
- 验证和清理数据结构
"""
from typing import Dict, List, Optional, Any


class ResponseFormatter:
    """Formats analysis results into structured JSON responses."""
    
    @staticmethod
    def format_feature_analysis(
        ai_result: Dict,
        execution_plan: Optional[str] = None
    ) -> Dict:
        """
        Format feature analysis results.
        
        Args:
            ai_result: Raw AI analysis result
            execution_plan: Optional execution plan suggestion
            
        Returns:
            Formatted response dictionary
        """
        response = {
            "feature_analysis": ai_result.get("feature_analysis", []),
            "execution_plan_suggestion": execution_plan or ai_result.get("execution_plan_suggestion", "")
        }
        
        # Validate and clean feature analysis
        if isinstance(response["feature_analysis"], list):
            response["feature_analysis"] = [
                ResponseFormatter._clean_feature_item(item)
                for item in response["feature_analysis"]
            ]
        
        return response
    
    @staticmethod
    def _clean_feature_item(item: Dict) -> Dict:
        """Clean and validate a single feature analysis item."""
        cleaned = {
            "feature_description": item.get("feature_description", ""),
            "implementation_location": []
        }
        
        locations = item.get("implementation_location", [])
        if isinstance(locations, list):
            for loc in locations:
                cleaned_loc = ResponseFormatter._clean_location(loc)
                if cleaned_loc:
                    cleaned["implementation_location"].append(cleaned_loc)
        
        return cleaned
    
    @staticmethod
    def _clean_location(loc: Dict) -> Optional[Dict]:
        """Clean and validate an implementation location."""
        if not isinstance(loc, dict):
            return None
        
        cleaned = {
            "file": loc.get("file", ""),
            "function": loc.get("function", ""),
            "lines": loc.get("lines", "")
        }
        
        # Validate that we have at least file and function
        if not cleaned["file"] or not cleaned["function"]:
            return None
        
        return cleaned
    
    @staticmethod
    def add_test_results(
        response: Dict,
        test_code: str,
        test_result: Dict
    ) -> Dict:
        """
        Add test generation and execution results to response.
        
        Args:
            response: Base response dictionary
            test_code: Generated test code
            test_result: Test execution results
            
        Returns:
            Response dictionary with test results added
        """
        response["functional_verification"] = {
            "generated_test_code": test_code,
            "execution_result": test_result
        }
        
        return response
    
    @staticmethod
    def format_error(error_message: str, error_type: str = "general") -> Dict:
        """
        Format error response.
        
        Args:
            error_message: Error message
            error_type: Type of error
            
        Returns:
            Error response dictionary
        """
        return {
            "error": True,
            "error_type": error_type,
            "message": error_message
        }
