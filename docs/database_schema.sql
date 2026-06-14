-- Esquema lógico do WikiDev
-- Baseado no núcleo do projeto: user, page e tag
-- e nas extensões necessárias para comentários, exemplos e linguagens.

CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    display_name VARCHAR(120) NOT NULL DEFAULT '',
    bio TEXT NOT NULL DEFAULT '',
    avatar_url TEXT NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE language (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(80) NOT NULL UNIQUE,
    slug VARCHAR(90) NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    official_url TEXT NOT NULL DEFAULT '',
    logo_url TEXT NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE tag (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE,
    slug VARCHAR(60) NOT NULL UNIQUE,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE page (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(200) NOT NULL,
    slug VARCHAR(220) NOT NULL UNIQUE,
    page_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    language_id INTEGER NULL REFERENCES language(id),
    author_id INTEGER NULL REFERENCES user(id),
    parent_page_id INTEGER NULL REFERENCES page(id),
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE page_tag (
    page_id INTEGER NOT NULL REFERENCES page(id),
    tag_id INTEGER NOT NULL REFERENCES tag(id),
    PRIMARY KEY (page_id, tag_id)
);

CREATE TABLE comment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id INTEGER NOT NULL REFERENCES page(id),
    author_id INTEGER NULL REFERENCES user(id),
    parent_comment_id INTEGER NULL REFERENCES comment(id),
    body TEXT NOT NULL DEFAULT '',
    is_deleted BOOLEAN NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE code_example (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id INTEGER NOT NULL REFERENCES page(id),
    author_id INTEGER NULL REFERENCES user(id),
    title VARCHAR(200) NOT NULL DEFAULT '',
    code TEXT NOT NULL DEFAULT '',
    explanation TEXT NOT NULL DEFAULT '',
    language_hint VARCHAR(50) NOT NULL DEFAULT '',
    is_public BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);
