"""MySQL-DDL für die relationale Zieldatenhaltung von FinanzPort Academic."""

MYSQL_SCHEMA_STATEMENTS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS companies (
        symbol VARCHAR(20) NOT NULL PRIMARY KEY,
        company_name VARCHAR(255) NULL,
        market_cap BIGINT NULL,
        price DECIMAL(18,4) NULL,
        currency VARCHAR(10) NULL,
        cik VARCHAR(32) NULL,
        isin VARCHAR(32) NULL,
        cusip VARCHAR(32) NULL,
        exchange VARCHAR(64) NULL,
        exchange_full_name VARCHAR(128) NULL,
        industry VARCHAR(128) NULL,
        sector VARCHAR(128) NULL,
        country VARCHAR(64) NULL,
        website VARCHAR(255) NULL,
        description TEXT NULL,
        ceo VARCHAR(255) NULL,
        full_time_employees VARCHAR(32) NULL,
        ipo_date DATE NULL,
        is_etf BOOLEAN NULL,
        is_actively_trading BOOLEAN NULL,
        is_adr BOOLEAN NULL,
        is_fund BOOLEAN NULL,
        profile_updated_at DATETIME NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_companies_sector (sector),
        INDEX idx_companies_country (country),
        INDEX idx_companies_exchange (exchange)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS insider_trades (
        id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        filing_date DATE NULL,
        transaction_date DATE NULL,
        reporting_cik VARCHAR(32) NULL,
        company_cik VARCHAR(32) NULL,
        reporting_name VARCHAR(255) NULL,
        type_of_owner VARCHAR(255) NULL,
        transaction_type VARCHAR(64) NULL,
        acquisition_or_disposition CHAR(1) NULL,
        direct_or_indirect CHAR(1) NULL,
        form_type VARCHAR(16) NULL,
        security_name VARCHAR(255) NULL,
        qty BIGINT NULL,
        price DECIMAL(18,4) NULL,
        trade_value_estimated DECIMAL(20,4) NULL,
        gate_status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
        source_url VARCHAR(512) NULL,
        dedupe_key CHAR(64) NOT NULL,
        fetched_at DATETIME NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_insider_trades_dedupe_key (dedupe_key),
        INDEX idx_insider_trades_symbol (symbol),
        INDEX idx_insider_trades_filing_date (filing_date),
        INDEX idx_insider_trades_transaction_date (transaction_date),
        INDEX idx_insider_trades_gate_status (gate_status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
]

# TODO: Bei wachsendem Projektumfang Migrationswerkzeug evaluieren statt direkter DDL-Initialisierung.
