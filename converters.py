from typing import Optional, List
from models import Task
from schemas import TaskSchema

def task_to_schema(task: Task) -> TaskSchema:
    """Конвертирует модель Task в схему TaskSchema"""
    if not task:
        return None
    
    return TaskSchema(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        updated=task.updated,
        parent=task_to_schema(task.parent) if task.parent else None,
        childs=[task_to_schema(child) for child in task.childs] if task.childs else []
    )

def tasks_to_schemas(tasks: List[Task]) -> List[TaskSchema]:
    """Конвертирует список моделей Task в список схем TaskSchema"""
    return [task_to_schema(task) for task in tasks] if tasks else []

def schema_to_task(schema: TaskSchema) -> Task:
    """Конвертирует схему TaskSchema в модель Task"""
    if not schema:
        return None
    
    return Task(
        id=schema.id,
        title=schema.title,
        description=schema.description,
        status=schema.status,
        updated=schema.updated,
        parent=schema_to_task(schema.parent) if schema.parent else None,
        childs=[schema_to_task(child) for child in schema.childs] if schema.childs else []
    )

def schemas_to_tasks(schemas: List[TaskSchema]) -> List[Task]:
    """Конвертирует список схем TaskSchema в список моделей Task"""
    return [schema_to_task(schema) for schema in schemas] if schemas else []
