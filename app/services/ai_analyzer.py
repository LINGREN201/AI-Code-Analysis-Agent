"""
AI Analysis Module

使用 OpenAI API（可配置 base_url）分析代码并匹配功能到实现位置。

主要功能：
- OpenAI/Qwen API 客户端初始化
- 功能分析和匹配（使用 LLM）
- 执行计划生成
- 支持 DashScope 兼容端点（默认）和标准 OpenAI API
"""
import json
from typing import Dict, List, Optional
from openai import OpenAI

from app.core.config import settings


class AIAnalyzer:
    """Uses OpenAI API to analyze code and generate feature analysis."""
    
    def __init__(self):
        """Initialize OpenAI API client."""
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )
        self.model = settings.OPENAI_MODEL
    
    def analyze_features(
        self,
        problem_description: str,
        code_summary: str,
        file_contents: Dict[str, str],
        code_structure: Dict
    ) -> Dict:
        """
        Analyze code and match features to implementation locations.
        
        Args:
            problem_description: Description of features to analyze
            code_summary: Summary of codebase structure
            file_contents: Dictionary of file paths to their content
            code_structure: Parsed code structure with functions/classes
            
            Returns:
            Dictionary with feature analysis results
            
        Raises:
            ValueError: If inputs are invalid
            Exception: If API call fails
        """
        if not problem_description or not problem_description.strip():
            raise ValueError("problem_description cannot be empty")
        
        if not file_contents and not code_structure:
            raise ValueError("No code content provided for analysis")
        
        prompt = self._build_analysis_prompt(
            problem_description,
            code_summary,
            file_contents,
            code_structure
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert code analyst. Analyze codebases and identify where specific features are implemented. Return structured JSON responses."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
                timeout=60
            )
            
            if not response.choices or not response.choices[0].message.content:
                raise Exception("Empty response from API")
            
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            # Validate result structure
            if "feature_analysis" not in result:
                result["feature_analysis"] = []
            
            return result
            
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse API response as JSON: {str(e)}")
        except Exception as e:
            raise Exception(f"API error: {str(e)}")
    
    def _build_analysis_prompt(
        self,
        problem_description: str,
        code_summary: str,
        file_contents: Dict[str, str],
        code_structure: Dict
    ) -> str:
        """Build the prompt for AI analysis."""
        
        # Build file contents section
        files_section = "\n\n## Relevant Code Files:\n\n"
        for file_path, content in list(file_contents.items())[:15]:  # Limit to avoid token limits
            files_section += f"### File: {file_path}\n```\n{content[:2000]}\n```\n\n"  # Limit content length
        
        # Build structure section
        structure_section = "\n## Code Structure (Functions and Classes):\n\n"
        for file_path, structure in list(code_structure.items())[:20]:
            structure_section += f"### {file_path}\n"
            if structure.get('functions'):
                structure_section += "Functions:\n"
                for func in structure['functions']:
                    structure_section += f"  - {func['name']} (lines {func['line_start']}-{func['line_end']})\n"
            if structure.get('classes'):
                structure_section += "Classes:\n"
                for cls in structure['classes']:
                    structure_section += f"  - {cls['name']} (lines {cls['line_start']}-{cls['line_end']})\n"
            structure_section += "\n"
        
        prompt = f"""Analyze the following codebase and identify where each feature from the problem description is implemented.

## Problem Description:
{problem_description}

## Codebase Summary:
{code_summary}

{structure_section}

{files_section}

## Task:
Based on the problem description, identify all features mentioned and find where each feature is implemented in the codebase.

For each feature, provide:
1. A clear description of the feature
2. All implementation locations (files, functions/methods, and line numbers)

## Output Format:
Return a JSON object with the following structure:
{{
  "feature_analysis": [
    {{
      "feature_description": "Description of the feature",
      "implementation_location": [
        {{
          "file": "relative/path/to/file.ts",
          "function": "functionName",
          "lines": "13-16"
        }}
      ]
    }}
  ],
  "execution_plan_suggestion": "Instructions on how to run/execute this project (e.g., npm install, npm start, etc.)"
}}

Important:
- Be specific about file paths (use relative paths from the codebase root)
- Include exact function/method names
- Provide accurate line number ranges
- If a feature spans multiple files/functions, list all of them
- Analyze the code structure and file contents to make accurate matches
- The execution_plan_suggestion should be practical and specific based on the codebase structure
"""
        
        return prompt
    
    def generate_execution_plan(
        self,
        code_summary: str,
        file_tree: Dict
    ) -> str:
        """
        Generate execution plan suggestion.
        
        Args:
            code_summary: Summary of codebase
            file_tree: File tree structure
            
        Returns:
            Execution plan suggestion string
        """
        # Detect package manager and framework
        has_package_json = any('package.json' in path for path in file_tree.keys())
        has_requirements_txt = any('requirements.txt' in path for path in file_tree.keys())
        has_pom_xml = any('pom.xml' in path for path in file_tree.keys())
        has_go_mod = any('go.mod' in path for path in file_tree.keys())
        
        # Detect framework
        has_graphql = any('graphql' in path.lower() or 'resolver' in path.lower() for path in file_tree.keys())
        has_express = has_package_json and any('express' in path.lower() for path in file_tree.keys())
        
        plan_parts = []
        
        if has_package_json:
            plan_parts.append("1. Install dependencies: `npm install`")
            if has_graphql:
                plan_parts.append("2. Start the development server: `npm run start:dev` or `npm start`")
                plan_parts.append("3. The GraphQL API will be available at http://localhost:3000/graphql (or the configured port)")
            elif has_express:
                plan_parts.append("2. Start the server: `npm start` or `node index.js`")
            else:
                plan_parts.append("2. Check package.json for start scripts: `npm start` or `npm run dev`")
        elif has_requirements_txt:
            plan_parts.append("1. Install dependencies: `pip install -r requirements.txt`")
            plan_parts.append("2. Run the application: `python main.py` or `python app.py`")
        elif has_pom_xml:
            plan_parts.append("1. Build the project: `mvn clean install`")
            plan_parts.append("2. Run the application: `mvn spring-boot:run` or `java -jar target/*.jar`")
        elif has_go_mod:
            plan_parts.append("1. Install dependencies: `go mod download`")
            plan_parts.append("2. Run the application: `go run main.go`")
        else:
            plan_parts.append("1. Check the codebase for setup instructions")
            plan_parts.append("2. Install necessary dependencies")
            plan_parts.append("3. Run the main entry point file")
        
        return " ".join(plan_parts)
