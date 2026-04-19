"""MySQL-DDL für die relationale Zieldatenhaltung von Mercator."""

MYSQL_SCHEMA_STATEMENTS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS companies (
        company_key VARCHAR(64) NOT NULL,
        company_cik VARCHAR(32) NULL UNIQUE,
        current_symbol VARCHAR(20) NULL,
        company_name VARCHAR(255) NULL,
        profile_status VARCHAR(32) NOT NULL DEFAULT 'NOT_REQUESTED',
        profile_reason VARCHAR(255) NULL,
        first_seen_at DATETIME NULL,
        last_seen_at DATETIME NULL,
        market_cap BIGINT NULL,
        price DECIMAL(18,4) NULL,
        currency VARCHAR(10) NULL,
        isin VARCHAR(32) NULL,
        cusip VARCHAR(32) NULL,
        exchange VARCHAR(64) NULL,
        exchange_full_name VARCHAR(128) NULL,
        industry VARCHAR(128) NULL,
        sector VARCHAR(128) NULL,
        sector_raw VARCHAR(128) NULL,
        sector_normalized VARCHAR(128) NULL,
        sector_source VARCHAR(64) NULL,
        sector_resolution_method VARCHAR(64) NULL,
        sector_resolution_status VARCHAR(32) NOT NULL DEFAULT 'UNRESOLVED',
        profile_enriched_at DATETIME NULL,
        profile_provider VARCHAR(64) NULL,
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
        source_system VARCHAR(32) NOT NULL DEFAULT 'fmp',
        trade_republic_universe_status VARCHAR(32) NOT NULL DEFAULT 'UNKNOWN',
        trade_republic_match_method VARCHAR(32) NOT NULL DEFAULT 'NONE',
        trade_republic_match_confidence VARCHAR(16) NOT NULL DEFAULT 'LOW',
        trade_republic_source_refreshed_at DATETIME NULL,
        trade_republic_reference_isin VARCHAR(32) NULL,
        trade_republic_reference_name VARCHAR(255) NULL,
        sync_version BIGINT NOT NULL DEFAULT 1,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (company_key),
        UNIQUE KEY uq_companies_current_symbol (current_symbol),
        INDEX idx_companies_current_symbol (current_symbol),
        INDEX idx_companies_sector (sector),
        INDEX idx_companies_country (country),
        INDEX idx_companies_exchange (exchange)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS insider_trades (
        id BIGINT NOT NULL AUTO_INCREMENT,
        company_key VARCHAR(64) NOT NULL,
        symbol_at_trade VARCHAR(20) NULL,
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
        validation_status VARCHAR(32) NOT NULL DEFAULT 'VALID',
        dashboard_valid BOOLEAN NOT NULL DEFAULT FALSE,
        gate_status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
        gate_reason VARCHAR(255) NULL,
        score DECIMAL(6,2) NULL,
        score_class CHAR(1) NULL,
        profile_status VARCHAR(32) NOT NULL DEFAULT 'NOT_REQUESTED',
        profile_reason VARCHAR(255) NULL,
        trade_republic_universe_status VARCHAR(32) NOT NULL DEFAULT 'UNKNOWN',
        trade_republic_match_method VARCHAR(32) NOT NULL DEFAULT 'NONE',
        trade_republic_match_confidence VARCHAR(16) NOT NULL DEFAULT 'LOW',
        trade_republic_source_refreshed_at DATETIME NULL,
        trade_republic_reference_isin VARCHAR(32) NULL,
        trade_republic_reference_name VARCHAR(255) NULL,
        source_url VARCHAR(512) NULL,
        dedupe_key CHAR(64) NOT NULL,
        fetched_at DATETIME NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        UNIQUE KEY uq_insider_trades_dedupe_key (dedupe_key),
        INDEX idx_insider_trades_company_key (company_key),
        INDEX idx_insider_trades_symbol_at_trade (symbol_at_trade),
        INDEX idx_insider_trades_filing_date (filing_date),
        INDEX idx_insider_trades_transaction_date (transaction_date),
        INDEX idx_insider_trades_gate_status (gate_status),
        CONSTRAINT fk_insider_trades_company_key
            FOREIGN KEY (company_key) REFERENCES companies(company_key)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS trade_republic_universe_reference (
        isin VARCHAR(32) NOT NULL,
        symbol VARCHAR(32) NULL,
        instrument_name VARCHAR(255) NULL,
        country VARCHAR(64) NULL,
        asset_class VARCHAR(64) NULL,
        source_url VARCHAR(512) NOT NULL,
        source_last_refreshed_at DATETIME NOT NULL,
        source_hash CHAR(64) NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (isin),
        INDEX idx_tr_universe_symbol (symbol)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS trade_republic_universe_meta (
        source_url VARCHAR(512) NOT NULL,
        source_last_refreshed_at DATETIME NULL,
        source_hash CHAR(64) NULL,
        instrument_count INT NOT NULL DEFAULT 0,
        last_error TEXT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (source_url)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS app_filter_settings (
        id BIGINT NOT NULL AUTO_INCREMENT,
        setting_scope VARCHAR(64) NOT NULL,
        setting_key VARCHAR(128) NOT NULL,
        setting_value_json JSON NOT NULL,
        source_system VARCHAR(32) NOT NULL DEFAULT 'app',
        sync_version BIGINT NOT NULL DEFAULT 1,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        UNIQUE KEY uq_app_filter_settings_scope_key (setting_scope, setting_key)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS app_runtime_preferences (
        id BIGINT NOT NULL AUTO_INCREMENT,
        preference_key VARCHAR(128) NOT NULL,
        preference_value_json JSON NOT NULL,
        source_system VARCHAR(32) NOT NULL DEFAULT 'app',
        sync_version BIGINT NOT NULL DEFAULT 1,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        UNIQUE KEY uq_app_runtime_preferences_key (preference_key)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS app_api_usage (
        day_key DATE NOT NULL,
        provider VARCHAR(32) NOT NULL,
        call_count INT NOT NULL DEFAULT 0,
        limit_count INT NOT NULL DEFAULT 250,
        last_request_at DATETIME NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (day_key, provider)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
]

# Offene Architekturpunkte sind zentral in ``docs/todos_offene_fragen.md`` dokumentiert.
