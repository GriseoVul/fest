import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Optional, Set
from contextlib import contextmanager
from config import settings
from models import Task
from datetime import datetime

class Database:
    """Simple DB context for tasks with parent/child relations and cycle protection.

    Public methods:
      - initialize()
      - insert_task(task)
      - get_tasks()  # root tasks (parent is NULL)
      - get_task(id)
      - delete_task_recursive(id)
      - toggle_task(id)
      - _update_childs(id, childs)
    """

    def __init__(self) -> None:
        self._connection = None

    def _get_connection(self):
        if self._connection is None:
            self._connection = psycopg2.connect(
                database=settings.DB_NAME,
                user=settings.DB_USER,
                password=settings.DB_PASS,
                host=settings.DB_HOST,
                port=settings.DB_PORT,
            )
        return self._connection

    @contextmanager
    def _cursor(self):
        conn = self._get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
            conn.commit()

    def initialize(self) -> None:
        """Create tasks table (no-op if exists)."""
        with self._cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    status BOOLEAN NOT NULL DEFAULT FALSE,
                    updated TIMESTAMP without time zone,
                    parent INT,
                    childs INT[]
                );
                """
            )

    def insert_task(self, task: Task) -> Optional[Task]:
        """Insert a new task. If initial childs are provided, _update_childs will be called
        to set parent pointers and validate cycles.
        Returns the created Task or None on failure.
        """
        childs_list = [child.id for child in task.childs] if task.childs else []
        parent_id = task.parent.id if task.parent else None
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO tasks (title, description, status, updated, parent, childs)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, title, description, status, updated, parent, childs
                """,
                (task.title, task.description, task.status, getattr(task, 'updated', None), parent_id, childs_list),
            )
            row = cur.fetchone()
            if not row:
                return None

            created = self._build_task(row)

            # If caller asked to attach childs immediately, ensure parents are set and cycles checked.
            if childs_list:
                try:
                    self._update_childs(created.id, childs_list)
                except Exception:
                    # rollback created row
                    cur.execute("DELETE FROM tasks WHERE id = %s", (created.id,))
                    return None

            return created

    def get_tasks(self) -> List[Task]:
        """Return root tasks (parent IS NULL) as Task objects with children populated."""
        with self._cursor() as cur:
            cur.execute("SELECT id, title, description, status, updated, parent, childs FROM tasks WHERE parent IS NULL")
            rows = cur.fetchall()
            return [self._build_task(r) for r in rows]

    def get_task(self, id: int, visited: Optional[Set[int]] = None) -> Optional[Task]:
        """Return a single Task by id. Uses `visited` internally to avoid infinite recursion."""
        if visited is None:
            visited = set()
        if id in visited:
            return None

        with self._cursor() as cur:
            cur.execute("SELECT id, title, description, status, updated, parent, childs FROM tasks WHERE id = %s", (id,))
            row = cur.fetchone()
            return self._build_task(row, visited) if row else None




    # def _build_task(self, row: dict, visited: Optional[Set[int]] = None) -> Task:
    #     """
    #     Создаёт Task из строки БД.
    #     parent хранится как int, childs — список id.
    #     """
    #     if visited is None:
    #         visited = set()

    #     task_id = row["id"]
    #     local_visited = set(visited)
    #     local_visited.add(task_id)

    #     childs_ids = row.get("childs") or []

    #     parent_id = row.get("parent")

    #     return Task(
    #         id=task_id,
    #         title=row.get("title"),
    #         description=row.get("description"),
    #         status=row.get("status"),
    #         updated=row.get("updated"),
    #         parent=parent_id,
    #         childs=childs_ids,
    #     )

    def _build_task(self, row: dict, visited: Optional[Set[int]] = None) -> Task:
        """Create a Task dataclass from a DB row and populate children recursively.

        The `visited` set is copied and passed to recursive calls to avoid cycles.
        """
        if visited is None:
            visited = set()

        task_id = row["id"]
        # copy visited to avoid mutating caller state
        local_visited = set(visited)
        local_visited.add(task_id)

        # build children
        childs: List[Task] = []
        for child_id in row.get("childs") or []:
            if child_id in local_visited:
                continue
            child = self.get_task(child_id, local_visited)
            if child:
                childs.append(child)

        # build parent (avoid cycles)
        parent = None
        parent_id = row.get("parent")
        if parent_id and parent_id not in local_visited:
            parent = self.get_task(parent_id, local_visited)

        return Task(
            id=task_id,
            title=row.get("title"),
            description=row.get("description"),
            status=row.get("status"),
            updated=row.get("updated"),
            parent=parent,
            childs=childs,
        )

    # ---- cycle detection helpers ----
    def _get_parent_id(self, task_id: int) -> Optional[int]:
        with self._cursor() as cur:
            cur.execute("SELECT parent FROM tasks WHERE id = %s", (task_id,))
            row = cur.fetchone()
            return row["parent"] if row else None

    def _is_ancestor(self, ancestor_id: int, descendant_id: Optional[int]) -> bool:
        """Return True if `ancestor_id` appears in the parent chain of `descendant_id`.

        A protection against cycles: if the DB already contains a loop we'll conservatively
        return True to avoid creating new links that would make it worse.
        """
        if ancestor_id is None or descendant_id is None:
            return False

        seen: Set[int] = set()
        current = descendant_id
        while current is not None:
            if current in seen:
                # existing DB cycle — treat as ancestor found to be safe
                return True
            seen.add(current)
            if current == ancestor_id:
                return True
            current = self._get_parent_id(current)
        return False

    # ---- operations ----
    def delete_task_recursive(self, task_id: int) -> None:
        task = self.get_task(task_id)
        if not task:
            return
        for child in task.childs or []:
            self.delete_task_recursive(child.id)
        with self._cursor() as cur:
            cur.execute("DELETE FROM tasks WHERE id = %s", (task_id,))

    def toggle_task(self, task_id: int) -> None:
        task = self.get_task(task_id)
        if not task:
            return
        new_status = not task.status
        with self._cursor() as cur:
            cur.execute("UPDATE tasks SET status = %s WHERE id = %s", (new_status, task_id))

        if new_status:
            for child in task.childs or []:
                self._set_task_status_recursive(child.id, True)

    def _set_task_status_recursive(self, task_id: int, status: bool) -> None:
        with self._cursor() as cur:
            cur.execute("UPDATE tasks SET status = %s WHERE id = %s", (status, task_id))
        child_task = self.get_task(task_id)
        for child in child_task.childs or []:
            self._set_task_status_recursive(child.id, status)

    def _update_childs(self, task_id: int, childs: List[int]) -> None:
        """Set the childs list for `task_id` while validating no cycles are created.

        Steps:
          - validate each child is not equal to task_id and not an ancestor of task_id
          - update the childs array for task
          - set parent = task_id for newly added children
          - clear parent for removed children
        """
        childs = childs or []

        # validation
        for c in childs:
            if c == task_id:
                raise ValueError("cannot set a task as its own child")
            if self._is_ancestor(c, task_id):
                raise ValueError(f"adding child {c} to {task_id} would create a cycle")

        with self._cursor() as cur:
            cur.execute("SELECT childs FROM tasks WHERE id = %s", (task_id,))
            row = cur.fetchone()
            prev = row["childs"] if row and row.get("childs") else []

            # write new childs list
            cur.execute("UPDATE tasks SET childs = %s WHERE id = %s", (childs, task_id))

            # set parent on new children
            for c in childs:
                cur.execute("UPDATE tasks SET parent = %s WHERE id = %s", (task_id, c))

            # unset parent on removed children
            removed = set(prev) - set(childs) if prev else set()
            for c in removed:
                cur.execute("UPDATE tasks SET parent = NULL WHERE id = %s", (c,))

    def update_task(self, task: Task) -> Optional[Task]:
        """
        Обновляет задачу в PostgreSQL.
        Автоматически обновляет поле updated.
        Обновляет title, description, status, parent и childs.
        Возвращает обновлённый Task или None, если не найден.
        """
        if not task or not task.id:
            return None

        task.updated = datetime.now()
        parent_id = task.parent.id if task.parent else None
        childs_list = [child.id for child in task.childs] if task.childs else []

        with self._cursor() as cur:
            cur.execute(
                """
                UPDATE tasks
                SET title = %s,
                    description = %s,
                    status = %s,
                    updated = %s,
                    parent = %s,
                    childs = %s
                WHERE id = %s
                RETURNING id, title, description, status, updated, parent, childs
                """,
                (task.title, task.description, task.status, task.updated, parent_id, childs_list, task.id),
            )
            row = cur.fetchone()
            if not row:
                return None

            # Возвращаем объект Task с актуальными данными
            return self._build_task(row)

db = Database()