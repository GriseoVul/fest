from fastapi import FastAPI
from models import Task
from typing import Optional

app = FastAPI(title="Tasks API",description="API для управления задачами (с рекурсией 😏)", version="1.0.0")

@app.get('/tasks', response_model=Task, summary="Получить корневые задачи", description="Получить задачи без детей")
def get_tasks():
    pass

@app.get('/tasks/{id}', response_model=Task, summary="Получить задачу", description="Получить задачу со всеми детьми")
def get_task(id: int):
    pass

@app.post('/tasks', response_model=Task, summary="Создать задачу", description="Добавляет новую задачу в систему")
def create_task(task: Task, parent: Optional[int]):
    pass

@app.delete('/tasks', response_model=Task, summary="Удалить задачу", description="Удаляет задачу вместе с её детьми")
def delete_task(id: int):
    pass

@app.post('/tasks/{id}/toggle', response_model=Task, summary="Переключить состояние", description="переключить состояние задачи активна\неактивна. Переключить можно вместе с детьми")
def toggle_task(id: int, with_childs: bool = False):
    pass

app.run()