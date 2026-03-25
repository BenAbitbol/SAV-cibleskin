-- Executer ce script dans l'editeur SQL de Supabase (supabase.com > SQL Editor)
-- ⚠️ Ce script nettoie tout et recree les tables + policies

-- Nettoyage complet
DROP TABLE IF EXISTS settings CASCADE;
DROP TABLE IF EXISTS knowledge_base CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS conversations CASCADE;
DROP TABLE IF EXISTS templates CASCADE;

-- Table settings
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Table base de savoir
CREATE TABLE knowledge_base (
    id SERIAL PRIMARY KEY,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    file_url TEXT,
    file_name TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Table produits
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    sku TEXT,
    price REAL,
    description TEXT,
    category TEXT,
    image_url TEXT,
    in_stock BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Table conversations
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    customer_name TEXT,
    customer_email TEXT,
    channel TEXT NOT NULL,
    category TEXT,
    customer_message TEXT NOT NULL,
    ai_response TEXT NOT NULL,
    context TEXT,
    status TEXT DEFAULT 'draft',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Table templates
CREATE TABLE templates (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    channel TEXT NOT NULL,
    category TEXT,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- DESACTIVER RLS (Row Level Security)
-- Necessaire pour que l'app puisse lire/ecrire
-- ============================================
ALTER TABLE settings DISABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_base DISABLE ROW LEVEL SECURITY;
ALTER TABLE products DISABLE ROW LEVEL SECURITY;
ALTER TABLE conversations DISABLE ROW LEVEL SECURITY;
ALTER TABLE templates DISABLE ROW LEVEL SECURITY;

-- ============================================
-- POLICIES pour le Storage (bucket "files")
-- ============================================
-- Si le bucket "files" est public, les lectures marchent.
-- Pour les uploads via anon key, il faut une policy INSERT :
CREATE POLICY "Allow public uploads" ON storage.objects
    FOR INSERT WITH CHECK (bucket_id = 'files');

CREATE POLICY "Allow public reads" ON storage.objects
    FOR SELECT USING (bucket_id = 'files');

CREATE POLICY "Allow public deletes" ON storage.objects
    FOR DELETE USING (bucket_id = 'files');
