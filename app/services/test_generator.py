"""
Test Generation Module

使用 LLM Function Calling 技术生成和执行单元测试。

主要功能：
- 使用 LLM Function Calling API 动态生成测试
- 通过函数调用让 LLM 探索代码库、生成测试、执行测试
- 收集测试代码和执行结果
- 支持多种测试框架（pytest, jest 等）

工作流程：
1. LLM 通过 read_file 探索代码库
2. LLM 生成测试代码并使用 write_file 保存
3. LLM 使用 run_command 执行测试
4. 收集并返回结果
"""
import os
import re
import subprocess
import tempfile
import json
from typing import Dict, Optional, List
from pathlib import Path

from app.services.code_analyzer import CodeAnalyzer
from app.services.ai_analyzer import AIAnalyzer
from app.services.test_executor_functions import TestExecutorFunctions


class TestGenerator:
    """Generates and executes tests for code verification."""
    
    def __init__(self, code_analyzer: CodeAnalyzer, ai_analyzer: AIAnalyzer):
        """
        Initialize test generator.
        
        Args:
            code_analyzer: CodeAnalyzer instance
            ai_analyzer: AIAnalyzer instance
        """
        self.code_analyzer = code_analyzer
        self.ai_analyzer = ai_analyzer
        self.executor = None
        if code_analyzer.extracted_path:
            self.executor = TestExecutorFunctions(code_analyzer.extracted_path)
    
    def generate_and_execute_tests(
        self,
        problem_description: str,
        feature_analysis: List[Dict]
    ) -> Dict:
        """
        Generate and execute tests using LLM Function Calling.
        
        Args:
            problem_description: Original problem description
            feature_analysis: Feature analysis results
            
        Returns:
            Dictionary with test code and execution results
        """
        try:
            if not self.code_analyzer.extracted_path:
                return {
                    "generated_test_code": "",
                    "execution_result": {
                        "tests_passed": False,
                        "log": "No extracted code path available"
                    }
                }
            
            # Initialize executor if not already done
            if not self.executor:
                self.executor = TestExecutorFunctions(self.code_analyzer.extracted_path)
            
            # Create conftest.py for Python path setup
            self._create_conftest_py()
            
            # Detect framework
            framework_info = self._detect_framework()
            
            # Use LLM Function Calling to generate and execute tests
            result = self._execute_with_function_calling(
                problem_description,
                feature_analysis,
                framework_info
            )
            
            return result
            
        except Exception as e:
            return {
                "generated_test_code": "",
                "execution_result": {
                    "tests_passed": False,
                    "log": f"Error generating/executing tests: {str(e)}"
                }
            }
    
    def _detect_framework(self) -> Dict:
        """Detect the framework and testing approach."""
        file_tree = self.code_analyzer.file_tree
        
        framework_info = {
            "type": "unknown",
            "test_framework": "unknown",
            "package_manager": "unknown"
        }
        
        # Detect package manager
        if any('package.json' in path for path in file_tree.keys()):
            framework_info["package_manager"] = "npm"
            # Check for test framework
            if any('jest' in path.lower() or 'jest.config' in path.lower() for path in file_tree.keys()):
                framework_info["test_framework"] = "jest"
            elif any('mocha' in path.lower() for path in file_tree.keys()):
                framework_info["test_framework"] = "mocha"
            else:
                framework_info["test_framework"] = "jest"  # Default for Node.js
        
        elif any('requirements.txt' in path for path in file_tree.keys()):
            framework_info["package_manager"] = "pip"
            if any('pytest' in path.lower() for path in file_tree.keys()):
                framework_info["test_framework"] = "pytest"
            else:
                framework_info["test_framework"] = "pytest"  # Default for Python
        
        # Detect API type
        if any('graphql' in path.lower() or 'resolver' in path.lower() for path in file_tree.keys()):
            framework_info["type"] = "graphql"
        elif any('express' in path.lower() or 'router' in path.lower() for path in file_tree.keys()):
            framework_info["type"] = "rest"
        elif any('flask' in path.lower() or 'fastapi' in path.lower() for path in file_tree.keys()):
            framework_info["type"] = "rest"
        
        return framework_info
    
    def _find_entry_points(self) -> Dict:
        """
        Find potential entry point files in the codebase.
        
        Returns:
            Dictionary with entry point information
        """
        file_tree = self.code_analyzer.file_tree
        entry_points = {
            "main_files": [],
            "app_files": [],
            "init_files": [],
            "recommended_import": None,
            "project_root": None  # The actual root folder if ZIP has one
        }
        
        # Check if there's a single root folder (common when ZIP is created from a folder)
        root_folders = set()
        for file_path in file_tree.keys():
            parts = file_path.replace('\\', '/').split('/')
            if len(parts) > 1:
                root_folders.add(parts[0])
        
        # If all files are under a single root folder, that's the project root
        if len(root_folders) == 1:
            entry_points["project_root"] = list(root_folders)[0]
        
        # Common entry point patterns
        for file_path in file_tree.keys():
            file_name = os.path.basename(file_path).lower()
            
            # Find main.py files
            if file_name == 'main.py':
                entry_points["main_files"].append(file_path)
            
            # Find app.py files
            elif file_name == 'app.py':
                entry_points["app_files"].append(file_path)
            
            # Find __init__.py files that might export app
            elif file_name == '__init__.py':
                entry_points["init_files"].append(file_path)
        
        # Build priority order based on whether there's a project root
        project_root = entry_points["project_root"]
        if project_root:
            priority_order = [
                f'{project_root}/main.py',
                f'{project_root}/app.py',
                f'{project_root}/src/main.py',
                f'{project_root}/src/app.py',
                f'{project_root}/app/main.py',
                f'{project_root}/app/app.py',
            ]
        else:
            priority_order = [
                'main.py',
                'app.py',
                'src/main.py',
                'src/app.py',
                'app/main.py',
                'app/app.py',
            ]
        
        for priority_path in priority_order:
            for file_path in entry_points["main_files"] + entry_points["app_files"]:
                # Normalize path for comparison
                normalized = file_path.replace('\\', '/').lstrip('./')
                if normalized == priority_path or normalized.endswith('/' + priority_path):
                    # Convert file path to import path
                    # If there's a project root, we need to handle it specially
                    if project_root and normalized.startswith(project_root + '/'):
                        # Remove project root from import path since PYTHONPATH will include it
                        import_file = normalized[len(project_root) + 1:]
                    else:
                        import_file = normalized
                    
                    import_path = import_file.replace('/', '.').replace('.py', '')
                    entry_points["recommended_import"] = {
                        "file": normalized,
                        "import_statement": f"from {import_path} import app",
                        "import_path": import_path
                    }
                    break
            if entry_points["recommended_import"]:
                break
        
        return entry_points
    
    def _create_conftest_py(self) -> bool:
        """
        Create a conftest.py file to set up Python path for tests.
        
        Returns:
            True if created successfully, False otherwise
        """
        if not self.code_analyzer.extracted_path:
            return False
        
        conftest_content = '''"""
Auto-generated conftest.py for test path setup.
"""
import sys
import os

# Add the current directory and its subdirectories to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Also add any subdirectories that might be Python packages
for item in os.listdir(current_dir):
    item_path = os.path.join(current_dir, item)
    if os.path.isdir(item_path) and not item.startswith('.') and item not in ['__pycache__', 'node_modules', '.git']:
        if item_path not in sys.path:
            sys.path.insert(0, item_path)
'''
        
        try:
            conftest_path = os.path.join(self.code_analyzer.extracted_path, 'conftest.py')
            # Only create if it doesn't exist
            if not os.path.exists(conftest_path):
                with open(conftest_path, 'w', encoding='utf-8') as f:
                    f.write(conftest_content)
                print(f"✓ Created conftest.py for test path setup")
                return True
            return True
        except Exception as e:
            print(f"Failed to create conftest.py: {e}")
            return False
    
    def _get_project_structure_summary(self) -> str:
        """
        Get a summary of the project structure for the LLM.
        
        Returns:
            String summary of project structure
        """
        file_tree = self.code_analyzer.file_tree
        
        # Categorize files
        python_files = []
        js_files = []
        config_files = []
        test_files = []
        
        for file_path in file_tree.keys():
            file_name = os.path.basename(file_path).lower()
            
            if file_path.endswith('.py'):
                if 'test' in file_name or file_path.startswith('tests/') or '/tests/' in file_path:
                    test_files.append(file_path)
                else:
                    python_files.append(file_path)
            elif file_path.endswith(('.js', '.ts', '.jsx', '.tsx')):
                if 'test' in file_name or 'spec' in file_name:
                    test_files.append(file_path)
                else:
                    js_files.append(file_path)
            elif file_name in ['package.json', 'requirements.txt', 'setup.py', 'pyproject.toml']:
                config_files.append(file_path)
        
        summary_parts = []
        
        if config_files:
            summary_parts.append(f"Config files: {', '.join(config_files)}")
        
        if python_files:
            summary_parts.append(f"Python source files ({len(python_files)}):")
            for f in sorted(python_files)[:20]:  # Limit to 20 files
                summary_parts.append(f"  - {f}")
            if len(python_files) > 20:
                summary_parts.append(f"  ... and {len(python_files) - 20} more")
        
        if js_files:
            summary_parts.append(f"JavaScript/TypeScript files ({len(js_files)}):")
            for f in sorted(js_files)[:20]:
                summary_parts.append(f"  - {f}")
            if len(js_files) > 20:
                summary_parts.append(f"  ... and {len(js_files) - 20} more")
        
        if test_files:
            summary_parts.append(f"Existing test files ({len(test_files)}):")
            for f in sorted(test_files)[:10]:
                summary_parts.append(f"  - {f}")
        
        return "\n".join(summary_parts)
    
    def _execute_with_function_calling(
        self,
        problem_description: str,
        feature_analysis: List[Dict],
        framework_info: Dict
    ) -> Dict:
        """
        Execute tests using LLM Function Calling API.
        
        Args:
            problem_description: Problem description
            feature_analysis: Feature analysis results
            framework_info: Framework information
            
        Returns:
            Dictionary with test code and execution results
        """
        # Get function definitions
        function_definitions = self.executor.get_function_definitions()
        
        # Build initial prompt
        prompt = self._build_function_calling_prompt(
            problem_description,
            feature_analysis,
            framework_info
        )
        
        messages = [
            {
                "role": "system",
                "content": """You are an expert test engineer. Your task is to generate and execute tests to verify that the codebase implements the required features correctly.

You have access to the following functions:
- execute_code: Execute code snippets
- read_file: Read files from the codebase (USE THIS FIRST to find correct import paths!)
- write_file: Write files to the codebase (CRITICAL: You MUST use this to save generated test code)
- run_command: Execute shell commands
- check_api_endpoint: Test API endpoints
- validate_test_result: Validate test results

## CRITICAL INSTRUCTIONS - READ CAREFULLY:

### 1. **FIND CORRECT IMPORT PATHS FIRST** (Most Important!)
Before writing ANY test code, you MUST:
- Use read_file to read main.py, app.py, or other entry point files
- Find where the app instance is created (e.g., `app = FastAPI()`)
- Determine the CORRECT import path based on the ACTUAL file location

**NEVER assume import paths like `from src.main import app`!**
Instead, verify by reading files:
- If app is in `./main.py` → `from main import app`
- If app is in `./src/main.py` → `from src.main import app`
- If app is in `./app/main.py` → `from app.main import app`

**IMPORTANT about project folders**: If the project has a root folder (e.g., `myproject/main.py`),
do NOT include the root folder in imports. The PYTHONPATH is configured to include it.
- File `myproject/main.py` → import as `from main import app` (NOT `from myproject.main`)
- File `myproject/src/main.py` → import as `from src.main import app`

### 2. **MANDATORY**: Write Test Code to File
- You MUST use write_file function to save your generated test code
- Suggested filenames: "test_generated.py", "generated_test.py"
- The file MUST have a .py extension (for Python)
- DO NOT skip writing the test file

### 3. **Test Code Template with Path Setup** (Use this structure!):
```python
import sys
import os
# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Also add subdirectories that might contain the code
for item in os.listdir(os.path.dirname(os.path.abspath(__file__))):
    item_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), item)
    if os.path.isdir(item_path) and not item.startswith('.'):
        sys.path.insert(0, item_path)

import pytest
from fastapi.testclient import TestClient
from main import app  # Adjust based on actual file location

client = TestClient(app)

def test_example():
    response = client.get("/")
    assert response.status_code == 200
```

### 4. **Execution Workflow**:
a. **FIRST**: Use read_file to find the app entry point and verify import paths
b. Read relevant source files to understand the code structure
c. Generate test code with CORRECT imports AND the sys.path setup shown above
d. **MANDATORY**: Write the test code using write_file (e.g., "test_generated.py")
e. Install dependencies: first "pip install -r requirements.txt", then "pip install pytest httpx==0.24.1 email-validator"
   **IMPORTANT**: Use httpx==0.24.1 (NOT latest) for compatibility with FastAPI TestClient!
f. **VERIFY IMPORT FIRST**: Run "python -c \"import test_generated\"" to check for import errors
g. Execute tests: "python -m pytest test_generated.py -v --tb=short"
h. If "found no collectors" or import errors occur, fix the imports and re-run

### 5. **Common Import Errors and Fixes**:
- `ModuleNotFoundError: No module named 'src'` → src folder might not exist or use different path
- `ModuleNotFoundError: No module named 'myproject'` → Don't include project root folder in import
- `ImportError: cannot import name 'app'` → Check the actual variable name in the file
- `found no collectors` → Test file has import/syntax errors, verify import first!
- Always include the sys.path setup in your test code as a safety measure!

### 6. **CRITICAL: Verify Test File Before Running pytest**:
Before running pytest, ALWAYS verify the test file can be imported:
```bash
python -c "import test_generated"  # or the name of your test file without .py
```
If this fails, fix the import errors first before running pytest!

### 7. **Use pytest with --tb=short for better error messages**:
When running pytest, use: `python -m pytest test_generated.py -v --tb=short`
This provides clearer error messages if tests fail.

Remember: Include sys.path setup at the top of your test file to ensure imports work correctly!"""
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        # Execute function calling loop
        max_iterations = 10
        iteration = 0
        test_code = ""
        execution_log = []
        
        while iteration < max_iterations:
            try:
                # Call API with function calling
                response = self.ai_analyzer.client.chat.completions.create(
                    model=self.ai_analyzer.model,
                    messages=messages,
                    tools=function_definitions,
                    tool_choice="auto",
                    temperature=0.3
                )
                
                message = response.choices[0].message
                
                # Convert message to dict format for messages list
                message_dict = {
                    "role": message.role,
                    "content": message.content
                }
                
                # Add tool_calls if present
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    message_dict["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in message.tool_calls
                    ]
                
                messages.append(message_dict)
                
                # Check if LLM wants to call functions
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    # Process each function call
                    for tool_call in message.tool_calls:
                        function_name = tool_call.function.name
                        function_args_str = tool_call.function.arguments
                        function_args = json.loads(function_args_str)
                        tool_call_id = tool_call.id
                        
                        # Execute the function
                        function_result = self.executor.call_function(function_name, function_args)
                        
                        # Add function result to messages
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": json.dumps(function_result)
                        })
                        
                        # Collect test code if written
                        if function_name == "write_file":
                            file_path = function_args.get("file_path", "")
                            content_arg = function_args.get("content", "")
                            
                            # Check if this looks like test code
                            is_test_file = (
                                "test" in file_path.lower() or 
                                "generated" in file_path.lower() or
                                file_path.endswith("_test.py") or
                                file_path.endswith("test_.py") or
                                file_path.startswith("test_") or
                                file_path.endswith(".test.js") or
                                file_path.endswith(".test.ts")
                            )
                            
                            # Check if content looks like test code
                            looks_like_test = content_arg and any(keyword in content_arg for keyword in [
                                'def test', 'def test_', 'describe(', 'it(', 'import pytest', 
                                'from fastapi.testclient', 'TestClient', 'import unittest',
                                'class Test', 'test_', 'assert ', 'expect(', 'toBe('
                            ])
                            
                            # Collect from content argument if it looks like test code
                            if content_arg and (is_test_file or looks_like_test):
                                if not test_code or len(content_arg) > len(test_code):
                                    test_code = content_arg
                                    print(f"✓ Collected test code from write_file content argument: {file_path} ({len(content_arg)} chars)")
                            
                            # Also read the file if write was successful (always read test files)
                            if function_result.get("success"):
                                if any(ext in file_path.lower() for ext in ['.py', '.js', '.ts', '.tsx', '.jsx']):
                                    file_content = self.executor.read_file(file_path)
                                    if file_content.get("success"):
                                        content = file_content.get("content", "")
                                        # Always prefer test files, or use if no test code collected yet
                                        if is_test_file or looks_like_test or not test_code:
                                            if len(content) > len(test_code) or not test_code:
                                                test_code = content
                                                print(f"✓ Collected test code from written file: {file_path} ({len(content)} chars)")
                        
                        # Collect execution logs
                        if function_name in ["execute_code", "run_command", "check_api_endpoint"]:
                            log_entry = {
                                "function": function_name,
                                "result": function_result
                            }
                            # Store command/arguments for better logging
                            if function_name == "run_command":
                                command = function_args.get("command", "")
                                log_entry["command"] = command
                                # Log command execution for debugging
                                print(f"Function call: run_command('{command}')")
                                if not function_result.get("success"):
                                    print(f"  Failed: {function_result.get('stderr', '')[:200]}")
                            elif function_name == "execute_code":
                                log_entry["code_snippet"] = function_args.get("code", "")[:100]  # Store first 100 chars
                            elif function_name == "write_file":
                                # Also log write_file calls for debugging
                                file_path = function_args.get("file_path", "")
                                print(f"Function call: write_file('{file_path}') - success: {function_result.get('success', False)}")
                            execution_log.append(log_entry)
                else:
                    # LLM finished - extract final response
                    final_response = message.content or ""
                    # Try to extract test code from final response
                    if "```" in final_response:
                        extracted = self._extract_code_from_markdown(final_response)
                        if extracted:
                            test_code = extracted
                    # Also check if there's code in the response even without markdown
                    elif final_response and len(final_response) > 100:
                        # If response is substantial and looks like code, use it
                        if any(keyword in final_response for keyword in ['def ', 'function', 'describe', 'it(', 'test']):
                            test_code = final_response
                    break
                
                iteration += 1
                
            except Exception as e:
                execution_log.append({
                    "error": f"Iteration {iteration} failed: {str(e)}"
                })
                break
        
        # Generate execution result summary
        execution_result = self._summarize_execution_results(execution_log, framework_info)
        
        # If no test code was collected, add detailed note
        if not test_code:
            # Check if write_file was called at all
            write_file_called = any(
                entry.get("function") == "write_file" 
                for entry in execution_log 
                if isinstance(entry, dict)
            )
            
            if write_file_called:
                warning_msg = (
                    "Warning: write_file was called but no test code was collected. " +
                    "The written files may not have contained test code, or the file paths " +
                    "didn't match test file patterns.\n"
                )
            else:
                warning_msg = (
                    "Warning: No test code was generated or collected. " +
                    "The LLM did not call write_file to save test code. " +
                    "Please ensure the LLM writes test code to a file using the write_file function.\n"
                )
            
            execution_result["log"] = warning_msg + execution_result.get("log", "")
        
        return {
            "generated_test_code": test_code if test_code else "",
            "execution_result": execution_result
        }
    
    def _build_function_calling_prompt(
        self,
        problem_description: str,
        feature_analysis: List[Dict],
        framework_info: Dict
    ) -> str:
        """Build prompt for function calling approach."""
        features_text = json.dumps(feature_analysis, indent=2)
        
        # Get project structure and entry points
        entry_points = self._find_entry_points()
        project_structure = self._get_project_structure_summary()
        
        # Build entry point guidance
        entry_point_guidance = ""
        project_root_note = ""
        
        # Note about project root folder
        if entry_points.get("project_root"):
            project_root = entry_points["project_root"]
            project_root_note = f"""
## PROJECT ROOT FOLDER DETECTED: `{project_root}/`
All source files are inside the `{project_root}/` folder. The PYTHONPATH has been configured
to include this folder, so you should import WITHOUT the `{project_root}.` prefix.

For example:
- If the file is `{project_root}/main.py`, import as: `from main import app`
- If the file is `{project_root}/src/main.py`, import as: `from src.main import app`
- Do NOT use `from {project_root}.main import app` - this will fail!
"""
        
        if entry_points["recommended_import"]:
            entry_point_guidance = f"""
## DETECTED APP ENTRY POINT (Use this for imports!):
- File: {entry_points["recommended_import"]["file"]}
- Recommended import: `{entry_points["recommended_import"]["import_statement"]}`
{project_root_note}
**IMPORTANT**: A `conftest.py` has been created to set up Python paths. The recommended 
import above should work correctly. If you still get import errors, try reading the 
actual file to verify the app variable name.
"""
        else:
            main_files = entry_points["main_files"] + entry_points["app_files"]
            if main_files:
                entry_point_guidance = f"""
## POTENTIAL APP ENTRY POINTS (You MUST verify these before importing!):
{chr(10).join(f'- {f}' for f in main_files[:5])}
{project_root_note}
**CRITICAL**: Before writing test code, you MUST:
1. Use read_file to check each potential entry point
2. Find which file contains the FastAPI/Flask/Express app instance
3. Use the CORRECT import path based on the actual file location
"""
            else:
                entry_point_guidance = f"""
## NO STANDARD ENTRY POINT DETECTED
{project_root_note}
**CRITICAL**: You MUST explore the codebase first to find the app entry point:
1. Use read_file to explore Python/JS files
2. Look for FastAPI(), Flask(), express() app creation
3. Determine the correct import path based on actual file structure
"""
        
        return f"""Analyze the codebase and verify that it implements the required features correctly.

## Problem Description:
{problem_description}

## Feature Analysis:
{features_text}

## Framework Information:
- API Type: {framework_info.get('type', 'unknown')}
- Test Framework: {framework_info.get('test_framework', 'unknown')}
- Package Manager: {framework_info.get('package_manager', 'unknown')}

## Project Structure:
{project_structure}
{entry_point_guidance}

## Your Task - Follow These Steps EXACTLY IN ORDER:

### Step 1: **MANDATORY - Find the App Entry Point First**
This is the MOST IMPORTANT step. DO NOT skip this!

1. Use read_file to read potential entry point files (main.py, app.py, etc.)
2. Find the file that creates the app instance (e.g., `app = FastAPI()` or `app = Flask(__name__)`)
3. Note the EXACT file path and how the app is created
4. Determine the correct import path:
   - If app is in `main.py` at root → `from main import app`
   - If app is in `src/main.py` → `from src.main import app`
   - If app is in `app/main.py` → `from app.main import app`

**CRITICAL**: DO NOT assume import paths! Verify by reading the actual files!

### Step 2: Read Feature Implementation Files
- Use read_file to read files mentioned in the feature analysis
- Understand the API endpoints, models, and business logic
- Note the exact endpoint paths (e.g., "/api/users/", "/users", etc.)

### Step 3: Generate Test Code with CORRECT Imports
- Based on Step 1, use the CORRECT import statement for the app
- Include all necessary imports (pytest, TestClient/httpx, etc.)
- Write tests for all features mentioned in the problem description
- Make sure endpoint paths match the actual implementation

Example test structure for Python FastAPI:
```python
import pytest
from fastapi.testclient import TestClient
# IMPORTANT: Use the correct import path you found in Step 1!
from <correct_module_path> import app  # e.g., from main import app

client = TestClient(app)

def test_feature():
    response = client.get("/correct/endpoint/path")
    assert response.status_code == 200
```

### Step 4: **MANDATORY - Write Test File**
- **YOU MUST USE write_file FUNCTION** to save your test code
- Suggested filename: "test_generated.py"
- The file MUST have a .py extension (or appropriate extension for the language)
- **DO NOT SKIP THIS STEP** - the system requires you to write the file

### Step 5: Install Dependencies
- First: run_command("pip install -r requirements.txt") if requirements.txt exists
- Then: run_command("pip install pytest httpx==0.24.1 email-validator")
- **CRITICAL**: Use httpx==0.24.1, NOT the latest version! Newer httpx versions are incompatible with FastAPI's TestClient.
- Note: Install separately for better compatibility

### Step 6: Verify Test File Import (CRITICAL!)
- **MUST DO THIS BEFORE RUNNING PYTEST**
- Run: run_command("python -c \"import test_generated\"")
- If this fails with ImportError, fix the test file imports first!
- Common fixes: adjust import paths, add missing sys.path entries

### Step 7: Execute Tests
- Run: run_command("python -m pytest test_generated.py -v --tb=short")
- If you see "found no collectors" error, it means the test file has import errors
- Go back to Step 6 to diagnose, then fix and re-run

### Step 8: Report Results
- Summarize test execution results
- If tests failed, explain the errors

## CRITICAL REMINDERS:
1. **NEVER assume import paths** - always verify by reading files first
2. **ALWAYS use write_file** to save test code before executing
3. **Match endpoint paths** exactly as implemented in the source code
4. **ALWAYS verify import** before running pytest: `python -c "import test_generated"`
5. **If "no collectors" error occurs**, it means import failed - fix imports first!
6. **If import fails**, re-read the source files and correct the import path

Start now by reading the entry point files to find the correct app import path."""
    
    def _extract_code_from_markdown(self, text: str) -> str:
        """Extract code from markdown code blocks."""
        if "```" not in text:
            return text
        
        lines = text.split("\n")
        code_lines = []
        in_code_block = False
        
        for line in lines:
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                code_lines.append(line)
        
        return "\n".join(code_lines)
    
    def _summarize_execution_results(self, execution_log: List[Dict], framework_info: Dict) -> Dict:
        """Summarize execution results from function calls."""
        if not execution_log:
            return {
                "tests_passed": False,
                "log": "No test execution performed"
            }
        
        # Analyze execution log
        tests_passed = False
        test_execution_found = False  # Track if any test command was executed
        test_execution_failed = False  # Track if test execution explicitly failed
        log_parts = []
        
        for entry in execution_log:
            if "error" in entry:
                log_parts.append(entry["error"])
                continue
            
            func_name = entry.get("function", "")
            result = entry.get("result", {})
            
            if func_name == "run_command":
                command = entry.get("command", "") if isinstance(entry, dict) else ""
                stdout = result.get("stdout", "")
                stderr = result.get("stderr", "")
                
                # Check if it's a test-related command
                is_test_command = any(cmd in command.lower() for cmd in ['test', 'pytest', 'jest', 'npm test', 'python -m pytest'])
                
                if result.get("success"):
                    # Prioritize stdout, use stderr only if stdout is empty
                    output = stdout if stdout.strip() else stderr
                    # Only show output for test commands; skip other successful commands
                    if is_test_command:
                        log_parts.append(f"Test Results:\n{output}")
                    # For non-test commands, don't log successful output (only log failures)
                    
                    if is_test_command:
                        test_execution_found = True
                        returncode = result.get("returncode", -1)
                        output_lower = output.lower()
                        
                        # Primary check: pytest returns 0 if all tests pass, non-zero if any fail
                        if returncode == 0:
                            # Command succeeded - check output for confirmation
                            # Look for test summary patterns: "X passed" or "passed" without "failed"
                            has_passed = re.search(r'\d+\s+passed', output_lower) or 'passed' in output_lower
                            has_failed = re.search(r'\d+\s+failed', output_lower) or (
                                'failed' in output_lower and 
                                ('test' in output_lower or 'tests' in output_lower)
                            )
                            
                            # If returncode is 0 and we see passed indicators without failed indicators
                            if has_passed and not has_failed:
                                tests_passed = True
                            elif has_failed:
                                # Rare case: returncode 0 but output shows failures
                                test_execution_failed = True
                                tests_passed = False
                            else:
                                # returncode 0 but unclear output - default to passed (command succeeded)
                                tests_passed = True
                        else:
                            # Command failed (returncode != 0), tests definitely failed
                            test_execution_failed = True
                            tests_passed = False
                else:
                    log_parts.append(f"Command failed: {command if command else 'command'}")
                    # Prioritize stdout, use stderr only if stdout is empty
                    error_msg = stdout if stdout.strip() else stderr
                    
                    if is_test_command:
                        test_execution_found = True
                        test_execution_failed = True
                        tests_passed = False
                    
                    # Provide helpful error messages for specific errors
                    if "no collectors" in error_msg.lower() or "found no collectors" in error_msg.lower():
                        log_parts.append(
                            "Error: pytest could not collect tests. This usually means the test file has "
                            "import errors or syntax errors. Try running 'python -c \"import test_file\"' "
                            "to diagnose the import issue."
                        )
                    elif "No module named" in error_msg or "ModuleNotFoundError" in error_msg:
                        # Extract module name if possible
                        module_match = re.search(r"No module named ['\"]?(\w+)['\"]?", error_msg)
                        if module_match:
                            missing_module = module_match.group(1)
                            log_parts.append(f"Error: Module '{missing_module}' not found. Check import paths.")
                        else:
                            log_parts.append("Error: Module import failed. Check import paths in test file.")
                    elif "ImportError" in error_msg:
                        log_parts.append("Error: Import failed. Verify the import statements in the test file.")
                    elif "SyntaxError" in error_msg:
                        log_parts.append("Error: Syntax error in test file. Check the generated code for syntax issues.")
                    elif "not found" in error_msg.lower():
                        missing_module = ""
                        if "pytest" in error_msg:
                            missing_module = "pytest"
                        elif "jest" in error_msg:
                            missing_module = "jest"
                        elif "node" in error_msg:
                            missing_module = "Node.js"
                        
                        if missing_module:
                            log_parts.append(f"Error: {missing_module} is not installed. Please install dependencies first.")
                    
                    # For test commands, show full error; for others, limit to 2000 chars
                    if is_test_command:
                        log_parts.append(f"Error details: {error_msg}")
                    else:
                        log_parts.append(f"Error details: {error_msg[:2000]}")
            
            elif func_name == "execute_code":
                if result.get("success"):
                    log_parts.append(f"Code executed: {result.get('output', '')}")
                else:
                    log_parts.append(f"Code execution failed: {result.get('error', '')}")
            
            elif func_name == "check_api_endpoint":
                if result.get("success"):
                    log_parts.append(f"API endpoint check passed: {result.get('status_code', '')}")
                    # API endpoint check success should NOT override test failure
                    # Only set tests_passed if no test execution was attempted or if tests already passed
                    if not test_execution_found:
                        tests_passed = True
                else:
                    log_parts.append(f"API endpoint check failed: {result.get('error', '')}")
        
        # Final validation: if test execution was attempted and failed, ensure tests_passed is False
        if test_execution_found and test_execution_failed:
            tests_passed = False
        
        return {
            "tests_passed": tests_passed,
            "log": "\n".join(log_parts) if log_parts else "Test execution completed"
        }
