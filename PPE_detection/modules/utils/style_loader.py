import os

class StyleLoader:
    @staticmethod
    def load_stylesheet(qss_file_name):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root = current_dir
        while root:
            if os.path.exists(os.path.join(root, 'resources', 'styles')):
                break
            parent = os.path.dirname(root)
            if parent == root:
                root = None
                break
            root = parent

        if root is None:
            root = os.path.dirname(os.path.dirname(current_dir))

        qss_path = os.path.join(root, 'resources', 'styles', qss_file_name)
        if not os.path.exists(qss_path):
            raise FileNotFoundError(f"Style file not found: {qss_path}")

        with open(qss_path, 'r', encoding='utf-8') as f:
            return f.read()
