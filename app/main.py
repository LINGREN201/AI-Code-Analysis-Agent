"""
Main FastAPI Application
AI Code Analysis Agent API Service

This service provides two main endpoints:
1. /analyze - Analyze codebase and generate feature location report
2. /generate-tests - Dynamically generate and execute test code using LLM Function Calling

For API documentation and testing, visit: http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import analyze, generate_tests


def create_application() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title=settings.APP_NAME,
        description="""
        AI-powered code analysis service that:
        
        - Analyzes codebases and identifies feature implementations
        - Generates structured reports with file paths, functions, and line numbers
        - Dynamically generates and executes test code using LLM Function Calling
        
        **Recommended**: Use the Swagger UI at http://localhost:8000/docs for testing
        """,
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Enable CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(analyze.router, tags=["analysis"])
    app.include_router(generate_tests.router, tags=["testing"])
    
    return app


# Create application instance
app = create_application()


@app.get("/")
async def root():
    """
    Root endpoint - API 信息
    
    **推荐使用 Swagger UI 进行测试**: http://localhost:8000/docs
    """
    return {
        "message": f"{settings.APP_NAME} API",
        "version": settings.APP_VERSION,
        "docs": {
            "swagger_ui": "http://localhost:8000/docs",
            "redoc": "http://localhost:8000/redoc"
        },
        "endpoints": {
            "analyze": "POST /analyze - Analyze code and generate feature report",
            "generate_tests": "POST /generate-tests - Dynamically generate and execute test code"
        },
        "recommended_usage": "Please use Swagger UI at http://localhost:8000/docs for testing"
    }


@app.get("/health")
async def health():
    """
    Health check endpoint
    
    用于检查服务是否正常运行
    """
    return {"status": "healthy", "service": settings.APP_NAME}
