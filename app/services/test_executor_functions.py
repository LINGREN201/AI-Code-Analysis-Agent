"""
Test Executor Functions Module

定义 LLM 可以通过 Function Calling API 调用的执行函数。

这些函数允许 LLM 动态地：
- 执行代码片段
- 读取和写入文件
- 执行 shell 命令
- 测试 API 端点
- 验证测试结果

所有函数都返回标准化的字典格式结果，便于 LLM 理解和处理。
"""
import os
import sys
import re
import subprocess
import json
import tempfile
import requests
from typing import Dict, Any, Optional
from pathlib import Path


class TestExecutorFunctions:
    """Functions that LLM can call to execute and verify tests."""
    
    def __init__(self, extracted_code_path: str):
        """
        Initialize executor with code path.
        
        Args:
            extracted_code_path: Path to extracted codebase
        """
        self.extracted_path = extracted_code_path
        # Store current Python interpreter path to ensure consistency
        self.python_executable = sys.executable
    
    def execute_code(self, code: str, language: str = "python") -> Dict[str, Any]:
        """
        Execute a code snippet and return the result.
        
        Args:
            code: Code to execute
            language: Programming language (python, javascript, etc.)
            
        Returns:
            Dictionary with execution result
        """
        try:
            if language == "python":
                return self._execute_python_code(code)
            elif language in ["javascript", "typescript", "js"]:
                return self._execute_javascript_code(code)
            else:
                return {
                    "success": False,
                    "output": "",
                    "error": f"Unsupported language: {language}"
                }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e)
            }
    
    def _execute_python_code(self, code: str) -> Dict[str, Any]:
        """Execute Python code using the current Python interpreter."""
        try:
            result = subprocess.run(
                [self.python_executable, "-c", code],
                cwd=self.extracted_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": "Execution timed out"
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e)
            }
    
    def _execute_javascript_code(self, code: str) -> Dict[str, Any]:
        """Execute JavaScript code."""
        try:
            # Create temporary file
            temp_file = os.path.join(self.extracted_path, "temp_exec.js")
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(code)
            
            result = subprocess.run(
                ["node", temp_file],
                cwd=self.extracted_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Cleanup
            if os.path.exists(temp_file):
                os.remove(temp_file)
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": "Execution timed out"
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e)
            }
    
    def read_file(self, file_path: str) -> Dict[str, Any]:
        """
        Read content of a file.
        
        Args:
            file_path: Relative path to file from extracted code root
            
        Returns:
            Dictionary with file content
        """
        try:
            full_path = os.path.join(self.extracted_path, file_path)
            if not os.path.exists(full_path):
                return {
                    "success": False,
                    "content": "",
                    "error": f"File not found: {file_path}"
                }
            
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "success": True,
                "content": content,
                "file_path": file_path
            }
        except Exception as e:
            return {
                "success": False,
                "content": "",
                "error": str(e)
            }
    
    def write_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """
        Write content to a file.
        
        Args:
            file_path: Relative path to file from extracted code root
            content: Content to write
            
        Returns:
            Dictionary with write result
        """
        try:
            full_path = os.path.join(self.extracted_path, file_path)
            # Create directory if needed
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                "success": True,
                "message": f"File written: {file_path}",
                "file_path": file_path
            }
        except Exception as e:
            return {
                "success": False,
                "message": "",
                "error": str(e)
            }
    
    def run_command(self, command: str, working_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a shell command.
        
        Automatically replaces 'python', 'pip', 'pytest' commands with the current Python interpreter
        to ensure environment consistency.
        
        Args:
            command: Command to execute
            working_dir: Working directory (defaults to extracted_path)
            
        Returns:
            Dictionary with command result
        """
        try:
            cwd = self.extracted_path
            if working_dir:
                if os.path.isabs(working_dir):
                    cwd = working_dir
                else:
                    cwd = os.path.join(self.extracted_path, working_dir)
            
            # Ensure directory exists
            if not os.path.exists(cwd):
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": f"Working directory does not exist: {cwd}",
                    "returncode": -1
                }
            
            # Normalize command to use current Python interpreter for consistency
            normalized_command = self._normalize_python_command(command)
            
            # Log the command being executed for debugging
            print(f"Executing command: {normalized_command} (in {cwd})")
            
            # Set up environment with PYTHONPATH to include the extracted code directory
            env = os.environ.copy()
            pythonpath_dirs = [cwd]
            
            # Also add any subdirectories that might contain Python packages
            # This handles cases where the ZIP has a root folder
            for item in os.listdir(cwd):
                item_path = os.path.join(cwd, item)
                if os.path.isdir(item_path) and not item.startswith('.') and item not in ['__pycache__', 'node_modules', '.git']:
                    pythonpath_dirs.append(item_path)
            
            # Combine with existing PYTHONPATH if any
            existing_pythonpath = env.get('PYTHONPATH', '')
            new_pythonpath = os.pathsep.join(pythonpath_dirs)
            if existing_pythonpath:
                env['PYTHONPATH'] = new_pythonpath + os.pathsep + existing_pythonpath
            else:
                env['PYTHONPATH'] = new_pythonpath
            
            print(f"PYTHONPATH set to: {env['PYTHONPATH']}")
            
            result = subprocess.run(
                normalized_command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=60,  # Increased timeout for test execution
                env=env
            )
            
            # Log result for debugging
            if result.returncode != 0:
                print(f"Command failed with return code {result.returncode}")
                print(f"stderr: {result.stderr[:500]}")
            else:
                print(f"Command succeeded: {result.stdout[:200]}")
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": "Command timed out",
                "returncode": -1
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }
    
    def _normalize_python_command(self, command: str) -> str:
        """
        Normalize Python-related commands to use the current Python interpreter.
        
        This ensures that pip install and pytest run use the same Python environment.
        
        Args:
            command: Original command string
            
        Returns:
            Normalized command string
        """
        normalized = command.strip()
        python_exe = self.python_executable
        
        # Handle "pip install ..." or "pip3 install ..." -> "python -m pip install ..."
        if normalized.startswith('pip install '):
            return f'{python_exe} -m pip install {normalized[12:]}'
        if normalized.startswith('pip3 install '):
            return f'{python_exe} -m pip install {normalized[13:]}'
        if normalized.startswith('pip '):
            return f'{python_exe} -m pip {normalized[4:]}'
        if normalized.startswith('pip3 '):
            return f'{python_exe} -m pip {normalized[5:]}'
        
        # Handle "pytest ..." -> "python -m pytest ..."
        if normalized.startswith('pytest '):
            return f'{python_exe} -m pytest {normalized[7:]}'
        if normalized == 'pytest':
            return f'{python_exe} -m pytest'
        
        # Handle "python -m ..." -> "{python_exe} -m ..."
        if normalized.startswith('python -m '):
            return f'{python_exe} -m {normalized[10:]}'
        if normalized.startswith('python3 -m '):
            return f'{python_exe} -m {normalized[11:]}'
        
        # Handle "python ..." -> "{python_exe} ..."
        if normalized.startswith('python '):
            return f'{python_exe} {normalized[7:]}'
        if normalized.startswith('python3 '):
            return f'{python_exe} {normalized[8:]}'
        
        # Handle standalone "python" or "python3" command
        if normalized == 'python' or normalized == 'python3':
            return python_exe
        
        return normalized
    
    def check_api_endpoint(
        self,
        url: str,
        method: str = "GET",
        payload: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Check an API endpoint.
        
        Args:
            url: API endpoint URL
            method: HTTP method (GET, POST, etc.)
            payload: Request payload (for POST/PUT)
            headers: Request headers
            
        Returns:
            Dictionary with API response
        """
        try:
            method = method.upper()
            default_headers = {"Content-Type": "application/json"}
            if headers:
                default_headers.update(headers)
            
            if method == "GET":
                response = requests.get(url, headers=default_headers, timeout=10)
            elif method == "POST":
                response = requests.post(
                    url,
                    json=payload,
                    headers=default_headers,
                    timeout=10
                )
            elif method == "PUT":
                response = requests.put(
                    url,
                    json=payload,
                    headers=default_headers,
                    timeout=10
                )
            elif method == "DELETE":
                response = requests.delete(url, headers=default_headers, timeout=10)
            else:
                return {
                    "success": False,
                    "status_code": 0,
                    "response": "",
                    "error": f"Unsupported HTTP method: {method}"
                }
            
            try:
                response_data = response.json()
            except:
                response_data = response.text
            
            return {
                "success": 200 <= response.status_code < 300,
                "status_code": response.status_code,
                "response": response_data,
                "headers": dict(response.headers)
            }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "status_code": 0,
                "response": "",
                "error": "Request timed out"
            }
        except Exception as e:
            return {
                "success": False,
                "status_code": 0,
                "response": "",
                "error": str(e)
            }
    
    def validate_test_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a test result.
        
        Args:
            result: Test result dictionary
            
        Returns:
            Dictionary with validation result
        """
        try:
            # Check if result has expected structure
            has_output = "output" in result or "response" in result or "stdout" in result
            is_success = result.get("success", False) or result.get("tests_passed", False)
            
            validation = {
                "valid": True,
                "has_output": has_output,
                "is_success": is_success,
                "message": "Test result validated"
            }
            
            if not has_output:
                validation["valid"] = False
                validation["message"] = "Test result missing output"
            
            return validation
        except Exception as e:
            return {
                "valid": False,
                "has_output": False,
                "is_success": False,
                "message": f"Validation error: {str(e)}"
            }
    
    def analyze_code_behavior(self, code: str, expected_behavior: str) -> Dict[str, Any]:
        """
        Analyze code behavior against expected behavior.
        
        Args:
            code: Code to analyze
            expected_behavior: Expected behavior description
            
        Returns:
            Dictionary with analysis result
        """
        # This is a placeholder - actual analysis would be done by LLM
        return {
            "success": True,
            "analysis": f"Code analysis for: {expected_behavior}",
            "code_snippet": code[:200],
            "note": "Detailed analysis should be performed by LLM"
        }
    
    def get_function_definitions(self) -> list:
        """
        Get function definitions for all executor functions (OpenAI-compatible format).
        
        Returns:
            List of function definitions compatible with OpenAI/Qwen Function Calling API
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "execute_code",
                    "description": "Execute a code snippet in the specified language and return the result",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "The code to execute"
                            },
                            "language": {
                                "type": "string",
                                "description": "Programming language (python, javascript, etc.)",
                                "enum": ["python", "javascript", "typescript", "js"]
                            }
                        },
                        "required": ["code"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read the content of a file from the codebase",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Relative path to the file from codebase root"
                            }
                        },
                        "required": ["file_path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Write content to a file in the codebase",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Relative path to the file from codebase root"
                            },
                            "content": {
                                "type": "string",
                                "description": "Content to write to the file"
                            }
                        },
                        "required": ["file_path", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "run_command",
                    "description": "Execute a shell command in the codebase directory",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "Shell command to execute"
                            },
                            "working_dir": {
                                "type": "string",
                                "description": "Working directory relative to codebase root (optional)"
                            }
                        },
                        "required": ["command"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_api_endpoint",
                    "description": "Check an API endpoint by making an HTTP request",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "API endpoint URL"
                            },
                            "method": {
                                "type": "string",
                                "description": "HTTP method",
                                "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"]
                            },
                            "payload": {
                                "type": "object",
                                "description": "Request payload (for POST/PUT requests)"
                            },
                            "headers": {
                                "type": "object",
                                "description": "Request headers"
                            }
                        },
                        "required": ["url", "method"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "validate_test_result",
                    "description": "Validate a test execution result",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "result": {
                                "type": "object",
                                "description": "Test result dictionary to validate"
                            }
                        },
                        "required": ["result"]
                    }
                }
            }
        ]
    
    def call_function(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call an executor function by name.
        
        Args:
            function_name: Name of the function to call
            arguments: Function arguments
            
        Returns:
            Function execution result
        """
        function_map = {
            "execute_code": self.execute_code,
            "read_file": self.read_file,
            "write_file": self.write_file,
            "run_command": self.run_command,
            "check_api_endpoint": self.check_api_endpoint,
            "validate_test_result": self.validate_test_result,
            "analyze_code_behavior": self.analyze_code_behavior
        }
        
        if function_name not in function_map:
            return {
                "success": False,
                "error": f"Unknown function: {function_name}"
            }
        
        try:
            func = function_map[function_name]
            return func(**arguments)
        except Exception as e:
            return {
                "success": False,
                "error": f"Error calling {function_name}: {str(e)}"
            }
