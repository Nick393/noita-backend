import os
import pyodbc
from typing import Optional
from PIL import Image
import io
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Azure SQL Database connection configuration
# these should be set as environment variables for security
DB_SERVER = os.getenv('AZURE_DB_SERVER')  
DB_NAME = os.getenv('AZURE_DB_NAME')      
DB_USER = os.getenv('AZURE_DB_USER')      
DB_PASSWORD = os.getenv('AZURE_DB_PASSWORD')  
DB_DRIVER = '{ODBC Driver 18 for SQL Server}' 

def get_connection():
    """
    Create and return a connection to Azure SQL Database.
    """
    connection_string = (
        f'DRIVER={DB_DRIVER};'
        f'SERVER={DB_SERVER};'
        f'DATABASE={DB_NAME};'
        f'UID={DB_USER};'
        f'PWD={DB_PASSWORD};'
        f'Encrypt=yes;'
        f'TrustServerCertificate=no;'
        f'Connection Timeout=30;'
    )
    return pyodbc.connect(connection_string)


def initialize_database():
    """
    Create necessary tables if they don't exist.
    Run this once when setting up your database.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # create camera_positions table
    cursor.execute('''
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='camera_positions' AND xtype='U')
        CREATE TABLE camera_positions (
            game_id VARCHAR(255) PRIMARY KEY,
            camera_x FLOAT NOT NULL,
            camera_y FLOAT NOT NULL,
            last_updated DATETIME DEFAULT GETDATE()
        )
    ''')

    # create terrain_images table
    cursor.execute('''
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='terrain_images' AND xtype='U')
        CREATE TABLE terrain_images (
            game_id VARCHAR(255) PRIMARY KEY,
            image_data VARBINARY(MAX) NOT NULL,
            last_updated DATETIME DEFAULT GETDATE()
        )
    ''')

    conn.commit()
    cursor.close()
    conn.close()
    print("Database initialized successfully!")


def update_camera_position(game_id: str, camera_x: float, camera_y: float) -> bool:
    """
    Save or update camera position for a given game_id.

    Args:
        game_id: Unique identifier for the game session
        camera_x: X coordinate of the camera
        camera_y: Y coordinate of the camera

    Returns:
        True if successful, False otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # use MERGE to insert or update
        cursor.execute('''
            MERGE camera_positions AS target
            USING (SELECT ? AS game_id, ? AS camera_x, ? AS camera_y) AS source
            ON target.game_id = source.game_id
            WHEN MATCHED THEN
                UPDATE SET camera_x = source.camera_x,
                          camera_y = source.camera_y,
                          last_updated = GETDATE()
            WHEN NOT MATCHED THEN
                INSERT (game_id, camera_x, camera_y)
                VALUES (source.game_id, source.camera_x, source.camera_y);
        ''', (game_id, camera_x, camera_y))

        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating camera position: {e}")
        return False


def get_camera_info(game_id: str) -> Optional[dict]:
    """
    Retrieve camera position for a given game_id.

    Args:
        game_id: Unique identifier for the game session

    Returns:
        Dictionary with 'x' and 'y' coordinates, or None if not found
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT camera_x, camera_y FROM camera_positions
            WHERE game_id = ?
        ''', (game_id,))

        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row:
            return {'x': row[0], 'y': row[1]}
        return None
    except Exception as e:
        print(f"Error getting camera info: {e}")
        return None


def save_image(game_id: str, image: Image.Image) -> bool:
    """
    Save a PIL Image to the database for a given game_id.

    Args:
        game_id: Unique identifier for the game session
        image: PIL Image object to save

    Returns:
        True if successful, False otherwise
    """
    try:
        # convert PIL Image to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_bytes = img_byte_arr.getvalue()

        conn = get_connection()
        cursor = conn.cursor()

        # use MERGE to insert or update
        cursor.execute('''
            MERGE terrain_images AS target
            USING (SELECT ? AS game_id, ? AS image_data) AS source
            ON target.game_id = source.game_id
            WHEN MATCHED THEN
                UPDATE SET image_data = source.image_data,
                          last_updated = GETDATE()
            WHEN NOT MATCHED THEN
                INSERT (game_id, image_data)
                VALUES (source.game_id, source.image_data);
        ''', (game_id, img_bytes))

        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving image: {e}")
        return False


def get_image(game_id: str) -> Optional[Image.Image]:
    """
    retrieve a PIL Image from the database for a given game_id.

    Args:
        game_id: Unique identifier for the game session

    Returns:
        PIL Image object, or None if not found
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT image_data FROM terrain_images
            WHERE game_id = ?
        ''', (game_id,))

        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row and row[0]:
            img_bytes = io.BytesIO(row[0])
            return Image.open(img_bytes)
        return None
    except Exception as e:
        print(f"Error getting image: {e}")
        return None


def game_id_exists(game_id: str) -> bool:
    """
    check if a game_id exists in the database.

    Args:
        game_id: Unique identifier for the game session

    Returns:
        True if exists, False otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT COUNT(*) FROM camera_positions
            WHERE game_id = ?
        ''', (game_id,))

        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        return count > 0
    except Exception as e:
        print(f"Error checking game_id: {e}")
        return False
