from sqlalchemy.orm import sessionmaker
from Models.__init__ import engine
from Models.Config_model import ConfigModel
import datetime

Session = sessionmaker(bind=engine)

def update_config(api_server):
    session = Session()
    try:
        res = session.query(ConfigModel).first()
        if res is None:
            print("No configuration data found! Update skipped.")
            return

        res.api_server = api_server
        session.commit()
        print("Configuration updated successfully!")
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
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
        print(f"Error: {e}")
        raise e
    finally:
        session.close()