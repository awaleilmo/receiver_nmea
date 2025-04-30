from sqlalchemy.orm import sessionmaker
from Models.__init__ import engine
from Models.Config_model import ConfigModel
import datetime

from Untils.logging_helper import sys_logger

Session = sessionmaker(bind=engine)

def update_config(api_server):
    session = Session()
    try:
        res = session.query(ConfigModel).first()
        if res is None:
            sys_logger.info("No configuration data found! Update skipped.")
            return

        res.api_server = api_server
        session.commit()
        sys_logger.info("Configuration updated successfully!")
    except Exception as e:
        session.rollback()
        sys_logger.error(f"Error: {e}")
        raise e
    finally:
        session.close()

def get_config():
    session = Session()
    try:
        res = session.query(ConfigModel).first()
        return {
            "id": res.id,
            "api_server": res.api_server
        }
    except Exception as e:
        session.rollback()
        sys_logger.error(f"Error: {e}")
        raise e
    finally:
        session.close()