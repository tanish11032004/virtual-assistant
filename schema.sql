CREATE TABLE IF NOT EXISTS activity_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    activity VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'complete',
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_user_activity ON activity_logs(user_id, created_at);

-- Add indexes for frequently accessed columns
CREATE INDEX idx_username ON users(username);
CREATE INDEX idx_email ON users(email);
CREATE INDEX idx_notes_user ON notes(user_id);

-- Optimize table structure
ALTER TABLE users ROW_FORMAT=DYNAMIC;
ALTER TABLE activity_logs ROW_FORMAT=DYNAMIC;
ALTER TABLE notes ROW_FORMAT=DYNAMIC;

-- Add partitioning for large tables
ALTER TABLE activity_logs
PARTITION BY RANGE (UNIX_TIMESTAMP(created_at)) (
    PARTITION p_2023 VALUES LESS THAN (UNIX_TIMESTAMP('2024-01-01 00:00:00')),
    PARTITION p_2024 VALUES LESS THAN (UNIX_TIMESTAMP('2025-01-01 00:00:00')),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);
