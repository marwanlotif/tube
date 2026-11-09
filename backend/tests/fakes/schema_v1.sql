-- Schema written by create_all before migrations existed (stamped user_version=1).
CREATE TABLE downloads (
	id VARCHAR(36) NOT NULL,
	url TEXT NOT NULL,
	site VARCHAR(64),
	video_id VARCHAR(64),
	title TEXT,
	uploader TEXT,
	thumbnail_name VARCHAR(80),
	duration_s INTEGER,
	mode VARCHAR(16) NOT NULL,
	status VARCHAR(16) NOT NULL,
	format_label TEXT,
	format_selector TEXT,
	container VARCHAR(16),
	output_dir TEXT,
	output_path TEXT,
	temp_path TEXT,
	file_size INTEGER,
	downloaded_bytes INTEGER NOT NULL,
	total_bytes INTEGER,
	progress FLOAT NOT NULL,
	speed FLOAT,
	eta_s INTEGER,
	error_code VARCHAR(64),
	error_message TEXT,
	log_tail TEXT,
	attempts INTEGER NOT NULL,
	job_spec JSON NOT NULL,
	pid INTEGER,
	pid_started_ticks INTEGER,
	resumable BOOLEAN NOT NULL,
	created_at DATETIME NOT NULL,
	started_at DATETIME,
	finished_at DATETIME,
	PRIMARY KEY (id)
);
CREATE INDEX ix_downloads_status ON downloads (status);
CREATE INDEX ix_downloads_created ON downloads (created_at DESC);
CREATE TABLE settings (
	id INTEGER NOT NULL,
	data JSON NOT NULL,
	PRIMARY KEY (id)
);
