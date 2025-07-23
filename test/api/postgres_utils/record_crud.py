import logging
import datetime
from typing import Dict, List, Optional, Any
import yaml
from pathlib import Path
from pydantic import BaseModel

from sqlalchemy import create_engine, Column, Integer, String, Text, inspect
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

# Define paths for configuration files
BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config_postgres.yml"

class Settings(BaseModel):
    """
    Pydantic model for validating database configuration settings.
    
    Attributes:
        host (str): The database host address.
        port (int): The port number for the database.
        dbname (str): The name of the database.
        user (str): The database user.
        password (str): The database password.
    """
    host: str
    port: int
    dbname: str
    user: str
    password: str

def _load_settings(path: Path) -> Settings:
    """
    Load and validate configuration settings from a YAML file.
    
    This function reads the configuration file, validates its structure,
    and returns a Settings object with the parsed configuration.
    
    Args:
        path (Path): Path to the YAML configuration file
        
    Returns:
        Settings: Validated configuration settings object
        
    Raises:
        FileNotFoundError: If the configuration file doesn't exist
        ValueError: If the YAML format is invalid or required fields are missing
    """
    # Check if configuration file exists
    if not path.is_file():
        raise FileNotFoundError(
            f"Configuration file does not exist at: {path}\n"
            f"Please create a 'config_apiserver.yml' file in the project root directory and fill in the required settings."
        )
    try:
        # Read and parse YAML configuration file
        with open(path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        # Validate configuration using Pydantic model
        return Settings(**config_data)
    except yaml.YAMLError as e:
        raise ValueError(f"Configuration file '{path}' has invalid format: {e}")
    except Exception as e:
        raise ValueError(f"An error occurred while loading configuration file '{path}': {e}")

# Load configuration settings at startup
settings = _load_settings(CONFIG_PATH)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define the Base class for SQLAlchemy models
Base = declarative_base()

# Define the DialogRecord model
class DialogRecord(Base):
    """SQLAlchemy model for dialog_records table"""
    __tablename__ = 'dialog_records'
    
    timestamp = Column(Integer, primary_key=True, default=int(datetime.datetime.now().timestamp()))
    session_id = Column(String(20), nullable=False)
    user_id = Column(Integer, nullable=True)
    user_message = Column(Text)
    system_message = Column(Text)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the model instance to a dictionary"""
        return {
            'timestamp': self.timestamp,
            'id': self.user_id,
            'session_id': self.session_id,
            'user_message': self.user_message,
            'system_message': self.system_message,
        }

class RecordAPI:
    """
    A class to handle interactions with the records_dialog PostgreSQL database using SQLAlchemy ORM.
    
    This class provides methods to connect to the database and perform
    operations related to dialog records.
    """
    _instance = None  # Singleton instance

    def __new__(cls, *args, **kwargs):
        """
        Implementation of singleton pattern to ensure only one instance of RecordAPI exists.
        
        Returns:
            RecordAPI: The single instance of RecordAPI.
        """
        if not cls._instance:
            cls._instance = super(RecordAPI, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """
        Initialize the RecordAPI with database connection parameters.
        """
        self.host = settings.host
        self.port = settings.port
        self.dbname = settings.dbname
        self.user = settings.user
        self.password = settings.password
        self.engine = None
        self.db_session = None
        self.db_session = None
        
    def __connect(self) -> bool:
        """
        Establish a connection to the PostgreSQL database using SQLAlchemy.
        
        Returns:
            bool: True if connection is successful, False otherwise.
        """
        try:
            # Create the database URI for SQLAlchemy
            db_uri = f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}"
            
            # Create the SQLAlchemy engine
            self.engine = create_engine(db_uri, echo=False)
            
            # Create a session factory
            self.db_session = sessionmaker(bind=self.engine)

            # Initialize a session
            self.db_session = self.db_session()
            
            logger.info(f"Successfully connected to {self.dbname} database on {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            return False
    
    def __disconnect(self) -> None:
        """
        Close the database connection.
        """
        if self.db_session:
            self.db_session.close()
            logger.info("Database session closed")
            
    def __enter__(self):
        """
        Context manager entry point - connect to the database.
        
        Returns:
            RecordAPI: The instance itself.
        """
        self.__connect()
        return self
        
    def __exit__(self, exc_type, exc_value, traceback):
        """
        Context manager exit point - disconnect from the database.
        """
        self.__disconnect()

    def create_tables_if_not_exist(self) -> bool:
        """
        Create necessary tables if they don't exist in the database using SQLAlchemy models.
        
        Returns:
            bool: True if tables were created or already exist, False if there was an error.
        """
        try:
            # Check if the engine is created
            if not self.engine:
                if not self.__connect():
                    return False
            
            # Check if the dialog_records table was created
            inspector = inspect(self.engine)
            if 'dialog_records' in inspector.get_table_names():
                logger.info("Tables created or already exist")
                return True
            else:
                Base.metadata.create_all(self.engine)
                logger.info("Tables created successfully")
                return True
                
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            return False

    def store_dialog(self, user_id:int, session_id: str, user_message: str, system_message: str) -> Optional[int]:
        """
        Store a dialog exchange in the database using SQLAlchemy ORM.
        
        Args:
            user_id (int): The ID of the user associated with the dialog.
            session_id (str): Unique identifier for the conversation session.
            user_message (str): Message from the user.
            system_message (str): Response from the system.
                
        Returns:
            Optional[int]: The timestramp of the created record, or None if an error occurred.
        """
        try:
            if not self.db_session:
                if not self.__connect():
                    return None
            
            # Create a new DialogRecord object
            new_dialog = DialogRecord(
                timestamp=int(datetime.datetime.now().timestamp()),
                user_id=user_id,
                session_id=session_id,
                user_message=user_message,
                system_message=system_message
            )
            
            # Add to the session and commit
            self.db_session.add(new_dialog)
            self.db_session.commit()
            
            record_timestamp = new_dialog.timestamp
            logger.info(f"Dialog stored with Timestamp: {record_timestamp}")
            return record_timestamp
        
        except Exception as e:
            logger.error(f"Error storing dialog: {e}")
            if self.db_session:
                self.db_session.rollback()
            return None

    def get_records_by_userid(self, user_id: int) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve all dialog records associated with the specified user ID.

        Args:
            user_id (int): The ID of the user whose dialog records should be retrieved.

        Returns:
            Optional[List[Dict[str, Any]]]: A list of dialog records as dictionaries if found, None otherwise.

        Raises:
            Exception: Logs any exceptions that occur during the retrieval process.
        """
        try:
            if not self.db_session:
                if not self.__connect():
                    return None

            records = self.db_session.query(DialogRecord).filter(DialogRecord.user_id == user_id).all()

            if records:
                logger.info(f"Retrieved dialog records for user ID: {user_id}")
                return [record.to_dict() for record in records]
            else:
                logger.info(f"No dialog records found for user ID: {user_id}")
                return None

        except Exception as e:
            logger.error(f"Error retrieving dialog records: {e}")
            return None
    
    
    def delete_dialog_by_userid(self, user_id: int) -> bool:
        """
        Deletes a dialog record associated with the specified user ID from the database.
        Args:
            user_id (int): The ID of the user whose dialog record should be deleted.
        Returns:
            bool: True if the record was successfully deleted, False otherwise.
        Raises:
            Exception: Logs any exceptions that occur during the deletion process and rolls back the transaction.
        """
        try:
            if not self.db_session:
                if not self.__connect():
                    return False
            
            # Find the record to delete
            record = self.db_session.query(DialogRecord).filter(DialogRecord.user_id == user_id).first()
            
            if not record:
                logger.info(f"No dialog record found with ID: {user_id}")
                return False
            
            # Delete the record
            self.db_session.delete(record)
            self.db_session.commit()
            logger.info(f"Deleted dialog record with ID: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting dialog: {e}")
            if self.db_session:
                self.db_session.rollback()
            return False

# Example usage
if __name__ == "__main__":
    # Create an instance (password would typically come from environment variables)
    record_api = RecordAPI()
    
    # Use as a context manager to auto-connect/disconnect
    with record_api:
        # Ensure tables exist
        record_api.create_tables_if_not_exist()
        
        # Store a dialog
        session_id = "session-123"
        record_id = record_api.store_dialog(
            user_id=2,
            session_id=session_id,
            user_message="Hello, how can you help me.",
            system_message="I can answer questions and assist with various tasks.",
        )
        
        # Get a specific dialog
        dialogs = record_api.get_records_by_userid(2)
        for dialog in dialogs:
            if dialog:
                print(f"Retrieved dialog #{dialog['id']}: {dialog['user_message']}")
        