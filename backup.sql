BEGIN;

CREATE TABLE usuario (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    senha TEXT NOT NULL
);

CREATE TABLE webhook_logs (
    id SERIAL PRIMARY KEY,
    payload TEXT,
    recebido_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE assinatura (
    id SERIAL PRIMARY KEY,
    preapproval_id TEXT,
    status TEXT,
    data_inicio TEXT,
    data_expiracao TEXT,
    username TEXT,
    email TEXT,
    senha TEXT,
    telefone TEXT,
    cpf TEXT,
    data_nascimento TEXT,
    stripe_subscription_id TEXT,
    mercado_pago_id TEXT
);

COMMIT;
