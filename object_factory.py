"""
ObjectFactory - класс для динамического создания объектов с инъекцией методов из JSON-данных
"""

import json
import gc


class ObjectFactory:
    """
    Класс для динамического создания объектов с инъекцией методов из JSON-данных
    """
    
    def __init__(self):
        self.created_objects = {}
        self.method_registry = {}
        
    def create_object_from_json(self, json_config):
        """
        Создание объекта из JSON-конфигурации
        """
        if isinstance(json_config, str):
            config = json.loads(json_config)
        else:
            config = json_config
            
        obj_type = config.get('type', 'generic')
        obj_id = config.get('id', 'default')
        
        # Создаем базовый объект
        obj = self._create_base_object(obj_type, config)
        
        # Инъекция атрибутов
        attributes = config.get('attributes', {})
        for attr_name, attr_value in attributes.items():
            setattr(obj, attr_name, attr_value)
            
        # Инъекция методов
        methods = config.get('methods', {})
        for method_name, method_code in methods.items():
            method = self._create_method(method_code)
            setattr(obj, method_name, method.__get__(obj, obj.__class__))
            
        # Сохраняем объект
        self.created_objects[obj_id] = obj
        
        return obj
        
    def _create_base_object(self, obj_type, config):
        """
        Создание базового объекта заданного типа
        """
        class DynamicObject:
            def __init__(self, obj_type, config):
                self.type = obj_type
                self.config = config
                self.id = config.get('id', 'default')
                
            def __repr__(self):
                return f"<DynamicObject type={self.type} id={self.id}>"
                
            def get_info(self):
                return {
                    'type': self.type,
                    'id': self.id,
                    'config': self.config
                }
                
        return DynamicObject(obj_type, config)
        
    def _create_method(self, method_code):
        """
        Создание метода из строкового представления кода
        """
        # Компилируем код метода
        compiled_code = compile(method_code, '<dynamic>', 'exec')
        
        # Создаем локальное пространство имен для выполнения
        local_ns = {}
        exec(compiled_code, {}, local_ns)
        
        # Находим первый определенный метод
        for name, obj in local_ns.items():
            if callable(obj):
                return obj
                
        # Если не найден, создаем пустой метод
        def placeholder_method(*args, **kwargs):
            print(f"Placeholder method called with args: {args}, kwargs: {kwargs}")
            return None
            
        return placeholder_method
        
    def inject_methods(self, obj, methods_dict):
        """
        Инъекция методов в существующий объект
        """
        for method_name, method_code in methods_dict.items():
            method = self._create_method(method_code)
            setattr(obj, method_name, method.__get__(obj, obj.__class__))
            
    def validate_object_structure(self, config):
        """
        Валидация структуры объекта
        """
        required_fields = ['type']
        optional_fields = ['id', 'attributes', 'methods', 'dependencies']
        
        # Проверяем обязательные поля
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field: {field}")
                
        # Проверяем типы полей
        if not isinstance(config['type'], str):
            raise ValueError("Field 'type' must be a string")
            
        if 'id' in config and not isinstance(config['id'], str):
            raise ValueError("Field 'id' must be a string")
            
        if 'attributes' in config and not isinstance(config['attributes'], dict):
            raise ValueError("Field 'attributes' must be a dictionary")
            
        if 'methods' in config and not isinstance(config['methods'], dict):
            raise ValueError("Field 'methods' must be a dictionary")
            
        return True
        
    def create_object_from_code(self, class_code, instance_params=None):
        """
        Создание объекта из строкового представления класса
        """
        if instance_params is None:
            instance_params = {}
            
        # Компилируем код класса
        compiled_code = compile(class_code, '<dynamic_class>', 'exec')
        
        # Создаем глобальное пространство имен
        global_ns = {}
        exec(compiled_code, global_ns)
        
        # Находим определение класса
        class_obj = None
        for name, obj in global_ns.items():
            if isinstance(obj, type):
                class_obj = obj
                break
                
        if class_obj is None:
            raise ValueError("No class definition found in provided code")
            
        # Создаем экземпляр класса
        instance = class_obj(**instance_params)
        
        return instance
        
    def register_method(self, method_name, method_func):
        """
        Регистрация метода в глобальном реестре
        """
        self.method_registry[method_name] = method_func
        
    def get_registered_method(self, method_name):
        """
        Получение зарегистрированного метода
        """
        return self.method_registry.get(method_name)
        
    def create_dynamic_module(self, module_name, functions_dict):
        """
        Создание динамического модуля с заданными функциями
        """
        class DynamicModule:
            def __init__(self, name, funcs):
                self.__name__ = name
                for func_name, func_code in funcs.items():
                    func = self._compile_function(func_code)
                    setattr(self, func_name, func)
                    
            def _compile_function(self, func_code):
                """Компиляция функции из строкового кода"""
                compiled_code = compile(func_code, '<dynamic_func>', 'exec')
                local_ns = {}
                exec(compiled_code, {}, local_ns)
                
                # Возвращаем первую найденную функцию
                for name, obj in local_ns.items():
                    if callable(obj):
                        return obj
                        
                return lambda *args, **kwargs: None  # Пустая функция по умолчанию
                
        return DynamicModule(module_name, functions_dict)
        
    def cleanup(self):
        """
        Очистка созданных объектов для освобождения памяти
        """
        self.created_objects.clear()
        self.method_registry.clear()
        gc.collect()


# Пример использования:
if __name__ == "__main__":
    factory = ObjectFactory()
    
    # Пример JSON-конфигурации объекта
    config = {
        "type": "led_controller",
        "id": "led1",
        "attributes": {
            "pin": 2,
            "state": False
        },
        "methods": {
            "turn_on": '''
def turn_on(self):
    self.state = True
    print(f"LED on pin {self.pin} turned ON")
    return True
''',
            "turn_off": '''
def turn_off(self):
    self.state = False
    print(f"LED on pin {self.pin} turned OFF")
    return False
'''
        }
    }
    
    # Создание объекта
    led = factory.create_object_from_json(config)
    
    # Использование объекта
    print(led.get_info())
    led.turn_on()
    led.turn_off()