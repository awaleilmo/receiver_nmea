import logging
import os

os.makedirs("logs", exist_ok=True)

error_file_logger = logging.getLogger("AisErrorLogger")
error_file_logger.setLevel(logging.ERROR)

file_handler = logging.FileHandler("logs/error.log")
formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(formatter)

if not error_file_logger.handlers:
    error_file_logger.addHandler(file_handler)

error_file_logger.propagate = False
