"""
Code Analyzer Module

代码分析模块，负责：
- ZIP 文件提取
- 文件树构建
- AST 解析（Python, JavaScript/TypeScript）
- 代码结构提取
- 代码摘要生成
"""
import os
import ast
import re
import zipfile
import tempfile
import shutil
from typing import Dict, List, Optional, Set
from pathlib import Path


class CodeAnalyzer:
    """Analyzes code structure from ZIP files."""
    
    def __init__(self, zip_path: str):
        """
        Initialize code analyzer.
        
        Args:
            zip_path: Path to ZIP file containing code
        """
        self.zip_path = zip_path
        self.extracted_path: Optional[str] = None
        self.file_tree: Dict[str, str] = {}
        self.code_structure: Dict[str, Dict] = {}
    
    def extract_zip(self) -> str:
        """
        Extract ZIP file to temporary directory.
        
        Returns:
            Path to extracted directory
            
        Raises:
            ValueError: If ZIP extraction fails
        """
        try:
            # Create temporary directory
            self.extracted_path = tempfile.mkdtemp(prefix="code_analysis_")
            
            # Extract ZIP file
            with zipfile.ZipFile(self.zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.extracted_path)
            
            return self.extracted_path
            
        except zipfile.BadZipFile:
            raise ValueError(f"Invalid ZIP file: {self.zip_path}")
        except Exception as e:
            raise ValueError(f"Failed to extract ZIP file: {str(e)}")
    
    def get_file_tree(self) -> Dict[str, str]:
        """
        Build file tree structure.
        
        Returns:
            Dictionary mapping file paths to their types
        """
        if not self.extracted_path:
            self.extract_zip()
        
        if self.file_tree:
            return self.file_tree
        
        self.file_tree = {}
        
        for root, dirs, files in os.walk(self.extracted_path):
            # Skip hidden directories and common ignore patterns
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', '.git']]
            
            for file in files:
                if file.startswith('.'):
                    continue
                
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, self.extracted_path)
                
                # Determine file type
                file_ext = os.path.splitext(file)[1].lower()
                file_type = self._get_file_type(file_ext, file)
                
                self.file_tree[relative_path] = file_type
        
        return self.file_tree
    
    def _get_file_type(self, ext: str, filename: str) -> str:
        """Determine file type from extension and name."""
        type_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.jsx': 'javascript',
            '.json': 'json',
            '.md': 'markdown',
            '.txt': 'text',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.xml': 'xml',
            '.html': 'html',
            '.css': 'css',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
        }
        
        if ext in type_map:
            return type_map[ext]
        
        # Check for special files
        if filename.lower() in ['package.json', 'requirements.txt', 'pom.xml', 'go.mod', 'cargo.toml']:
            return 'config'
        
        return 'unknown'
    
    def analyze_code_structure(self) -> Dict[str, Dict]:
        """
        Analyze code structure using AST parsing.
        
        Returns:
            Dictionary mapping file paths to their code structure
        """
        if not self.extracted_path:
            self.extract_zip()
        
        if self.code_structure:
            return self.code_structure
        
        self.code_structure = {}
        file_tree = self.get_file_tree()
        
        for file_path, file_type in file_tree.items():
            if file_type not in ['python', 'javascript', 'typescript']:
                continue
            
            full_path = os.path.join(self.extracted_path, file_path)
            
            if not os.path.exists(full_path):
                continue
            
            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                if file_type == 'python':
                    structure = self._analyze_python_structure(content)
                elif file_type in ['javascript', 'typescript']:
                    structure = self._analyze_javascript_structure(content)
                else:
                    structure = {}
                
                if structure:
                    self.code_structure[file_path] = structure
                    
            except Exception as e:
                # Skip files that can't be parsed
                continue
        
        return self.code_structure
    
    def _analyze_python_structure(self, content: str) -> Dict:
        """Analyze Python code structure using AST."""
        try:
            tree = ast.parse(content)
            
            functions = []
            classes = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append({
                        'name': node.name,
                        'line_start': node.lineno,
                        'line_end': self._get_node_end_line(node, content),
                        'args': [arg.arg for arg in node.args.args],
                        'is_async': isinstance(node, ast.AsyncFunctionDef)
                    })
                elif isinstance(node, ast.ClassDef):
                    methods = []
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            methods.append(item.name)
                    
                    classes.append({
                        'name': node.name,
                        'line_start': node.lineno,
                        'line_end': self._get_node_end_line(node, content),
                        'methods': methods
                    })
            
            return {
                'functions': functions,
                'classes': classes
            }
            
        except SyntaxError:
            return {}
        except Exception:
            return {}
    
    def _analyze_javascript_structure(self, content: str) -> Dict:
        """Analyze JavaScript/TypeScript code structure using regex."""
        functions = []
        classes = []
        
        lines = content.split('\n')
        
        # Pattern for function declarations
        function_patterns = [
            r'function\s+(\w+)\s*\([^)]*\)\s*\{',  # function name() {}
            r'const\s+(\w+)\s*=\s*\([^)]*\)\s*=>\s*\{',  # const name = () => {}
            r'(\w+)\s*:\s*function\s*\([^)]*\)\s*\{',  # name: function() {}
            r'(\w+)\s*:\s*\([^)]*\)\s*=>\s*\{',  # name: () => {}
            r'async\s+function\s+(\w+)\s*\([^)]*\)\s*\{',  # async function name() {}
            r'const\s+(\w+)\s*=\s*async\s*\([^)]*\)\s*=>\s*\{',  # const name = async () => {}
        ]
        
        # Pattern for class declarations
        class_pattern = r'class\s+(\w+)(?:\s+extends\s+\w+)?\s*\{'
        
        for i, line in enumerate(lines, 1):
            # Check for functions
            for pattern in function_patterns:
                match = re.search(pattern, line)
                if match:
                    func_name = match.group(1)
                    # Find end of function (simplified - looks for closing brace)
                    end_line = self._find_js_block_end(lines, i - 1)
                    functions.append({
                        'name': func_name,
                        'line_start': i,
                        'line_end': end_line
                    })
                    break
            
            # Check for classes
            match = re.search(class_pattern, line)
            if match:
                class_name = match.group(1)
                end_line = self._find_js_block_end(lines, i - 1)
                classes.append({
                    'name': class_name,
                    'line_start': i,
                    'line_end': end_line
                })
        
        return {
            'functions': functions,
            'classes': classes
        }
    
    def _find_js_block_end(self, lines: List[str], start_idx: int) -> int:
        """Find the end line of a JavaScript block."""
        brace_count = 0
        in_block = False
        
        for i in range(start_idx, len(lines)):
            line = lines[i]
            for char in line:
                if char == '{':
                    brace_count += 1
                    in_block = True
                elif char == '}':
                    brace_count -= 1
                    if in_block and brace_count == 0:
                        return i + 1
        
        return start_idx + 1
    
    def _get_node_end_line(self, node: ast.AST, content: str) -> int:
        """Get end line of AST node."""
        if hasattr(node, 'end_lineno') and node.end_lineno:
            return node.end_lineno
        
        # Fallback: estimate based on content
        lines = content.split('\n')
        start_line = node.lineno - 1
        
        # Simple heuristic: look for next def/class at same or lower indentation
        if start_line < len(lines):
            start_indent = len(lines[start_line]) - len(lines[start_line].lstrip())
            
            for i in range(start_line + 1, min(start_line + 100, len(lines))):
                line = lines[i]
                if not line.strip():
                    continue
                
                indent = len(line) - len(line.lstrip())
                if indent <= start_indent and (line.strip().startswith('def ') or 
                                               line.strip().startswith('class ') or
                                               line.strip().startswith('@')):
                    return i
                
                # Check for end of file
                if i == len(lines) - 1:
                    return i + 1
        
        return node.lineno + 10  # Default fallback
    
    def get_code_summary(self) -> str:
        """
        Generate summary of codebase structure.
        
        Returns:
            String summary of codebase
        """
        file_tree = self.get_file_tree()
        code_structure = self.analyze_code_structure()
        
        summary_parts = []
        
        # Count files by type
        file_types = {}
        for file_path, file_type in file_tree.items():
            file_types[file_type] = file_types.get(file_type, 0) + 1
        
        summary_parts.append("## Codebase Overview")
        summary_parts.append(f"Total files: {len(file_tree)}")
        summary_parts.append("\nFile types:")
        for file_type, count in sorted(file_types.items()):
            summary_parts.append(f"  - {file_type}: {count}")
        
        # Key files
        key_files = []
        for file_path in file_tree.keys():
            filename = os.path.basename(file_path)
            if filename.lower() in ['package.json', 'requirements.txt', 'pom.xml', 
                                   'go.mod', 'cargo.toml', 'main.py', 'app.py', 
                                   'index.js', 'index.ts', 'server.js', 'server.ts']:
                key_files.append(file_path)
        
        if key_files:
            summary_parts.append("\nKey files:")
            for key_file in key_files[:10]:
                summary_parts.append(f"  - {key_file}")
        
        # Code structure summary
        if code_structure:
            total_functions = sum(len(s.get('functions', [])) for s in code_structure.values())
            total_classes = sum(len(s.get('classes', [])) for s in code_structure.values())
            
            summary_parts.append(f"\nCode structure:")
            summary_parts.append(f"  - Total functions: {total_functions}")
            summary_parts.append(f"  - Total classes: {total_classes}")
            summary_parts.append(f"  - Files with code: {len(code_structure)}")
        
        return "\n".join(summary_parts)
    
    def get_relevant_files_content(self, max_files: int = 20, max_size: int = 5000) -> Dict[str, str]:
        """
        Get content of relevant files for analysis.
        
        Args:
            max_files: Maximum number of files to return
            max_size: Maximum size per file (characters)
            
        Returns:
            Dictionary mapping file paths to their content
        """
        if not self.extracted_path:
            self.extract_zip()
        
        file_tree = self.get_file_tree()
        code_structure = self.analyze_code_structure()
        
        # Prioritize files with code structure
        relevant_files = set()
        
        # Add files with functions/classes
        for file_path in code_structure.keys():
            relevant_files.add(file_path)
        
        # Add key configuration files
        for file_path in file_tree.keys():
            filename = os.path.basename(file_path).lower()
            if filename in ['package.json', 'requirements.txt', 'pom.xml', 
                          'go.mod', 'cargo.toml', 'dockerfile', 'docker-compose.yml',
                          'readme.md', 'main.py', 'app.py', 'index.js', 'index.ts',
                          'server.js', 'server.ts']:
                relevant_files.add(file_path)
        
        # Limit number of files
        relevant_files = list(relevant_files)[:max_files]
        
        file_contents = {}
        
        for file_path in relevant_files:
            full_path = os.path.join(self.extracted_path, file_path)
            
            if not os.path.exists(full_path):
                continue
            
            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Limit content size
                if len(content) > max_size:
                    content = content[:max_size] + "\n... (truncated)"
                
                file_contents[file_path] = content
                
            except Exception:
                continue
        
        return file_contents
    
    def cleanup(self):
        """Clean up extracted files."""
        if self.extracted_path and os.path.exists(self.extracted_path):
            try:
                shutil.rmtree(self.extracted_path)
            except Exception:
                pass
            self.extracted_path = None
        
        self.file_tree = {}
        self.code_structure = {}
