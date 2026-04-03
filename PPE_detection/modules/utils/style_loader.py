import os


class StyleLoader:
    @staticmethod
    def load_stylesheet(qss_file_name):

        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        qss_path = os.path.join(project_root,  "..",'resources', 'styles', qss_file_name)
        with open(qss_path, 'r', encoding='utf-8') as f:
            return f.read()