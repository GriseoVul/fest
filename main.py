from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from models import Task
from typing import Optional, List
from db_context import db
from schemas import TaskSchema, TaskCreateSchema

app = FastAPI(title="Tasks API",description="API для управления задачами ", version="1.0.0")
db.initialize()

origins = [
    "http://localhost",
    "http://localhost:3000",  # React, Vue и т.д.
    "https://yourdomain.com",  # продакшн фронт
    "*" # all
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,         # список разрешённых источников
    allow_credentials=True,        # разрешаем cookies, авторизацию
    allow_methods=["*"],           # разрешаем все HTTP методы (GET, POST ...)
    allow_headers=["*"],           # разрешаем все заголовки
)

@app.get(
        '/tasks', 
        response_model=List[TaskSchema], 
        summary="Получить корневые задачи", 
        description="Получить задачи без детей")
def get_tasks():
    tasks = db.get_tasks()

    # фильтруем только корневые задачи (которые не встречаются в чужих childs)
    all_child_ids = set()
    for t in db.get_tasks():
        if t.childs:
            all_child_ids.update(child.id for child in t.childs)

    roots = [t for t in tasks if t.id not in all_child_ids]

    return roots



@app.get('/tasks/{id}', 
         response_model=TaskSchema, 
         summary="Получить задачу", 
         description="Получить задачу со всеми детьми")
def get_task(id: int):
    task = db.get_task(id)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return task


@app.post('/tasks', response_model=TaskSchema,
          summary="Создать задачу", 
          description="Добавляет новую задачу в систему")
def create_task(task: TaskCreateSchema, parent: Optional[int] = None):
    # проверка родителя
    parent_task = None
    if parent:
        parent_task = db.get_task(parent)
        if not parent_task:
            raise HTTPException(status_code=404, detail="Родительская задача не найдена")

    # сохраняем новую задачу; передаём parent_task если есть
    new_task = db.insert_task(Task(
        id=0,  # БД сама сгенерирует
        title=task.title,
        description=task.description,
        status=task.status,
        parent=parent_task,
        childs=[]
    ))

    if not new_task:
        raise HTTPException(status_code=500, detail="Не удалось создать задачу")

    # если есть родитель — обновляем его childs
    if parent_task:
        if parent_task.childs is None:
            parent_task.childs = []

        parent_task.childs.append(new_task)
        db._update_childs(parent_task.id, [child.id for child in parent_task.childs])

    return new_task



@app.delete('/tasks', 
            response_model=TaskSchema, 
            summary="Удалить задачу", 
            description="Удаляет задачу вместе с её детьми")
def delete_task(id: int):
    task = db.get_task(id)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    db.delete_task_recursive(id)
    return task




@app.post('/tasks/{id}/toggle', 
          response_model=TaskSchema, 
          summary="Переключить состояние", 
          description="переключить состояние задачи активна\неактивна. Переключить можно вместе с детьми")
def toggle_task(id: int, with_childs: bool = False):
    task = db.get_task(id)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    db.toggle_task(id)
    return db.get_task(id)  # возвращаем обновлённое дерево


@app.post("/tasks/{id}/change-parent", response_model=TaskSchema)
def change_parent(id: int, parent_id: Optional[int] = Body(None)):
    task = db.get_task(id)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    old_parent_id = task.parent

    # Проверка нового родителя
    if parent_id is not None:
        if parent_id == task.id:
            raise HTTPException(status_code=400, detail="Нельзя сделать себя родителем")

        # Защита от циклов
        def is_descendant(descendant_id: int, target_id: int) -> bool:
            descendant_task = db.get_task(descendant_id)
            if not descendant_task:
                return False
            if any(child.id == target_id for child in descendant_task.childs):
                return True
            return any(is_descendant(child.id, target_id) for child in descendant_task.childs)

        if is_descendant(id, parent_id):
            raise HTTPException(status_code=400, detail="Нельзя назначить потомка родителем задачи")

    # Обновляем childs старого родителя
    if old_parent_id:
        old_parent_task = db.get_task(old_parent_id)
        if old_parent_task:
            old_parent_task.childs = [child for child in old_parent_task.childs if child.id != id]
            db._update_childs(old_parent_id, [child.id for child in old_parent_task.childs])

    # Обновляем childs нового родителя
    if parent_id:
        new_parent_task = db.get_task(parent_id)
        if new_parent_task:
            if new_parent_task.childs is None:
                new_parent_task.childs = []
            # Добавляем текущую задачу в список детей нового родителя
            new_parent_task.childs.append(task)
            db._update_childs(parent_id, [child.id for child in new_parent_task.childs])

    # Обновляем самого task
    task.parent = parent_id
    db.update_task(task)

    return db.get_task(id)
