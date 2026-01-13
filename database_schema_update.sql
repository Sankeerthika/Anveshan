-- Add event_type column if it doesn't exist
ALTER TABLE events
ADD COLUMN IF NOT EXISTS event_type VARCHAR(50) NOT NULL DEFAULT 'event' AFTER id;

-- Add new columns to events table
ALTER TABLE events
ADD COLUMN IF NOT EXISTS end_time DATETIME NULL AFTER start_time,
ADD COLUMN IF NOT EXISTS mode ENUM('online', 'offline', 'hybrid') NOT NULL DEFAULT 'offline' AFTER venue,
ADD COLUMN IF NOT EXISTS meeting_link VARCHAR(255) NULL AFTER venue,
ADD COLUMN IF NOT EXISTS registration_deadline DATETIME NULL AFTER end_time,
ADD COLUMN IF NOT EXISTS eligibility TEXT NULL AFTER registration_deadline,
ADD COLUMN IF NOT EXISTS registration_fee DECIMAL(10,2) DEFAULT 0.00 AFTER eligibility,
ADD COLUMN IF NOT EXISTS poster_path VARCHAR(255) NULL AFTER registration_fee,
ADD COLUMN IF NOT EXISTS max_team_size INT DEFAULT 1 AFTER registration_fee,
ADD COLUMN IF NOT EXISTS min_team_size INT DEFAULT 1 AFTER registration_fee,
ADD COLUMN IF NOT EXISTS is_team_event BOOLEAN DEFAULT FALSE AFTER registration_fee,
ADD COLUMN IF NOT EXISTS discount_percentage DECIMAL(5,2) DEFAULT 0.00 AFTER registration_fee,
ADD COLUMN IF NOT EXISTS discount_description VARCHAR(255) NULL AFTER discount_percentage;

-- Create teams table if it doesn't exist
CREATE TABLE IF NOT EXISTS teams (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    leader_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY (leader_id) REFERENCES students(id) ON DELETE CASCADE
);

-- Create team_members table if it doesn't exist
CREATE TABLE IF NOT EXISTS team_members (
    id INT AUTO_INCREMENT PRIMARY KEY,
    team_id INT NOT NULL,
    student_id INT NOT NULL,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    UNIQUE KEY unique_team_member (team_id, student_id)
);

-- Add index on event_type for better performance
CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_created_by ON events(created_by);
