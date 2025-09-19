#!/usr/bin/env python3
"""
Quick syntax check for the updated Streamlit app.
"""

import ast
import sys

def check_syntax(filename):
    """Check Python syntax of a file."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the AST to check for syntax errors
        ast.parse(content)
        print(f"✅ {filename} - Syntax OK")
        return True
        
    except SyntaxError as e:
        print(f"❌ {filename} - Syntax Error: {e}")
        print(f"   Line {e.lineno}: {e.text}")
        return False
    except FileNotFoundError:
        print(f"❌ {filename} - File not found")
        return False
    except Exception as e:
        print(f"❌ {filename} - Error: {e}")
        return False

def main():
    """Check syntax of key files."""
    files_to_check = [
        'streamlit_app.py',
        'crossfit_twin/athlete.py',
        'crossfit_twin/__init__.py',
        'crossfit_twin/simulator.py'
    ]
    
    all_good = True
    for filename in files_to_check:
        if not check_syntax(filename):
            all_good = False
    
    if all_good:
        print("\n🎉 All syntax checks passed!")
    else:
        print("\n💥 Some syntax errors found!")
        sys.exit(1)

if __name__ == "__main__":
    main()