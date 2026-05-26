-- Migração para atualizar o esquema de incidentes e criar as flags de obrigatoriedade

-- 1) Criar tabela de flags de campo se ainda não existir
CREATE TABLE IF NOT EXISTS config_campos (
    id BIGSERIAL PRIMARY KEY,
    "Campo" TEXT UNIQUE NOT NULL,
    "Obrigatorio" BOOLEAN NOT NULL DEFAULT FALSE
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
END$$;

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
