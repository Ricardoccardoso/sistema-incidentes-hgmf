-- Migração para atualizar o esquema de incidentes e criar as flags de obrigatoriedade

-- 1) Criar tabela de flags de campo se ainda não existir
CREATE TABLE IF NOT EXISTS config_campos (
    id BIGSERIAL PRIMARY KEY,
    "Campo" TEXT UNIQUE NOT NULL,
    "Obrigatorio" BOOLEAN NOT NULL DEFAULT FALSE
);

-- 1b) Criar tabelas de configuração por menu para manter IDs isolados por área
CREATE TABLE IF NOT EXISTS config_turno (
    id BIGSERIAL PRIMARY KEY,
    "Opcao" TEXT UNIQUE NOT NULL,
    "Ativo" BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE TABLE IF NOT EXISTS config_tipo_geral (
    id BIGSERIAL PRIMARY KEY,
    "Opcao" TEXT UNIQUE NOT NULL,
    "Ativo" BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE TABLE IF NOT EXISTS config_setor (
    id BIGSERIAL PRIMARY KEY,
    "Opcao" TEXT UNIQUE NOT NULL,
    "Ativo" BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE TABLE IF NOT EXISTS config_categoria (
    id BIGSERIAL PRIMARY KEY,
    "Opcao" TEXT UNIQUE NOT NULL,
    "Ativo" BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE TABLE IF NOT EXISTS config_subcategoria_lpp (
    id BIGSERIAL PRIMARY KEY,
    "Opcao" TEXT UNIQUE NOT NULL,
    "Ativo" BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE TABLE IF NOT EXISTS config_subcategoria_queda (
    id BIGSERIAL PRIMARY KEY,
    "Opcao" TEXT UNIQUE NOT NULL,
    "Ativo" BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE TABLE IF NOT EXISTS config_subcategoria_med (
    id BIGSERIAL PRIMARY KEY,
    "Opcao" TEXT UNIQUE NOT NULL,
    "Ativo" BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE TABLE IF NOT EXISTS config_gravidade (
    id BIGSERIAL PRIMARY KEY,
    "Opcao" TEXT UNIQUE NOT NULL,
    "Ativo" BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE TABLE IF NOT EXISTS config_fator_causador (
    id BIGSERIAL PRIMARY KEY,
    "Opcao" TEXT UNIQUE NOT NULL,
    "Ativo" BOOLEAN NOT NULL DEFAULT TRUE
);

-- 1c) Migrar dados do modelo antigo `config_tabelas`, se existir
CREATE TABLE IF NOT EXISTS config_tabelas (
    id BIGSERIAL PRIMARY KEY,
    "Tabela" TEXT,
    "Opcao" TEXT,
    "Ativo" BOOLEAN
);

INSERT INTO config_turno ("Opcao", "Ativo")
SELECT "Opcao", "Ativo"
FROM config_tabelas
WHERE "Tabela" = 'Turno'
ON CONFLICT ("Opcao") DO NOTHING;

INSERT INTO config_tipo_geral ("Opcao", "Ativo")
SELECT "Opcao", "Ativo"
FROM config_tabelas
WHERE "Tabela" = 'Tipo Geral'
ON CONFLICT ("Opcao") DO NOTHING;

INSERT INTO config_setor ("Opcao", "Ativo")
SELECT "Opcao", "Ativo"
FROM config_tabelas
WHERE "Tabela" = 'Setor'
ON CONFLICT ("Opcao") DO NOTHING;

INSERT INTO config_categoria ("Opcao", "Ativo")
SELECT "Opcao", "Ativo"
FROM config_tabelas
WHERE "Tabela" = 'Categoria'
ON CONFLICT ("Opcao") DO NOTHING;

INSERT INTO config_subcategoria_lpp ("Opcao", "Ativo")
SELECT "Opcao", "Ativo"
FROM config_tabelas
WHERE "Tabela" = 'Subcategoria_LPP'
ON CONFLICT ("Opcao") DO NOTHING;

INSERT INTO config_subcategoria_queda ("Opcao", "Ativo")
SELECT "Opcao", "Ativo"
FROM config_tabelas
WHERE "Tabela" = 'Subcategoria_Queda'
ON CONFLICT ("Opcao") DO NOTHING;

INSERT INTO config_subcategoria_med ("Opcao", "Ativo")
SELECT "Opcao", "Ativo"
FROM config_tabelas
WHERE "Tabela" = 'Subcategoria_Med'
ON CONFLICT ("Opcao") DO NOTHING;

INSERT INTO config_gravidade ("Opcao", "Ativo")
SELECT "Opcao", "Ativo"
FROM config_tabelas
WHERE "Tabela" = 'Gravidade'
ON CONFLICT ("Opcao") DO NOTHING;

INSERT INTO config_fator_causador ("Opcao", "Ativo")
SELECT "Opcao", "Ativo"
FROM config_tabelas
WHERE "Tabela" = 'Fator Causador'
ON CONFLICT ("Opcao") DO NOTHING;

-- 1d) Criar tabela básica de incidentes se ainda não existir
CREATE TABLE IF NOT EXISTS incidentes (
    id BIGSERIAL PRIMARY KEY,
    "Data_Registro" TIMESTAMP,
    "Data_Incidente" DATE,
    "Turno" TEXT,
    "Setor" TEXT,
    "Leito" TEXT,
    "Tipo_Geral" TEXT,
    "Categoria_Incidente" TEXT,
    "Subcategoria" TEXT,
    "Medicamento_Envolvido" TEXT,
    "Gravidade" TEXT,
    "Fatores_Causadores" TEXT,
    "Descricao" TEXT,
    "Acoes_Imediatas" TEXT,
    "Sugestao_Melhoria" TEXT,
    "Data_Relato" DATE,
    "Hora_Relato" TEXT,
    "Nome_Paciente" TEXT,
    "Data_Nascimento" DATE,
    "Relator" TEXT,
    "Funcao_Relator" TEXT,
    "Status" TEXT
);

-- 2) Criar os novos campos na tabela incidentes
ALTER TABLE incidentes ADD COLUMN IF NOT EXISTS "Leito" TEXT;
ALTER TABLE incidentes ADD COLUMN IF NOT EXISTS "Data_Relato" DATE;
ALTER TABLE incidentes ADD COLUMN IF NOT EXISTS "Hora_Relato" TEXT;
ALTER TABLE incidentes ADD COLUMN IF NOT EXISTS "Nome_Paciente" TEXT;
ALTER TABLE incidentes ADD COLUMN IF NOT EXISTS "Data_Nascimento" DATE;

-- 3) Renomear coluna Cama_Leito para Leito se existir
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'incidentes' AND column_name = 'Cama_Leito'
    ) THEN
        EXECUTE 'ALTER TABLE incidentes RENAME COLUMN "Cama_Leito" TO "Leito"';
    END IF;
END$$ LANGUAGE plpgsql;

-- 4) Remover colunas legadas que não são mais usadas pelo formulário
ALTER TABLE incidentes DROP COLUMN IF EXISTS "Hora_Aproximada";
ALTER TABLE incidentes DROP COLUMN IF EXISTS "Dano_Paciente";
ALTER TABLE incidentes DROP COLUMN IF EXISTS "Paciente_Foi_Comunicado";
ALTER TABLE incidentes DROP COLUMN IF EXISTS "Familiar_Foi_Comunicado";
ALTER TABLE incidentes DROP COLUMN IF EXISTS "Medico_Foi_Comunicado";

-- 5) Sementes iniciais para a tabela de flags de campos
INSERT INTO config_campos ("Campo", "Obrigatorio")
VALUES
    ('Data_Registro', FALSE),
    ('Data_Incidente', FALSE),
    ('Turno', FALSE),
    ('Setor', FALSE),
    ('Leito', FALSE),
    ('Tipo_Geral', FALSE),
    ('Categoria_Incidente', FALSE),
    ('Subcategoria', FALSE),
    ('Medicamento_Envolvido', FALSE),
    ('Gravidade', FALSE),
    ('Fatores_Causadores', FALSE),
    ('Descricao', FALSE),
    ('Acoes_Imediatas', FALSE),
    ('Sugestao_Melhoria', FALSE),
    ('Data_Relato', FALSE),
    ('Hora_Relato', FALSE),
    ('Nome_Paciente', FALSE),
    ('Data_Nascimento', FALSE),
    ('Relator', FALSE),
    ('Funcao_Relator', FALSE),
    ('Status', FALSE)
ON CONFLICT ("Campo") DO NOTHING;
