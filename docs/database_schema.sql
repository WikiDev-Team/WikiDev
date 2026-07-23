-- Esquema lógico do WikiDev
-- Inclui autenticação, páginas, amizades e compartilhamento.

CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(255) NOT NULL,
    display_name VARCHAR(120) NOT NULL DEFAULT '',
    bio TEXT NOT NULL DEFAULT '',
    avatar_url TEXT NOT NULL DEFAULT '',
    hashed_password TEXT NOT NULL,
    token TEXT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE friendship (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requester_id INTEGER NOT NULL REFERENCES user(id),
    addressee_id INTEGER NOT NULL REFERENCES user(id),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    CONSTRAINT uq_friendship_direction UNIQUE (requester_id, addressee_id),
    CONSTRAINT ck_friendship_distinct_users CHECK (requester_id <> addressee_id)
);

CREATE TABLE language (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(80) NOT NULL,
    slug VARCHAR(90) NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    official_url TEXT NOT NULL DEFAULT '',
    logo_url TEXT NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE folder (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(150) NOT NULL,
    slug VARCHAR(170) NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    author_id INTEGER NULL REFERENCES user(id),
    parent_folder_id INTEGER NULL REFERENCES folder(id),
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE tag (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) NOT NULL,
    slug VARCHAR(60) NOT NULL UNIQUE,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE page (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(200) NOT NULL,
    slug VARCHAR(220) NOT NULL,
    page_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    visibility VARCHAR(20) NOT NULL DEFAULT 'PRIVATE',
    summary TEXT NOT NULL DEFAULT '',
    language_id INTEGER NULL REFERENCES language(id),
    author_id INTEGER NULL REFERENCES user(id),
    parent_page_id INTEGER NULL REFERENCES page(id),
    folder_id INTEGER NULL REFERENCES folder(id),
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE page_share (
    page_id INTEGER NOT NULL REFERENCES page(id),
    user_id INTEGER NOT NULL REFERENCES user(id),
    permission VARCHAR(20) NOT NULL DEFAULT 'VIEW',
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (page_id, user_id)
);

CREATE TABLE page_tag_link (
    page_id INTEGER NOT NULL REFERENCES page(id),
    tag_id INTEGER NOT NULL REFERENCES tag(id),
    PRIMARY KEY (page_id, tag_id)
);

CREATE TABLE page_block (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id INTEGER NOT NULL REFERENCES page(id),
    position INTEGER NOT NULL DEFAULT 0,
    block_type VARCHAR(20) NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    language VARCHAR(50) NOT NULL DEFAULT '',
    font_size VARCHAR(20) NOT NULL DEFAULT 'normal',
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE comment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id INTEGER NOT NULL REFERENCES page(id),
    author_id INTEGER NOT NULL REFERENCES user(id),
    block_id INTEGER NULL REFERENCES pageblock(id),
    parent_comment_id INTEGER NULL REFERENCES comment(id),
    body TEXT NOT NULL,
    code TEXT NULL,
    language VARCHAR(20) NULL,
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
