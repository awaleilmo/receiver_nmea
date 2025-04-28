import logging
import os

os.makedirs("logs", exist_ok=True)

error_file_logger = logging.getLogger("AisErrorLogger")
error_file_logger.setLevel(logging.ERROR)
info_file_logger = logging.getLogger("AisInfoLogger")
info_file_logger.setLevel(logging.INFO)
def fileHandler(name, classes):
    file_handler = logging.FileHandler(f"logs/{name}.log",encoding = 'utf-8')
    formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(formatter)
    classes.addHandler(file_handler)

if not error_file_logger.handlers:
    fileHandler("error", error_file_logger)

if not info_file_logger.handlers:
    fileHandler("info", info_file_logger)


error_file_logger.propagate = False


