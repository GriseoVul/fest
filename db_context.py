import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Optional
from contextlib import contextmanager


from config import settings
from models import Task
# --- Контекст базы ---
class Database:
    def __init__(self):
        self._connection = None

    def _get_connection(self):
        if self._connection is None:
            self._connection = psycopg2.connect(
                database=settings.DB_NAME,
                user=settings.DB_USER,
                password=settings.DB_PASS,
                host=settings.DB_HOST,
                port=settings.DB_PORT
            )
        return self._connection

    @contextmanager
    def _cursor(self):
        conn = self._get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
            conn.commit()

    # --- создание таблицы ---
    def initialize(self):
        with self._cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    status BOOLEAN NOT NULL DEFAULT FALSE,
                    childs INT[]
                );
            """)

    # --- вставка задачи ---
    def insert_task(self, task: Task) -> Optional[Task]:
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO tasks (title, description, status, childs)
                VALUES (%s, %s, %s, %s)
                RETURNING id, title, description, status, childs
                """,
                (
                    task.title,
                    task.description,
                    task.status,
                    [c.id for c in task.childs] if task.childs else []
                )
            )
            row = cur.fetchone()
            if row:
                return self._build_task(row)
        return None

    # --- все задачи ---
    def get_tasks(self) -> List[Task]:
        with self._cursor() as cur:
            cur.execute("SELECT id, title, description, status, childs FROM tasks")
            rows = cur.fetchall()
            return [self._build_task(row) for row in rows]

    # --- одна задача ---
    def get_task(self, id: int) -> Optional[Task]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT id, title, description, status, childs FROM tasks WHERE id = %s",
                (id,)
            )
            row = cur.fetchone()
            return self._build_task(row) if row else None


    # вспомогательная сборка задачи
    def _build_task(self, row: dict) -> Task:
        """Создаёт Task и рекурсивно подгружает его childs"""
        childs = []
        if row["childs"]:
            for child_id in row["childs"]:
                child_task = self.get_task(child_id)
                if child_task:
                    childs.append(child_task)

        return Task(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            status=row["status"],
            childs=childs
        )
    
db = Database()