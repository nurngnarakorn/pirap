from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import Link, is_link_alive, DATABASE_URL
from datetime import datetime

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

def check_links():
    links = session.query(Link).all()
    for link in links:
        link.is_alive = is_link_alive(link.url)
        link.checked_at = datetime.now()
        session.commit()

if __name__ == "__main__":
    check_links()
