from __future__ import annotations

from alembic import op


revision = "0001_multi_family_foundation"
down_revision = None
branch_labels = None
depends_on = None


DDL = [
    "CREATE EXTENSION IF NOT EXISTS pgcrypto",
    "CREATE EXTENSION IF NOT EXISTS citext",
    """
    CREATE TABLE IF NOT EXISTS users (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        email citext UNIQUE NOT NULL,
        password_hash text NOT NULL,
        display_name text,
        status text NOT NULL DEFAULT 'active',
        password_changed_at timestamptz,
        last_login_at timestamptz,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS user_identities (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        provider text NOT NULL,
        provider_subject text,
        provider_email citext,
        metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
        created_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_user_identities_provider_subject
        ON user_identities (provider, provider_subject)
        WHERE provider_subject IS NOT NULL
    """,
    """
    CREATE TABLE IF NOT EXISTS families (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        name text NOT NULL,
        slug text UNIQUE NOT NULL,
        status text NOT NULL DEFAULT 'active',
        default_currency text NOT NULL DEFAULT 'BRL',
        timezone text NOT NULL DEFAULT 'America/Sao_Paulo',
        created_by_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS family_members (
        family_id uuid NOT NULL REFERENCES families(id) ON DELETE CASCADE,
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        role text NOT NULL,
        status text NOT NULL DEFAULT 'active',
        joined_at timestamptz NOT NULL DEFAULT now(),
        invited_by_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
        PRIMARY KEY (family_id, user_id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_family_members_user_family
        ON family_members (user_id, family_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS family_people (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        family_id uuid NOT NULL REFERENCES families(id) ON DELETE CASCADE,
        linked_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
        display_name text NOT NULL,
        legal_name text,
        document_hash text,
        document_last4 text,
        aliases_json jsonb NOT NULL DEFAULT '[]'::jsonb,
        status text NOT NULL DEFAULT 'active',
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS ux_family_people_family_linked_user
        ON family_people (family_id, linked_user_id)
        WHERE linked_user_id IS NOT NULL
    """,
    """
    CREATE TABLE IF NOT EXISTS sessions (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        active_family_id uuid REFERENCES families(id) ON DELETE SET NULL,
        token_hash text UNIQUE NOT NULL,
        csrf_token_hash text,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        expires_at timestamptz NOT NULL,
        rotated_at timestamptz,
        revoked_at timestamptz,
        ip_hash text,
        user_agent_hash text
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_sessions_token_hash
        ON sessions (token_hash)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_sessions_user_active
        ON sessions (user_id, active_family_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS login_attempts (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid REFERENCES users(id) ON DELETE SET NULL,
        normalized_email_hash text,
        ip_hash text,
        user_agent_hash text,
        success boolean NOT NULL DEFAULT false,
        failure_reason text,
        created_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_login_attempts_email_created
        ON login_attempts (normalized_email_hash, created_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_login_attempts_ip_created
        ON login_attempts (ip_hash, created_at DESC)
    """,
    """
    CREATE TABLE IF NOT EXISTS user_security_state (
        user_id uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        failed_login_count integer NOT NULL DEFAULT 0,
        last_failed_login_at timestamptz,
        locked_until timestamptz,
        password_reset_required boolean NOT NULL DEFAULT false,
        updated_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS provider_connections (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        family_id uuid NOT NULL REFERENCES families(id) ON DELETE CASCADE,
        provider text NOT NULL,
        external_item_id text,
        connector_id text,
        connector_name text,
        status text NOT NULL DEFAULT 'active',
        client_user_id text,
        owner_person_id uuid REFERENCES family_people(id) ON DELETE SET NULL,
        last_synced_at timestamptz,
        consent_expires_at timestamptz,
        metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_provider_connections_family_provider_item
        ON provider_connections (family_id, provider, external_item_id)
        WHERE external_item_id IS NOT NULL
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_provider_connections_family_provider_item
        ON provider_connections (family_id, provider, external_item_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS accounts (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        family_id uuid NOT NULL REFERENCES families(id) ON DELETE CASCADE,
        connection_id uuid REFERENCES provider_connections(id) ON DELETE SET NULL,
        source text NOT NULL,
        external_account_id text,
        institution text,
        name text NOT NULL,
        type text NOT NULL,
        subtype text,
        currency text NOT NULL DEFAULT 'BRL',
        last4 text,
        status text NOT NULL DEFAULT 'active',
        metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_accounts_family_source_external
        ON accounts (family_id, source, external_account_id)
        WHERE external_account_id IS NOT NULL
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_accounts_family_source_external
        ON accounts (family_id, source, external_account_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_accounts_family_connection
        ON accounts (family_id, connection_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS account_people (
        account_id uuid NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
        person_id uuid NOT NULL REFERENCES family_people(id) ON DELETE CASCADE,
        relationship text NOT NULL,
        source text NOT NULL,
        confidence real,
        created_at timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (account_id, person_id, relationship)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tags (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        family_id uuid NOT NULL REFERENCES families(id) ON DELETE CASCADE,
        name text NOT NULL,
        color text,
        created_at timestamptz NOT NULL DEFAULT now(),
        UNIQUE (family_id, name),
        UNIQUE (family_id, id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS budget_buckets (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        family_id uuid NOT NULL REFERENCES families(id) ON DELETE CASCADE,
        key text NOT NULL,
        name text NOT NULL,
        color text,
        planned_kind text,
        planned_value numeric(14,2),
        sort_order integer NOT NULL DEFAULT 0,
        is_system boolean NOT NULL DEFAULT false,
        UNIQUE (family_id, key),
        UNIQUE (family_id, id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS savings_goals (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        family_id uuid NOT NULL REFERENCES families(id) ON DELETE CASCADE,
        name text NOT NULL,
        target_amount numeric(14,2) NOT NULL,
        term_months integer,
        saved_amount numeric(14,2) NOT NULL DEFAULT 0,
        priority integer NOT NULL DEFAULT 0,
        status text NOT NULL DEFAULT 'active',
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        UNIQUE (family_id, id)
    )
    """,
    # Legacy imported transaction IDs remain deterministic text for deduplication.
    """
    CREATE TABLE IF NOT EXISTS transactions (
        id text PRIMARY KEY,
        family_id uuid NOT NULL REFERENCES families(id) ON DELETE CASCADE,
        account_id uuid NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
        connection_id uuid REFERENCES provider_connections(id) ON DELETE SET NULL,
        external_id text,
        posted_at date NOT NULL,
        reference_month date NOT NULL,
        amount numeric(14,2) NOT NULL,
        currency text NOT NULL DEFAULT 'BRL',
        description text NOT NULL,
        raw_description text,
        category text,
        category_source text,
        tag_id uuid,
        bucket_id uuid,
        savings_goal_id uuid,
        hidden boolean NOT NULL DEFAULT false,
        note text,
        counterparty_name text,
        counterparty_document_hash text,
        merchant_key text,
        source text NOT NULL,
        metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
        created_at timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY (family_id, tag_id) REFERENCES tags(family_id, id),
        FOREIGN KEY (family_id, bucket_id) REFERENCES budget_buckets(family_id, id),
        FOREIGN KEY (family_id, savings_goal_id) REFERENCES savings_goals(family_id, id)
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_transactions_family_source_external
        ON transactions (family_id, source, external_id)
        WHERE external_id IS NOT NULL
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_transactions_family_account_posted
        ON transactions (family_id, account_id, posted_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_transactions_family_reference_month
        ON transactions (family_id, reference_month)
    """,
    """
    CREATE TABLE IF NOT EXISTS transaction_links (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        family_id uuid NOT NULL REFERENCES families(id) ON DELETE CASCADE,
        source_transaction_id text NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
        target_transaction_id text NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
        link_type text NOT NULL,
        confidence real,
        source text NOT NULL,
        metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
        created_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_transaction_links_family_source
        ON transaction_links (family_id, source_transaction_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_transaction_links_family_target
        ON transaction_links (family_id, target_transaction_id)
    """,
]


DROP_TABLES = [
    "transaction_links",
    "transactions",
    "savings_goals",
    "budget_buckets",
    "tags",
    "account_people",
    "accounts",
    "provider_connections",
    "user_security_state",
    "login_attempts",
    "sessions",
    "family_people",
    "family_members",
    "families",
    "user_identities",
    "users",
]


def upgrade() -> None:
    for statement in DDL:
        op.execute(statement)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_family_people_family_linked_user")
    for table in DROP_TABLES:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
