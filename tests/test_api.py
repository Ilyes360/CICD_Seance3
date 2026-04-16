import json

from django.test import TestCase

from core.models import Task

class ApiTests(TestCase):
    def test_list_tasks(self):
        Task.objects.create(title="Task A")
        Task.objects.create(title="Task B", completed=True)

        response = self.client.get("/api/tasks")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 2)

    def test_get_task(self):
        task = Task.objects.create(title="Buy milk")
        response = self.client.get(f"/api/tasks/{task.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "Buy milk")

    def test_create_task(self):
        response = self.client.post(
            "/api/tasks",
            data=json.dumps({"title": "New task", "description": "A desc"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Task.objects.filter(title="New task").exists())

    def test_update_task(self):
        task = Task.objects.create(title="Old title", completed=False)
        response = self.client.put(
            f"/api/tasks/{task.id}",
            data=json.dumps({"title": "Updated title", "completed": True}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.title, "Updated title")
        self.assertTrue(task.completed)

    def test_delete_task(self):
        task = Task.objects.create(title="To delete")
        response = self.client.delete(f"/api/tasks/{task.id}")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Task.objects.filter(id=task.id).exists())
