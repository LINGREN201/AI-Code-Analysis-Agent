"""
Analysis API Routes
"""
import os
import tempfile
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
import aiofiles
import traceback

from app.core.config import settings
from app.services.code_analyzer import CodeAnalyzer
from app.services.ai_analyzer import AIAnalyzer
from app.utils.response_formatter import ResponseFormatter
from app.services.test_generator import TestGenerator

router = APIRouter()


@router.post("/analyze")
async def analyze_code(
    problem_description: str = Form(
        ..., 
        description="功能描述，例如：'实现用户管理功能，包括创建用户、获取用户列表、更新用户信息'"
    ),
    code_zip: UploadFile = File(
        ..., 
        description="包含源代码的 ZIP 压缩文件（最大 50MB）"
    ),
    include_tests: Optional[bool] = Form(
        False, 
        description="是否包含测试生成和执行（可选，默认 false）"
    )
):
    """
    分析代码库并生成功能定位报告
    
    此接口的主要功能：
    
    1. **代码分析**: 提取代码结构，识别文件、函数、类等
    2. **功能匹配**: 使用 AI 分析功能描述，匹配到代码实现位置
    3. **报告生成**: 生成包含文件路径、函数名、行号的结构化报告
    4. **测试生成**（可选）: 如果 `include_tests=true`，还会生成并执行测试
    
    **推荐使用 Swagger UI 测试**: http://localhost:8000/docs
    
    **请求参数**:
    - `problem_description`: 功能描述（字符串，必填）
    - `code_zip`: 代码 ZIP 文件（文件上传，必填）
    - `include_tests`: 是否包含测试（布尔值，可选）
    
    **响应格式**:
    ```json
    {
      "feature_analysis": [
        {
          "feature_description": "功能描述",
          "implementation_location": [
            {
              "file": "path/to/file.py",
              "function": "function_name",
              "lines": "10-20"
            }
          ]
        }
      ],
      "execution_plan_suggestion": "执行计划建议",
      "functional_verification": {
        "generated_test_code": "...",
        "execution_result": {...}
      }
    }
    ```
    
    **示例**:
    1. 访问 http://localhost:8000/docs
    2. 找到 `/analyze` 接口
    3. 点击 "Try it out"
    4. 填写参数并上传文件
    5. 点击 "Execute" 执行
    """
    temp_zip_path = None
    code_analyzer = None
    
    try:
        # Validate file type
        if not code_zip.filename:
            raise HTTPException(
                status_code=400,
                detail="No filename provided"
            )
        
        if not code_zip.filename.endswith('.zip'):
            raise HTTPException(
                status_code=400,
                detail="File must be a .zip file"
            )
        
        # Validate file size
        file_size = 0
        temp_zip_path = os.path.join(tempfile.gettempdir(), f"code_analysis_{os.urandom(8).hex()}.zip")
        
        async with aiofiles.open(temp_zip_path, 'wb') as f:
            while chunk := await code_zip.read(1024 * 1024):  # Read in 1MB chunks
                file_size += len(chunk)
                if file_size > settings.MAX_UPLOAD_SIZE:
                    raise HTTPException(
                        status_code=400,
                        detail=f"File size exceeds {settings.MAX_UPLOAD_SIZE / (1024*1024)}MB limit"
                    )
                await f.write(chunk)
        
        # Validate problem description
        if not problem_description or len(problem_description.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="problem_description is required"
            )
        
        # Initialize code analyzer
        code_analyzer = CodeAnalyzer(temp_zip_path)
        
        # Extract and analyze code
        extracted_path = code_analyzer.extract_zip()
        file_tree = code_analyzer.get_file_tree()
        code_structure = code_analyzer.analyze_code_structure()
        code_summary = code_analyzer.get_code_summary()
        file_contents = code_analyzer.get_relevant_files_content()
        
        # Initialize AI analyzer
        try:
            ai_analyzer = AIAnalyzer()
        except ValueError as e:
            raise HTTPException(
                status_code=500,
                detail=f"AI service initialization failed: {str(e)}. Please check OPENAI_API_KEY in environment variables."
            )
        
        # Perform AI analysis
        try:
            ai_result = ai_analyzer.analyze_features(
                problem_description=problem_description,
                code_summary=code_summary,
                file_contents=file_contents,
                code_structure=code_structure
            )
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"AI analysis failed: {str(e)}"
            )
        
        # Generate execution plan
        execution_plan = ai_analyzer.generate_execution_plan(
            code_summary=code_summary,
            file_tree=file_tree
        )
        
        # Format response
        response = ResponseFormatter.format_feature_analysis(
            ai_result=ai_result,
            execution_plan=execution_plan
        )
        
        # Generate and execute tests if requested
        if include_tests:
            try:
                test_generator = TestGenerator(code_analyzer, ai_analyzer)
                test_results = test_generator.generate_and_execute_tests(
                    problem_description=problem_description,
                    feature_analysis=response.get("feature_analysis", [])
                )
                
                response = ResponseFormatter.add_test_results(
                    response=response,
                    test_code=test_results.get("generated_test_code", ""),
                    test_result=test_results.get("execution_result", {})
                )
            except Exception as e:
                # Don't fail the entire request if test generation fails
                traceback.print_exc()
                response["functional_verification"] = {
                    "generated_test_code": "",
                    "execution_result": {
                        "tests_passed": False,
                        "log": f"Test generation failed: {str(e)}"
                    }
                }
        
        return JSONResponse(content=response)
        
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        error_response = ResponseFormatter.format_error(
            error_message=f"Unexpected error: {str(e)}",
            error_type="internal_error"
        )
        return JSONResponse(
            status_code=500,
            content=error_response
        )
    finally:
        # Cleanup
        if code_analyzer:
            code_analyzer.cleanup()
        
        if temp_zip_path and os.path.exists(temp_zip_path):
            try:
                os.remove(temp_zip_path)
            except Exception:
                pass
