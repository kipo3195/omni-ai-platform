CREATE TABLE IF NOT EXISTS returned_message_topics_execution (
    tenant_id VARCHAR(191) NOT NULL,
    execution_id VARCHAR(191) NOT NULL,
    request_id VARCHAR(191) NOT NULL,
    request_payload LONGTEXT NOT NULL,
    request_fingerprint CHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL,
    result_payload LONGTEXT NULL,
    error_payload LONGTEXT NULL,
    worker_owner VARCHAR(64) NULL,
    lease_until DOUBLE NULL,
    accepted_at DOUBLE NULL,
    started_at DOUBLE NULL,
    completed_at DOUBLE NULL,
    created_at DOUBLE NOT NULL,
    updated_at DOUBLE NOT NULL,
    PRIMARY KEY (tenant_id, execution_id),
    KEY idx_rmt_execution_status (status, lease_until, updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS returned_message_topics_callback_outbox (
    event_id CHAR(36) NOT NULL,
    tenant_id VARCHAR(191) NOT NULL,
    execution_id VARCHAR(191) NOT NULL,
    request_id VARCHAR(191) NOT NULL,
    payload LONGTEXT NOT NULL,
    status VARCHAR(32) NOT NULL,
    attempt_count INT NOT NULL,
    next_attempt_at DOUBLE NOT NULL,
    worker_owner VARCHAR(64) NULL,
    lease_until DOUBLE NULL,
    last_error VARCHAR(500) NULL,
    created_at DOUBLE NOT NULL,
    delivered_at DOUBLE NULL,
    updated_at DOUBLE NOT NULL,
    PRIMARY KEY (event_id),
    KEY idx_rmt_outbox_due (status, next_attempt_at, lease_until),
    CONSTRAINT fk_rmt_callback_execution
        FOREIGN KEY (tenant_id, execution_id)
        REFERENCES returned_message_topics_execution (tenant_id, execution_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
