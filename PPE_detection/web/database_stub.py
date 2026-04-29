"""Заглушка для БД. Потом заменим на реальный SQLiteLogger"""


class DatabaseStub:

    def __init__(self):
        self._violations = [
            {
                "date": "2026-04-28",
                "time": "14:22:18",
                "human_id": 42,
                "violation_type": "Без каски",
                "confidence": 0.87,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001234.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "10:15:32",
                "human_id": 17,
                "violation_type": "Без жилета",
                "confidence": 0.92,
                "camera_id": "rtsp://localhost:8554/stream2",
                "screenshot_path": "violations/frame_001235.jpg"
            },
            {
                "date": "2026-04-27",
                "time": "16:45:03",
                "human_id": 8,
                "violation_type": "Без перчаток",
                "confidence": 0.78,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001236.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "14:22:18",
                "human_id": 42,
                "violation_type": "Без каски",
                "confidence": 0.87,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001234.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "10:15:32",
                "human_id": 17,
                "violation_type": "Без жилета",
                "confidence": 0.92,
                "camera_id": "rtsp://localhost:8554/stream2",
                "screenshot_path": "violations/frame_001235.jpg"
            },
            {
                "date": "2026-04-27",
                "time": "16:45:03",
                "human_id": 8,
                "violation_type": "Без перчаток",
                "confidence": 0.78,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001236.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "10:15:32",
                "human_id": 17,
                "violation_type": "Без жилета",
                "confidence": 0.92,
                "camera_id": "rtsp://localhost:8554/stream2",
                "screenshot_path": "violations/frame_001235.jpg"
            },
            {
                "date": "2026-04-27",
                "time": "16:45:03",
                "human_id": 8,
                "violation_type": "Без перчаток",
                "confidence": 0.78,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001236.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "14:22:18",
                "human_id": 42,
                "violation_type": "Без каски",
                "confidence": 0.87,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001234.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "10:15:32",
                "human_id": 17,
                "violation_type": "Без жилета",
                "confidence": 0.92,
                "camera_id": "rtsp://localhost:8554/stream2",
                "screenshot_path": "violations/frame_001235.jpg"
            },
            {
                "date": "2026-04-27",
                "time": "16:45:03",
                "human_id": 8,
                "violation_type": "Без перчаток",
                "confidence": 0.78,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001236.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "10:15:32",
                "human_id": 17,
                "violation_type": "Без жилета",
                "confidence": 0.92,
                "camera_id": "rtsp://localhost:8554/stream2",
                "screenshot_path": "violations/frame_001235.jpg"
            },
            {
                "date": "2026-04-27",
                "time": "16:45:03",
                "human_id": 8,
                "violation_type": "Без перчаток",
                "confidence": 0.78,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001236.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "14:22:18",
                "human_id": 42,
                "violation_type": "Без каски",
                "confidence": 0.87,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001234.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "10:15:32",
                "human_id": 17,
                "violation_type": "Без жилета",
                "confidence": 0.92,
                "camera_id": "rtsp://localhost:8554/stream2",
                "screenshot_path": "violations/frame_001235.jpg"
            },
            {
                "date": "2026-04-27",
                "time": "16:45:03",
                "human_id": 8,
                "violation_type": "Без перчаток",
                "confidence": 0.78,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001236.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "10:15:32",
                "human_id": 17,
                "violation_type": "Без жилета",
                "confidence": 0.92,
                "camera_id": "rtsp://localhost:8554/stream2",
                "screenshot_path": "violations/frame_001235.jpg"
            },
            {
                "date": "2026-04-27",
                "time": "16:45:03",
                "human_id": 8,
                "violation_type": "Без перчаток",
                "confidence": 0.78,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001236.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "14:22:18",
                "human_id": 42,
                "violation_type": "Без каски",
                "confidence": 0.87,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001234.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "10:15:32",
                "human_id": 17,
                "violation_type": "Без жилета",
                "confidence": 0.92,
                "camera_id": "rtsp://localhost:8554/stream2",
                "screenshot_path": "violations/frame_001235.jpg"
            },
            {
                "date": "2026-04-27",
                "time": "16:45:03",
                "human_id": 8,
                "violation_type": "Без перчаток",
                "confidence": 0.78,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001236.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "10:15:32",
                "human_id": 17,
                "violation_type": "Без жилета",
                "confidence": 0.92,
                "camera_id": "rtsp://localhost:8554/stream2",
                "screenshot_path": "violations/frame_001235.jpg"
            },
            {
                "date": "2026-04-27",
                "time": "16:45:03",
                "human_id": 8,
                "violation_type": "Без перчаток",
                "confidence": 0.78,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001236.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "14:22:18",
                "human_id": 42,
                "violation_type": "Без каски",
                "confidence": 0.87,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001234.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "10:15:32",
                "human_id": 17,
                "violation_type": "Без жилета",
                "confidence": 0.92,
                "camera_id": "rtsp://localhost:8554/stream2",
                "screenshot_path": "violations/frame_001235.jpg"
            },
            {
                "date": "2026-04-27",
                "time": "16:45:03",
                "human_id": 8,
                "violation_type": "Без перчаток",
                "confidence": 0.78,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001236.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "10:15:32",
                "human_id": 17,
                "violation_type": "Без жилета",
                "confidence": 0.92,
                "camera_id": "rtsp://localhost:8554/stream2",
                "screenshot_path": "violations/frame_001235.jpg"
            },
            {
                "date": "2026-04-27",
                "time": "16:45:03",
                "human_id": 8,
                "violation_type": "Без перчаток",
                "confidence": 0.78,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001236.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "14:22:18",
                "human_id": 42,
                "violation_type": "Без каски",
                "confidence": 0.87,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001234.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "10:15:32",
                "human_id": 17,
                "violation_type": "Без жилета",
                "confidence": 0.92,
                "camera_id": "rtsp://localhost:8554/stream2",
                "screenshot_path": "violations/frame_001235.jpg"
            },
            {
                "date": "2026-04-27",
                "time": "16:45:03",
                "human_id": 8,
                "violation_type": "Без перчаток",
                "confidence": 0.78,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001236.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "10:15:32",
                "human_id": 17,
                "violation_type": "Без жилета",
                "confidence": 0.92,
                "camera_id": "rtsp://localhost:8554/stream2",
                "screenshot_path": "violations/frame_001235.jpg"
            },
            {
                "date": "2026-04-27",
                "time": "16:45:03",
                "human_id": 8,
                "violation_type": "Без перчаток",
                "confidence": 0.78,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001236.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "14:22:18",
                "human_id": 42,
                "violation_type": "Без каски",
                "confidence": 0.87,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001234.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "10:15:32",
                "human_id": 17,
                "violation_type": "Без жилета",
                "confidence": 0.92,
                "camera_id": "rtsp://localhost:8554/stream2",
                "screenshot_path": "violations/frame_001235.jpg"
            },
            {
                "date": "2026-04-27",
                "time": "16:45:03",
                "human_id": 8,
                "violation_type": "Без перчаток",
                "confidence": 0.78,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001236.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "10:15:32",
                "human_id": 17,
                "violation_type": "Без жилета",
                "confidence": 0.92,
                "camera_id": "rtsp://localhost:8554/stream2",
                "screenshot_path": "violations/frame_001235.jpg"
            },
            {
                "date": "2026-04-27",
                "time": "16:45:03",
                "human_id": 8,
                "violation_type": "Без перчаток",
                "confidence": 0.78,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001236.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "14:22:18",
                "human_id": 42,
                "violation_type": "Без каски",
                "confidence": 0.87,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001234.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "10:15:32",
                "human_id": 17,
                "violation_type": "Без жилета",
                "confidence": 0.92,
                "camera_id": "rtsp://localhost:8554/stream2",
                "screenshot_path": "violations/frame_001235.jpg"
            },
            {
                "date": "2026-04-27",
                "time": "16:45:03",
                "human_id": 8,
                "violation_type": "Без перчаток",
                "confidence": 0.78,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001236.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "10:15:32",
                "human_id": 17,
                "violation_type": "Без жилета",
                "confidence": 0.92,
                "camera_id": "rtsp://localhost:8554/stream2",
                "screenshot_path": "violations/frame_001235.jpg"
            },
            {
                "date": "2026-04-27",
                "time": "16:45:03",
                "human_id": 8,
                "violation_type": "Без перчаток",
                "confidence": 0.78,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001236.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "14:22:18",
                "human_id": 42,
                "violation_type": "Без каски",
                "confidence": 0.87,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001234.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "10:15:32",
                "human_id": 17,
                "violation_type": "Без жилета",
                "confidence": 0.92,
                "camera_id": "rtsp://localhost:8554/stream2",
                "screenshot_path": "violations/frame_001235.jpg"
            },
            {
                "date": "2026-04-27",
                "time": "16:45:03",
                "human_id": 8,
                "violation_type": "Без перчаток",
                "confidence": 0.78,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001236.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "10:15:32",
                "human_id": 17,
                "violation_type": "Без жилета",
                "confidence": 0.92,
                "camera_id": "rtsp://localhost:8554/stream2",
                "screenshot_path": "violations/frame_001235.jpg"
            },
            {
                "date": "2026-04-27",
                "time": "16:45:03",
                "human_id": 8,
                "violation_type": "Без перчаток",
                "confidence": 0.78,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001236.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "14:22:18",
                "human_id": 42,
                "violation_type": "Без каски",
                "confidence": 0.87,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001234.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "10:15:32",
                "human_id": 17,
                "violation_type": "Без жилета",
                "confidence": 0.92,
                "camera_id": "rtsp://localhost:8554/stream2",
                "screenshot_path": "violations/frame_001235.jpg"
            },
            {
                "date": "2026-04-27",
                "time": "16:45:03",
                "human_id": 8,
                "violation_type": "Без перчаток",
                "confidence": 0.78,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001236.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "10:15:32",
                "human_id": 17,
                "violation_type": "Без жилета",
                "confidence": 0.92,
                "camera_id": "rtsp://localhost:8554/stream2",
                "screenshot_path": "violations/frame_001235.jpg"
            },
            {
                "date": "2026-04-27",
                "time": "16:45:03",
                "human_id": 8,
                "violation_type": "Без перчаток",
                "confidence": 0.78,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001236.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "14:22:18",
                "human_id": 42,
                "violation_type": "Без каски",
                "confidence": 0.87,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001234.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "10:15:32",
                "human_id": 17,
                "violation_type": "Без жилета",
                "confidence": 0.92,
                "camera_id": "rtsp://localhost:8554/stream2",
                "screenshot_path": "violations/frame_001235.jpg"
            },
            {
                "date": "2026-04-27",
                "time": "16:45:03",
                "human_id": 8,
                "violation_type": "Без перчаток",
                "confidence": 0.78,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001236.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "10:15:32",
                "human_id": 17,
                "violation_type": "Без жилета",
                "confidence": 0.92,
                "camera_id": "rtsp://localhost:8554/stream2",
                "screenshot_path": "violations/frame_001235.jpg"
            },
            {
                "date": "2026-04-27",
                "time": "16:45:03",
                "human_id": 8,
                "violation_type": "Без перчаток",
                "confidence": 0.78,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001236.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "14:22:18",
                "human_id": 42,
                "violation_type": "Без каски",
                "confidence": 0.87,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001234.jpg"
            },
            {
                "date": "2026-04-28",
                "time": "10:15:32",
                "human_id": 17,
                "violation_type": "Без жилета",
                "confidence": 0.92,
                "camera_id": "rtsp://localhost:8554/stream2",
                "screenshot_path": "violations/frame_001235.jpg"
            },
            {
                "date": "2026-04-27",
                "time": "16:45:03",
                "human_id": 8,
                "violation_type": "Без перчаток",
                "confidence": 0.78,
                "camera_id": "rtsp://localhost:8554/stream1",
                "screenshot_path": "violations/frame_001236.jpg"
            }
        ]

    def get_violations(self, limit=100, offset=0, **filters):
        result = self._violations[offset:offset + limit]
        return result

    def get_violations_count(self, **filters):
        return len(self._violations)