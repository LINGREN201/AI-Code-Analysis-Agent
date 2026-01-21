"""
Test Generation API Routes
"""
import os
import tempfile
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
import aiofiles
import traceback

from app.core.config import settings
from app.services.code_analyzer import CodeAnalyzer
from app.services.ai_analyzer import AIAnalyzer
from app.services.test_generator import TestGenerator

router = APIRouter()


@router.post("/generate-tests")
async def generate_tests(
    problem_description: str = Form(
        ..., 
        description="要测试的功能描述，例如：'测试产品创建功能，包括创建产品、获取产品列表等'"
    ),
    code_zip: UploadFile = File(
        ..., 
        description="包含源代码的 ZIP 压缩文件（最大 50MB）"
    )
):
    """
    动态生成和执行测试代码
    
    此接口专注于测试生成和执行，使用 LLM Function Calling 技术：
    
    1. **代码分析**: 提取并分析代码库结构
    2. **功能定位**: 识别功能实现位置
    3. **测试生成**: LLM 智能生成测试代码
    4. **测试执行**: 自动安装依赖并执行测试
    5. **结果返回**: 返回生成的测试代码和执行结果
    
    **推荐使用 Swagger UI 测试**: http://localhost:8000/docs
    
    **请求参数**:
    - `problem_description`: 要测试的功能描述（字符串）
    - `code_zip`: 代码 ZIP 文件（文件上传）
    
    **响应格式**:
    ```json
    {
      "feature_analysis": [...],
      "functional_verification": {
        "generated_test_code": "生成的测试代码",
        "execution_result": {
          "tests_passed": true/false,
          "log": "执行日志"
        }
      }
    }
    ```
    
    **示例**:
    1. 访问 http://localhost:8000/docs
    2. 找到 `/generate-tests` 接口
    3. 点击 "Try it out"
    4. 填写 `problem_description` 和上传 `code_zip`
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
        temp_zip_path = os.path.join(tempfile.gettempdir(), f"test_generation_{os.urandom(8).hex()}.zip")
        
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
        
        # Initialize AI analyzer
        try:
            ai_analyzer = AIAnalyzer()
        except ValueError as e:
            raise HTTPException(
                status_code=500,
                detail=f"AI service initialization failed: {str(e)}. Please check OPENAI_API_KEY in environment variables."
            )
        
        # Perform feature analysis for context (optional but helpful)
        try:
            file_contents = code_analyzer.get_relevant_files_content()
            feature_analysis_result = ai_analyzer.analyze_features(
                problem_description=problem_description,
                code_summary=code_summary,
                file_contents=file_contents,
                code_structure=code_structure
            )
            feature_analysis = feature_analysis_result.get("feature_analysis", [])
        except Exception as e:
            traceback.print_exc()
            print(f"Feature analysis warning (continuing anyway): {str(e)}")
            feature_analysis = []
        
        # Generate and execute tests using LLM Function Calling
        try:
            test_generator = TestGenerator(code_analyzer, ai_analyzer)
            test_results = test_generator.generate_and_execute_tests(
                problem_description=problem_description,
                feature_analysis=feature_analysis
            )
            
            # Format response according to required structure
            response = {
                "feature_analysis": feature_analysis if feature_analysis else [],
                "functional_verification": {
                    "generated_test_code": test_results.get("generated_test_code", ""),
                    "execution_result": test_results.get("execution_result", {
                        "tests_passed": False,
                        "log": ""
                    })
                }
            }
            
            return JSONResponse(content=response)
            
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"Test generation failed: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        error_response = {
            "error": True,
            "error_type": "internal_error",
            "message": f"Unexpected error: {str(e)}"
        }
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
