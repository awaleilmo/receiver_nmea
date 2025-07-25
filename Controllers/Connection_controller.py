from sqlalchemy.orm import sessionmaker
from Models.__init__ import engine
from Models.Connection_model import ConnectionModel
import datetime

from Untils.logging_helper import sys_logger

Session = sessionmaker(bind=engine)
def save_connection(name, type, data_port, baudrate, protocol, network, address, port, active):
    session = Session()
    try:
        res = ConnectionModel(name=name, type=type, data_port=data_port, baudrate=baudrate, protocol=protocol, network=network, address=address, port=port, active=active)
        session.add(res)
        session.commit()
    except Exception as e:
        session.rollback()
        sys_logger.error(f"Error: {e}")
        raise e
    finally:
        session.close()

def update_connection(id, name, type, data_port, baudrate, protocol, network, address, port, active):
    session = Session()
    try:
        res = session.query(ConnectionModel).filter_by(id=id).first()
        res.name = name
        res.type = type
        res.data_port = data_port
        res.baudrate = baudrate
        res.protocol = protocol
        res.network = network
        res.address = address
        res.port = port
        res.active = active
        session.commit()
    except Exception as e:
        session.rollback()
        sys_logger.error(f"Error: {e}")
        raise e
    finally:
        session.close()

def get_connection():
    session = Session()
    try:
        res = session.query(ConnectionModel).all()
        return [{
            "id": con.id,
            "name": con.name,
            "type": con.type,
            "data_port": con.data_port,
            "baudrate": con.baudrate,
            "protocol": con.protocol,
            "network": con.network,
            "address": con.address,
            "port": con.port,
            "active": con.active
        } for con in res]
    except Exception as e:
        session.rollback()
        sys_logger.error(f"Error: {e}")
        raise e
    finally:
        session.close()

def update_connection_status(id, active):
    session = Session()
    try:
        res = session.query(ConnectionModel).filter_by(id=id).first()
        res.active = active
        session.commit()
    except Exception as e:
        session.rollback()
        sys_logger.error(f"Error: {e}")
        raise e
    finally:
        session.close()

def delete_connection(id):
    session = Session()
    try:
        res = session.query(ConnectionModel).filter_by(id=id).first()
        session.delete(res)
        session.commit()
    except Exception as e:
        session.rollback()
        sys_logger.error(f"Error: {e}")
        raise e
    finally:
        session.close()