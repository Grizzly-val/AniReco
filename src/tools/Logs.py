import logging
import os

from pathlib import Path



class Logger:
    def __init__(self, logger_name, log_file, level=logging.INFO):

        # 1. Get the directory where this script sits
        # This turns "relative" into "absolute" automatically
        base_dir = Path(__file__).resolve().parent.parent.parent
        log_folder = base_dir / "logs"

        # 2. Create the /logs folder if it isn't there
        # exist_ok=True prevents an error if the folder already exists
        log_folder.mkdir(parents=True, exist_ok=True)
        
        # 3. Create the full path to the file
        log_path = log_folder / log_file

        self.logger = logging.getLogger(logger_name)
        self.logger.propagate = False
        self.logger.setLevel(level)

        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        # FileHandler accepts the Path object directly!
        handler = logging.FileHandler(log_path, mode='w')        
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))

        self.logger.addHandler(handler) 
    
    def get_logger(self):
        return self.logger