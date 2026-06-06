import os
import py_compile
import sys

def run_linter():
    print("Starting static syntax check...")
    has_errors = False
    exclude_dirs = {".git", "__pycache__", ".venv", "venv"}
    
    for root, dirs, files in os.walk("."):
        # Modifying dirs in-place to skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    py_compile.compile(file_path, doraise=True)
                    print(f"[OK] {file_path} - Syntax OK")
                except py_compile.PyCompileError as e:
                    print(f"[ERROR] {file_path} - Syntax Error: {e.msg}")
                    has_errors = True
                except Exception as e:
                    print(f"[FAILED] {file_path} - Failed to check: {e}")
                    has_errors = True
                    
    if has_errors:
        print("Linter failed: Syntax errors found.")
        sys.exit(1)
    else:
        print("Linter passed: All files have valid syntax.")
        sys.exit(0)

if __name__ == "__main__":
    run_linter()
