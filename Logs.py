import logging

class Logger:
    def __init__(self, logger_name, log_file, level=logging.INFO):
        # 1. Get a logger with a UNIQUE name. 
        # If you use the same name, you get the same logger.
        self.logger = logging.getLogger(logger_name)
        
        # Prevent logs from propagating to the root logger (duplicates in console)
        self.logger.propagate = False
        self.logger.setLevel(level)

        # Clear existing handlers if this logger was already set up 
        # (Prevents duplicate lines if you instantiate the class twice)
        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        # 2. Create handler with mode='w'
        # mode='w' overwrites the file (Refresh every run)
        # mode='a' appends to the file (Keep history)
        handler = logging.FileHandler(log_file, mode='w')        
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))

        # 3. Add handler to logger
        self.logger.addHandler(handler)
    
    def get_logger(self):
        return self.logger