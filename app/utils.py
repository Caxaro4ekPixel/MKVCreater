import os
import logging


def get_font_files(font_directory):
    font_files = []
    for root, dirs, files in os.walk(font_directory):
        for file in files:
            if file.lower().endswith(('.ttf', '.otf')):
                logging.info(f"Обнаружены: {os.path.join(root, file)}")
                font_files.append(os.path.join(root, file))
    return font_files
