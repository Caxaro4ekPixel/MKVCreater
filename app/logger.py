import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', filename='application.log',
                    filemode='w')

logging.getLogger().handlers.clear()
logging.getLogger().addHandler(logging.StreamHandler())
