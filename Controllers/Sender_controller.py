from sqlalchemy.orm import sessionmaker
from Models.__init__ import engine
from Models.Sender_model import SenderModel
import datetime

Session = sessionmaker(bind=engine)


def get_sender():
    session = Session()
    try:
        data = session.query(SenderModel).all()
        return [{
            "id": res.id,
            "name": res.name,
            "host": res.host,
            "port": res.port,
            "network": res.network,
            "last_send_id": res.last_send_id,
            "active": res.active
        } for res in data]
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        raise e
    finally:
        session.close()


def update_sender(identity, name, host, port, network, active):
    session = Session()
    try:
        res = session.query(SenderModel).filter_by(id=identity).first()
        if res is None:
            print("No sender data found! Update skipped.")
            return

        res.name = name
        res.host = host
        res.port = port
        res.network = network
        res.active = active
        session.commit()
        print("Sender updated successfully!")
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        raise e
    finally:
        session.close()

def add_sender(name, host, port, network, active):
    session = Session()
    try:
        new_sender = SenderModel(name=name, host=host, port=port, network=network, active=active)
        session.add(new_sender)
        session.commit()
        print("Sender added successfully!")
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        raise e
    finally:
        session.close()

def remove_sender(identity):
    session = Session()
    try:
        res = session.query(SenderModel).filter_by(id=identity).first()
        session.delete(res)
        session.commit()
        print("Sender removed successfully!")
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        raise e
    finally:
        session.close()

def update_sender_status(identity, active):
    session = Session()
    try:
        res = session.query(SenderModel).filter_by(id=identity).first()
        if res is None:
            print("No sender data found! Update skipped.")
            return

        res.active = active
        session.commit()
        print("Sender status updated successfully!")
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        raise e
    finally:
        session.close()

def update_sender_last_send_id(identity, last_send_id):
    session = Session()
    try:
        res = session.query(SenderModel).filter_by(id=identity).first()
        if res is None:
            print("No sender data found! Update skipped.")
            return

        res.last_send_id = last_send_id
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        raise e
    finally:
        session.close()