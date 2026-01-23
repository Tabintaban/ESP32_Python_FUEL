import json
import ast
from typing import Union, Dict, Any

class CodeJSONConverter:
    """
    Класс для конвертации между программным кодом и JSON структурой
    """
    
    def __init__(self):
        self.conversion_history = []
    
    def code_to_json(self, code: str) -> str:
        """
        Преобразует программный код в JSON структуру
        """
        try:
            # Разбиваем код на строки
            lines = code.split('\n')
            
            # Создаем структуру для хранения информации о каждой строке
            code_structure = {
                "type": "code",
                "lines": []
            }
            
            for i, line in enumerate(lines):
                line_info = {
                    "line_number": i + 1,
                    "content": line,
                    "indentation": len(line) - len(line.lstrip()) if line.strip() else 0,
                    "is_empty": not line.strip()
                }
                
                # Пытаемся определить тип строки
                stripped_line = line.strip()
                if stripped_line.startswith('#'):
                    line_info["type"] = "comment"
                elif stripped_line.startswith(('def ', 'class ', 'if ', 'elif ', 'else:', 'for ', 'while ', 'try:', 'except', 'finally:', 'with ')):
                    line_info["type"] = "statement"
                elif '=' in stripped_line and not stripped_line.startswith(('=', '==', '!=', '<=', '>=')):
                    line_info["type"] = "assignment"
                elif stripped_line.endswith(':'):
                    line_info["type"] = "block_start"
                else:
                    line_info["type"] = "expression"
                
                code_structure["lines"].append(line_info)
            
            return json.dumps(code_structure, indent=2, ensure_ascii=False)
        
        except Exception as e:
            error_structure = {
                "type": "error",
                "message": f"Ошибка при парсинге кода: {str(e)}",
                "lines": []
            }
            return json.dumps(error_structure, indent=2, ensure_ascii=False)
    
    def json_to_code(self, json_str: str) -> str:
        """
        Преобразует JSON структуру обратно в программный код
        """
        try:
            data = json.loads(json_str)
            
            if data.get("type") == "code":
                lines = []
                for line_info in data.get("lines", []):
                    content = line_info.get("content", "")
                    if line_info.get("is_empty"):
                        lines.append("")
                    else:
                        # Восстанавливаем отступы
                        indentation = line_info.get("indentation", 0)
                        indented_content = " " * indentation + content
                        lines.append(indented_content)
                
                return "\n".join(lines)
            
            elif data.get("type") == "error":
                return f"# Ошибка: {data.get('message', 'Неизвестная ошибка')}"
            
            else:
                return "# Неизвестный формат данных"
        
        except json.JSONDecodeError as e:
            return f"# Ошибка при разборе JSON: {str(e)}"
        except Exception as e:
            return f"# Общая ошибка: {str(e)}"
    
    def is_json_format(self, text: str) -> bool:
        """
        Проверяет, является ли текст JSON структурой
        """
        try:
            # Пробуем распарсить как JSON
            parsed = json.loads(text.strip())
            # Проверяем наличие характерных признаков JSON структуры кода
            if isinstance(parsed, dict) and "type" in parsed and "lines" in parsed:
                return True
            return False
        except:
            return False
    
    def convert_text(self, text: str) -> str:
        """
        Универсальный метод для преобразования текста
        Если текст выглядит как JSON, преобразуем в код, иначе в JSON
        """
        text_stripped = text.strip()
        
        # Если текст пустой, возвращаем пустой результат
        if not text_stripped:
            return self.code_to_json("")
        
        # Проверяем, является ли текст JSON
        if self.is_json_format(text_stripped):
            return self.json_to_code(text_stripped)
        else:
            return self.code_to_json(text_stripped)