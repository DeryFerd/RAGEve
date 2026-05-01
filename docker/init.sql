-- Initialize RAGEve database user
-- This script runs when the MySQL container first starts

-- Create the application user if it doesn't exist
CREATE USER IF NOT EXISTS 'rageve'@'%' IDENTIFIED BY 'rageve_password';
CREATE USER IF NOT EXISTS 'rageve'@'localhost' IDENTIFIED BY 'rageve_password';
CREATE USER IF NOT EXISTS 'rageve'@'127.0.0.1' IDENTIFIED BY 'rageve_password';

-- Grant all privileges on the rageve database to the application user
GRANT ALL PRIVILEGES ON `rageve`.* TO 'rageve'@'%';
GRANT ALL PRIVILEGES ON `rageve`.* TO 'rageve'@'localhost';
GRANT ALL PRIVILEGES ON `rageve`.* TO 'rageve'@'127.0.0.1';

-- Also grant privileges on the database that may have been created with a different name during initial setup
GRANT ALL PRIVILEGES ON `rag_flow`.* TO 'rageve'@'%';
GRANT ALL PRIVILEGES ON `rag_flow`.* TO 'rageve'@'localhost';
GRANT ALL PRIVILEGES ON `rag_flow`.* TO 'rageve'@'127.0.0.1';

FLUSH PRIVILEGES;
